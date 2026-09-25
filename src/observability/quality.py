from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def _result_payload(result: Any) -> dict[str, Any]:
    data = result.to_json_dict() if hasattr(result, "to_json_dict") else dict(result)
    config = data.get("expectation_config", {})
    return {"success": bool(data.get("success", False)), "expectation": config.get("type") or config.get("expectation_type"), "kwargs": config.get("kwargs", {}), "result": data.get("result", {})}


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Execute Great Expectations 1.x data quality checks and freshness evaluation.

    Contract return keys:
    - success (bool): True if all GX expectations pass.
    - checks / results (list[dict]): Detailed results of each expectation.
    - row_count / total_rows (int): Total rows evaluated.
    - is_fresh (bool): True if stale row ratio is <= 25%.
    - stale_rows (int): Number of rows with age_days > threshold.
    - freshness (dict): Detailed freshness metrics (threshold_days, stale_rows, total_rows, stale_ratio, is_fresh).
    - report_name (str): Name of the report (e.g. 'baseline', 'corrupted', 'repaired').
    """
    import great_expectations as gx

    context = gx.get_context(mode="ephemeral")
    source = context.data_sources.add_pandas(name=f"papers_source_{report_name}")
    asset = source.add_dataframe_asset(name=f"papers_asset_{report_name}")
    batch_def = asset.add_batch_definition_whole_dataframe(f"papers_batch_{report_name}")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})
    expectations = [gx.expectations.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000)]
    expectations += [gx.expectations.ExpectColumnValuesToNotBeNull(column=column) for column in ["paper_id", "title", "text_for_embedding"]]
    expectations += [
        gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30),
    ]
    results = [_result_payload(batch.validate(expectation)) for expectation in expectations]
    stale_rows = int((pd.to_numeric(df["age_days"], errors="coerce") > settings.freshness_threshold_days).sum()) if len(df) else 0
    stale_ratio = stale_rows / len(df) if len(df) else 1.0
    is_fresh = stale_ratio <= 0.25
    payload = {
        "report_name": report_name,
        "success": all(item["success"] for item in results),
        "row_count": len(df),
        "total_rows": len(df),
        "checks": results,
        "results": results,
        "is_fresh": is_fresh,
        "stale_rows": stale_rows,
        "freshness": {
            "threshold_days": settings.freshness_threshold_days,
            "stale_rows": stale_rows,
            "total_rows": len(df),
            "stale_ratio": stale_ratio,
            "is_fresh": is_fresh,
        },
    }
    report_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"
    if report_name == "baseline":
        report_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        report_path = settings.paths.corrupted_quality_report
    write_json(report_path, payload)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path) -> dict[str, Any]:
    """Calculate data freshness metrics and persist to report_path.

    Contract return keys:
    - latest_published (str | None): ISO date of newest record.
    - oldest_published (str | None): ISO date of oldest record.
    - freshness_threshold_days (int): SLA freshness threshold in days.
    - stale_rows (int): Count of records exceeding threshold.
    - total_rows (int): Total records in dataframe.
    - stale_ratio (float): Ratio of stale records to total records.
    - is_fresh (bool): True if stale_ratio <= 25%.
    """
    published = pd.to_datetime(df.get("published", pd.Series(dtype=str)), errors="coerce", utc=True)
    ages = pd.to_numeric(df.get("age_days", pd.Series(dtype=float)), errors="coerce")
    stale_rows = int((ages > settings.freshness_threshold_days).sum())
    total_rows = len(df)
    stale_ratio = stale_rows / total_rows if total_rows else 1.0
    payload = {
        "latest_published": published.max().date().isoformat() if published.notna().any() else None,
        "oldest_published": published.min().date().isoformat() if published.notna().any() else None,
        "freshness_threshold_days": settings.freshness_threshold_days,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": stale_ratio,
        "is_fresh": stale_ratio <= 0.25,
    }
    write_json(report_path, payload)
    return payload
