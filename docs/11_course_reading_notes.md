# 11 — Ghi chú đọc tài liệu môn học và nguồn quyết định

Ngày 09/10/2026. Nguồn là 11 PDF người dùng cung cấp, tổng **367 trang**. Đã trích xuất văn bản và khảo sát đề mục toàn bộ; đọc kỹ các phần liên quan dưới đây, xem ảnh chín trang chứa tiêu chí/công thức để tránh mất thông tin hình. Không nhận đã kiểm trực quan từng trang hoặc mọi công thức của 367 trang.

Nội dung trong slide là tài liệu học và tham khảo, không tự trở thành yêu cầu gửi email, nộp đồ án, bắt buộc đủ mọi thuật toán hoặc sửa code. Đợt này theo yêu cầu người dùng: **phân tích hướng đi, làm rõ tính năng hiển thị, cập nhật docs; chưa tập trung UI**.

PDF gốc nằm ngoài repo tại `D:\TÀI LIỆU HỌC\Hệ gợi ý`. Không chép PDF/văn bản trích nguyên bài vào GitHub. [Manifest tài liệu](reference/course_material_manifest.json) ghi tên file, số trang, SHA-256 và phần đã dùng; người nhận dùng bản môn học của mình để đối chiếu. Trang dẫn bên dưới là **trang PDF tính từ 1**, không luôn trùng số slide in trên trang; ví dụ L7 trang PDF 18 in số 17.

## 1. Từng bài đóng góp điều gì?

| Mã | Số trang | Phần đã dùng chính | Kết luận cho RecSysEdu |
| --- | ---: | --- | --- |
| L0 | 12 | 6–10: mục tiêu/đề xuất/yêu cầu/đánh giá đồ án | Phải rõ input/output, phương pháp, nhận xét, báo cáo, prototype và tái sử dụng; chưa có căn cứ biến độ đẹp UI thành ưu tiên đầu |
| L1 | 20 | 8–18: mục tiêu, xếp hạng và họ phương pháp | Chọn một mục tiêu có thể đo; hàm phù hợp để xếp hạng khác với kết luận năng lực |
| L2 | 43 | 7–10, 20–26, 31–38: CF, item similarity, sparsity/cold-start, MF | Giải thích nguồn hành vi; ItemKNN chỉ là ví dụ/baseline tùy chọn; không sao chép ratings 1–5 thành dữ liệu đăng ký |
| L3 | 59 | 15–16, 31–47: biểu diễn ẩn, LightGCN, implicit/explicit, BPR | BPR được dạy trực tiếp; phù hợp xếp hạng từ hành vi quan sát; LightGCN không đồng nghĩa graph tiền đề |
| L4 | 29 | 5–19, 24–27: content/profile, TF-IDF, cosine, Rocchio, hạn chế | Nền Content từ tên/mô tả; chỉ dùng lịch sử train dương; cần kiểm ngôn ngữ/overspecialization |
| L5 | 30 | 6–12, 16–22, 29: nhu cầu, luật/ràng buộc, giải thích, giới hạn tri thức | Tri thức phải có thuộc tính và luật có căn cứ; cảnh báo tiền đề là chuyển dụng sang giáo dục, không công thức có sẵn trong slide |
| L6 | 44 | 6–13, 42–43: phiên, item similarity, association rules, hướng mở rộng | Enrollment dài hạn có thứ tự chưa là session; chưa gắn SASRec/GRU vào lõi chỉ vì có timestamp |
| L7 | 23 | 5–21: các thiết kế lai, trọng số, switching/cascade và hạn chế | Dùng weighted hybrid + fallback; chọn trọng số từ valid, không lắp mọi kiểu lai |
| L8 | 31 | 5–12, 17–30: thiết kế/metric xếp hạng/sparsity/offline | Chỉ số phụ thuộc câu hỏi; chốt định nghĩa evaluator và hạn chế dữ liệu quan sát |
| L9 | 48 | 5–8, 15–16, 46: dữ liệu MIND, impressions, kiến trúc và kết luận | Tham khảo cấu trúc item/user/scoring; chưa có dữ liệu impression tương ứng trong raw đang dùng |
| L10 | 28 | 6–7, 10–15, 19–22, 26: contrastive, views/augmentation, chuỗi ngắn | Chưa có lý do tăng chi phí Transformer/augmentation trong lõi; reordering có thể mất thứ tự, crop/mask ảnh hưởng chuỗi ngắn |

## 2. Đã nhìn công thức/hình nào?

Ảnh kiểm nằm ở `results/local/course_material/renders/`, ngoài Git: L0 p10; L2 p21; L3 p42/p47; L4 p18; L5 p8; L7 p11; L8 p12/p21.

