# Bắt đầu đọc tài liệu RecSysEdu

Cập nhật: 16/10/2026. **P0 offline đã có dữ liệu/split thật, bốn mô hình,
validation, test sau freeze và snapshot thật.** Đã kiểm trình duyệt và môi trường
Python sạch trên cùng máy Windows. Xem [nghiệm thu](../reports/acceptance.md),
[kết quả test](../results/final/report.md), [tái lập](../results/reproduction.md)
và chạy theo [runbook](09_runbook.md). Các báo cáo base ngày09/10 và lịch sáu
tuần là nhật ký/kế hoạch lịch sử, không thay cho trạng thái hiện tại.

## Dự án làm gì?

Đọc [10 — Hướng đồ án theo môn học](10_course_direction.md) để hiểu vì sao chọn
phương pháp và [11 — Ghi chú nguồn](11_course_reading_notes.md) để kiểm bài/trang.
Demo hiện có hai tab đọc kết quả đã tính, không train khi bấm. Clone Git mặc
định mở fixture có nhãn; snapshot thật và dữ liệu/model phải nhận riêng.

**RecSysEdu** là tên dự án mã nguồn. **LearnPath** là tên giao diện demo. Hệ thống đọc lịch sử đăng ký khóa học, xếp hạng các khóa chưa đăng ký và giải thích vì sao chúng được gợi ý.

Ví dụ minh họa: một người từng đăng ký Python có thể được gợi ý khóa về lập
trình hoặc dữ liệu. P0 chỉ giải thích cơ chế tính điểm, chưa xác nhận tiền đề
hoặc tạo lộ trình. Đăng ký chưa chứng minh đã học xong hoặc thành thạo.

## Hướng đi chung

```text
1. Lấy user/course từ MOOCCubeX, giữ bản gốc trên SSD.
2. Kiểm tra và làm sạch, lưu bảng chuẩn bằng Parquet.
3. Chia train/valid/test; chạy bốn mô hình trên cùng quy tắc.
4. Xuất file kết quả nhỏ demo_bundle.json.
5. LearnPath đọc file: Gợi ý học tập | Model Lab.
6. Kiểm tra chạy lại được và bàn giao qua một repo GitHub.
```

DuckDB giúp lọc và thống kê bảng Parquet. RecBole giúp huấn luyện BPR. Streamlit dựng giao diện bằng Python. Cloud/Drive chỉ cần khi chia sẻ hoặc sao lưu file; chưa cần database hay backend riêng cho demo sáu tuần.

| Phạm vi | Trạng thái hiện tại |
| --- | --- |
| **P0 — bắt buộc** | Đã có pipeline, evaluator, MostPopular/Content/BPR/Hybrid, snapshot và hai tab; kết quả/giới hạn ở báo cáo nghiệm thu |
| **P1 — có điều kiện** | Có công cụ audit và fixture; chưa chạy graph thật vì thiếu ba nguồn; `P1_STOP_INSUFFICIENT_EVIDENCE`, chưa rerank/path |
| **P2 — sau sáu tuần** | LightGCN, video/bài tập, đánh giá năng lực, React/FastAPI/PostgreSQL hoặc web nhiều người dùng |

Hybrid không tốt hơn BPR vẫn có thể đạt yêu cầu nếu triển khai và đánh giá đúng. Thiếu BPR/Hybrid là thiếu P0; thiếu graph được báo riêng là P1 chưa đạt.

## Đọc tài liệu nào trước?

