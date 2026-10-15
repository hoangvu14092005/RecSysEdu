# 05 — So sánh mô hình thế nào cho công bằng?

Cập nhật: 09/10/2026. Đây là quy tắc đánh giá dự kiến, chưa có metric thật. Chỉ số đo khả năng tìm lượt đăng ký được giữ lại; chưa đo năng lực hoặc hiệu quả học tập. Thuật ngữ ở [trang bắt đầu](README.md).

Căn cứ L8 và điểm cần chốt so với slide ở [11, mục 4](11_course_reading_notes.md). Dự án chọn Top-10 từ enrollment, không dùng MAE/RMSE của ratings làm chỉ số chính. Coverage đo độ phủ catalog, không thay diversity trong một danh sách.

## 1. Ý tưởng qua một ví dụ

Một user đăng ký A → B → C → D theo thời gian khác nhau. Dùng A/B để học mô hình (**train**), giữ C để chọn tham số (**valid**), giữ D để kiểm tra cuối (**test**). Không cho model nhìn C/D khi học profile.

Mục tiêu kiểm tra: khóa giữ lại có nằm trong Top-10 không, và đứng ở vị trí nào? Bốn model phải có cùng user, target, danh sách khóa được chấm và quy tắc loại khóa đã quan sát.

## 2. Cách chia dữ liệu

Sau làm sạch/gộp trùng, user cần ít nhất ba khóa khác nhau. Lượt cuối là test, áp chót là valid, phần trước là train. Hai ranh giới train→valid→test phải tăng thời gian nghiêm ngặt. Timestamp bằng nhau tại ranh giới thì cách ly khỏi nhóm temporal và thống kê; không dùng ID để bịa thứ tự.

| Giai đoạn | Model/profile/tiếp xúc concept lấy từ đâu? | Khóa bị loại khỏi gợi ý |
| --- | --- | --- |
| Valid | Train | Train của user |
| Test | Vẫn train, giữ model/param đã chọn | Train + valid của user |

Valid ở test chỉ dùng để biết khóa đã quan sát và loại khỏi gợi ý, không dùng cập nhật profile/retrain. Test target luôn được giữ trong candidate khi thuộc benchmark. Muốn retrain bằng train+valid phải tạo protocol riêng và áp dụng cho mọi model.

**Giới hạn cần ghi trong báo cáo:** cách chia trên tránh nhìn tương lai của chính user, nhưng train của user khác có thể xảy ra sau test của user này. Catalog/metadata tĩnh cũng chưa có availability theo thời gian. Muốn mô phỏng dự đoán tại thời điểm thực cần thí nghiệm riêng với mốc toàn cục T1/T2 và availability khóa; không trộn hai bảng metric.

## 3. Nhóm người và danh sách khóa

Benchmark chính là **warm-start**: user có train và target có tương tác train ở toàn bộ dataset. Universe gồm khóa đã có tương tác train, rồi loại các khóa đã quan sát theo bảng trên. Lưu cohort valid/test riêng; mọi model dùng cùng cohort của split đó.

Target chưa có tương tác train là **cold-item**, báo số lượng và đánh giá Content/fallback riêng nếu làm. Không đưa embedding BPR chưa học vào rồi nhận đã giải quyết cold-start.

Ưu tiên **full ranking**: chấm toàn bộ universe chung. Candidate union Top-50/model chỉ là tối ưu demo có kiểm tra candidate recall riêng; không đem so trực tiếp với full ranking. Nếu buộc chấm mẫu, khóa cùng candidate file/seed cho mọi model và ghi protocol khác.

Loại ID lạ, padding RecBole và duplicate. Điểm bằng nhau: course ID tăng dần. K=10; ít hơn 10 candidate vẫn trả danh sách ngắn và báo số user gặp trường hợp đó, không chèn khóa giả.

## 4. Chỉ số cần hiểu

| Chỉ số | Câu hỏi nó trả lời |
| --- | --- |
| NDCG@10 — chính | Khóa đúng có đứng gần đầu danh sách không? |
| HitRate@10 | Bao nhiêu user có target nằm trong Top-10? |
| Recall@10 | Tìm được bao nhiêu target giữ lại? |
| Precision@10 | Bao nhiêu trong 10 vị trí là target? |
| Coverage@10 | Có bao nhiêu khóa khác nhau được gợi ý so với universe? |

Với **một target/user**, Recall = HitRate; Precision = HitRate/10. Không trình bày chúng như ba bằng chứng độc lập. NDCG cho một target ở rank 1 là 1, rank 2 khoảng 0,6309, ngoài Top-10 là 0. Đây là ví dụ tính tay, không phải kết quả model.

### Công thức cho người viết evaluator

Với `G_u` là target của user, `R_u` là tối đa K gợi ý:

```text
Hit@K(u)       = 1 nếu R_u giao G_u khác rỗng, ngược lại 0
Recall@K(u)    = |R_u giao G_u| / |G_u|
Precision@K(u) = |R_u giao G_u| / K
DCG@K(u)       = tổng rel(rank) / log2(rank + 1), rank bắt đầu từ 1
NDCG@K(u)      = DCG@K(u) / IDCG@K(u)
IDCG@K(u)      = tổng 1 / log2(rank + 1), rank từ 1 đến min(K, |G_u|)
Coverage@K    = số course khác nhau được gợi ý / số course trong universe
```

