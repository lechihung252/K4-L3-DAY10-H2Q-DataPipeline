# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4              |
| Tên nhóm         | H2Q     |
| Repository         | https://github.com/lechihung252/K4-L3A-Day10-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-25               |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Lê Chí Hùng | 2A202602863 | Trưởng nhóm — Pipeline Integrator & RAG | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `src/core/`, `src/retrieval/` (tích hợp), toàn bộ artifact trong `data/` (trừ `data/raw/`), báo cáo nhóm |
| 2 | Nguyễn Văn Hưởng | 2A202602743 | Data Foundation — Ingestion, Cleaning, Corruption | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/ingestion/corruption.py`, `data/raw/` |
| 3 | Lê Duy Quân | 2A202602731 | Observability & Evaluation | `src/observability/quality.py`, `src/observability/reporting.py`, `src/evaluation/testset.py` |

## 2. Tóm tắt kết quả

**Tóm tắt của nhóm:**

Nhóm hoàn thành đủ 7 tầng của pipeline: thu thập 24 bài báo từ Crossref (retry 429/503, fallback về snapshot offline), làm sạch thành 11 cột theo data contract chung, kiểm định bằng Great Expectations 1.x (6 expectation) và freshness SLA, index vào ChromaDB bằng `all-MiniLM-L6-v2`, và đánh giá trên bộ test 10 câu với Gemini `gemini-2.5-flash` làm LLM judge. Baseline sinh đủ artifact (`papers_clean.*`, `test_set.json`, `baseline_metrics.json`, `phase1_report.md`) và đạt tối đa: hit rate 1.0, token F1 1.0, judge accuracy 1.0.

Khi tiêm 6 loại lỗi (24 → 22 dòng), quality gate chuyển sang fail (trùng `paper_id`, `summary` rỗng), freshness chuyển sang stale (36% bài quá 180 ngày), còn agent vẫn trả lời bình thường nhưng hit rate giảm còn 0.6, token F1 0.779, judge accuracy 0.8 — đúng hiện tượng silent failure. Lỗi ảnh hưởng rõ nhất là `drop_latest_records`: 4/10 câu hỏi nhắm vào bài bị mất, cả 4 đều không retrieve được tài liệu đúng, 2 câu hỏi ngày xuất bản trả lời sai hoàn toàn. Repair tái tạo dữ liệu từ raw snapshot, cho kết quả trùng từng dòng với baseline (`identical_to_baseline=True`), qua lại quality gate và freshness, và phục hồi toàn bộ 4 metric về 1.0.

Giới hạn chính: test set chỉ 10 câu và lấy từ 10 bài đầu theo DOI, nên các lỗi `blank_summary`, `truncate_title`, `inject_noise` không rơi vào bài nào được hỏi và không thể hiện trên metric; `inject_noise` và `truncate_title` cũng không bị quality gate hiện tại bắt.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API (hoặc snapshot offline data/raw/crossref_response.json)
    -> raw response + raw records (data/raw/)                     [lineage, bất biến]
    -> cleaning & data modeling (data/clean/papers_clean.*)
    -> QUALITY GATE: GX 1.x + freshness (data/quality/)            [fail => dừng, không index]
    -> embedding MiniLM + ChromaDB 'papers-baseline'
    -> test set (tạo 1 lần) + evaluation baseline
    -> phase1_report.md
    -> corruption (6 lỗi) -> quality check (kỳ vọng fail) -> index 'papers-corrupted' -> evaluate
    -> repair: đọc lại raw -> clean lại -> quality gate (bắt buộc pass) -> index 'papers-repaired' -> evaluate
    -> corruption_report.md (so sánh 3 trạng thái)
```