- L0 p10: tiêu chí chất lượng phương pháp/lập luận, báo cáo/trình bày, prototype, khai báo tái sử dụng.
- L2 p21: cosine và biến thể điều chỉnh cho ratings. Dự án không mặc định ratings centered phù hợp ma trận nhị phân.
- L3 p42/p47: tương tác chưa quan sát có thể negative hoặc missing; loss học chênh lệch hai điểm cùng regularization.
- L4 p18: Rocchio có cả phần phản hồi dương/âm. Dữ liệu hiện tại chưa có dislike; dùng phần tổng hợp lịch sử dương, không tạo D- từ mọi khóa chưa đăng ký.
- L5 p8: luật nối nhu cầu và thuộc tính, ràng buộc cứng/mềm. Không suy ra bắt buộc knowledge graph.
- L7 p11: tổng có trọng số; việc chuẩn hóa và tune alpha theo NDCG là quy tắc dự án, không bảo đảm sẵn trong ví dụ.
- L8 p12/p21: xác nhận các diễn đạt Recall/IDCG cần định nghĩa tường minh khi xây evaluator.

## 3. Phân biệt căn cứ môn học và quyết định của nhóm

| Có trong bài giảng | Nhóm lựa chọn/chuyển dụng, còn phải kiểm |
| --- | --- |
| BPR học thứ tự với implicit feedback | Lấy enrollment làm tín hiệu dương; chọn subset, sampler, RecBole, checkpoint và protocol |
| TF-IDF, cosine, profile từ item | Dùng name/about; thử char n-gram 2–4 cho bản nhiều tiếng Trung; fit feature trên train universe |
| Weighted hybrid, switching | Min–max cùng candidate, alpha từ valid, fallback cụ thể |
| Luật/ràng buộc có tri thức | Áp dụng concept-prerequisite làm cảnh báo mềm, cần mapping/label/cycle và không suy thành thạo |
| Precision/Recall/NDCG và giới hạn offline | K=10, one-target holdout, warm benchmark, Coverage bổ sung, freeze D25/test D26 |
| Các mô hình phiên/deep/contrastive | Chưa đưa vào lõi sáu tuần; không có đánh giá cho phép nói chúng sẽ tốt hơn BPR trên dataset này |

## 4. Hai định nghĩa cần làm rõ khi viết evaluator

**Recall:** L8 p9 trình bày tỷ lệ tìm lại các item liên quan; p12 có biến thể chia `min(P_u, K)`. Dự án [05](05_evaluation.md) chọn recall theo số target thật `|G_u|`. Với một target/user và K=10, hai cách cùng mẫu số 1. Khi mở nhiều target, chúng có thể khác: ví dụ 20 target, tìm 5 ở Top-10 thì recall theo `|G_u|` là 0,25, biến thể p12 là 0,5. Phải ghi tên/quy ước, không trộn bảng.

**NDCG:** L8 p21 mô tả h là số item gợi ý đúng trong phần IDCG. Khi triển khai benchmark, dự án chọn danh sách lý tưởng của **toàn bộ ground truth hợp lệ**, giới hạn K: `m = min(K, |G_u|)` và `IDCG = sum(1/log2(r+1), r=1..m)` cho target nhị phân. Không lấy số hit do chính model tìm được làm m, vì mẫu số sẽ phụ thuộc model và bằng 0 khi không tìm được hit. Với một target luôn có `IDCG=1`, miss nhận NDCG=0. Đây là quy ước cần nêu để đối chiếu slide/thư viện; không phải một kết quả thí nghiệm.

Ví dụ kiểm evaluator dự kiến: target ở rank 1 → NDCG=1; rank 2 → khoảng 0,6309; ngoài Top-10 → 0. Dùng những case tính tay này trước khi chạy data lớn. Không thêm test/code trong đợt phân tích này.

## 5. Giới hạn của căn cứ hiện có

- L0 mô tả yêu cầu trong bản slide, chưa xác minh thay đổi theo lớp/học kỳ. Đọc như tiêu chí tham khảo, không như lịch nộp hiện hành.
- Những bảng kết quả NeuMF/LightGCN/MIND/contrastive trong slide là kết quả của tài liệu tương ứng, không của RecSysEdu; không đưa vào Model Lab như run thật.
- Quét metadata chỉ xác nhận chuỗi không rỗng/kiểu dữ liệu/ký tự; chưa xác nhận chất lượng mô tả hoặc phù hợp giáo dục.
- Một tập dữ liệu enrollment không quan sát toàn bộ lựa chọn đã được hiển thị cho user. Khóa chưa đăng ký không tự là negative thực hoặc lựa chọn kém.
- BPR, Content và Hybrid là phương pháp có căn cứ để thử, chưa có bằng chứng chúng cải thiện ở dự án này. Phải triển khai và so sánh đúng trước khi kết luận.

Hướng tổng hợp ở [10](10_course_direction.md); các task điều chỉnh theo [ADR-002](decisions/ADR-002-course-grounded-direction.md). Không chỉnh các PDF nguồn.

Nguồn kỹ thuật bổ sung: [API TfidfVectorizer chính thức](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html), đối chiếu hỗ trợ char analyzer/ngram range. Cấu hình cụm ký tự 2–4 là đề xuất triển khai của dự án, không trích từ bài giảng hoặc nhận là đã kiểm thử trên raw.
