# Bắt đầu đọc tài liệu RecSysEdu

Cập nhật: 09/10/2026. Bộ tài liệu mô tả hướng triển khai trong **sáu tuần**. Đã có package/CLI, base UI hai tab và raw user/course đã tải/audit; chưa có split hoặc kết quả huấn luyện. Người mới chạy theo [runbook](09_runbook.md), xem [audit thật](../results/data_audit.md) và [bằng chứng base](../results/base_verification.md).

## Dự án làm gì?

Đọc [10 — Hướng đồ án theo môn học](10_course_direction.md) để hiểu vì sao chọn phương pháp và [11 — Ghi chú nguồn](11_course_reading_notes.md) để kiểm bài/trang. Hiện tập trung bài toán, dữ liệu, model và đánh giá; UI chỉ được phân tích chức năng, chưa phát triển thêm.

**RecSysEdu** là tên dự án mã nguồn. **LearnPath** là tên giao diện demo. Hệ thống đọc lịch sử đăng ký khóa học, xếp hạng các khóa chưa đăng ký và giải thích vì sao chúng được gợi ý.

Ví dụ minh họa: một người từng đăng ký Python có thể được gợi ý khóa về lập trình hoặc dữ liệu. Nếu có thông tin kiến thức cần học trước, giao diện cho biết nên kiểm tra những kiến thức nào. Đăng ký một khóa chưa chứng minh người đó đã học xong hoặc đã thành thạo.

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

| Phạm vi | Cần làm |
| --- | --- |
| **P0 — bắt buộc** | Dữ liệu sạch; cách đánh giá chung; MostPopular, Content, BPR, Hybrid; lý do gợi ý; hai tab UI; báo cáo và hướng dẫn chạy |
| **P1 — có điều kiện** | Dữ liệu concept/kiến thức tiên quyết đủ dùng thì thêm xếp hạng lại và lộ trình; thiếu dữ liệu phải ghi rõ |
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

Người mới đọc trang này, tài liệu 10, rồi tài liệu 01 và phần việc mình nhận. Chốt đầu vào/đầu ra và căn cứ thuật toán trước khi tiếp tục làm sản phẩm.

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

## Sáu tuần sẽ bàn giao gì?

Tuần 1 làm dữ liệu và thử môi trường BPR. Tuần 2 có MostPopular/Content TF-IDF và evaluator. Tuần 3 đủ bốn mô hình. Tuần 4 phân tích lỗi và kiểm tra có làm được graph/lộ trình không. Tuần 5 mới ghép demo tối thiểu với kết quả thật và khóa cấu hình. Tuần 6 đánh giá cuối, báo cáo và thử bàn giao trên môi trường sạch. Base mẫu đã có không là lý do dành thêm tuần 1–4 cho trang trí UI.

Download/audit/demo validate đã chạy theo [runbook](09_runbook.md); prepare/split/train/evaluate/graph vẫn là **phần sẽ xây**. Khi thay quy ước dữ liệu, sửa tài liệu 04, loader, fixture và các bên dùng dữ liệu trong cùng thay đổi; tránh mỗi người hiểu một định dạng.
