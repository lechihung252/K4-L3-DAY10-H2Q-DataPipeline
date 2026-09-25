# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                                          |
| ------------------ | ---------------------------------------------------------------------------------- |
| Họ và tên       | Lê Duy Quân                                                                       |
| MSSV               | 2A202602731                                                                       |
| Khóa/Lớp         | K4                                                                                |
| Tên nhóm         | Nhóm 3 người — K4-L3A-Day10                                                       |
| Vai trò chính    | TV3: Data Observability & Benchmark Evaluation Lead                               |
| Repository         | https://github.com/lechihung252/K4-L3A-Day10-Data-Pipeline-Data-Observability.git |
| Ngày hoàn thành | 2026-09-25                                                                        |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| **Data Quality Gate & Freshness SLA** | `src/observability/quality.py`<br>- `run_data_quality_checks`<br>- `build_freshness_report` | `clean_df` (DataFrame pandas chứa 24 bài báo sau làm sạch), `Settings` cấu hình | Các file báo cáo chất lượng định dạng JSON:<br>- `data/quality/baseline_quality_report.json`<br>- `data/quality/corrupted_quality_report.json`<br>- `data/quality/freshness_report.json` | Hoàn thành |
| **Benchmark Evaluation Test Set** | `src/evaluation/testset.py`<br>- `build_test_set`<br>- `load_or_create_test_set` | `clean_df` (DataFrame dữ liệu sạch) | File JSON chứa bộ 10 câu hỏi chuẩn hóa kèm ground truth:<br>`data/eval/test_set.json` | Hoàn thành |
| **Observability Reporting** | `src/observability/reporting.py`<br>- `generate_phase1_report`<br>- `generate_corruption_report` | Metrics đánh giá (Hit Rate, Token F1), Quality Gate results, Freshness SLA results | 2 báo cáo Markdown hoàn chỉnh:<br>- `data/reports/phase1_report.md`<br>- `data/reports/corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| **Sửa lỗi ModuleNotFoundError thư viện `datasets`** | TV1 / `src/evaluation/metrics.py` | Đưa import `Dataset` vào khối lazy-load `try:` bên trong `_run_ragas`, giúp pipeline chạy offline ổn định khi không bật Ragas mà không bị sập. |
| **Hòa hợp hợp đồng dữ liệu (Data Contract)** | TV1 / `src/pipelines/phase1.py` & `src/observability/reporting.py` | Đồng bộ các key `source_api`, `clean_rows`, `collection_name` giữa pipeline và reporting, triệt tiêu hoàn toàn các trường bị `None` trong báo cáo markdown. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Thiết lập Data Quality Gate Great Expectations 1.x | `src/observability/quality.py` (`run_data_quality_checks`) | Báo cáo kiểm định 4 Expectations và tỉ lệ dữ liệu mốc | Lệnh kiểm tra Checkpoint 1 (in ra `Quality check status = True`) |
| Giám sát độ tươi mới dữ liệu Freshness SLA | `src/observability/quality.py` (`build_freshness_report`) | Báo cáo Freshness với ngưỡng cảnh báo `stale_ratio <= 0.25` | Kiểm tra file `data/quality/freshness_report.json` và `corrupted_freshness_report.json` |
| Xây dựng Benchmark Test Set 10 câu hỏi | `src/evaluation/testset.py` (`build_test_set`) | Bộ 10 câu hỏi cố định phủ đủ 4 dạng câu hỏi (`summary`, `authors`, `date`, `categories`) | Lệnh test Checkpoint 2 (in ra `Sinh được 10 câu hỏi test`) |
| Báo cáo Baseline và So sánh 3 trạng thái | `src/observability/reporting.py` | 2 bản báo cáo Markdown phân tích định lượng | Sinh ra file `data/reports/phase1_report.md` và `data/reports/corruption_report.md` |

### Output cụ thể tạo ra:
Bảng tổng hợp định lượng 3 trạng thái trong file `data/reports/corruption_report.md`:
- **Baseline**: Quality Gate `PASSED (True)`, Freshness SLA `Đạt chuẩn (True)`, Retrieval Hit Rate `1.000`, Token F1 `1.000`.
- **Corrupted**: Quality Gate `FAILED (False)`, Freshness SLA `Vi phạm cảnh báo (False)`, Retrieval Hit Rate tụt xuống `0.600`, Token F1 tụt xuống `0.779`.
- **Repaired**: Quality Gate phục hồi `PASSED (True)`, Freshness SLA `Đạt chuẩn (True)`, Retrieval Hit Rate phục hồi `1.000`, Token F1 phục hồi `1.000`.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. **Chặn đứng hiện tượng Silent Failure**: Trong hệ thống RAG thực tế, dữ liệu bẩn (null, tóm tắt rỗng, bài báo bị trùng DOI, ngày xuất bản cũ 5 năm trước) khi nạp vào Vector Database sẽ không gây ra Runtime Error, nhưng làm mô hình LLM bị ảo giác (hallucination) và trả lời sai. Cần một chốt kiểm soát tự động để chặn dữ liệu xấu ngay trước khi index.
2. **Thước đo đánh giá khách quan**: Cần một tập đề thi cố định (Benchmark Test Set) có ground truth và ground truth document IDs chuẩn xác để đo lường công bằng trước và sau khi tiêm lỗi.

### Cách triển khai
1. **Great Expectations 1.x (mode="ephemeral")**:
   - Sử dụng cú pháp mới `context = gx.get_context(mode="ephemeral")` chạy trực tiếp trên DataFrame trong bộ nhớ RAM, không sinh file cấu hình thừa.
   - Thêm Data Source (`add_pandas`), Data Asset (`add_dataframe_asset`), Batch Definition (`add_batch_definition_whole_dataframe`) và lấy Batch.
   - Thiết lập 4 Expectations bắt buộc:
     - `ExpectTableRowCountToBeBetween(min_value=5, max_value=5000)`: Kiểm tra độ đầy đủ bản ghi.
     - `ExpectColumnValuesToNotBeNull(column)` cho `paper_id`, `title`, `text_for_embedding`.
     - `ExpectColumnValuesToBeUnique(column="paper_id")`: Khóa duy nhất, cấm trùng lặp.
     - `ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30)`: Ngăn chặn tóm tắt rác/rỗng.
2. **Freshness SLA Monitoring**:
   - Tính toán số ngày tuổi `age_days = (now_utc - published).days`.
   - Đếm số bản ghi cũ quá 180 ngày (`stale_rows`). Tính tỉ lệ `stale_ratio = stale_rows / total_rows`.
   - Nếu `stale_ratio <= 0.25` thì đạt chuẩn (`is_fresh = True`), ngược lại cảnh báo dữ liệu cũ mốc.
3. **Bộ Benchmark 10 câu hỏi (`testset.py`)**:
   - Sắp xếp DataFrame theo `paper_id` cố định.
   - Trích xuất 10 câu hỏi phân bổ cân bằng: 3 câu hỏi `summary` (lấy `first_sentence`), 3 câu hỏi `authors` (`authors_joined`), 2 câu hỏi `date` (`published`), 2 câu hỏi `categories` (`categories_joined`).

### Input, output và contract

| Thành phần | Mô tả |
| ------------------------------ | ------------------------------------------- |
| **Input** | `df`: `pd.DataFrame` chứa các cột chuẩn `paper_id, title, summary, published, authors_joined, categories_joined, text_for_embedding, age_days`. `settings`: Chứa đường dẫn và tham số SLA. |
| **Output** | `run_data_quality_checks` trả về dict gồm: `success`, `row_count`, `checks`, `results`, `is_fresh`, `stale_rows`, `freshness`. Xuất file `*_quality_report.json`.<br>`build_test_set` trả về `TestSet` (list 10 dicts) và ghi vào `test_set.json`. |
| **Module phụ thuộc** | Nhận dữ liệu sạch từ `src/ingestion/cleaning.py` (TV2 phụ trách). |
| **Module sử dụng output** | `src/pipelines/phase1.py` (TV1) dùng `quality['success']` để quyết định có cho phép nạp ChromaDB không; `src/evaluation/metrics.py` đọc `test_set.json` để chấm điểm. |
| **Điều kiện lỗi cần xử lý** | DataFrame rỗng hoặc ít hơn 10 dòng, cột ngày tháng bị lỗi format, trường `summary` bị null/rỗng. |

### Cách xác minh

```bash
# 1. Xác minh Quality Gate GX 1.x:
python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); res=run_data_quality_checks(df, s, 'test'); print('Tín hiệu hoàn thành: Quality check status =', res['success'])"

