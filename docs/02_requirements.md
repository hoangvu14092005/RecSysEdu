# 02 — Sản phẩm cần làm được gì?

Cập nhật: 09/10/2026. Đây là yêu cầu để lập trình và kiểm tra; base chỉ hiển thị fixture, chưa có chức năng tích hợp model thật. Hiện phân tích tính năng, chưa phát triển thêm UI. Căn cứ phương pháp ở [10](10_course_direction.md); [trang bắt đầu](README.md) giải thích P0/P1/P2.

## 1. Người dùng và hai màn hình

Nhóm làm đồ án và giảng viên dùng LearnPath để xem một hồ sơ mẫu, các khóa gợi ý và kết quả so sánh mô hình. Hệ thống dự đoán đăng ký được giữ lại để đánh giá; chưa đo được học tốt hơn hay hoàn thành khóa.

- **Gợi ý học tập:** chọn hồ sơ/model → xem lịch sử → xem Top-10 → mở lý do → xem lộ trình nếu có.
- **Model Lab:** xem bảng kết quả offline → kiểm tra nguồn lần chạy → so sánh mô hình cùng quy tắc → tải bảng.

Hai nhóm chức năng có thể dùng hai tab khi ghép demo; đây chưa là yêu cầu thiết kế bố cục trong đợt này. [Tính năng hiển thị](08_ui_handoff.md) xác định input/output, evidence và nghiệm thu trước khi dựng màn hình.

## 2. Chức năng và điều kiện xong

FR là mã yêu cầu chức năng, giúp issue/PR và báo cáo chỉ đúng phần cần làm.

| Mã | Phần việc | Điều kiện kiểm tra |
| --- | --- | --- |
| FR-01 | Hồ sơ/lịch sử | Đúng ID và lịch sử được phép quan sát; không lộ khóa mục tiêu đang giữ lại |
| FR-02 | Top-K | Tối đa 10 khóa hợp lệ, không trùng/đã quan sát; ít hơn 10 thì ghi lý do |
| FR-03 | Chọn model | MostPopular, Content, BPR, Hybrid có kết quả tương thích; đổi model cập nhật ranking và giải thích |
| FR-04 | Hybrid | Trọng số chọn trên valid; lưu điểm thành phần và cấu hình để đối chiếu |
| FR-05 | Lý do gợi ý | Có bằng chứng từ nội dung/lịch sử/tín hiệu model; không tự bịa người học tương tự hoặc phần trăm phù hợp |
| FR-06 | User mới/thiếu lịch sử | Có gợi ý dự phòng từ popularity train và ghi rõ; Content từ sở thích chỉ dùng khi đã có đầu vào/feature phù hợp |
| FR-07 | Xếp hạng theo tiền đề — P1 | Lưu phần điều chỉnh và độ phủ graph; thiếu graph hiện unknown |
| FR-08 | Lộ trình — P1 | Có thứ tự concept hợp lệ hoặc lý do không tạo được; vòng lặp/danh sách bị cắt có trạng thái riêng |
| FR-09 | Model Lab | Metric có nguồn run/dataset/protocol; bảng so sánh không trộn điều kiện; mẫu/thật hiện rõ |

FR-01–06 và FR-09 thuộc P0. FR-07–08 chỉ nghiệm thu khi graph đạt G4. Không dùng “đã thành thạo” thay cho “đã đăng ký”, hoặc “đủ năng lực” thay cho “chưa phát hiện tiền đề cần ôn”.

## 3. Thực nghiệm phải có bằng chứng gì?

EX là mã yêu cầu thí nghiệm.

| Mã | Yêu cầu | File/bằng chứng cần có |
| --- | --- | --- |
| EX-01 | Model dùng cùng cách đánh giá | Dataset/split hash, nhóm người học, tập khóa và quy tắc loại khóa đã quan sát |
| EX-02 | Có hai mốc so sánh đơn giản | Metric và ranking thật của MostPopular/Content TF-IDF tên/mô tả; feature/profile fit đúng train |
| EX-03 | BPR train và dùng lại được | Log, checkpoint, ID map; score trước/sau load khớp trong sai số đã ghi |
| EX-04 | Chọn tham số không dùng test | Search log valid, config khóa D25, test run từ D26 |
| EX-05 | P1: đo có/không tiền đề | Cùng dữ liệu/graph, có trường hợp penalty bằng 0; tách metric ranking và graph |
| EX-06 | Phân tích ít/nhiều lịch sử | Nhóm xác định bằng train, có cỡ mẫu và kết quả riêng |

Metric thật bằng 0 vẫn là kết quả. Metric chưa chạy phải ghi “chưa có”, không thay bằng 0 hoặc số minh họa. Quy tắc chi tiết nằm ở [đánh giá](05_evaluation.md).

## 4. Yêu cầu vận hành và bàn giao

NFR là yêu cầu giúp phần mềm chạy và bàn giao được.

- **NFR-01:** có lệnh tái lập từ raw tới metric; lưu version, config, seed và checksum.
- **NFR-02:** lỗi dữ liệu được thống kê/cách ly, không im lặng bỏ lỗi hoặc đổi ID.
- **NFR-03:** loader chặn file sai định dạng/phiên bản; đổi user/model không lấy lại cache sai.
- **NFR-04:** demo dùng ID/bí danh; không cần tên thật, giới tính hay ngày sinh.
- **NFR-05:** CPU chạy được fixture và baseline nhỏ; thử BPR sớm trước khi chốt thiết bị/dependency.
- **NFR-06:** người nhận UI dựng được từ mẫu; người nhận bản cuối mở demo từ snapshot mà không bắt buộc train lại.

Raw, dữ liệu đã xử lý và checkpoint lớn lưu ngoài Git. Quy ước cột/file ở [04](04_data_contract.md), vị trí lưu ở [07](07_storage_analysis.md), cách cùng làm ở [CONTRIBUTING](../CONTRIBUTING.md).

## 5. Khi nào gọi là hoàn thành?

P0 hoàn thành khi có đủ bốn model trên dữ liệu thật, đánh giá chung, demo ít nhất ba hồ sơ và trường hợp mới, giải thích có nguồn, báo cáo và runbook đã được người khác chạy lại. Kết quả Hybrid không cải thiện phải được phân tích trung thực.

P1 báo riêng đạt/chưa đạt. Chưa có graph thì vẫn có thể bàn giao P0, nhưng không nhận đã hoàn thành chức năng lộ trình. Video, bài tập, đăng nhập, thanh toán và đo năng lực nằm ngoài lịch hiện tại.

EX-01: M2/M6; EX-02: M3/M4; EX-03: M6; EX-04: M7; EX-05: M9a; EX-06: M11. FR-01–09 tích hợp ở M10; tái lập/bàn giao ở M12 trong [kế hoạch](../tasks/plan.md).
