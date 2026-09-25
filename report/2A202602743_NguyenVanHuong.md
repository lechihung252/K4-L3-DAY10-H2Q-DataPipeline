# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Nguyễn Văn Hưởng |
| MSSV | 2A202602743 |
| Khóa/Lớp | K4 |
| Tên nhóm | H2Q |
| Vai trò chính | TV2 — Data Foundation: thu thập, làm sạch và tiêm lỗi dữ liệu |
| Repository | https://github.com/lechihung252/K4-L3-DAY10-H2Q-DataPipeline |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
|---|---|---|---|---|
| Crossref ingestion và raw lineage | `src/ingestion/crossref.py`: `parse_crossref_payload`, `fetch_source_records`, `load_raw_records` | Crossref API hoặc `data/raw/crossref_response.json` | `list[PaperRecord]`, `data/raw/crossref_records.json` | Hoàn thành |
| Chuẩn hóa dữ liệu trước embedding | `src/ingestion/cleaning.py`: `build_clean_dataframe` | `list[PaperRecord]`, thời điểm chạy UTC | DataFrame sạch 24 dòng, đúng schema 11 cột | Hoàn thành |
| Synthetic data corruption | `src/ingestion/corruption.py`: `corrupt_clean_dataframe` | DataFrame baseline sạch | DataFrame corrupted và `corruption_log.json` ghi đủ 6 lỗi | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
|---|---|---|
| Kiểm tra contract tích hợp | TV1 — `phase1.py`, `corruption_flow.py`, `LocalEmbeddingIndex` | Xác nhận 24 clean rows có thể chuyển thành 24 Chroma documents; corrupted output có 22 rows |
| Kiểm tra chất lượng sau tích hợp | TV3 — quality, testset và reporting | Baseline quality/freshness đạt; corrupted quality/freshness bị cảnh báo đúng; testset đủ 10 câu |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
|---|---|---|---|
| Parse và bảo toàn dữ liệu Crossref | `src/ingestion/crossref.py`, `data/raw/` | 24 `PaperRecord`; retry khi gặp 429/503; fallback snapshot khi offline | Chạy `fetch_source_records(load_settings())` và kiểm tra số record bằng 24 |
| Chuẩn hóa schema và nội dung embedding | `src/ingestion/cleaning.py`, `data/clean/papers_clean.json` | 24 dòng, 11 cột, DOI unique; `text_for_embedding` đủ 5 phần | Đối chiếu clean JSON và baseline quality report |
| Tiêm lỗi có khả năng tái lập | `src/ingestion/corruption.py`, `data/results/corruption_log.json` | 6 loại lỗi: drop, blank, noise, truncate, stale, duplicate | Log ghi 6 events; corrupted quality `success=False` |

Các commit chính của cá nhân trên `main`:

- `8b524d2` — Crossref parsing, API retry, offline fallback và raw loading.
- `265f31b` — Làm sạch dữ liệu và xây dựng nội dung embedding.
- `c645dfb` — Tiêm sáu dạng lỗi dữ liệu theo cách deterministic.

Output cụ thể từ phần việc của tôi là DataFrame sạch 24 dòng với schema ổn định cho quality gate và vector index. Từ chính DataFrame này, corruption suite tạo 22 dòng lỗi và log có thể truy vết từng `paper_id` bị tác động.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Dữ liệu từ Crossref có cấu trúc lồng nhau, trường tùy chọn, JATS/XML trong abstract và nhiều định dạng ngày. Nếu đưa thẳng dữ liệu này vào embedding, record thiếu hoặc trùng có thể làm vector index sai. Pipeline cũng cần một bộ lỗi có kiểm soát để chứng minh quality gate phát hiện được silent failure và repair có thể tái tạo dữ liệu sạch từ raw snapshot.

### Cách triển khai

Ở ingestion, tôi ánh xạ DOI, title, abstract, author, subject, date và URL thành `PaperRecord`; loại record thiếu DOI/title/summary/ngày và khử DOI trùng. Chế độ mặc định dùng snapshot để chạy ổn định; khi bật `REFRESH_SOURCE`, API được gọi với timeout, retry tối đa ba lần cho 429/503 và fallback về snapshot nếu nguồn ngoài không khả dụng.

