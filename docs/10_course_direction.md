# 10 — Hướng làm đồ án từ tài liệu môn Hệ gợi ý

Cập nhật 09/10/2026. **Đây là tài liệu nên đọc trước khi tiếp tục code.** Bản này giải thích bài toán và lựa chọn phương pháp; không phải kết quả mô hình đã chạy. Căn cứ theo 11 bài giảng người dùng cung cấp, được đối chiếu theo trang ở [11 — Ghi chú nguồn](11_course_reading_notes.md).

## 1. Hướng đề xuất trong một đoạn

Làm **hệ gợi ý khóa học cá nhân hóa từ lịch sử đăng ký trên MOOCCubeX**. Mỗi người học nhận tối đa 10 khóa chưa đăng ký. Dùng hai nguồn thông tin: **hành vi của cộng đồng** và **nội dung khóa học**. So sánh MostPopular, Content TF-IDF, BPR và Hybrid trên cùng tập dữ liệu. Nếu quan hệ kiến thức đủ tin cậy, bổ sung thông tin cần ôn trước khóa học như một phần riêng. Việc cần chứng minh là thuật toán tìm và xếp hạng lượt đăng ký giữ lại tốt đến đâu; chưa đo người học tiến bộ hoặc hoàn thành khóa.

Chuỗi công việc: **mô tả bài toán → chuẩn bị dữ liệu → phương pháp → đánh giá → xác định kết quả cần hiển thị → giao diện tối thiểu**. Base UI đã có chỉ là mẫu tham khảo; hiện không dành thêm công việc cho bố cục, màu sắc hoặc mở trang mới.

## 2. Môn học yêu cầu đồ án chứng minh điều gì?

L0, trang PDF 6 và 8–10, nhấn mạnh việc mô hình hóa bài toán, chọn giải pháp phù hợp, trình bày đầu vào/đầu ra, phương pháp, khó khăn, nhận xét và hệ thống thử nghiệm. Chất lượng phương pháp, lập luận, báo cáo và trình bày đều là tiêu chí. Một prototype dễ dùng là một phần của đồ án; nhiều màn hình không tự tạo bằng chứng thuật toán tốt.

Đây là nội dung trong bộ slide được cung cấp, chưa xác nhận quy định lớp hiện tại. Yêu cầu nộp PDF/source nén và thời lượng trình bày trong L0 là thông tin để chuẩn bị hồ sơ, không phải lệnh tự động tạo/nộp/gửi tài liệu.

| Câu hỏi người chấm cần được trả lời | Đồ án này trả lời bằng gì? |
| --- | --- |
| Giải quyết khó khăn nào? | Người học có nhiều khóa để chọn; cần rút ngắn việc tìm khóa gần sở thích thể hiện qua đăng ký |
| Dữ liệu có gì và có thể suy ra gì? | Người–khóa–thời gian, tên/mô tả; đăng ký là dấu hiệu quan tâm, không là rating hoặc năng lực |
| Vì sao chọn phương pháp? | L3 có BPR cho phản hồi ngầm; L4 có biểu diễn nội dung; L7 có lai trọng số |
| Đã cài phần nào? | Tự viết cleaning/split/evaluator/Content/Hybrid và kết nối BPR qua thư viện; báo rõ phần tái sử dụng |
| Phương pháp tốt đến đâu? | So sánh chung NDCG@10/HitRate@10, độ phủ và chi phí chạy; phân tích trường hợp thất bại |
| Người xem hệ thống nhận được gì? | Danh sách gợi ý, lịch sử làm căn cứ, giải thích có nguồn và bảng thí nghiệm |

Không cần đưa mọi thuật toán L0–L10 vào một đồ án. Cần cho thấy mình hiểu vì sao một số thuật toán phù hợp và một số chưa phù hợp với dữ liệu/mục tiêu hiện tại.

## 3. Phát biểu bài toán cụ thể

**Người dùng:** người học trong kho dữ liệu, được đại diện bằng ID và lịch sử đăng ký. **Đối tượng gợi ý:** khóa học, không phải video, bài tập hay concept. **Đầu vào:** các khóa đã được quan sát, danh mục khóa và mô hình đã học từ dữ liệu train. **Đầu ra:** danh sách Top-10 chưa đăng ký, thứ hạng, nguồn mô hình, lý do nếu có bằng chứng. Có thể ít hơn 10 khi không đủ khóa ứng viên.

