# Corruption and Idempotent Repair Report

The same fixed evaluation set was used for all three states.

| Metric / Chỉ số | Baseline (Dữ liệu Sạch) | Corrupted (Dữ liệu Bị Lỗi) | Repaired (Sau Khi Phục Hồi) |
|---|---:|---:|---:|
| `retrieval_hit_rate` | 1.0 | 0.6 | 1.0 |
| `mean_token_f1` | 1.0 | 0.7787878787878788 | 1.0 |
| `judge_accuracy` | 1.0 | 0.8 | 1.0 |
| `mean_judge_score` | 5 | 4.1 | 5 |
| Data Quality Gate | PASSED (True) | FAILED (False) | PASSED (True) |
| Freshness SLA | Đạt chuẩn (True) | Vi phạm cảnh báo (>180 ngày) (False) | Đạt chuẩn (True) |

## Observed impact

- Corruption introduced missing summaries, noisy text, truncated titles, stale dates, missing recent papers, and duplicate document IDs.
- The quality gate detects structural violations while freshness separately detects an excessive stale-record ratio.
- Repair rebuilds the dataset and vector collection from preserved raw records, so repeated repair runs converge to the same clean state.
