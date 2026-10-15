# 01 — Hướng đi của RecSysEdu

Cập nhật: 09/10/2026. Đây là phân tích để triển khai, chưa phải kết quả thực nghiệm. Bản [10 — Hướng theo môn học](10_course_direction.md) bổ sung căn cứ L0–L10 và điều chỉnh Content theo audit thật; hiện chưa tập trung UI. Người mới đọc [trang bắt đầu](README.md) rồi tài liệu 10.

## 1. Bài toán cần giải quyết

Từ lịch sử **đăng ký**, tìm các khóa học chưa đăng ký mà hệ thống nên gợi ý. Đầu ra là tối đa 10 khóa, một lý do dễ hiểu cho mỗi khóa và thông tin kiến thức cần trước nếu dữ liệu đủ.

Ví dụ giả: người học từng đăng ký Python và xác suất; hệ thống xếp hạng khóa phân tích dữ liệu cao hơn khóa không liên quan. Đây chỉ là ví dụ giải thích, chưa phải kết quả trên MOOCCubeX.

MOOCCubeX cung cấp kho dữ liệu, mô tả và script hỗ trợ; nhóm vẫn cần viết bước làm sạch, mô hình, đánh giá và giao diện của dự án. Quy mô hơn 296 triệu hành vi là quy mô nguồn công bố, không phải số dòng đăng ký phải đưa vào đồ án. [Nguồn chính thức](https://github.com/THU-KEG/MOOCCubeX).

## 2. Sản phẩm nên làm trong sáu tuần

| Mức | Nội dung | Cách xác nhận |
| --- | --- | --- |
| P0 — bắt buộc | Enrollment sạch; MostPopular, Content, BPR, Hybrid; đánh giá chung; giải thích; hai tab LearnPath; báo cáo/runbook | Có kết quả thật, cùng quy tắc đánh giá, chạy lại được |
| P1 — có điều kiện | Concept, kiến thức tiên quyết, xếp hạng lại, lộ trình | Có báo cáo chất lượng graph và ví dụ truy vết được |
| P2 — để sau | LightGCN, video/bài tập, năng lực, web nhiều người dùng | Không chặn việc hoàn thành P0 |

Giao diện có **Gợi ý học tập** cho người xem khóa và **Model Lab** cho người xem kết quả mô hình. Hồ sơ/lịch sử nằm trong màn hình chính. Không cần tách thành sáu trang.

## 3. Bốn mô hình hiểu đơn giản thế nào?

| Mô hình | Cách chọn khóa | Vì sao cần |
| --- | --- | --- |
| MostPopular | Khóa nhiều người đăng ký trong train | Mốc đơn giản để biết mô hình phức tạp có giúp gì không |
| Content-based | Khóa có tên/mô tả gần nội dung các khóa train của người đó; TF-IDF + cosine | Cá nhân hóa bằng nội dung theo L4; field bổ sung khi có |
| BPR | Học thứ tự ưu tiên từ nhiều cặp người học–khóa học | Cá nhân hóa bằng hành vi cộng tác |
| Hybrid | Kết hợp điểm Content và BPR sau chuẩn hóa | Kiểm tra hai nguồn tín hiệu có bổ sung nhau không |

Graph, nếu đủ tốt, điều chỉnh nhẹ thứ hạng và gợi ý concept cần tham khảo. Nó không xác nhận người học đủ năng lực theo khóa.

## 4. Cách tổ chức để dễ hoàn thành và cùng làm

Một pipeline Python xử lý/huấn luyện offline, nghĩa là chạy trước để sinh kết quả. Một app Streamlit đọc file kết quả nhỏ để hiển thị. Dữ liệu lớn nằm trên SSD, bảng chuẩn lưu Parquet và được thống kê bằng DuckDB. GitHub chứa source, config, tài liệu và mẫu nhỏ.

Base UI mẫu được giữ làm tham khảo; hiện chốt những kết quả cần hiển thị và điều kiện có kết quả, chưa phát triển thêm bố cục. Người làm model xuất artifact trước, demo tối thiểu đọc artifact khi lõi đạt. Không cần thêm API/database. Chi tiết ở [kiến trúc](03_architecture.md), [dữ liệu](04_data_contract.md) và [tính năng hiển thị](08_ui_handoff.md).

## 5. Câu hỏi mà báo cáo cần trả lời

1. Content và BPR khác MostPopular thế nào trên cùng dữ liệu?
2. Hybrid cải thiện thứ hạng hoặc độ đa dạng khóa được gợi ý hay không?
3. Nếu có graph, xếp hạng lại đổi kết quả và chỉ báo thiếu tiếp xúc với kiến thức nền ra sao?

Kết quả không cải thiện vẫn phải báo. Mục tiêu là so sánh có căn cứ, không phải cố làm Hybrid thắng bằng đổi dữ liệu đánh giá.

## 6. Rủi ro và cách giảm

| Vướng mắc | Việc làm sớm |
| --- | --- |
| Người học có quá ít lịch sử | Thống kê trước khi chọn subset; không cố lọc một lĩnh vực khiến mất dữ liệu |
| ID/thời gian không nối được | Ghi lỗi và nguồn; không ghép mảng lệch hoặc điền thời gian giả |
| BPR không cài/train được | Thử fixture nhỏ ở tuần 1, không chờ tuần 3 mới phát hiện |
| Graph thưa hoặc vòng lặp | Chỉ bật P1 khi đủ bằng chứng; thiếu thì hiện “chưa đủ dữ liệu” |
| Giao diện kéo dài tiến độ | Giữ hai tab và file kết quả; trang trí làm sau luồng chính |
| Chia thời gian theo user bị hiểu thành dự đoán thực tế hoàn chỉnh | Ghi giới hạn giữa các user và availability khóa ở tài liệu 05 |
| Người khác không chạy lại được | Khóa dependency, ghi nguồn/checksum, thử runbook trên môi trường sạch |

## 7. Làm gì tiếp?

Base và raw đã có. Phiên tiếp theo hoàn thiện M1–M2: timezone, metadata, subset, Parquet/split và manifest; sau đó evaluator và bốn model. Pilot đề xuất 10.000 người từ nhóm đủ lịch sử, tăng sau số đo. [Kế hoạch](../tasks/plan.md) và [lịch 30 ngày](../tasks/six_week_schedule.md) giữ các mốc nghiệm thu; chưa thêm công việc UI trong đợt phân tích.