# 2. Xác minh Bộ đề thi 10 câu hỏi:
python -c "from core.config import load_settings; from evaluation.testset import build_test_set; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); ts=build_test_set(df, s.paths.eval_testset); print(f'Tín hiệu hoàn thành: Sinh được {len(ts)} câu hỏi test')"
```

- **Kết quả mong đợi:** Lệnh 1 in ra `Quality check status = True`; Lệnh 2 in ra `Sinh được 10 câu hỏi test`.
- **Kết quả thực tế:** Cả 2 lệnh đều chạy thành công 100%, in đúng tín hiệu hoàn thành.
- **Artifact:** `data/quality/test_quality_report.json`, `data/eval/test_set.json`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương thức vận hành Great Expectations: Lưu cấu hình tĩnh (Context dạng File `great_expectations.yml`) hay Chạy động trên bộ nhớ (Ephemeral Context).
- **Các phương án đã cân nhắc:**
  1. *Phương án A*: Khởi tạo project GX chuẩn truyền thống (`great_expectations --init`), lưu file cấu hình vào thư mục `gx/`.
  2. *Phương án B*: Khởi tạo Ephemeral Context `gx.get_context(mode="ephemeral")` và nạp DataFrame trực tiếp qua Pandas Data Source.
- **Phương án đã chọn:** Phương án B (`mode="ephemeral"`).
- **Lý do:**
  - Chuẩn GX 1.x đã loại bỏ cơ chế cũ `context.sources.pandas_default`.
  - Giữ cho kho mã nguồn sạch sẽ, không phát sinh hàng loạt file metadata / JSON cache gây xung đột Git giữa 3 thành viên khi chạy song song.
  - Tốc độ thực thi trên RAM cực nhanh (< 1 giây), hoàn toàn phù hợp cho pipeline CI/CD và môi trường kiểm thử tự động.
- **Bằng chứng quyết định phù hợp:** Chạy lệnh kiểm tra bước 3 hoàn tất tức thì, kiểm tra đúng 6 expectation rules mà không tạo ra bất kỳ file rác nào trong workspace.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  ModuleNotFoundError: No module named 'datasets'
  Traceback: in src/evaluation/metrics.py, line 10: from datasets import Dataset
  ```