Ví dụ giả: người A đăng ký khóa Python và cơ sở dữ liệu. Nội dung cho biết A có lịch sử gần chủ đề lập trình; hành vi cộng đồng có thể cho thấy những mẫu đăng ký liên quan đến phân tích dữ liệu. Hai tín hiệu có thể cùng đưa một khóa lên cao hoặc bất đồng. Phải tính và đánh giá để biết có hữu ích; không lấy ví dụ này làm kết quả thật.

Hai kịch bản cần tách:

- **Thí nghiệm offline:** che một lượt đăng ký có thật, kiểm tra mô hình có đưa khóa đó vào Top-10 không. Đây là căn cứ so sánh thuật toán.
- **Trình diễn chức năng:** chọn một hồ sơ và xem kết quả đã tính. Đây là minh họa cách sử dụng, không tự chứng minh người thật thích hoặc học tốt hơn.

Theo L1 trang 8–12, mục tiêu và tiêu chí thành công phụ thuộc bài toán. Ở đây chọn **xếp hạng khóa có khả năng được đăng ký**, không chọn dự đoán điểm 1–5, tối đa doanh thu, xác nhận năng lực hoặc chứng minh hiệu quả giáo dục.

## 4. Dữ liệu hiện có cho phép làm gì?

Đã tải/audit hai file user/course; hash và quy mô tại [báo cáo raw](../results/data_audit.md). Kiểm thêm metadata toàn catalog ngày 09/10/2026, có [bản đếm JSON và source hash](../results/course_metadata_audit.json):

| Tín hiệu | Đã quan sát | Hệ quả đối với hướng làm |
| --- | --- | --- |
| Đăng ký nối được người–khóa | 11.523.119 cặp; 3.330.294 người | Đủ cơ sở khảo sát CF và chọn subset; chưa cần log video/bài tập |
| Ứng viên có ≥3 khóa và mốc cuối tách biệt | 678.126 người | Chọn pilot 10.000 người từ nhóm đủ lịch sử; còn kiểm cold-item và split |
| Khóa có tên không rỗng | 3.781/3.781 | Có đầu vào cho Content ở toàn catalog |
| Khóa có mô tả `about` không rỗng | 3.692/3.781, khoảng 97,65% | Tên + mô tả đáng thử làm nền Content; không mặc định văn bản đều chất lượng tốt |
| Khóa có nhãn lĩnh vực trong raw | 547/3.781, khoảng 14,47% | Không dùng field-only làm mô hình Content chính trên toàn catalog |
| Tên có ký tự Hán | 3.398/3.781 | Xử lý ngôn ngữ phù hợp; không mặc định tách từ bằng khoảng trắng như tiếng Anh |
| Múi giờ trong timestamp | Chưa xác định; không có offset | Chưa tự chuyển UTC hoặc phát hành timestamp Unix/split |
| Concept/prerequisite | Chưa tải và audit trong base | Chưa cam kết có lộ trình hoặc đủ thông tin tiền đề |

Số mô tả không rỗng là số chuỗi raw, chưa là chất lượng văn bản sau cleaning. Không dịch toàn dataset hoặc làm mô hình ngôn ngữ lớn chỉ để mở được Content. Giữ tên nguồn; mô tả phương pháp và nhãn giao diện có thể viết tiếng Việt.

**Điều chỉnh quan trọng:** tài liệu cũ chọn Content field-only. Căn cứ L4 và coverage thật, thay cấu hình chính bằng **TF-IDF từ tên/mô tả + cosine**, còn field là thông tin bổ sung hoặc thí nghiệm phụ. Xem [ADR-002](decisions/ADR-002-course-grounded-direction.md).

## 5. Các thuật toán và vai trò của chúng

### MostPopular — mốc đơn giản

Đếm số người đăng ký mỗi khóa trong train; loại khóa user đã được phép quan sát, rồi lấy đầu danh sách. Nó không cá nhân hóa về sở thích, nhưng là mốc để kiểm mô hình phức tạp có đem lại lợi ích. Không đếm toàn raw vì sẽ sử dụng lượt đăng ký của valid/test.

### Content — dùng nội dung, theo L4

TF-IDF là cách đổi văn bản thành vector số, tăng vai trò của dấu hiệu đặc trưng và giảm dấu hiệu xuất hiện quá phổ biến. Cosine đo hai vector gần nhau. L4 trang 5–18 mô tả item, profile người dùng, TF-IDF, cosine và cách tổng hợp phản hồi.

Quy trình đề xuất:

