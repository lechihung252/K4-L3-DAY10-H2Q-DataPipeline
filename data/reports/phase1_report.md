# Phase 1 Baseline Report

## Source and dataset

- Source: Crossref REST API
- Raw records: 24
- Clean records: 24
- Embedding model: sentence-transformers/all-MiniLM-L6-v2
- Chroma collection: papers-baseline

## Evaluation metrics

| Metric | Value |
|---|---:|
| `samples` | 10 |
| `retrieval_hit_rate` | 1.0 |
| `mean_token_f1` | 1.0 |
| `judge_accuracy` | 1.0 |
| `mean_judge_score` | 5 |

## Data quality and freshness

- Quality success: **True**
- Checks passed: 6/6
- Fresh: **True**
- Stale rows: 1/24
- Published range: 2026-03-28 to 2026-07-22