Ở cleaning, text được bỏ markup, decode HTML entity và chuẩn hóa khoảng trắng. Ngày được chuyển về ISO `YYYY-MM-DD`; `age_days` được tính theo thời điểm chạy UTC. Record lỗi và DOI trùng bị loại, sau đó tạo `authors_joined`, `categories_joined`, `summary_chars` và nội dung embedding gồm Title, Authors, Published, Categories, Summary.

Ở corruption, tôi sao chép sâu DataFrame đầu vào rồi chọn row theo thứ tự xác định. Bộ lỗi bỏ 20% bản ghi mới nhất, làm rỗng summary, chèn noise, cắt title dưới tám ký tự, lùi ngày 365 ngày và thêm row trùng. Sau thay đổi, `age_days`, `summary_chars` và `text_for_embedding` được dựng lại để lỗi thực sự đi vào quality check và vector index.

### Input, output và contract

| Thành phần | Mô tả |
|---|---|
| Input | Crossref payload hoặc raw JSON; `list[PaperRecord]`; DataFrame sạch khi chạy corruption |
| Output | `list[PaperRecord]`; DataFrame với 11 cột; corruption log chứa type, count, paper IDs và description |
| Module phụ thuộc | `core.config.Settings`, `core.utils`, `requests`, `pandas` |
| Module sử dụng output | `phase1.py`, `corruption_flow.py`, quality/freshness, testset và `LocalEmbeddingIndex` |
| Điều kiện lỗi cần xử lý | 429/503, mất mạng, JSON/schema sai, ngày không hợp lệ, record thiếu, DOI trùng và dataset quá nhỏ để tiêm đủ lỗi |

Schema DataFrame bàn giao:

```text
paper_id, title, summary, published, authors_joined, categories_joined,
abs_url, pdf_url, text_for_embedding, age_days, summary_chars
```

### Cách xác minh

```bash
.venv/bin/python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); print(len(fetch_source_records(s)))"
.venv/bin/python script/run_phase1.py
.venv/bin/python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** 24 raw/clean records; baseline pass; corrupted bị phát hiện; repaired trở lại trạng thái baseline.
- **Kết quả thực tế:** Baseline có 24 rows, corrupted có 22 rows, repaired có 24 rows. Baseline và repaired quality pass; corrupted quality fail.
- **Artifact/log:** `data/raw/`, `data/clean/`, `data/results/corruption_log.json`, `data/quality/` và `data/reports/`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Nếu chọn ngẫu nhiên các row để corruption, mỗi lần chạy có thể cho metrics khác nhau và rất khó so sánh baseline/corrupted/repaired.
- **Các phương án đã cân nhắc:** Chọn ngẫu nhiên không seed; random có seed; hoặc chọn deterministic theo thứ tự ngày/index.
- **Phương án đã chọn:** Chọn deterministic theo ngày và vị trí row, đồng thời tách nhóm row cho các lỗi khi dữ liệu đủ lớn.
- **Lý do:** Kết quả tái lập, log dễ đối chiếu, thuận lợi debug và bảo đảm phép so sánh ba trạng thái công bằng.
- **Bằng chứng quyết định phù hợp:** Hai lần gọi corruption với cùng input tạo DataFrame giống nhau; full run tạo ổn định 5 drop, 3 blank, 3 noise, 3 truncated title, 6 stale date và 3 duplicate rows.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ModuleNotFoundError: No module named 'pandas'` khi chạy kiểm tra bằng Python hệ thống.
- **Lệnh hoặc bước tái hiện:** Chạy lệnh kiểm tra với `python3` ngoài virtual environment.
- **Nguyên nhân gốc:** Interpreter hệ thống không dùng môi trường `.venv` đã cài dependencies của dự án.
- **Cách xử lý:** Chuyển sang `.venv/bin/python` và giữ package ở editable environment của dự án.
- **Cách xác minh sau khi sửa:** Import `pandas`, chạy parse/load 24 records, build DataFrame `(24, 11)` và thực thi quality checks thành công.
- **Điều học được:** Luôn kiểm tra interpreter đang dùng trước khi kết luận lỗi nằm trong source code.

## 7. Hiểu biết về luồng end-to-end

