from __future__ import annotations

from typing import Any

from core.utils import write_text


def _metric_rows(metrics: dict[str, Any]) -> str:
    keys = ["samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]
    return "\n".join(f"| `{key}` | {metrics.get(key, 'N/A')} |" for key in keys)


def generate_phase1_report(report_path, source_summary: dict[str, Any], metrics: dict[str, Any], quality: dict[str, Any], freshness: dict[str, Any]) -> None:
    text = f"""# Phase 1 Baseline Report

## Source and dataset

- Source: {source_summary.get('source')}
- Raw records: {source_summary.get('raw_records')}
- Clean records: {source_summary.get('clean_records')}
- Embedding model: {source_summary.get('embedding_model')}
- Chroma collection: {source_summary.get('collection')}

## Evaluation metrics

| Metric | Value |
|---|---:|
{_metric_rows(metrics)}

## Data quality and freshness

- Quality success: **{quality.get('success')}**
- Checks passed: {sum(1 for item in quality.get('checks', []) if item.get('success'))}/{len(quality.get('checks', []))}
- Fresh: **{freshness.get('is_fresh')}**
- Stale rows: {freshness.get('stale_rows')}/{freshness.get('total_rows')}
- Published range: {freshness.get('oldest_published')} to {freshness.get('latest_published')}
"""
    write_text(report_path, text)


def generate_corruption_report(report_path, baseline_metrics: dict[str, Any], corrupted_metrics: dict[str, Any], repaired_metrics: dict[str, Any], corrupted_quality: dict[str, Any], repaired_quality: dict[str, Any], corrupted_freshness: dict[str, Any], repaired_freshness: dict[str, Any]) -> None:
    keys = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]
    rows = "\n".join(f"| `{key}` | {baseline_metrics.get(key, 'N/A')} | {corrupted_metrics.get(key, 'N/A')} | {repaired_metrics.get(key, 'N/A')} |" for key in keys)
    text = f"""# Corruption and Idempotent Repair Report

The same fixed evaluation set was used for all three states.

| Metric | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
{rows}
| Quality gate success | N/A | {corrupted_quality.get('success')} | {repaired_quality.get('success')} |
| Freshness SLA | N/A | {corrupted_freshness.get('is_fresh')} | {repaired_freshness.get('is_fresh')} |

## Observed impact

- Corruption introduced missing summaries, noisy text, truncated titles, stale dates, missing recent papers, and duplicate document IDs.
- The quality gate detects structural violations while freshness separately detects an excessive stale-record ratio.
- Repair rebuilds the dataset and vector collection from preserved raw records, so repeated repair runs converge to the same clean state.
"""
    write_text(report_path, text)