Lấy trung bình mỗi user với trọng số bằng nhau. Precision vẫn chia K dù danh sách ngắn; Coverage dùng universe chung trước seen mask. Evaluator dự án là nguồn so sánh; đối chiếu RecBole chỉ khi ID/candidate/mask giống nhau. [RecBole evaluation settings](https://recbole.io/docs/user_guide/config/evaluation_settings.html).

IDCG lấy từ ground truth hợp lệ, không từ số hit model tìm được. Miss vẫn có IDCG=1 trong protocol một target, NDCG=0. Recall dùng mẫu số `|G_u|`; biến thể chia `min(|G_u|, K)` ở L8 p12 cho cùng kết quả khi một target, nhưng cần tách định nghĩa nếu mở nhiều target.

## 5. Chọn tham số và thời điểm mở test

Trong tuần 1–5, chỉ dùng valid để chọn cấu hình. Khóa dataset/cohort/seed/alpha/lambda ở **D25**. Chạy test chính thức từ **D26**; Model Lab không mở test sớm để tuning.

BPR dùng enrollment dương. Negative sampling lấy trong universe train và loại positive train của user; không dùng target valid/test để chỉnh sampler cho có lợi. Ghi sampler/seed/config.

Budget ban đầu: BPR tối đa 6 cấu hình; alpha `{0, 0.25, 0.5, 0.75, 1}`; nếu P1 bật, lambda `{0, 0.1, 0.2}`. Đây là tập thử, chưa phải tham số tối ưu. Alpha 0/1 tốt nhất thì báo kết hợp chưa có lợi.

Thử một seed trước; tối đa ba seed cuối cho BPR nếu thời gian đo được cho phép. Có nhiều seed thì báo mean/std; một run phải ghi rõ một run. Nếu tính khoảng tin cậy, dùng paired bootstrap theo user và mô tả cách tính. Không nhận chênh lệch nhỏ là chắc chắn khi chưa có bằng chứng.

## 6. P1: tiền đề và lộ trình

Concept là một khái niệm, ví dụ đệ quy. Cạnh A→B nghĩa là A cần trước B theo nguồn graph. Lịch sử đăng ký chỉ tạo tập concept **có dấu hiệu tiếp xúc**, không phải đã biết.

Gọi `C(course)` là concept của khóa, `E(user)` là concept từ khóa train đã đăng ký:

```text
P_direct(course) = {p: có cạnh p → c, c thuộc C(course)} trừ C(course)
missing(course)  = P_direct(course) trừ E(user)
missing_ratio   = |missing| / |P_direct|, khi mẫu số > 0
```

Penalty dùng tiền đề trực tiếp. Không có mapping là unknown; có mapping nhưng không thấy cạnh là `no_observed_prerequisite`; penalty 0 trong hai trường hợp nhưng trạng thái khác nhau. Báo coverage và chỉ lấy trung bình missing ratio trên khóa có tiền đề được quan sát, kèm mẫu số/số unknown.

Path dùng các concept tổ tiên của mục tiêu, bỏ concept mục tiêu khỏi phần tiền đề, giữ phần cần bổ sung, sắp thứ tự trước–sau rồi nối mục tiêu. Course liên quan được gắn như tài nguyên tham khảo, không gọi là quan hệ course-prerequisite đã xác nhận.

Thứ tự topo phải ổn định; tối đa 20 concept, còn phần chưa hiện thì `truncated`. Vòng lặp trong phần liên quan thì `cycle_blocked`; không âm thầm xóa cạnh. Kiểm 3–5 case có nguồn nếu dữ liệu đủ; báo độ phủ, số bước, tỷ lệ tạo được/thất bại.

Giảm missing ratio trên graph dùng để rerank chỉ chứng minh thuật toán làm đúng chỉ báo đó. Chưa chứng minh học tốt hơn. Nếu review case, ghi người đánh giá/tiêu chí/giới hạn; học tập thực cần nghiên cứu riêng.

## 7. Bảng thí nghiệm tối thiểu

| Mã | So sánh | Điều kiện |
| --- | --- | --- |
| E1 | MostPopular / Content / BPR | Cùng split/cohort/universe/mask |
| E2 | BPR / Content / Hybrid | Alpha chọn từ valid |
| E3 — P1 | Hybrid / Hybrid + tiền đề | Cùng graph-covered cohort, có lambda=0 |
| E4 | Ít / nhiều lịch sử | Ít: 1–3 khóa train; nhiều: từ 4; báo cỡ mẫu |
| E5 — tùy chọn | Full ranking / candidate union | Tách bảng, đo candidate recall và thời gian |

Metric 0 vẫn hợp lệ. Không chọn lại user/split dựa trên test score để tăng kết quả. Nếu phải đổi dataset/protocol, phát hành version mới và chạy lại tất cả model trong bảng.

## 8. File phải lưu sau mỗi run

`run_manifest.json`, `metrics.csv`, `per_user_metrics.csv`, `recommendations.jsonl`, config đã dùng, environment lock; BPR có train log/checkpoint/ID map. Manifest ghi run ID, model ID, seed, raw/dataset/split/graph hash, protocol ID, cohort size, candidate/seen policy, history mode, thời gian/thiết bị và Git revision hoặc trạng thái chưa có Git.

Model Lab chỉ ghép các run tương thích. Snapshot UI theo [04](04_data_contract.md) có nhãn mẫu/thật, run metadata và metric chưa có thì `not_available`. `history_mode=demo` không gắn metric offline cho ranking live; `history_mode=offline` giữ đúng profile/mask ở mục 2.