1. Crossref payload được giữ nguyên ở raw snapshot, parse thành `PaperRecord`, làm sạch thành DataFrame 11 cột và đi qua quality/freshness gate. Khi đạt yêu cầu, `text_for_embedding` được MiniLM biến thành vector và lưu trong ChromaDB.
2. Mỗi câu hỏi evaluation có `ground_truth` và `ground_truth_doc_ids`. IDs dùng để tính retrieval hit; ground truth dùng để tính token F1 và làm tham chiếu cho LLM judge.
3. Quality checks kiểm tra cấu trúc/nội dung như số dòng, null, unique và độ dài summary. Freshness monitoring kiểm tra tuổi dữ liệu và tỷ lệ record vượt SLA 180 ngày. Dữ liệu có thể đúng schema nhưng vẫn quá cũ.
4. Ba trạng thái phải dùng cùng test set để thay đổi metric phản ánh thay đổi dữ liệu, không phải do đổi câu hỏi đánh giá.
5. Repair thành công khi dữ liệu được dựng lại từ raw snapshot, quality/freshness pass và metrics trở về baseline. Full run cho repaired Hit Rate, Token F1 và Judge Accuracy đều bằng `1.0`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
|---|---:|---:|---:|---|
| `retrieval_hit_rate` | 1.0 | 0.6 | 1.0 | Mất 40 điểm phần trăm khi dữ liệu lỗi và phục hồi hoàn toàn sau repair |
| `mean_token_f1` | 1.0 | 0.7788 | 1.0 | Nội dung lỗi làm giảm độ khớp câu trả lời; repair trả lại mức ban đầu |
| `judge_accuracy` | 1.0 | 0.8 | 1.0 | Hai trên mười câu không còn được judge đánh giá đúng ở trạng thái corrupted |
| `mean_judge_score` | 5.0 | 4.1 | 5.0 | Chất lượng trung bình giảm 0.9 điểm rồi phục hồi |
| Quality checks | Passed | Failed | Passed | Duplicate ID và summary rỗng bị quality gate phát hiện |
| Freshness status | True (1/24 stale) | False (8/22 stale) | True (1/24 stale) | Corrupted stale ratio 36.36%, vượt SLA tối đa 25% |

### Kết luận từ số liệu

1. Sáu dạng corruption làm row count đổi từ 24 xuống 22, tạo duplicate/summary rỗng và tăng stale rows từ 1 lên 8 → quality và freshness cùng fail → Hit Rate giảm từ 1.0 xuống 0.6, Token F1 còn 0.7788.
2. Repair đọc lại raw snapshot và chạy cleaning idempotent → dữ liệu trở lại 24 rows, quality/freshness pass → toàn bộ metrics trở về đúng baseline.

`drop_latest_records` ảnh hưởng trực tiếp và rõ nhất tới retrieval: 5 tài liệu mới nhất bị bỏ, trong đó 4 DOI là ground-truth của các câu `eval_002`, `eval_004`, `eval_007`, `eval_008`. Khi tài liệu đích không còn trong index, retrieval không thể hit đúng tài liệu. Các lỗi stale/noise/duplicate vẫn quan trọng cho observability, nhưng không phải tất cả đều tác động trực tiếp đến câu hỏi trong test set.

Kết quả khác kỳ vọng là hệ thống không sụp đổ hoàn toàn: Token F1 vẫn đạt 0.7788 và Judge Accuracy đạt 0.8. Nguyên nhân là một phần test set vẫn trỏ tới tài liệu không bị xóa hoặc chỉ bị lỗi metadata; embedding/retrieval vẫn tìm được ngữ cảnh đủ dùng cho các câu còn lại. Tôi kiểm tra giả thuyết bằng cách đối chiếu từng `ground_truth_doc_ids` với các `paper_ids` trong corruption log.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Raw snapshot và data contract ổn định giúp pipeline có lineage rõ ràng và repair có thể chạy lặp lại mà không sửa tay.
2. Data quality và freshness giải quyết hai loại rủi ro khác nhau; chỉ kiểm tra schema là chưa đủ để phát hiện dữ liệu cũ.
3. RAG có thể vẫn trả lời trôi chảy khi corpus bị lỗi, nên phải đo retrieval/answer metrics và quan sát dữ liệu để phát hiện silent failure.

### Nếu có thêm thời gian

Tôi sẽ bổ sung pytest tham số hóa cho từng corruption riêng biệt, đo metric sau từng lỗi thay vì chỉ đo cả suite. Cách này xác định chính xác mức ảnh hưởng của drop, blank, noise, truncate, stale và duplicate, đồng thời giúp đặt threshold quality dựa trên bằng chứng.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Văn Hưởng

**Ngày xác nhận:** 2026-09-25
