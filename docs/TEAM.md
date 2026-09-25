# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** H2Q
- **Mã Nhóm / Lớp:** `K4-L3-DAY10`
- **Tên Repository Nộp Bài:** https://github.com/lechihung252/K4-L3A-Day10-Data-Pipeline-Data-Observability

---

## # Thành viên

Nhóm 3 thành viên. Mỗi file chỉ do một người sở hữu; chi tiết phân công và data contract xem [`docs/PHAN_CONG.md`](PHAN_CONG.md).

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Lê Chí Hùng | 2A202602863 | lechihung252@gmail.com | Trưởng nhóm / Pipeline Integrator & RAG (`core/`, `phase1.py`, `corruption_flow.py`, `retrieval/`, artifacts `data/`) — CP0, CP2, CP3, CP5 | `report/2A202602863_LeChiHung.md` |
| 2 | Nguyễn Văn Hưởng | 2A202602743 | nguyenvanhuong2405@gmail.com | Data Foundation (`crossref.py`, `cleaning.py`, `corruption.py`, `data/raw/`) — CP0, CP1, CP4 | `report/2A202602743_NguyenVanHuong.md` |
| 3 | Lê Duy Quân | 2A202602731 | leduyquan2574@gmail.com | Observability & Evaluation (`quality.py` GX 1.x, `testset.py`, `reporting.py`) — CP1, CP2, CP3, CP5 | `report/2A202602731_LeDuyQuan.md` |

---

## # Cá nhân

### ## LeChiHung-2A202602863
- **Vai trò:** Trưởng nhóm, Pipeline Integrator & RAG.
- **Công việc chi tiết đã hoàn thành:**
  - Phân công theo file và chốt data contract giữa các module (`docs/PHAN_CONG.md`): 11 cột clean bắt buộc, `published` dạng chuỗi, key `success` / `is_fresh`, mẫu câu hỏi test set khớp `retrieval/qa.py`.
  - Ghép baseline pipeline `src/pipelines/phase1.py`: ingest → clean → quality gate (fail thì dừng, không index) → ChromaDB `papers-baseline` → test set → evaluate → report → agent demo.
  - Ghép `src/pipelines/corruption_flow.py`: corrupt → quality check → index `papers-corrupted` → evaluate → repair từ raw snapshot → quality gate → index `papers-repaired` → evaluate → báo cáo 3 trạng thái.
  - Thêm `write_dataframe` vào `src/core/utils.py`; review và chạy kiểm thử tích hợp code của TV2, TV3.
  - Chạy pipeline cuối, commit toàn bộ artifacts `data/`, viết báo cáo nhóm `report/group_report.md`.
- **Điều học được / Đóng góp chính:**
  - Quality gate phải đặt trước vector store mới chặn được dữ liệu xấu; repair idempotent dựa trên việc giữ raw snapshot bất biến và tái tạo từ đó thay vì vá tay.

### ## NguyenVanHuong-2A202602743
- **Vai trò:** Data Foundation — Ingestion, Cleaning & Corruption.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng module thu thập Crossref API với retry cho 429/503 và cơ chế fallback offline trong `src/ingestion/crossref.py`.
  - Chuẩn hóa schema 11 cột, xử lý text/ngày, khử DOI trùng, tính `age_days`, `summary_chars` và `text_for_embedding` trong `src/ingestion/cleaning.py`.
  - Xây dựng corruption suite gồm 6 lỗi có khả năng tái lập trong `src/ingestion/corruption.py` và ghi log chi tiết theo `paper_id`.
  - Cung cấp `load_raw_records()` và `build_clean_dataframe()` để TV1 thực thi Idempotent Repair từ raw snapshot.
- **Điều học được / Đóng góp chính:**
  - Hiểu kỹ thuật truy vết nguồn gốc dữ liệu, bảo toàn raw snapshot, thiết kế data contract ổn định và tác động của dữ liệu lỗi đến RAG.
  - Các commit chính: `8b524d2`, `265f31b`, `c645dfb`.

### ## LeDuyQuan-2A202602731
- **Vai trò:** Observability & Evaluation (TV3).
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập Quality Gate theo chuẩn mới **Great Expectations 1.x** (`mode="ephemeral"`) với 4 Expectations và giám sát Freshness SLA trong `src/observability/quality.py`.
  - Xây dựng bộ câu hỏi đánh giá chuẩn 10 câu hỏi bao phủ 4 dạng (`summary`, `authors`, `date`, `categories`) trong `src/evaluation/testset.py`.
  - Đo lường và xuất bảng đối chiếu 3 trạng thái vào `data/reports/corruption_report.md` và `data/reports/phase1_report.md`.
  - Tối ưu lazy loading import `datasets` trong `src/evaluation/metrics.py` và chuẩn hóa hợp đồng dữ liệu với `src/pipelines/phase1.py`.
- **Điều học được / Đóng góp chính:**
  - Hiểu rõ cơ chế ngăn chặn Silent Failure bằng Quality Gate tự động trước khi nạp dữ liệu vào Vector Database, nguyên lý Idempotent Repair và kỹ thuật đánh giá định lượng sự suy giảm chất lượng của hệ thống RAG.
  - Các commit chính: `4257758`, `7023d48`.