Khác với thứ tự trong pseudo-code của starter (quality check chạy sau evaluate), nhóm đặt quality gate **trước** bước index để dữ liệu xấu không vào được vector store. Riêng trạng thái corrupted, gate vẫn chạy và báo lỗi nhưng dữ liệu vẫn được cố ý index, để đo được hậu quả khi production không có gate.

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref REST API / snapshot | Gọi API, retry 429/503, fallback snapshot, parse DOI/title/abstract/authors/subject/dates/URLs, bỏ record thiếu trường bắt buộc hoặc trùng DOI | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | TV2 |
| Cleaning          | `list[PaperRecord]`, `run_date` | Chuẩn hóa text, bỏ markup, chuẩn hóa ngày, tính `age_days`, ghép `text_for_embedding`, khử trùng lặp | `data/clean/papers_clean.csv/json` | TV2 |
| Embedding/index   | Clean DataFrame | MiniLM 384 chiều, Chroma cosine, mỗi trạng thái 1 collection, build lại từ đầu mỗi lần chạy | `data/chroma/`, `data/embeddings/*.json` | TV1 (code có sẵn, tích hợp) |
| Evaluation        | Clean DataFrame, index | Test set 4 loại câu hỏi; hit rate, token F1, LLM judge | `data/eval/test_set.json`, `data/results/*_metrics.json` | TV3 (test set), TV1 (chạy) |
| Observability     | DataFrame từng trạng thái | GX 1.x expectations + freshness SLA | `data/quality/*_quality_report.json`, `freshness_report*.json` | TV3 |
| Corruption/repair | Clean DataFrame / raw records | 6 lỗi có tính tái lập; repair = tái tạo từ raw | `data/clean/papers_clean_{corrupted,repaired}.*`, `data/results/corruption_log.json` | TV2 (corruption), TV1 (repair flow) |
| Orchestration     | Tất cả các khối trên | Thứ tự chạy, quality gate, tách collection, report | `data/reports/*.md` | TV1 |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | `gemini`         |
| `LLM_MODEL`                | `gemini-2.5-flash`         |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2`         |
| Số lượng Crossref records | 24         |
| Retrieval`top_k`           | 4         |
| Freshness threshold          | 180 ngày; `is_fresh=False` khi > 25% số bài vượt ngưỡng         |
| Random seed, nếu có        | Không dùng random: corruption chọn dòng theo vị trí cố định nên mỗi lần chạy cho cùng kết quả         |

### Lệnh cài đặt

```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -e .
cp .env.example .env   # điền GOOGLE_API_KEY
```

### Lệnh chạy

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

Mặc định pipeline đọc snapshot offline. Đặt `REFRESH_SOURCE=1` để gọi Crossref API; `REFRESH_TEST_SET=1` để tạo lại test set.

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công | 2026-09-25 (~2 phút) | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow   | Thành công | 2026-09-25 (~8 phút, chủ yếu là lượt gọi Gemini judge) | `data/results/{corrupted,repaired}_metrics.json`, `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API `https://api.crossref.org/works` (chế độ mặc định: snapshot `data/raw/crossref_response.json`) |
| Query/filter                | query `agentic retrieval augmented generation large language model`; filter `from-pub-date:<hôm nay − 180 ngày>,has-abstract:true`; `rows=24` |
| Thời điểm lấy dữ liệu | Snapshot có sẵn trong starter repo |
| Số record nhận được    | 24 items → 24 records hợp lệ |
| Cơ chế retry/backoff      | Tối đa 3 lần với 429/503; đợi theo header `Retry-After` (giới hạn 1–10 giây), không có thì backoff 1s, 2s. Hết lượt retry hoặc lỗi mạng → đọc lại snapshot đã lưu |

### Raw và clean schema

Clean schema là data contract chung giữa 3 thành viên (`CLEAN_COLUMNS` trong `src/ingestion/cleaning.py`):

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id` | string (DOI) | Có | Document ID, dùng làm ground truth | Thiếu → bỏ record; trùng → giữ bản `updated` mới nhất |
| `title` | string | Có | Tiêu đề, cũng dùng để tra cứu chính xác trong QA | Thiếu → bỏ record |
| `summary` | string | Có | Abstract đã bỏ markup JATS/HTML | Thiếu → bỏ record |
| `published` | string `YYYY-MM-DD` | Có | Ngày xuất bản | Không parse được → bỏ record. Giữ dạng chuỗi vì Chroma metadata không nhận Timestamp |
| `authors_joined` | string | Có (có thể rỗng) | Tác giả nối bằng `", "` | Thiếu → `""` |
| `categories_joined` | string | Có (có thể rỗng) | Subject Crossref nối bằng `", "` | Thiếu → `""` |
| `abs_url`, `pdf_url` | string | Có | Link bài báo | Thiếu → `https://doi.org/<DOI>` |
| `text_for_embedding` | string | Có | Văn bản được nhúng | Luôn được tạo lại từ các cột khác |
| `age_days` | int | Có | Số ngày từ `published` đến `run_date` | Tính khi clean |
| `summary_chars` | int | Có | Độ dài summary | Tính khi clean |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Bỏ record thiếu `paper_id`/`title`/`summary`/ngày hợp lệ | Completeness, Validity | 0 | 24 records → 24 dòng |
| Khử trùng lặp theo DOI, giữ bản `updated` mới nhất | Uniqueness | 0 | `paper_id` không trùng |
| Bỏ tag markup JATS/HTML trong abstract, unescape HTML, gộp khoảng trắng | Consistency | 24 | So sánh raw và clean |
| Chuẩn hóa ngày về `YYYY-MM-DD` | Validity, Consistency | 24 | Cột `published` |
| Khử trùng lặp tác giả/subject trong cùng record | Uniqueness | 0 | `authors_joined` |