1. Tạo văn bản từ `name` và `about`; xử lý giá trị thiếu/HTML, chuẩn hóa Unicode và khoảng trắng, giữ nguồn.
2. Với bản chứa nhiều tiếng Trung, thử TF-IDF theo **cụm ký tự 2–4 ký tự** để chưa phải thêm công cụ tách từ. Đây là lựa chọn kỹ thuật của dự án, không phải cấu hình bắt buộc trong slide; đo và kiểm trên valid.
3. Học vocabulary/IDF từ metadata của khóa thuộc universe train đã chốt; lưu vectorizer và feature version. Khóa ngoài train được transform bằng bộ đó trong thí nghiệm cold riêng. Không dùng lượt đăng ký valid/test để fit hoặc tạo profile.
4. Profile user là trung bình vector của các khóa train của chính user; chấm cosine với khóa ứng viên chưa quan sát.
5. Vector/profile rỗng thì chuyển sang MostPopular và ghi lý do. Nhãn field khi có dùng để diễn giải/bổ sung; không điền field giả cho khóa thiếu.

Tham chiếu triển khai: [TfidfVectorizer — scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html) hỗ trợ `analyzer='char'` và `ngram_range=(2, 4)`. Đây là cấu hình thử; phiên bản thư viện/dependency sẽ khóa khi thực hiện M4. Tài liệu API không chứng minh cấu hình này tốt hơn tách từ trên MOOCCubeX.

Chỉ có tín hiệu đăng ký dương, nên chưa dùng phần phản hồi âm của Rocchio. “Chưa đăng ký” không có nghĩa “không thích”. Phần giải thích có thể dẫn khóa lịch sử giống nội dung nhất và dấu hiệu chung thực sự được tính, không tự bịa sở thích.

### BPR — dùng hành vi cộng đồng, theo L3

L3 trang 39–47 phân biệt phản hồi ngầm/rõ ràng và trình bày Bayesian Personalized Ranking. Đăng ký trong dữ liệu này được mô hình hóa như **phản hồi ngầm**: có hành vi, nhưng không có mức thích 1–5.

Với user u, lấy khóa i đã đăng ký trong train và một khóa j chưa quan sát trong train; học để điểm i cao hơn j. j là mẫu so sánh theo giả định của thuật toán, không phải bằng chứng user ghét j. BPR với phân tích ma trận học vector user/khóa; điểm là tích của hai vector.

```text
score(u, i) = vector_user(u) · vector_course(i)
loss_pair   = -log(sigmoid(score(u, i) - score(u, j))) + regularization
```

Regularization hạn chế mô hình học quá sát dữ liệu train. Trong triển khai, dùng RecBole để giảm công việc huấn luyện, nhưng nhóm phải hiểu loss, sampling, ID map, split, checkpoint và evaluator. Không coi việc gọi thư viện là toàn bộ đóng góp.

BPR thuần không tự có embedding đã học cho người/khóa mới. Chỉ so sánh benchmark warm với target có dữ liệu train; người mới dùng fallback. Không nói BPR tìm hàng xóm cụ thể rồi diễn giải một cộng đồng giả.

### Hybrid — kết hợp hai tín hiệu, theo L7

L7 trang 10–14 có lai song song dùng trọng số và chuyển đổi phương pháp khi thiếu dữ liệu. Chọn cách dễ kiểm tra:

```text
Hybrid = alpha × normalized_BPR + (1 - alpha) × normalized_Content
```

Hai thành phần chấm **cùng tập ứng viên** của user/run, rồi chuẩn hóa theo quy tắc ở [03](03_architecture.md). Thử alpha trên valid, không mặc định 0,5 tốt nhất và không tune trên test. Nếu một thành phần không chạy được vì hồ sơ mới/rỗng, chuyển Content hoặc MostPopular theo quy tắc rõ ràng.

Nếu alpha tốt nhất là 0 hoặc 1, báo rằng kết hợp chưa giúp ở thí nghiệm đó. Hai danh sách nằm cạnh nhau trên màn hình chỉ minh họa so sánh; chưa phải Hybrid đã tính.

### ItemKNN — ví dụ học/đối chiếu tùy chọn từ L2

L2 trang 20–24 mô tả CF dựa trên item. Có thể làm ví dụ nhỏ: khóa thường được cùng người đăng ký có vector hành vi tương đồng. **Content cũng dùng cosine nhưng vector đến từ văn bản; ItemKNN dùng vector đến từ người đăng ký.** Đây là khác biệt quan trọng khi giải thích môn học.

Không thêm ItemKNN thành mô hình bắt buộc thứ năm. Nếu còn thời gian, thử như baseline phụ sau evaluator; nếu không, dùng ví dụ tính tay trong báo cáo. Không chuyển nguyên công thức Pearson/mean-centered ratings 1–5 sang dữ liệu nhị phân toàn giá trị dương.

