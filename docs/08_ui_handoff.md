# 08 — Những tính năng cần hiển thị và điều kiện có kết quả

Cập nhật 09/10/2026. **Tài liệu này xác định người xem cần biết gì, chưa thiết kế bố cục hoặc màu sắc.** Theo yêu cầu hiện tại, ưu tiên dữ liệu, phương pháp và đánh giá ở [10](10_course_direction.md). App base đã có hai tab bằng fixture SYNTHETIC; đó là mẫu kiểm tra cách đọc file, chưa có thuật toán hay metric thật. Cách mở mẫu ở [09](09_runbook.md).

## 1. Một luồng sử dụng cần giải thích được

```text
Lịch sử đăng ký + nội dung khóa
            ↓
MostPopular / Content / BPR / Hybrid
            ↓
Top-10 + bằng chứng giải thích + thông tin run
            ↓
Người xem biết được nên tham khảo khóa nào và căn cứ là gì

Cùng dữ liệu/split → evaluator → bảng so sánh bốn mô hình
```

Gợi ý học tập và Model Lab là hai nhóm chức năng. Hai tab hiện có là một cách chứa chúng, không phải quyết định bắt buộc về hình thức. Trước khi tích hợp, mỗi kết quả phải có artifact và nguồn tương ứng theo [04](04_data_contract.md).

## 2. Bảy chức năng và kết quả cần thấy

| Chức năng | Đầu vào | Thông tin cần hiển thị | Điều kiện và nguồn |
| --- | --- | --- | --- |
| Lịch sử làm căn cứ | Hồ sơ được chọn | ID/tên khóa đã đăng ký được phép quan sát, phần lịch sử thực sự dùng tạo profile | Dataset/split và history mode; target giữ lại không thành đầu vào |
| Gợi ý khóa tiếp theo | Hồ sơ + model đã có kết quả | Tối đa 10 khóa, tên/ID, rank, nguồn mô hình; thiếu ứng viên thì danh sách ngắn | Ranking artifact; không trùng hoặc chứa khóa đã quan sát |
| Giải thích | Khóa được gợi ý + evidence | Lý do ngắn và bằng chứng đúng model/khóa/hồ sơ | Pipeline xuất reason/evidence; quy tắc ở mục 3 |
| Trường hợp thiếu dữ liệu | Hồ sơ mới/rỗng hoặc model không áp dụng | Gợi ý dự phòng, phương pháp thay thế và lý do | Fallback có quy tắc; không tạo lịch sử giả hoặc nhận là cá nhân hóa khi không có tín hiệu |
| So sánh thí nghiệm | Run của bốn model cùng protocol | NDCG@10, HitRate@10, Coverage@10, cỡ mẫu, thời gian và cấu hình | Evaluator theo [05](05_evaluation.md); chưa chạy thì ghi chưa có |
| Trạng thái và nguồn dữ liệu | Manifest/audit | Mẫu hay thật, bản dataset/split, số đã xử lý, coverage và giới hạn | Audit thật; quy mô toàn kho nguồn không thay số dùng trong thí nghiệm |
| Tiền đề/lộ trình — P1 | Khóa mục tiêu + graph đã kiểm | Concept cần tham khảo, thứ tự, nguồn và trạng thái thiếu dữ liệu | Chỉ thêm nếu mapping/chiều cạnh/nhãn/cycle hợp lệ; không xác nhận thành thạo |

Tên khóa giữ nguyên từ nguồn. Lĩnh vực, thumbnail, thời lượng chỉ hiện nếu có dữ liệu; không tạo thông tin còn thiếu. Điểm model có thể dùng đối chiếu kỹ thuật, nhưng không đổi thành “phù hợp 92%” hoặc xác suất học tốt.

## 3. Giải thích phải đúng phương pháp

| Phương pháp | Có thể nói gì khi có bằng chứng? | Cần lưu gì? |
| --- | --- | --- |
| MostPopular | Khóa có nhiều người đăng ký trong tập train | Số người đăng ký và bản train dùng đếm; không nhận đây là sở thích cá nhân |
| Content TF-IDF | Nội dung gần khóa cụ thể trong lịch sử, ví dụ có dấu hiệu văn bản chung | Khóa lịch sử tham chiếu, độ tương đồng, feature version và dấu hiệu thật đã tính |
| BPR | Mô hình học mẫu đăng ký của cộng đồng để xếp hạng cho hồ sơ này | Model/run ID và mô tả cơ chế; không tự có hàng xóm cụ thể hoặc nguyên nhân user sẽ thích |
| Hybrid | Kết hợp điểm hành vi và nội dung với trọng số đã chọn | Alpha, điểm thành phần đã chuẩn hóa cùng candidate, quy tắc chuẩn hóa và evidence của Content nếu có |
| Fallback | Dùng phương pháp dự phòng vì lịch sử hoặc mô hình thiếu điều kiện | Lý do chuyển và phương pháp thực sự sinh ranking |

Không đọc tên khóa rồi viết một lý do có vẻ hợp lý nhưng không xuất phát từ feature/model. BPR chưa có giải thích riêng vẫn có thể mô tả đúng cơ chế; phải phân biệt mô tả phương pháp với bằng chứng cụ thể cho một khóa.

## 4. Bảng thí nghiệm phải trả lời câu hỏi gì?

**Model nào tìm được lượt đăng ký giữ lại tốt hơn, và kết quả có tái lập được không?** So sánh MostPopular, Content, BPR, Hybrid khi cùng dataset/split/cohort/candidate/seen policy. Nếu điều kiện khác, tách bảng và giải thích. Điểm raw BPR và cosine Content không so trực tiếp để kết luận model nào tốt hơn.