- **Lệnh hoặc bước tái hiện:** `python script/run_phase1.py` sau khi kéo code từ `origin/main`.
- **Nguyên nhân gốc:** Thư viện `datasets` (phục vụ Ragas evaluation) chỉ được dùng khi bật biến môi trường `RUN_RAGAS=1`. Tuy nhiên, câu lệnh import bị đặt ở top-level của module `src/evaluation/metrics.py`, dẫn đến việc môi trường lab mặc định (chưa cài gói `datasets`) bị crash ngay lập tức khi khởi động pipeline.
- **Cách xử lý:** Xóa dòng import ở đầu file, chuyển `from datasets import Dataset` vào bên trong khối `try:` của hàm `_run_ragas` (Lazy Import).
- **Cách xác minh sau khi sửa:** Chạy lại `python script/run_phase1.py` $\rightarrow$ Pipeline chạy mượt mà từ đầu đến cuối với Exit Code 0, xuất báo cáo đầy đủ.
- **Điều học được:** Với các dependency nặng hoặc tùy chọn (optional dependencies như Ragas/Datasets), luôn áp dụng kỹ thuật Lazy Loading bên trong hàm sử dụng thay vì import tĩnh ở mức module.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   - API Crossref trả về danh sách bài báo JSON $\rightarrow$ Được lưu trữ bảo toàn tại `data/raw/crossref_response.json` (Raw Snapshot).
   - Hàm `build_clean_dataframe()` bóc tách DOI, làm sạch thẻ HTML trong summary, chuẩn hóa ngày tháng và ghép thành ngữ cảnh `text_for_embedding`.
   - Dữ liệu sạch bắt buộc phải vượt qua chốt kiểm soát **Quality Gate Great Expectations 1.x**; nếu `success == True` mới được đưa vào mô hình nhúng `all-MiniLM-L6-v2` để lưu vector vào ChromaDB.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   - Bộ Test Set gồm các câu hỏi cố định kèm `ground_truth` (đáp án chuẩn) và `ground_truth_doc_ids` (mã DOI của bài báo chứa thông tin).
   - Khi chạy QA, hệ thống truy xuất Top-$K$ tài liệu từ ChromaDB:
     - Nếu Top-$K$ chứa ít nhất một mã trong `ground_truth_doc_ids` $\rightarrow$ Ghi nhận **Retrieval Hit = 1.0**.
     - Câu trả lời sinh ra được đối chiếu từ vựng với `ground_truth` để tính điểm trùng khớp **Token F1**.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - **Quality checks (Kiểm định chất lượng)**: Đánh giá **tính toàn vẹn cấu trúc và định dạng** của dữ liệu (không null, độ dài summary $\ge 30$, ID không trùng lặp, số dòng hợp lệ).
   - **Freshness monitoring (Giám sát độ tươi mới)**: Đánh giá **tính thời sự và giá trị sử dụng** theo thời gian (dữ liệu có thể rất sạch và đầy đủ nhưng nếu $> 25\%$ bài báo cũ quá 180 ngày thì tri thức đã bị lỗi thời).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   - Trong phương pháp luận nghiên cứu khoa học, để so sánh công bằng giữa các trạng thái (A/B Testing), tập dữ liệu kiểm thử (Test Set) phải được **giữ cố định làm hằng số**. Nếu đổi câu hỏi giữa các lần chạy, sự thay đổi của Hit Rate và F1 sẽ bị nhiễu và không phản ánh đúng tác động của dữ liệu bẩn.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - **Data Quality Gate**: Trạng thái chuyển từ `FAILED (False)` ở Corrupted quay trở lại `PASSED (True)` ở Repaired.
   - **Freshness SLA**: Phục hồi về `is_fresh = True` (`stale_ratio <= 0.25`).
   - **Retrieval Hit Rate**: Tăng từ `0.600` lên lại `1.000` (100%).
   - **Mean Token F1**: Phục hồi từ `0.779` lên mức hoàn hảo `1.000`.
   - **Artifact đối chứng**: Bảng số liệu trong `data/reports/corruption_report.md` thể hiện trạng thái Repaired tương đồng 100% với Baseline ban đầu.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | 1.000 | 0.600 | 1.000 | Tiêm lỗi cắt ngắn tiêu đề và loại bỏ bài mới khiến vector search tìm trượt 40% câu hỏi. |