## 6. Tri thức và lộ trình thuộc phần nào?

L5 trang 6–10 nói về tri thức kết nối **nhu cầu người dùng** với **thuộc tính sản phẩm**, gồm ràng buộc cứng và mềm; trang 16–19 có cách giải thích và xử lý khi không có kết quả. Nó không yêu cầu mọi hệ gợi ý tri thức đều phải có knowledge graph.

Với đồ án này, tri thức có thể hỗ trợ hai việc sau khi lõi đạt:

- Nhu cầu/lĩnh vực đã chọn có thể là điều kiện lọc, nếu metadata được xác minh. Đây là kịch bản khai báo nhu cầu, tách khỏi benchmark chỉ dùng lịch sử.
- Quan hệ concept tiền đề có nguồn giúp nêu kiến thức nên tham khảo trước khóa mục tiêu. Thiếu bằng chứng tiếp xúc chỉ là cảnh báo mềm, không phải kết luận không đủ năng lực hoặc điều kiện cấm đăng ký.

**Ba quan hệ không được nhầm:** đồ thị user–course của LightGCN (L3) mô tả tương tác; co-enrollment mô tả cùng đăng ký; graph concept-prerequisite mô tả trước–sau về kiến thức. Không lấy khóa hay được đăng ký chung làm tiền đề học thuật. Prerequisite văn bản cũng không tự là cạnh graph đã kiểm chứng.

P1 chỉ bật sau kiểm ID mapping, chiều cạnh, nhãn và cycle. Chọn khóa mục tiêu rồi xuất thứ tự concept/tài nguyên tham khảo là chức năng riêng; không hứa lộ trình tối ưu, thời gian hoàn thành hay xác nhận kiến thức đã biết.

## 7. Phần nào trong môn học chưa đưa vào lõi?

| Bài giảng | Dùng thế nào trong đồ án? |
| --- | --- |
| L0 | Khung phát biểu bài toán, báo cáo, prototype và khai báo thư viện tái sử dụng |
| L1 | Xác định mục tiêu, nguồn dữ liệu và tiêu chí thành công |
| L2 | Giải thích CF cơ bản, dữ liệu thưa/cold-start; ItemKNN tùy chọn |
| L3 | BPR là CF chính; LightGCN/NeuMF là hướng phát triển sau lõi |
| L4 | Nền của Content TF-IDF, profile/cosine và giới hạn chuyên môn hóa quá mức |
| L5 | Căn cứ cho nhu cầu/ràng buộc/giải thích; ứng dụng tiền đề là phần chuyển sang giáo dục của dự án |
| L6 | Tách gợi ý phiên khỏi lịch sử dài hạn; enrollment có thứ tự chưa là phiên truy cập |
| L7 | Lai trọng số + chuyển phương pháp dự phòng, giữ thiết kế đơn giản |
| L8 | Thiết kế thí nghiệm, chỉ số xếp hạng, thưa dữ liệu và giới hạn offline |
| L9 | Học cách tách item/user/scoring; chưa chuyển mô hình tin tức sang khóa học vì không có impression/click tương ứng |
| L10 | Hướng cải thiện biểu diễn sau này; chưa thêm augmentation/Transformer/contrastive loss vào sáu tuần |

Không cần GRU/BERT/LLM hoặc Spark để chứng minh bốn mô hình đầu. Chỉ tăng độ phức tạp khi kết quả hoặc câu hỏi nghiên cứu yêu cầu.

## 8. Đánh giá theo L8: chứng minh gì, chưa chứng minh gì?

Giữ protocol cụ thể ở [05](05_evaluation.md). L8 đưa nhiều cách đánh giá; dự án chọn cách phù hợp với Top-10 từ phản hồi ngầm:

- NDCG@10 chính: khóa giữ lại xuất hiện gần đầu danh sách không?
- HitRate@10: bao nhiêu người có khóa giữ lại trong 10 gợi ý? Với một target/user, Recall@10 trùng HitRate@10; không xem là hai bằng chứng độc lập.
- Coverage@10: mô hình gợi ý bao nhiêu khóa khác nhau trong universe chung? Đây là chỉ số dự án bổ sung để xem có dồn vào vài khóa phổ biến; không tự là diversity của từng danh sách.
- Thời gian train, thời gian chấm và dung lượng artifact: có chạy/bàn giao được trên subset không?

Không lấy MAE/RMSE của rating làm chỉ số chính khi không có rating thật. Không lấy metric offline làm tỷ lệ hoàn thành hoặc hiệu quả học tập. L8 trang 29–30 nêu giới hạn offline và khác biệt với kiểm tra người dùng thực.

