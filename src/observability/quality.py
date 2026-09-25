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
    payload = {
        "report_name": report_name, "success": all(item["success"] for item in results),
        "row_count": len(df), "checks": results,
        "freshness": {"threshold_days": settings.freshness_threshold_days, "stale_rows": stale_rows, "total_rows": len(df), "stale_ratio": stale_ratio, "is_fresh": stale_ratio <= 0.25},
    }
    report_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"
    if report_name == "baseline":
        report_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        report_path = settings.paths.corrupted_quality_report
    write_json(report_path, payload)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path) -> dict[str, Any]:
    published = pd.to_datetime(df.get("published", pd.Series(dtype=str)), errors="coerce", utc=True)
    ages = pd.to_numeric(df.get("age_days", pd.Series(dtype=float)), errors="coerce")
    stale_rows = int((ages > settings.freshness_threshold_days).sum())
    total_rows = len(df)
    stale_ratio = stale_rows / total_rows if total_rows else 1.0
    payload = {
        "latest_published": published.max().date().isoformat() if published.notna().any() else None,
        "oldest_published": published.min().date().isoformat() if published.notna().any() else None,
        "freshness_threshold_days": settings.freshness_threshold_days,
        "stale_rows": stale_rows, "total_rows": total_rows, "stale_ratio": stale_ratio,
        "is_fresh": stale_ratio <= 0.25,
    }
    write_json(report_path, payload)
    return payload