| `mean_token_f1` | 1.000 | 0.779 | 1.000 | Do ngữ cảnh bị rác và tóm tắt bị xóa trắng nên câu trả lời của AI bị sai lệch từ vựng nghiêm trọng. |
| `judge_accuracy` | 1.000 | 0.800 | 1.000 | Tỉ lệ câu trả lời được LLM Judge chấm đạt giảm sút khi dữ liệu bị lỗi. |
| `mean_judge_score` | 5.0 | 4.0 | 5.0 | Điểm đánh giá trung bình bị giảm sút rõ rệt ở pha dữ liệu bẩn. |
| Data Quality Gate | PASSED (True) | FAILED (False) | PASSED (True) | Chốt GX 1.x bắt chính xác vi phạm Unique ID (do duplicate) và vi phạm độ dài summary (do blank). |
| Freshness status | Đạt chuẩn (True) | Vi phạm (False) | Đạt chuẩn (True) | Phát hiện 54% bài báo bị lùi ngày về 5 năm trước, vượt ngưỡng SLA 25%. |

### Kết luận từ số liệu

1. **Chuỗi nguyên nhân – bằng chứng 1:**
   `[Tiêm 6 lỗi dữ liệu: Blank summary, Truncate title, Stale date, Duplicate rows]` $\rightarrow$ `[Quality Gate FAILED, Freshness SLA vi phạm cảnh báo (stale_ratio = 54.2%)]` $\rightarrow$ `[Retrieval Hit Rate tụt từ 1.000 xuống 0.600, Token F1 tụt từ 1.000 xuống 0.779]`.
2. **Chuỗi nguyên nhân – bằng chứng 2:**
   `[Kích hoạt Idempotent Repair tái tạo từ Raw Snapshot]` $\rightarrow$ `[Quality Gate PASSED 100%, Freshness phục hồi chuẩn]` $\rightarrow$ `[Retrieval Hit Rate lấy lại 1.000, Token F1 lấy lại 1.000 hoàn toàn như Baseline]`.

- **Corruption ảnh hưởng rõ nhất và vì sao?**
  Lỗi **Blank Summary** và **Drop Latest Records** gây tổn thất nặng nề nhất. Khi summary bị rỗng, AI không có ngữ cảnh để trích xuất câu trả lời, dẫn đến Token F1 rớt về 0. Khi các bài mới bị bỏ rơi, Vector Search hoàn toàn không thể tìm thấy tài liệu gốc (Hit Rate = 0).
- **Kết quả nào khác với kỳ vọng ban đầu?**
  Ban đầu em dự đoán khi dữ liệu bị lỗi, mã nguồn sẽ báo lỗi đỏ (Crash). Tuy nhiên thực tế hệ thống vẫn chạy trơn tru từ đầu đến cuối mà không có exception nào — đây chính là minh chứng sống động nhất cho hiện tượng **Silent Failure**!

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Kiến trúc Data Pipeline**: Phải luôn áp dụng nguyên tắc **Immutable Raw Snapshot** (bảo toàn dữ liệu gốc) để đảm bảo khả năng phục hồi an toàn (Idempotency).
2. **Data Observability**: Không bao giờ được tin tưởng dữ liệu đầu vào. Quality Gate tự động là chốt chặn bắt buộc để bảo vệ serving layer của AI.
3. **Bản chất của AI/RAG**: AI chỉ thông minh khi dữ liệu nuôi dưỡng nó sạch và tươi mới. Khi dữ liệu suy thoái, AI sẽ tự tin đưa ra thông tin sai lệch (Silent Failure).

### Nếu có thêm thời gian
Em sẽ mở rộng thêm kỳ vọng **Semantic Drift Detection** trong Great Expectations: Sử dụng khoảng cách Embedding Drift để cảnh báo khi văn phong của các bài báo khoa học bị thay đổi đột ngột giữa các đợt nạp dữ liệu.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Lê Duy Quân  
**Ngày xác nhận:** 2026-09-25