**Câu hỏi báo cáo:** E1: BPR/Content hơn hoặc kém MostPopular ra sao? E2: Hybrid có bổ sung tín hiệu so với từng thành phần không? E3 nếu P1 đạt: rerank tiền đề thay đổi ranking ra sao, có nguồn và độ phủ thế nào? E4: khác biệt với người ít/nhiều lịch sử? Mã khớp [05, mục 7](05_evaluation.md). Thất bại/không cải thiện phải được phân tích, không giấu bằng đổi cohort/test.

Các công thức trong slide có biến thể hoặc diễn đạt cần chốt khi viết evaluator. [Ghi chú nguồn, mục 4](11_course_reading_notes.md) nêu rõ Recall và IDCG để tránh chép máy móc.

## 9. Những tính năng phải hiển thị, chưa quyết định bố cục UI

| Chức năng | Đầu vào | Kết quả cần thấy | Nguồn kết quả và điều kiện |
| --- | --- | --- | --- |
| Xem lịch sử | Hồ sơ được chọn | Khóa đã đăng ký được phép quan sát | Split/history mode; không dùng target làm lịch sử |
| Gợi ý cá nhân hóa | Hồ sơ + model đã chạy | Top-10, tên/ID, thứ hạng; không có khóa đã quan sát | Ranking artifact từ pipeline |
| Giải thích | Khóa gợi ý + evidence | Nội dung gần lịch sử, hoặc mô tả cơ chế CF/kết hợp có nguồn | Content có bằng chứng cụ thể; BPR không bịa hàng xóm/nhân quả |
| Người mới/thiếu dữ liệu | Lịch sử rỗng hoặc model không áp dụng | Danh sách dự phòng và lý do dùng dự phòng | MostPopular/Content; không nhận cá nhân hóa nếu thiếu tín hiệu |
| So sánh thí nghiệm | Các run cùng protocol | Chỉ số, cỡ mẫu, model/config, thời gian và kết luận | Evaluator; metric chưa chạy phải báo chưa có |
| Trạng thái dữ liệu | Manifest/audit | Nguồn, bản dữ liệu, coverage và giới hạn | Audit thật; số quy mô nguồn không thay số đã xử lý |
| Tiền đề/lộ trình — P1 | Khóa mục tiêu + graph đã kiểm | Concept nên ôn, thứ tự tham khảo, nguồn/unknown/cycle | Graph mapping và kiểm tra; không xác nhận thành thạo |

Hai tab hiện tại chỉ là một cách chứa các chức năng. Không lấy việc đã có tab làm bằng chứng đã có thuật toán. Đặc tả chức năng và nghiệm thu ở [08](08_ui_handoff.md).

## 10. Sáu tuần nên tạo ra kết quả theo thứ tự nào?

| Tuần | Việc chính | Bằng chứng để chuyển tiếp |
| --- | --- | --- |
| 1 | Chốt bài toán/protocol, timezone, metadata và subset; cleaning/split; thử BPR rất nhỏ | Dataset/split/manifest hợp lệ, không rò rỉ target; môi trường BPR có thể chạy |
| 2 | Evaluator tính tay + MostPopular + Content TF-IDF | Hai baseline cùng valid; có ví dụ giải thích bằng feature thật |
| 3 | BPR rồi Hybrid; chọn alpha bằng valid | Bốn model cùng protocol; checkpoint reload; kết quả kể cả khi Hybrid không hơn |
| 4 | Phân tích lỗi/ít-nhiều lịch sử; khảo sát P1 tri thức | Core report rõ; graph đủ nguồn thì làm case, thiếu thì ghi chưa đạt |
| 5 | Ghép các kết quả đã có vào demo tối thiểu; khóa config D25 | Tính năng chỉ hiển thị artifact thật, trạng thái/fallback chính xác |
| 6 | Chạy test cuối từ D26; phân tích, báo cáo, tái lập và bàn giao | Bảng thí nghiệm + code/config/hướng dẫn, kết luận đúng giới hạn |

Ngày chi tiết ở [lịch sáu tuần](../tasks/six_week_schedule.md); task kỹ thuật ở [plan](../tasks/plan.md). Màu sắc/bố cục không là đầu ra của tuần 1–4. Phiên tiếp theo ưu tiên **M1–M2: dữ liệu/split**, theo [kickoff](../tasks/kickoff.md); không thêm tính năng UI trong lúc hướng phương pháp chưa rõ.
