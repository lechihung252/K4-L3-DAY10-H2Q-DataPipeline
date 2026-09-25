from __future__ import annotations

from datetime import datetime
from html import unescape
import re
from typing import Any

import pandas as pd

from ingestion.crossref import PaperRecord


CLEAN_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "published",
    "authors_joined",
    "categories_joined",
    "abs_url",
    "pdf_url",
    "text_for_embedding",
    "age_days",
    "summary_chars",
]


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Transform raw records into the stable schema consumed by the RAG flow."""
    if not isinstance(run_date, datetime):
        raise TypeError("run_date must be a datetime instance.")

    run_timestamp = pd.Timestamp(run_date)
    if run_timestamp.tzinfo is None:
        run_timestamp = run_timestamp.tz_localize("UTC")
    else:
        run_timestamp = run_timestamp.tz_convert("UTC")
    run_timestamp = run_timestamp.normalize()

    rows: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, PaperRecord):
            raise TypeError("records must contain only PaperRecord instances.")

        paper_id = normalize_text(record.paper_id)
        title = normalize_text(record.title, strip_markup=True)
        summary = normalize_text(record.summary, strip_markup=True)
        authors = normalize_string_list(record.authors)
        categories = normalize_string_list(record.categories)
        published_timestamp = pd.to_datetime(record.published, errors="coerce", utc=True)
        updated_timestamp = pd.to_datetime(record.updated, errors="coerce", utc=True)

        if not paper_id or not title or not summary or pd.isna(published_timestamp):
            continue

        authors_joined = ", ".join(authors)
        categories_joined = ", ".join(categories)
        published = published_timestamp.date().isoformat()
        age_days = int((run_timestamp - published_timestamp.normalize()).days)

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "published": published,
                "updated": (
                    updated_timestamp.date().isoformat()
                    if not pd.isna(updated_timestamp)
                    else published
                ),
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "abs_url": normalize_text(record.abs_url),
                "pdf_url": normalize_text(record.pdf_url),
                "text_for_embedding": build_embedding_text(
                    title=title,
                    authors_joined=authors_joined,
                    published=published,
                    categories_joined=categories_joined,
                    summary=summary,
                ),
                "age_days": age_days,
                "summary_chars": len(summary),
            }
        )

    if not rows:
        return pd.DataFrame(columns=CLEAN_COLUMNS)

    dataframe = pd.DataFrame(rows)
    # Prefer the most recently updated copy when a DOI occurs more than once.
    dataframe = dataframe.sort_values(
        ["updated", "paper_id"],
        ascending=[False, True],
        kind="stable",
    )
    dataframe = dataframe.drop_duplicates(subset=["paper_id"], keep="first")
    dataframe = dataframe.sort_values(
        ["published", "paper_id"],
        ascending=[False, True],
        kind="stable",
    ).reset_index(drop=True)
    return dataframe.loc[:, CLEAN_COLUMNS]


def normalize_text(value: Any, *, strip_markup: bool = False) -> str:
    """Normalize human-readable text without changing its letter casing."""
    if value is None:
        return ""
    text = str(value)
    if strip_markup:
        text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def normalize_string_list(values: Any) -> list[str]:
    """Clean a list while preserving order and removing repeated values."""
    if not isinstance(values, (list, tuple)):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = normalize_text(value, strip_markup=True)
        key = cleaned.casefold()
        if cleaned and key not in seen:
            result.append(cleaned)
            seen.add(key)
    return result


def build_embedding_text(
    *,
    title: str,
    authors_joined: str,
    published: str,
    categories_joined: str,
    summary: str,
) -> str:
    """Build the five-part document text expected by the embedding index."""
    return "\n".join(
        [
            f"Title: {title}",
            f"Authors: {authors_joined}",
            f"Published: {published}",
            f"Categories: {categories_joined}",
            f"Summary: {summary}",
        ]
    )
