from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from core.utils import write_json
from ingestion.cleaning import CLEAN_COLUMNS, build_embedding_text


REQUIRED_COLUMNS = set(CLEAN_COLUMNS)
NOISE_TEXT = "@@@ ### CORRUPTED_DATA !!! xqz_9831"


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Inject six deterministic data failures into a clean dataframe.

    The input dataframe is never modified. Deterministic row selection keeps
    baseline/corrupted/repaired comparisons reproducible across repeated runs.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame.")

    missing_columns = sorted(REQUIRED_COLUMNS.difference(df.columns))
    if missing_columns:
        raise ValueError(f"Clean dataframe is missing required columns: {missing_columns}")
    if len(df) < 6:
        raise ValueError("At least 6 clean records are required to inject all corruption types.")

    corrupted = df.loc[:, CLEAN_COLUMNS].copy(deep=True)
    corrupted["published"] = pd.to_datetime(corrupted["published"], errors="coerce")
    if corrupted["published"].isna().any():
        raise ValueError("All published values must be valid dates before corruption.")

    input_rows = len(corrupted)
    events: list[dict[str, object]] = []

    # 1. Simulate a failed incremental ingestion by removing the newest 20%.
    latest_order = corrupted.sort_values("published", ascending=False, kind="stable").index
    drop_count = max(1, math.ceil(input_rows * 0.20))
    dropped_indices = list(latest_order[:drop_count])
    dropped_ids = corrupted.loc[dropped_indices, "paper_id"].astype(str).tolist()
    corrupted = corrupted.drop(index=dropped_indices).reset_index(drop=True)
    events.append(
        {
            "type": "drop_latest_records",
            "count": len(dropped_ids),
            "paper_ids": dropped_ids,
            "description": "Removed the newest 20% of source records.",
        }
    )

    corruption_size = max(1, math.ceil(len(corrupted) * 0.15))
    cursor = 0

    # 2. Empty abstracts emulate missing content returned by a crawler.
    blank_indices = _take_indices(corrupted, cursor, corruption_size)
    cursor += corruption_size
    corrupted.loc[blank_indices, "summary"] = ""
    events.append(_event("blank_summary", corrupted, blank_indices))

    # 3. Add a recognizable garbage token sequence to otherwise valid text.
    noise_indices = _take_indices(corrupted, cursor, corruption_size)
    cursor += corruption_size
    corrupted.loc[noise_indices, "summary"] = (
        corrupted.loc[noise_indices, "summary"].astype(str).str.cat(
            pd.Series([NOISE_TEXT] * len(noise_indices), index=noise_indices),
            sep=" ",
        )
    )
    events.append(_event("inject_noise", corrupted, noise_indices))

    # 4. Titles shorter than eight characters should trip title checks.
    title_indices = _take_indices(corrupted, cursor, corruption_size)
    cursor += corruption_size
    corrupted.loc[title_indices, "title"] = (
        corrupted.loc[title_indices, "title"].astype(str).str.slice(stop=7)
    )
    events.append(_event("truncate_title", corrupted, title_indices))

    # 5. Make enough rows stale to exceed the 25% freshness SLA threshold.
    stale_count = max(1, math.ceil(len(corrupted) * 0.30))
    stale_indices = _take_indices(corrupted, cursor, stale_count)
    corrupted.loc[stale_indices, "published"] = (
        corrupted.loc[stale_indices, "published"] - pd.Timedelta(days=365)
    )
    corrupted.loc[stale_indices, "age_days"] = (
        pd.to_numeric(corrupted.loc[stale_indices, "age_days"], errors="coerce").fillna(0).astype(int)
        + 365
    )
    events.append(_event("stale_date", corrupted, stale_indices))

    # Rebuild derived columns before duplication so duplicates are exact copies.
    corrupted["published"] = corrupted["published"].dt.strftime("%Y-%m-%d")
    corrupted["summary_chars"] = corrupted["summary"].astype(str).str.len()
    corrupted["text_for_embedding"] = corrupted.apply(_embedding_text_from_row, axis=1)

    # 6. Repeated paper IDs emulate an append-only index without deduplication.
    duplicate_count = max(1, math.ceil(len(corrupted) * 0.15))
    duplicate_indices = _take_indices(corrupted, len(corrupted) - duplicate_count, duplicate_count)
    duplicated_rows = corrupted.loc[duplicate_indices].copy(deep=True)
    duplicate_ids = duplicated_rows["paper_id"].astype(str).tolist()
    corrupted = pd.concat([corrupted, duplicated_rows], ignore_index=True)
    events.append(
        {
            "type": "duplicate_rows",
            "count": len(duplicate_ids),
            "paper_ids": duplicate_ids,
            "description": "Appended exact copies with repeated paper IDs.",
        }
    )

    corrupted = corrupted.loc[:, CLEAN_COLUMNS].reset_index(drop=True)
    log_payload = {
        "input_rows": input_rows,
        "output_rows": len(corrupted),
        "corruption_types": 6,
        "events": events,
    }
    write_json(Path(output_log_path), log_payload)
    return corrupted


def _take_indices(df: pd.DataFrame, start: int, count: int) -> list[int]:
    """Take deterministic positions, wrapping only when the dataset is small."""
    indices = list(df.index)
    return [indices[(start + offset) % len(indices)] for offset in range(count)]


def _event(event_type: str, df: pd.DataFrame, indices: list[int]) -> dict[str, object]:
    descriptions = {
        "blank_summary": "Replaced summaries with empty strings.",
        "inject_noise": "Injected garbage tokens into summaries.",
        "truncate_title": "Truncated titles to fewer than eight characters.",
        "stale_date": "Moved publication dates back by 365 days.",
    }
    return {
        "type": event_type,
        "count": len(indices),
        "paper_ids": df.loc[indices, "paper_id"].astype(str).tolist(),
        "description": descriptions[event_type],
    }


def _embedding_text_from_row(row: pd.Series) -> str:
    return build_embedding_text(
        title=str(row["title"]),
        authors_joined=str(row["authors_joined"]),
        published=str(row["published"]),
        categories_joined=str(row["categories_joined"]),
        summary=str(row["summary"]),
    )
