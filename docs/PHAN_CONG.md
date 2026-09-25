# Phân công nhóm 3 người — Lab Day 10

> Mọi người đọc hết file này trước khi code nhé. Nguyên tắc chính: **mỗi file chỉ một người sửa**, nên nếu làm đúng thì sẽ không bị conflict.

---

## 1. Ai làm gì

Phần `src/retrieval/` (embedding, ChromaDB, QA agent) và `src/evaluation/metrics.py` **đã được viết sẵn**. Việc cần làm chỉ nằm ở các file còn `TODO(student)`.

| Người | Vai trò | File sở hữu (chỉ người này sửa) | Checkpoint chính |
|---|---|---|---|
| **TV1** — `[Tên]` | Trưởng nhóm, ghép pipeline, phụ trách RAG | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `src/core/`, `src/retrieval/` (đọc hiểu, chỉnh nếu cần), `script/`, **toàn bộ output trong `data/`** (trừ `data/raw/`), `report/group_report.md` | CP0, CP2, CP3, CP5 |
| **TV2** — `[Tên]` | Dữ liệu: lấy, làm sạch, tiêm lỗi | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/ingestion/corruption.py`, `data/raw/` | CP0, CP1, CP4 |
| **TV3** — `[Tên]` | Giám sát chất lượng và đánh giá | `src/observability/quality.py` (Great Expectations 1.x và Freshness), `src/observability/reporting.py`, `src/evaluation/testset.py` | CP1, CP2, CP3, CP5 |

Bước phục hồi (repair) không cần file riêng: TV1 gọi lại `load_raw_records()` rồi `build_clean_dataframe()` của TV2 trong `corruption_flow.py`.

### Việc cụ thể từng người

**TV1**
- `phase1.py`: load settings → load raw → clean → lưu CSV → build Chroma index → test set → evaluate → quality và freshness → report (làm theo pseudo-code trong file).
- `corruption_flow.py`: corrupt → evaluate → quality check → repair từ raw → evaluate → report so sánh 3 trạng thái.
- Cuối giờ: chạy 2 script và commit toàn bộ `data/`.

**TV2**
- `crossref.py`: `parse_crossref_payload`, `fetch_source_records` (có retry khi gặp 429/503), `load_raw_records`.
- `cleaning.py`: chuẩn hóa text, parse ngày, tính `age_days`, tạo các cột phụ, bỏ dòng trùng và dòng lỗi.
- `corruption.py`: tiêm đủ 6 lỗi (bỏ bản ghi mới nhất, xóa summary, chèn ký tự rác, cắt ngắn title, làm cũ ngày, nhân bản dòng), sau đó ghi `corruption_log.json`.

**TV3**
- `quality.py`: GX 1.x (`gx.get_context()`, `add_pandas()`) kiểm tra số dòng, `paper_id` không null và unique, `title` không null, độ dài `summary`, `age_days`. Viết thêm `build_freshness_report`.
- `testset.py`: sinh câu hỏi 4 loại (summary, authors, date, categories). Mỗi câu hỏi có đủ `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`.
- `reporting.py`: `phase1_report.md` và `corruption_report.md` (bảng 3 cột Baseline, Corrupted, Repaired).

---

## 2. Hợp đồng dữ liệu (chốt ở CP0, không tự ý đổi)

**DataFrame sau khi clean (TV2 xuất ra, TV1 và TV3 dùng)** bắt buộc có các cột:

```
paper_id, title, summary, published, authors_joined, categories_joined,
abs_url, pdf_url, text_for_embedding, age_days, summary_chars
```

(`src/retrieval/index.py` đọc trực tiếp các cột này, thiếu một cột là pipeline chết.)

**Dict mà `quality.py` trả về (TV3 xuất ra, TV1 và `reporting.py` dùng):** TV3 ghi rõ danh sách key trong docstring rồi báo lên nhóm. Ví dụ: `success`, `results`, `is_fresh`, `stale_rows`, `total_rows`, `latest_published`, `oldest_published`.

Muốn đổi tên cột hoặc key nào thì **báo cả nhóm trước khi đổi**.

---

## 3. Quy tắc Git để không conflict

GitHub chỉ đếm contributor theo các commit trên **`main`**, nên cả nhóm push thẳng lên `main`.

```bash
git pull --rebase origin main        # trước khi bắt đầu và trước MỖI lần push
git add src/ingestion/cleaning.py    # chỉ add đúng file của mình
git commit -m "feat(cleaning): normalize schema and compute age_days"
git push origin main
```

- ❌ **Không dùng `git add .` hay `git add -A`.** Khi chạy thử, máy bạn sẽ sinh file trong `data/` (ChromaDB là file nhị phân). Hai người cùng commit các file này thì conflict không gộp được.
- ✅ Chạy thử trên máy thoải mái, nhưng **chỉ TV1 commit `data/`**, một lần vào cuối giờ.
- ✅ Commit nhỏ và thường xuyên, **mỗi người ít nhất 3–5 commit** để hiện trên Insights > Contributors.
- ✅ Tắt "format on save" trong editor để khỏi vô tình format lại file của người khác.
- ❌ **Không commit file `.env`** (lộ API key bị trừ 20 điểm).
- Nếu push bị reject: chạy `git pull --rebase origin main` rồi push lại. Nếu vẫn conflict thì nhắn nhóm, đừng force push.

### File dùng chung
- `docs/TEAM.md`: TV1 điền bảng thành viên. Mỗi người **chỉ viết phần `## HoTen-MSSV` của mình**, sửa xong thì commit và push ngay.
- Báo cáo cá nhân: mỗi người tạo file riêng `report/<MSSV>_HoTen.md` (copy từ `report/individual_report.md`).

---

## 4. Làm song song, không chờ nhau

- **TV3** chưa cần đợi TV2: tự tạo một DataFrame giả 3–4 dòng, đủ các cột ở mục 2, để test `quality.py` và `testset.py`.
- **TV1** viết khung `phase1.py` theo pseudo-code ngay từ đầu, rồi ghép dần khi code của TV2 và TV3 được push lên.

| Mốc | Cần xong |
|---|---|
| Phút 30 (CP0) | Cả nhóm cài môi trường xong, chạy được lệnh kiểm tra ra `Môi trường sẵn sàng`, chốt hợp đồng dữ liệu |
| Phút 65 (CP1) | TV2 push `crossref.py` và `cleaning.py` |
| Phút 95 (CP2) | TV3 push `quality.py` và `testset.py` |
| Phút 120 (CP3) | TV1 chạy được `python script/run_phase1.py`. TV3 push phần `generate_phase1_report` |
| Phút 150 | TV2 push `corruption.py`. TV3 push phần `generate_corruption_report` |
| Phút 210 (CP5) | TV1 chạy được `python script/run_corruption_flow.py`, commit toàn bộ `data/` |
| Phút 240 (CP6) | Demo, mọi người đã có commit trên `main` |

---

## 5. Trước khi nộp

- [ ] Cả 3 người hiện trên **Insights > Contributors**
- [ ] Mỗi người đã viết phần của mình trong `docs/TEAM.md` và file `report/<MSSV>_HoTen.md`
- [ ] **Ai cũng giải thích được toàn bộ luồng** (Crossref → clean → quality gate → index → eval → corrupt → repair), không chỉ phần mình làm, vì giảng viên hỏi ngẫu nhiên
- [ ] **Mỗi người tự nộp link repo lên VLearn LMS bằng tài khoản của mình.** Không nộp là 0 điểm dù nhóm làm tốt.
