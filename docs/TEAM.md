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

### ## NguyenVanHuong-2A202602743 (TV2 tự điền)
- **Vai trò:** Data Foundation — Ingestion, Cleaning & Corruption.
- **Công việc chi tiết đã hoàn thành:**
  - [TV2 tự điền]
- **Điều học được / Đóng góp chính:**
  - [TV2 tự điền]

### ## LeDuyQuan-2A202602731 (TV3 tự điền)
- **Vai trò:** Observability & Evaluation.
- **Công việc chi tiết đã hoàn thành:**
  - [TV3 tự điền]
- **Điều học được / Đóng góp chính:**
  - [TV3 tự điền]