| Bạn cần biết | Đọc |
| --- | --- |
| Vì sao chọn hướng này, phạm vi và rủi ro | [01 — Phân tích](01_analysis.md) |
| Sản phẩm phải làm được gì, khi nào tính là xong | [02 — Yêu cầu](02_requirements.md) |
| Chia mã nguồn và ghép các phần như thế nào | [03 — Kiến trúc](03_architecture.md) |
| Tên cột, kiểu dữ liệu, file model bàn giao cho UI | [04 — Quy ước dữ liệu](04_data_contract.md) |
| Chia tập dữ liệu và so sánh mô hình công bằng | [05 — Đánh giá](05_evaluation.md) |
| Nguồn thông tin và điều gì còn chưa kiểm chứng | [06 — Nguồn](06_sources.md) |
| Dữ liệu nào lưu ở đâu, cần bao nhiêu dung lượng | [07 — Lưu trữ](07_storage_analysis.md) |
| Thông tin cần hiển thị, nguồn kết quả và cách phân việc | [08 — Tính năng và bàn giao](08_ui_handoff.md) |
| Lý do chọn công nghệ/phương pháp và khi nào cần đổi | [ADR-001](decisions/ADR-001-scope-stack.md), [ADR-002](decisions/ADR-002-course-grounded-direction.md) |
| Công việc cụ thể theo ngày | [Lịch sáu tuần](../tasks/six_week_schedule.md) và [task kỹ thuật](../tasks/plan.md) |
| Cùng sửa mã qua GitHub | [CONTRIBUTING](../CONTRIBUTING.md) |

Người mới đọc trang này, báo cáo nghiệm thu, runbook rồi phần việc mình nhận.
Tài liệu10/11 giải thích căn cứ lựa chọn ban đầu; docs03/04/05 mô tả kiến trúc,
contract và protocol đang dùng. Lịch cũ không có quyền đổi freeze/test đã công bố.

## Các từ thường gặp

| Từ trong tài liệu/code | Hiểu đơn giản |
| --- | --- |
| Raw / processed | File gốc / dữ liệu đã làm sạch |
| Metadata | Thông tin mô tả, ví dụ tên và lĩnh vực của khóa |
| Pipeline | Chuỗi bước: đọc → xử lý → train → đánh giá → xuất kết quả |
| Train / valid / test | Tập học mô hình / tập chọn tham số / tập đánh giá cuối |
| Candidate | Khóa nằm trong danh sách được mô hình chấm điểm |
| Cohort | Nhóm người học được dùng trong một bảng đánh giá |
| Protocol | Bộ quy tắc chia dữ liệu, chọn khóa và tính metric |
| Metric | Chỉ số đo chất lượng gợi ý |
| Artifact / checkpoint | File kết quả / file lưu mô hình đã huấn luyện |
| Snapshot / run | Gói kết quả tại một phiên bản / một lần chạy mô hình hoặc đánh giá |
| Manifest / hash | File ghi nguồn và phiên bản / mã kiểm tra nội dung file |
| Fixture / synthetic | Mẫu nhỏ phục vụ kiểm tra / dữ liệu giả có nhãn |
| Fallback / unknown | Cách gợi ý dự phòng / chưa đủ thông tin |
| Prerequisite / graph | Kiến thức cần trước / các khái niệm nối bằng quan hệ trước–sau |

## Kế hoạch sáu tuần và kết quả đã có

Lịch lịch sử chia dữ liệu/BPR spike→baseline→bốn model→cổng P1→demo/freeze→test/
tái lập. Công việc P0 này đã được thực thi; không khẳng định sáu tuần thực tế
đã trôi qua. Pilot10.000 người tạo9.909 warm valid/9.858 warm test và2.586
candidate. Hybrid alpha0,25 có test NDCG@10=0,0773727819; đó là một pilot/một
seed, không phải bằng chứng học tốt hơn hoặc thắng mọi nhóm.

Prepare/split/RecBole/evaluate/export đã chạy trên dữ liệu thật. Graph thật
chưa chạy. Danh sách trạng thái/bằng chứng ở [todo](../tasks/todo.md), hướng dẫn
chuyển artifact ngoài Git ở runbook. Thay data/config/protocol cần validation
và freeze mới; không dùng test đã mở để chọn lại tham số. Khi đổi contract,
sửa docs04, loader, fixture, exporter và các bên dùng cùng một thay đổi.