`text_for_embedding` gồm 5 dòng `Title`, `Authors`, `Published`, `Categories`, `Summary`, để câu hỏi về tác giả, ngày hoặc lĩnh vực đều khớp được về mặt ngữ nghĩa. Document ID là DOI. Chroma dùng `record_id = <DOI>::<vị trí>` để các dòng trùng ở trạng thái corrupted vẫn được index riêng. `age_days = (run_date − published).days`, với `run_date` tính theo UTC và làm tròn về 0 giờ.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 10 (3 summary, 3 authors, 2 date, 2 categories), lấy từ 10 bài đầu tiên theo thứ tự DOI |
| Các`question_type`                    | `summary`, `authors`, `date`, `categories`                  |
| Ground-truth document ID                 | DOI (`paper_id`) của bài được hỏi     |
| Embedding model                          | `all-MiniLM-L6-v2`, embedding đã chuẩn hóa                  |
| Vector store/collection                  | ChromaDB persistent `data/chroma/`, cosine; `papers-baseline` / `papers-corrupted` / `papers-repaired`                 |
| Retrieval`top_k`                       | 4                   |
| LLM provider/model                       | Gemini `gemini-2.5-flash` (dùng cho LLM judge và agent demo)                   |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` |

Test set được tạo một lần ở phase 1 và chỉ tạo lại khi đặt `REFRESH_TEST_SET=1`. Corruption flow luôn đọc lại đúng file đó. Nếu mỗi trạng thái dùng câu hỏi khác nhau thì chênh lệch metric có thể đến từ độ khó câu hỏi thay vì từ dữ liệu. Giữ nguyên test set giúp mọi thay đổi metric đều quy được về thay đổi của dữ liệu. Ground truth được sinh từ dữ liệu sạch, nên khi bài bị drop hoặc title bị cắt ngắn, câu hỏi về bài đó sẽ không còn retrieve được DOI đúng.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/`                          | Có | 24 items / 24 records |
| Cleaned dataset          | `data/clean/`                        | Có | 24 dòng; kèm bản `_corrupted` (22) và `_repaired` (24) |
| Embedding manifest/index | `data/embeddings/`, `data/chroma/`                   | Có | 3 collection: `papers-baseline` 24, `papers-corrupted` 22, `papers-repaired` 24 |
| Evaluation set           | `data/eval/`                         | Có | 10 câu |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | Kèm `baseline_answers.json`, `agent_demo_answers.json` |
| Quality/freshness        | `data/quality/`                      | Có | Quality + freshness cho cả 3 trạng thái |
| Baseline report          | `data/reports/phase1_report.md`      | Có | |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` |     1.000 | Cả 10 câu đều có DOI đúng trong top-4. Câu hỏi chứa title trong `'...'` nên `qa.py` tra cứu chính xác được |
| `mean_token_f1`      |     1.000 | Câu trả lời trích đúng trường metadata tương ứng với `ground_truth` |
| `judge_accuracy`     |     1.000 | Gemini chấm 10/10 đúng; không câu nào rơi vào heuristic fallback |
| `mean_judge_score`   |     5.0 | Điểm tối đa ở mọi câu |
| Ragas, nếu có        | N/A | Không bật `RUN_RAGAS=1` vì chạy chậm và tốn thêm lượt gọi LLM; hit rate, token F1 và LLM judge đã đủ để so sánh 3 trạng thái |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| `ExpectTableRowCountToBeBetween` | Completeness | 5–5000 dòng | Pass (24) | `data/quality/baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (`paper_id`, `title`, `text_for_embedding`) | Completeness | 0 null | Pass (3 check) | nt |
| `ExpectColumnValuesToBeUnique` (`paper_id`) | Uniqueness | Không trùng | Pass | nt |
| `ExpectColumnValueLengthsToBeBetween` (`summary`) | Validity | ≥ 30 ký tự | Pass (ngắn nhất 193 ký tự) | nt |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | Clean DataFrame (cột `published` / `age_days`) của từng trạng thái            |
| Timestamp mới nhất       | `published` mới nhất 2026-07-22, cũ nhất 2026-03-28                         |
| Ngưỡng freshness         | `age_days > 180` là stale; `is_fresh=False` khi > 25% số dòng stale                         |
| Trạng thái baseline      | Fresh (`is_fresh=True`)               |
| Lý do                     | 1/24 bài (4.2%) có `age_days > 180`, dưới ngưỡng 25% |

