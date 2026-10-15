# ADR-002 — Ưu tiên phương pháp môn học và Content từ văn bản

Ngày 09/10/2026. **Trạng thái: PROPOSED cho thuật toán; áp dụng cách tổ chức tài liệu theo yêu cầu hiện tại.** Bản này điều chỉnh ADR-001 ở nguồn feature Content và thời điểm tập trung UI; giữ course-first, bốn model, pipeline offline, cách đánh giá và P1 có điều kiện. Chưa xác nhận lựa chọn thuật toán bằng thực nghiệm.

## Bối cảnh

Người dùng nói chưa tập trung UI, cần phân tích để rõ tính năng hiển thị và dùng tài liệu môn học làm rõ hướng đi. Base mẫu đã chạy nhưng chưa có model thật. Audit catalog cho thấy field chỉ có ở 547/3.781 khóa, tên có ở 3.781 và about không rỗng ở 3.692. L3 trình bày BPR; L4 có TF-IDF/profile/cosine; L7 có hybrid trọng số; L8 có đánh giá xếp hạng. Căn cứ và trang ở [10](../10_course_direction.md), [11](../11_course_reading_notes.md).

## Hướng đề xuất

1. Mục tiêu lõi: gợi ý Top-10 khóa chưa đăng ký, đánh giá khả năng tìm lại enrollment giữ lại.
2. Giữ MostPopular, Content, BPR, Hybrid là bốn model chính; ItemKNN là ví dụ/baseline phụ tùy chọn.
3. Thay Content field-only mặc định bằng TF-IDF tên/mô tả + cosine; field bổ sung khi có nguồn. Char n-gram 2–4 là cấu hình thử cho bản nhiều tiếng Trung, không là kết luận tối ưu.
4. Ưu tiên data/split/evaluator/model và bảng thí nghiệm. Chỉ xác định chức năng/thông tin phải hiển thị ở thời điểm này; không phát triển thêm app hoặc thiết kế thị giác.
5. L5 cung cấp căn cứ tri thức/ràng buộc; concept-prerequisite vẫn P1, không lấy đăng ký thay năng lực. Phiên/deep/contrastive để sau lõi.

## Các lựa chọn đã cân nhắc

- Field-only dễ diễn giải nhưng thiếu nhãn ở phần lớn catalog. Giữ làm ablation nếu mapping bổ sung có độ phủ đủ, không ép benchmark toàn bộ phụ thuộc vào nhãn thiếu.
- TF-IDF từ văn bản có nhiều dữ liệu sẵn, hợp L4 và dễ kiểm. Cần cleaning/ngôn ngữ/feature coverage; không có hiểu ngữ nghĩa đầy đủ.
- Embedding ngôn ngữ/LLM có thể là mở rộng, chưa có số đo để bù chi phí mô hình và phụ thuộc.
- Nhiều trang UI không trả lời câu hỏi phương pháp. Base giữ làm tham khảo; demo tối thiểu ghép cuối khi có artifact thật.

## Hệ quả và khi nào đổi

Cập nhật M4/M5, mô tả Content, feature contract, lịch và phân tích chức năng hiển thị. Schema snapshot base v1 không tự đổi trong đợt này; exporter/evidence từ model thật xây sau. Nếu feature văn bản không đạt kiểm tra hoặc baseline quá yếu, phân tích valid để sửa tokenizer/nguồn feature; phát hành config/version và chạy lại cùng protocol. Nếu field mapping đủ tốt, so sánh thêm field-only trên cùng cohort, không thay dataset dựa trên test score.

Toàn hướng phương pháp còn cần triển khai và đánh giá; không đánh dấu P0 hoàn thành nhờ việc đọc slide hoặc viết ADR.