Mỗi bảng kèm run ID, model/config, dataset/split version, cohort/cỡ mẫu, candidate policy, seed và valid/test. Trong tuần 1–5, chỉ dùng valid để chọn tham số; test cuối từ D26 sau khi khóa config D25. Một target/user thì Recall@10 trùng HitRate@10, không tính thành hai bằng chứng độc lập. Coverage không tự đo đa dạng trong từng danh sách.

Metric chưa chạy là “chưa có”, không là 0 hoặc số mô phỏng. Một metric bằng 0 sau evaluator vẫn là kết quả hợp lệ. Số liệu offline chưa chứng minh người học hoàn thành hoặc tiến bộ. Model Lab đọc kết quả đã chạy; MVP không cần nút train.

Thời gian train/chấm và dung lượng artifact nằm trong run manifest/báo cáo. Nếu snapshot v1 chưa chứa trường cần hiển thị, mở rộng schema cùng exporter/loader/fixture khi tích hợp; không tự suy hoặc tạo trường giả từ UI.

## 5. Tiền đề và lộ trình chỉ thêm khi đủ nguồn

| Trạng thái pipeline | Diễn đạt dễ hiểu |
| --- | --- |
| `missing_exposure` | Có tiền đề chưa có dấu hiệu tiếp xúc |
| `no_missing_exposure` | Chưa phát hiện tiền đề cần ôn trong dữ liệu hiện có |
| `no_observed_prerequisite` | Chưa thấy thông tin tiền đề cho khóa trong graph |
| `unknown` | Chưa đủ dữ liệu tiền đề |

Các nhãn không xác nhận năng lực. Đăng ký khóa chưa chứng minh đã biết concept. Vòng lặp phải báo bị chặn; path bị giới hạn độ dài phải báo còn phần chưa hiển thị. Không viết path thủ công rồi gọi là kết quả graph. Base hiện dùng `paths=[]`; phải cập nhật contract và kiểm tra trước khi nhận path thật.

## 6. Trạng thái cần xử lý để người khác không hiểu nhầm

- Không có lịch sử: giải thích fallback; không điền khóa giả vào hồ sơ.
- Chưa có model hoặc metric: ghi chưa có kết quả; không hiện như đã train.
- Không đủ ứng viên: trả danh sách ngắn và ghi lý do.
- Thiếu graph/mapping: ghi chưa đủ thông tin; không khẳng định “có thể bắt đầu”.
- Artifact sai, thiếu hoặc khác version: báo lỗi cụ thể; không âm thầm chuyển sang mẫu.
- Đổi hồ sơ/model/snapshot: ranking, giải thích và nguồn phải cập nhật cùng nhau.

Nhãn SYNTHETIC/REAL phải rõ. Metric offline và ranking trình diễn phải có history mode; không lấy target offline làm lịch sử để tạo gợi ý rồi nhận đó là kết quả đánh giá.

## 7. Bàn giao qua GitHub và thời điểm tích hợp

| Nhóm việc | Đầu ra giao cho phần tiếp theo |
| --- | --- |
| Dữ liệu | Parquet hợp lệ, raw/dataset/split manifest, audit và rejects |
| Phương pháp/đánh giá | Feature/checkpoint, ranking/reason/evidence, metrics và run manifest |
| Hiển thị kết quả — M10 | Đọc snapshot, thể hiện đúng các chức năng/trạng thái trên |
| Báo cáo/tái lập | Cấu hình, hướng dẫn chạy, bảng thí nghiệm, kết luận và giới hạn |

Đây là nhóm việc, không yêu cầu bốn người. Theo [plan](../tasks/plan.md) và [CONTRIBUTING](../CONTRIBUTING.md), nhận issue có đầu vào/đầu ra rõ; dùng PR nhỏ. Git chỉ chứa source/config/fixture nhỏ, không chứa raw hay checkpoint lớn.

**Tuần 1–4:** dữ liệu, evaluator, Content, BPR, Hybrid và phân tích; P1 khảo sát có điều kiện. **Tuần 5:** M10 ghép artifact thật vào demo tối thiểu; khóa config D25. **Tuần 6:** thêm test cuối, báo cáo và tái lập. Không phát triển thêm bố cục UI trong đợt phân tích hiện tại.

`demo_bundle.json` ở [04, mục 6](04_data_contract.md) là contract thống nhất. UI nhận kết quả đã tính; không tự làm thuật toán hoặc đọc toàn raw. Bản [HTML tham khảo](reference/learnpath_ui_prototype.original.html) giữ để truy nguồn đề xuất cũ; màu sắc, thanh điểm, metric và nhãn “ready” trong đó chưa là yêu cầu hiện hành hoặc bằng chứng kết quả.

## 8. Nghiệm thu chức năng M10 sau khi lõi chạy

- [ ] Có ít nhất ba hồ sơ và một trường hợp mới; mẫu/thật rõ ràng.
- [ ] Ranking đúng hồ sơ/model/run; không trùng hoặc chứa khóa đã quan sát.
- [ ] Giải thích đúng bằng chứng và phương pháp; không biến điểm thành tỷ lệ phù hợp.
- [ ] Fallback được ghi rõ; thiếu model/metric/artifact báo đúng trạng thái.
- [ ] Bảng so sánh có nguồn và điều kiện tương thích; không dùng số mẫu làm metric thật.
- [ ] P1 chưa đạt thì ghi thiếu dữ liệu; nếu đạt có nguồn và xử lý cycle/truncated.
- [ ] Người khác chạy demo từ snapshot theo runbook, không bắt buộc train lại.

Các ô là tiêu chí tương lai, chưa là bằng chứng đã đạt. Đợt này chỉ phân tích chức năng và sửa tài liệu, không thay code giao diện.