## 9. Corruption scenarios và repair

Số record bị tác động lấy từ `corruption_log.json`. Các dòng được chọn theo vị trí cố định nên số liệu giống nhau ở mọi lần chạy.

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| `drop_latest_records` | Bỏ 20% bài mới nhất (làm tròn lên) | 5 | Freshness xấu đi; số dòng giảm | Không expectation nào bắt được (row count 22 vẫn trong 5–5000). Gây hại lớn nhất: 4/10 câu mất tài liệu đúng | Tái tạo từ raw |
| `blank_summary` | Thay summary bằng `""` | 3 | Fail check độ dài `summary` | Bị bắt: `ExpectColumnValueLengthsToBeBetween(summary)` fail. Không bài nào trong test set bị ảnh hưởng | Tái tạo từ raw |
| `inject_noise` | Nối chuỗi rác `@@@ ### CORRUPTED_DATA !!! xqz_9831` vào summary | 3 | Khó phát hiện bằng check cấu trúc | Không bị bắt. Rơi vào 1 bài trong test set (`eval_010`) nhưng câu trả lời categories không đổi | Tái tạo từ raw |
| `truncate_title` | Cắt title còn 7 ký tự | 3 | Fail check độ dài title (nếu có) | Không bị bắt vì chưa có check độ dài title. Không bài nào trong test set bị ảnh hưởng | Tái tạo từ raw |
| `stale_date` | Lùi `published` 365 ngày, cộng 365 vào `age_days` | 6 | `is_fresh=False` (> 25% stale) | Bị bắt: 8/22 = 36% stale → `is_fresh=False`. 1 bài trong test set (`eval_001`) bị lùi ngày nhưng là câu hỏi summary nên không đổi | Tái tạo từ raw |
| `duplicate_rows` | Nhân bản 15% số dòng | 3 | Fail check unique `paper_id` | Bị bắt: `ExpectColumnValuesToBeUnique(paper_id)` fail. 3 bài trong test set bị nhân bản nhưng vẫn retrieve đúng | Tái tạo từ raw |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có — `input_rows` 24, `output_rows` 22, đủ 6 event
- Nhận xét: Log ghi `input_rows`, `output_rows` và với mỗi loại lỗi có `type`, `count`, danh sách `paper_ids` bị ảnh hưởng và mô tả, đủ để truy ngược câu hỏi nào bị ảnh hưởng bởi lỗi nào.

**Vì sao repair không chỉ che lỗi:** repair không sửa trên dữ liệu đã hỏng (ví dụ không xóa dòng trùng hay điền lại summary). Nó bỏ hẳn dữ liệu đó, đọc lại raw snapshot bất biến trong `data/raw/` rồi chạy lại đúng hàm cleaning của baseline. Dữ liệu repaired phải qua quality gate mới được index. Pipeline so sánh từng dòng `text_for_embedding` với baseline và in `identical_to_baseline=True`. Mỗi lần chạy đều xóa rồi tạo lại collection, nên chạy lại nhiều lần vẫn cho cùng kết quả (idempotent).

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   |    1.000 |     0.600 |    1.000 |                   −0.400 |            100% | 4 câu nhắm vào bài bị drop không retrieve được DOI đúng |
| `mean_token_f1`        |    1.000 |     0.779 |    1.000 |                   −0.221 |            100% | 2 câu date F1 = 0, 1 câu summary F1 = 0.79 |
| `judge_accuracy`       |    1.000 |     0.800 |    1.000 |                   −0.200 |            100% | 2 câu date bị Gemini chấm sai |
| `mean_judge_score`     |      5.0 |       4.1 |      5.0 |                     −0.9 |            100% | |
| Quality checks pass/fail |      6/6 |       4/6 |      6/6 |          −2 (unique, summary) |            100% | Gate phát hiện 2/6 loại lỗi trực tiếp |
| Freshness status         | Fresh (4.2% stale) | Stale (36.4%) | Fresh (4.2%) | Fresh → Stale | 100% | Freshness bắt được lỗi `stale_date` mà GX không bắt |

