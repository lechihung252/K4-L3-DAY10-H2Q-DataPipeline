from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_dataframe
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _log(step: str, message: str) -> None:
    print(f"[corruption-flow] {step}: {message}")


def _require(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Run `python script/run_phase1.py` first.")


def check_data(df: pd.DataFrame, settings: Settings, state: str) -> tuple[dict[str, Any], dict[str, Any]]:
    quality = run_data_quality_checks(df, settings, state)
    freshness = build_freshness_report(df, settings, settings.paths.quality_dir / f"freshness_report_{state}.json")
    _log(f"{state}-quality", f"success={quality['success']}, is_fresh={freshness['is_fresh']}")
    return quality, freshness


def index_and_evaluate(
    df: pd.DataFrame,
    settings: Settings,
    embeddings_path: Path,
    metrics_path: Path,
    answers_path: Path,
    state: str,
) -> dict[str, Any]:
    # Cung test set voi baseline de 3 trang thai so sanh duoc voi nhau.
    index = LocalEmbeddingIndex.build(df, settings, embeddings_path)
    metrics = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=metrics_path,
        answers_output_path=answers_path,
    ).summary
    _log(
        f"{state}-eval",
        f"collection='{index.collection_name}', docs={len(index.documents)}, "
        f"hit_rate={metrics['retrieval_hit_rate']:.3f}, token_f1={metrics['mean_token_f1']:.3f}",
    )
    return metrics


def repair_from_raw(settings: Settings) -> pd.DataFrame:
    """Idempotent repair: bo qua data dang hong, tai tao lai tu raw snapshot bat bien."""
    records = load_raw_records(settings.paths.raw_records_json)
    return build_clean_dataframe(records, now_utc())


def main() -> None:
    settings = load_settings()
    paths = settings.paths
    for required in (paths.clean_json, paths.baseline_metrics, paths.eval_testset, paths.raw_records_json):
        _require(required)

    baseline_metrics = read_json(paths.baseline_metrics)
    clean_df = pd.read_json(paths.clean_json, orient="records", dtype=False, convert_dates=False)
    _log("load", f"{len(clean_df)} clean rows, baseline hit_rate={baseline_metrics['retrieval_hit_rate']:.3f}")

    # --- Corrupted: mo phong production KHONG co quality gate -> data xau van vao index (silent failure).
    corrupted_df = corrupt_clean_dataframe(clean_df.copy(), paths.corruption_log)
    write_dataframe(corrupted_df, paths.corrupted_clean_csv, paths.corrupted_clean_json)
    _log("corrupt", f"{len(clean_df)} -> {len(corrupted_df)} rows, log -> {paths.corruption_log}")

    corrupted_quality, corrupted_freshness = check_data(corrupted_df, settings, "corrupted")
    if corrupted_quality["success"]:
        _log("corrupted-quality", "WARNING: quality gate did NOT detect the corruption")
    corrupted_metrics = index_and_evaluate(
        corrupted_df,
        settings,
        paths.corrupted_embeddings_json,
        paths.corrupted_metrics,
        paths.corrupted_answers,
        "corrupted",
    )

    # --- Repaired: tai tao tu raw, quality gate phai pass truoc khi index.
    repaired_df = repair_from_raw(settings)
    write_dataframe(repaired_df, paths.repaired_clean_csv, paths.repaired_clean_json)
    same_as_baseline = repaired_df["text_for_embedding"].tolist() == clean_df["text_for_embedding"].tolist()
    _log("repair", f"{len(repaired_df)} rows rebuilt from raw, identical_to_baseline={same_as_baseline}")

    repaired_quality, repaired_freshness = check_data(repaired_df, settings, "repaired")
    if not repaired_quality["success"]:
        raise RuntimeError(f"Repaired data still fails the quality gate. See {paths.quality_dir}.")
    repaired_metrics = index_and_evaluate(
        repaired_df,
        settings,
        paths.repaired_embeddings_json,
        paths.repaired_metrics,
        paths.repaired_answers,
        "repaired",
    )

    generate_corruption_report(
        paths.comparison_report,
        baseline_metrics,
        corrupted_metrics,
        repaired_metrics,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
    )
    _log("report", f"{paths.comparison_report}")
