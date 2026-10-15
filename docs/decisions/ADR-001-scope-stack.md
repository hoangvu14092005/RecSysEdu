# ADR-001 — Chọn hướng triển khai gọn trong sáu tuần

**Trạng thái: PROPOSED cho toàn stack.** Ngày lập/cập nhật: 09/10/2026. ADR là bản ghi lý do chọn hướng kỹ thuật. Base Python/CLI/Streamlit đã chạy theo hướng này; toàn stack BPR/graph/Parquet chưa được kiểm chứng. Xem [báo cáo base](../../results/base_verification.md).

## 1. Vì sao cần quyết định này?

**Điều chỉnh một phần:** [ADR-002](ADR-002-course-grounded-direction.md) thay Content field-only bằng TF-IDF tên/mô tả và ưu tiên data/model/đánh giá trước UI. Các mô tả field-only/UI làm sớm phía dưới ghi lại hướng ban đầu, không phải cấu hình hiện hành. Những lựa chọn còn lại giữ nguyên.

Khi khởi tạo, root chưa có mã/dữ liệu. Đề xuất gốc rộng: khóa học, tài nguyên, Hybrid, năng lực và lộ trình. Người dùng muốn hoàn thành trong sáu tuần, tránh phức tạp và bàn giao người khác cùng làm trên GitHub. Cần một luồng nhỏ đủ kiểm chứng thay vì nhiều hệ thống cần tích hợp.

## 2. Hướng đang đề xuất

- **P0:** user–course enrollment; MostPopular → Content field-only → BPR qua RecBole → Hybrid; evaluator chung; giải thích; hai tab LearnPath; báo cáo và chạy lại được.
- **P1:** graph tiền đề, xếp hạng lại và path concept khi dữ liệu đủ; báo riêng trạng thái đạt/chưa đạt.
- **Lưu trữ:** raw trên SSD và manifest; processed Parquet/DuckDB; TSV export RecBole; checkpoint cùng ID map/config; snapshot JSON cho demo.
- **Sản phẩm:** Python + Streamlit, một repo GitHub; model/UI cùng làm qua `demo_bundle.json`. Bố cục mẫu có thể làm từ M0, tích hợp thật tuần 5.
- **Đánh giá:** train cố định, valid chọn tham số, test sau khóa D25; warm benchmark cùng cohort/candidate/mask. Giới hạn chia theo user phải được báo.

Đăng ký là dấu hiệu tiếp xúc, không phải thành thạo. Graph chỉ nhận cạnh nhãn dương xác nhận; unknown không được đổi thành “đủ kiến thức”.

## 3. Vì sao chưa chọn các hướng khác?

| Hướng | Đánh đổi |
| --- | --- |
| React + FastAPI + PostgreSQL ngay | Thêm backend/migration/API/frontend trước khi có ranking thật |
| Nhập toàn bộ raw vào DB | Tăng công việc import/index/backup không cần cho P0 |
| LightGCN/KGAN hoặc năng lực ngay | Tăng phụ thuộc và bài toán trước khi baseline ổn |
| Dùng nguyên repo demo cộng đồng | Chưa kiểm logic dữ liệu/evaluator/runtime/tái lập |
| Tải toàn video/bài tập | Thêm dung lượng/parser/nhãn ngoài bài toán enrollment ban đầu |

## 4. Lợi ích và giới hạn

Người làm UI có thể bắt đầu bằng mẫu mà không có GPU/raw. File chung giúp ghép model/UI và bàn giao đơn giản. Nhóm vẫn phải viết adapter ID/exporter, evaluator và loader kiểm tra tương thích; dùng thư viện không tự thay thế các phần đó.

Streamlit lấy tinh thần LearnPath, không hứa giống từng pixel. Lộ trình là gợi ý dựa trên graph, chưa bảo đảm phù hợp sư phạm hay learning gain. Hybrid không thắng BPR vẫn có thể đạt nếu so sánh đúng. Chưa biết phần cứng nên quy mô/version chốt bằng thử nghiệm nhỏ, không bằng suy đoán.

## 5. Khi nào đổi hướng?

Đổi khi enrollment không đủ, môi trường BPR không vượt thử tương thích, giảng viên bắt buộc tài nguyên học tập, hoặc có yêu cầu web online/UI riêng vượt Streamlit. Graph thiếu thì giảm P1 và ghi rõ, không đổi âm thầm bài toán P0.

Nếu thay quyết định đáng kể, tạo ADR bổ sung, cập nhật docs/plan/contract và chạy lại model chịu ảnh hưởng. Giữ ADR cũ để biết lý do lịch sử; không ghép metric từ hai dataset/protocol.

## 6. Việc tiếp theo

Làm M0/M1 theo [plan](../../tasks/plan.md), dùng [contract 04](../04_data_contract.md) và [protocol 05](../05_evaluation.md). Thử BPR sớm D04, ghi RAM/temp/thời gian và version. Cập nhật trạng thái ADR khi quyết định kỹ thuật được chốt với bằng chứng; không cần tạo thêm hạ tầng để bắt đầu.