1. `drop_latest_records` xóa 5 bài mới nhất, trong đó có 4 bài được hỏi trong test set → quality gate **không** bắt được (22 dòng vẫn hợp lệ về cấu trúc), chỉ freshness thay đổi gián tiếp → hit rate giảm 1.0 → 0.6. Đáng chú ý: agent vẫn trả lời tự tin cho cả 4 câu; `eval_004` (authors) còn được chấm đúng dù retrieve sai bài, vì một bài khác trong corpus có cùng tác giả — đúng nhờ may mắn, chính là silent failure mà chỉ metric retrieval mới lộ ra.
2. Repair đọc lại `data/raw/crossref_records.json` và chạy lại đúng hàm cleaning → dữ liệu trùng khớp từng dòng với baseline (`identical_to_baseline=True`) → quality 6/6 và `is_fresh=True` → cả 4 metric về đúng 1.0. Chạy lại corruption flow nhiều lần cho cùng số liệu vì corruption chọn dòng theo vị trí cố định và mỗi lần build đều tạo lại collection từ đầu.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Các module được viết song song bởi 3 người, trong khi các lớp có sẵn (`retrieval/index.py`, `retrieval/qa.py`) có những ràng buộc ngầm không ghi trong docstring. Ví dụ: ChromaDB chỉ nhận metadata kiểu str/int/float/bool, nên cột `published` kiểu Timestamp hoặc ô NaN sẽ làm lỗi lúc index. `qa.py` chỉ trả đúng cột (tác giả, ngày, lĩnh vực) khi câu hỏi có từ khóa `who authored`, `when was`, `what categories` và tên bài nằm trong dấu `'...'`.
- **Nguyên nhân:** Hàm của từng module có sẵn trong starter nhưng schema dữ liệu truyền giữa các module thì không được quy định.
- **Cách xử lý:** Trưởng nhóm đọc code có sẵn trước khi ghép, chốt data contract trong `docs/PHAN_CONG.md` (11 cột bắt buộc, `published` là chuỗi, không NaN, key `success`/`is_fresh`, mẫu câu hỏi) và gửi cho từng người. Trước khi code thành viên xong, pipeline được chạy thử bằng bản giả của các hàm, ghi output ra thư mục riêng để kiểm tra phần ghép nối.
- **Cách xác minh:** Khi TV2 push code, cả 2 pipeline chạy được ngay với code thật mà không phải sửa: 24 dòng sạch; corrupted 22 dòng, quality `False`, freshness `False`; repaired `identical_to_baseline=True`.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Test set 10 câu lấy từ 10 bài đầu theo DOI | `blank_summary` và `truncate_title` không rơi vào bài nào được hỏi nên không thể hiện trên metric; mỗi câu chiếm 10% hit rate | Mỗi bài ≥ 1 câu hoặc chọn bài rải đều; kiểm tra bằng số loại corruption có ít nhất 1 câu hỏi bị ảnh hưởng (mục tiêu 6/6) |
| `inject_noise`, `truncate_title`, `drop_latest_records` không bị GX bắt | Nhiễu, title hỏng và mất bài mới vẫn lọt qua gate | Thêm `ExpectColumnValueLengthsToBeBetween(title, min 8)`, expectation regex trên `summary`, và so số dòng với lần ingest trước; đo bằng số loại lỗi gate bắt được (hiện 2/6 qua GX + 1 qua freshness) |
| `age_days` phụ thuộc ngày chạy, snapshot cố định | Chạy muộn hơn vài tháng thì baseline cũng thành stale | Lưu `run_date` vào report; freshness đo theo thời điểm ingest thay vì ngày chạy |
| Quality gate chỉ chạy khi chạy pipeline thủ công | Không tự phát hiện khi nguồn thay đổi | Chạy theo lịch, gate fail thì tự động repair và cảnh báo |

## 13. Checklist trước khi nộp

- [ ] Thông tin nhóm và repository chính xác.
- [ ] Phân công khớp với module, artifact và kết quả thực tế.
- [ ] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [ ] Baseline, corrupted và repaired dùng cùng evaluation set.
- [ ] Bảng metrics khớp với các file trong `data/results/`.
- [ ] Quality/freshness conclusions khớp với `data/quality/`.
- [ ] Các đường dẫn báo cáo và artifact truy cập được.
- [ ] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [ ] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
