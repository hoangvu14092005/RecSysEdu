# 04 — Quy ước dữ liệu và file bàn giao

Cập nhật: 16/10/2026. Raw user/course đã tải/audit; loader snapshot v1 và bước chuẩn hóa Parquet đã kiểm thử trên fixture. Chưa chạy prepare trên raw đầy đủ, chưa có split hoặc exporter model. Người xử lý dữ liệu, model và UI dùng tài liệu này để thống nhất tên trường. Thuật ngữ ở [trang bắt đầu](README.md).

## 1. Cần lấy file nào từ MOOCCubeX?

| File nguồn | Dùng để làm gì? | Thời điểm |
| --- | --- | --- |
| `entities/user.json` | Người học và lịch sử đăng ký | Tuần 1 |
| `entities/course.json` | ID, tên, nội dung/lĩnh vực khóa | Tuần 1 |
| `relations/course-field.json` | Bổ sung lĩnh vực nếu cần sau đối chiếu | Tuần 1–2 |
| `entities/concept.json`, `relations/concept-course.txt` | Concept và khóa có concept đó | P1, tuần 4 |
| `prerequisites/cs.json` | Quan hệ kiến thức trước–sau trong CS | P1, tuần 4 |
| User-video/user-problem | Hành vi chi tiết | P2, chưa tải cho lõi |

`user.json` mô tả hai mảng `course_order` và `enroll_time` tương ứng theo vị trí: khóa thứ i có thời gian thứ i. Phải kiểm tra độ dài trước khi ghép. [Schema user](https://github.com/THU-KEG/MOOCCubeX/blob/main/docs/user-en.md).

`course.json` có `id`, `name`, `about`, `field`, `prerequisites`, `resource`. Văn bản prerequisite của khóa được giữ riêng, không tự chuyển thành cạnh graph. [Schema course](https://github.com/THU-KEG/MOOCCubeX/blob/main/docs/course-en.md).

Concept–course là hai cột `concept_id`, TAB, `course_id`; kiểm tra bản tải trước khi parse. [Script nguồn](https://github.com/THU-KEG/MOOCCubeX/blob/main/scripts/concept_course.py). Prerequisite có `c1` là kiến thức cần trước, `c2` là kiến thức sau; graph chỉ nhận `ground_truth=1`. [Schema prerequisite](https://github.com/THU-KEG/MOOCCubeX/blob/main/docs/prerequisites-en.md).

Hai file tải ngày 09/10/2026 là JSON Lines. Catalog có ID string `C_<số>`; `course_order` trong user dùng integer. Audit nối số với **mã có thật trong catalog**, ví dụ `584313` chỉ thành `C_584313` nếu catalog chứa mã đó. String đã đúng mã được nối nguyên trạng; bool/float/ID không có catalog bị báo lỗi. Không sửa raw hoặc tự tạo khóa học. Mapping này dựa trên bản tải đã kiểm tra; M2 phải giữ quy tắc và provenance. Xem [audit](../results/data_audit.md). Timestamp đều không có offset; chưa chốt timezone.

## 2. Bảng chuẩn sau làm sạch

**Định dạng chính: Parquet.** CSV/JSON chỉ dùng cho mẫu/báo cáo nhỏ; nếu xuất cột list sang CSV thì mã hóa JSON trong ô, không nối tùy ý bằng dấu phẩy.

### `interactions.parquet` — mỗi dòng là một lần đăng ký đã gộp

| Cột | Kiểu | Quy tắc |
| --- | --- | --- |
| `user_id` | string | ID nguồn, không rỗng |
| `course_id` | string | ID nguồn, tồn tại trong catalog |
| `event_time` | timestamp[us] hoặc timestamp[us, UTC] | Naive nếu `source_local_naive`; UTC nếu khai báo IANA timezone |
| `event_time_raw` | string | Giữ nguyên chuỗi nguồn của lần đăng ký được chọn |
| `interaction` | int | 1 = đăng ký; không phải điểm đánh giá/năng lực |
| `source_record` | string | `user.json:record:<n>:slot:<i>`; n từ 1 theo object hợp lệ, i từ 0 trong mảng nguồn |

Mỗi cặp `(user_id, course_id)` chỉ có một dòng. Trùng đăng ký giữ thời gian hợp lệ sớm nhất và provenance tương ứng, ghi số đã gộp; hòa thì giữ lần xuất hiện đầu. User theo thứ tự xuất hiện trong nguồn; trong mỗi user sắp `(event_time, course_id)` để output ổn định và có thể ghi từng lô. ID chỉ phá hòa khi ghi file, không biến hai thời gian bằng nhau thành trước–sau.

Ví dụ giả: `(U_demo_01, C_demo_python, 2024-01-01 00:00:00, 1)` ghi một user đăng ký một khóa tại một thời điểm; số 1 chỉ đánh dấu đăng ký. Không có trường nào trong dòng này chứng minh người đó đã hoàn thành khóa.

`time_basis` bắt buộc là `source_local_naive` hoặc một IANA key hợp lệ, ví dụ `Asia/Shanghai`. Với `source_local_naive`, giữ đồng hồ nguồn, không tạo giá trị UTC; timestamp có offset bị cách ly bằng `timestamp_awareness_mismatch`. Với IANA key, gắn timezone đó cho timestamp naive rồi đổi sang UTC; timestamp đã có offset giữ đúng instant và đổi sang UTC. Giờ không tồn tại hoặc nhập nhằng khi chuyển DST bị cách ly bằng `nonexistent_local_time` / `ambiguous_local_time`. Không dùng timezone của máy chạy để suy diễn. Prepare luôn ghi `temporal_dataset_ready=false`: bước này chưa tạo temporal split.

### `courses.parquet` — danh mục khóa học

| Cột | Kiểu | Quy tắc |
| --- | --- | --- |
| `course_id` | string | Duy nhất, giữ ID nguồn |
| `name` | string | Có thể rỗng; UI dùng ID thay tên khi thiếu |
| `about` | string | Chuẩn hóa null thành rỗng, giữ nguồn; dùng cùng name cho Content TF-IDF, thiếu thì name-only |
| `fields` | list[string] | Lĩnh vực không trùng, lưu nguồn nhãn trong manifest |
| `prerequisite_text` | string | Văn bản tham khảo, tách khỏi graph |

`name`, `about`, `prerequisites` null thành chuỗi rỗng; giá trị có cấu trúc được mã hóa JSON để giữ nội dung. `field` string thành một phần tử; array loại trùng và sắp ổn định. Manifest ghi `fields_source=course.json:field`. ID catalog trùng metadata giống nhau được gộp; metadata mâu thuẫn hoặc hai mã như `C_1` và `C_01` cùng nối tới số 1 chặn phát hành.

### `cohort_users.parquet` và `rejects.parquet`

`cohort_users` gồm `user_id: string`, `history_length: int64` cho người được chọn ở prepare. Người đủ điều kiện có ít nhất ba khóa catalog khác nhau sau làm sạch. Đây chưa phải cohort đánh giá: timestamp hòa và target cold được xử lý ở split.

Lấy mẫu reservoir bằng `random.Random(seed)` trên toàn bộ người đủ điều kiện theo thứ tự nguồn; người không đủ điều kiện không tham gia phép chọn. `sample_users=0` giữ tất cả; số dương yêu cầu đúng số người đó, thiếu người đủ điều kiện thì báo lỗi và không phát hành output. Pilot cấu hình `sample_users=10000`, `seed=20261016`, nên bắt buộc chọn đủ 10.000 người. Giữ catalog đầy đủ; interactions chỉ chứa người được chọn. Không cần nạp toàn bộ lịch sử raw vào RAM: mỗi lần đọc một user, buffer Parquet tối đa 4096 dòng; reservoir giữ tối đa số user yêu cầu. Catalog và tập ID user đã gặp vẫn được giữ trong bộ nhớ để nối và phát hiện trùng.

`rejects` gồm `reason_code`, `user_id`, `raw_course_id`, `event_time_raw`, `source_record` (string nullable), và `count` (int64). `raw_course_id` mã hóa JSON để phân biệt integer, float, bool và string. Lỗi tương tác giữ vị trí slot; lỗi lịch sử giữ vị trí object. `iter_records` chỉ trả tổng số dòng JSON lỗi/object không hợp lệ nên các lỗi đó được ghi thành dòng tổng hợp theo file với `count`; không tuyên bố có số dòng nguồn chính xác. `duplicate_interaction` ghi lần bị gộp; `insufficient_history` ghi người còn dưới ba khóa. Lỗi và bản gộp của mọi user được thống kê trước lấy mẫu, kể cả người không được chọn; tổng `count` bằng tổng `error_counts` trong manifest.

### Feature Content — M4, sẽ xây

Lưu riêng văn bản đã làm sạch, vectorizer/IDF, ma trận feature và `feature_manifest.json`: dataset/hash catalog, course ID đúng thứ tự, nguồn `name/about`, cleaning version, analyzer/ngram/vocabulary config, fit scope universe train và số vector rỗng. Profile chỉ từ train. Cấu hình char n-gram là lựa chọn thử theo [10](10_course_direction.md), không phải yêu cầu nguyên từ slide. Snapshot UI v1 không đổi trong đợt phân tích; nó nhận kết quả/evidence, không nhận ma trận TF-IDF.

### P1: concept và cạnh tiền đề

Giữ bảng concept có `concept_id`/tên; bảng liên kết có cặp `(concept_id, course_id)` duy nhất. Cạnh gồm `prerequisite_id` từ `c1`, `target_concept_id` từ `c2`, `label` từ `ground_truth`, `provenance` từ file/vị trí nguồn.

Đối chiếu namespace/kiểu ID với catalog và bảng liên kết. Nhãn 0 không là cạnh; nhãn khác, gồm -1 **nếu xuất hiện**, được ghi `unknown_label`. `text_predict/graph_predict` không thay nhãn xác nhận trong MVP. Vòng lặp/self-loop được báo và xử lý theo tài liệu 05, không âm thầm xóa để có path đẹp.

## 3. Dữ liệu lỗi xử lý thế nào?

| Lỗi | Hành động | Mã ghi trong báo cáo |
| --- | --- | --- |
| JSON lỗi | Cách ly, giữ vị trí và thông báo | `invalid_json` |
| Hai mảng khóa/thời gian lệch | Cách ly lịch sử user; không ghép phần ngắn hơn | `array_length_mismatch` |
| Course không có trong catalog | Cách ly tương tác; user còn lịch sử hợp lệ vẫn được giữ | `unknown_course_id` |
| Timestamp lỗi/rỗng | Cách ly tương tác, không điền thời gian giả | `invalid_timestamp` |
| Enrollment trùng | Giữ lần sớm nhất hợp lệ, đếm bản gộp | `duplicate_interaction` |
| Cùng course ID nhưng metadata mâu thuẫn | Chặn phát hành catalog đến khi giải quyết | `conflicting_course_id` |
| Graph tự nối/label lạ/ID lạ | Không đưa vào graph hoạt động, ghi lý do | `self_loop` / `unknown_label` / `unmapped_concept` |

Bảng chuẩn không còn ID mồ côi. Không đặt một tỷ lệ lỗi cố định là “chấp nhận được” trước khi thấy dữ liệu; báo mức lỗi/nguyên nhân để quyết định có đủ dùng không.

## 4. Dataset, split và manifest

Prepare đặt bảng dưới `data/processed/<dataset_version>/`: `interactions.parquet`, `courses.parquet`, `rejects.parquet`, `cohort_users.parquet`, `dataset_manifest.json`. CLI: `python -m recsysedu.cli data prepare --config configs/prepare.yaml`; `output_dir` là thư mục version cuối cùng, không tự nối thêm version. Cấu hình cần đủ `raw_dir`, `output_dir`, `dataset_version`, `time_basis`, `sample_users`, `seed`. Thư mục output đã tồn tại sẽ bị từ chối; ghi/kiểm tra trong thư mục tạm rồi mới phát hành. Raw chỉ được đọc và kiểm hash trước/sau chạy. DuckDB chỉ kiểm tra Parquet đã ghi: khóa ghép duy nhất, không orphan và độ dài cohort đúng.

Dataset manifest ghi schema version, dataset version, time basis, seed, số user yêu cầu/đủ điều kiện/đã chọn, số user đã quét, enrollment trước dedup, số cặp sạch trước lấy mẫu, số dòng từng bảng, mã lỗi/tổng số lỗi, schema Arrow, đường dẫn/bytes/SHA-256 raw và SHA-256 bốn output Parquet. Manifest không tự hash chính nó; bước sau có thể SHA-256 file manifest để làm dataset identity. Hai lần cùng raw/config/phiên bản thư viện tạo cùng output hash; không hứa hash Parquet giống nhau qua mọi phiên bản PyArrow.

Bước split sau mới thêm `train.parquet`, `valid.parquet`, `test.parquet`, cohort đánh giá, candidate universe và `split_manifest.json`; P1 có thêm concept/mapping/edges.

Audit ghi số user/course, số đăng ký trước/sau lọc, lỗi theo loại, người có ít nhất ba khóa khác nhau, mốc thời gian, độ phủ lĩnh vực và graph. Độ thưa tính bằng `1 - số cặp user–course / (số user * số course)`; phải nói rõ catalog ở mẫu số.

Raw manifest ghi URL, ngày tải, bytes, SHA-256. Split manifest ghi dataset version, hash input/config/output, seed, quy tắc chia và số target cold/timestamp hòa. Nếu đổi cleaning/subset/split, phát hành version mới và chạy lại các model so sánh.

## 5. Bản xuất cho RecBole

Từ **cùng split Parquet**, xuất TSV UTF-8 `mooc.train.inter`, `mooc.valid.inter`, `mooc.test.inter`. Header:

```text
user_id:token<TAB>item_id:token<TAB>timestamp:float
```

`<TAB>` là ký tự tab thật; `item_id` giữ course ID nguồn. Config dùng `benchmark_filename: [train, valid, test]`. Parser/exporter phải làm sạch trước, rồi kiểm số dòng/ID của loader; không để thư viện tự chia lại benchmark. [Atomic files](https://recbole.io/docs/user_guide/data/atomic_files.html), [data settings](https://recbole.io/docs/user_guide/config/data_settings.html).

## 6. `demo_bundle.json` — file model giao cho UI

Đây là snapshot nhỏ cho các hồ sơ demo, không chứa toàn dữ liệu train hay checkpoint. Mẫu giả và bản thật dùng cùng schema; một snapshot cùng dataset, split và history mode. Loader và fixture v1 đã có; exporter từ model thật xây ở M10.

| Phần | Trường chính | Ý nghĩa |
| --- | --- | --- |
| `meta` — object | `schema_version`, `snapshot_id`, `data_mode`, `dataset_version`, `dataset_hash`, `split_hash`, `protocol_id`, `history_mode`, `generated_at` | Nhận diện định dạng, nguồn và chế độ; `data_mode` là `synthetic` hoặc `real` |
| `users` — array | `user_id`, `display_name`, `observed_course_ids`, `profile_course_ids` | Lịch sử hiển thị/loại khỏi gợi ý và lịch sử thực sự dùng tạo profile |
| `courses` — array | `course_id`, `name`, `fields` | Catalog nhỏ đủ để hiển thị lịch sử, ranking và path |
| `runs` — array | `run_id`, `model_id`, `dataset_hash`, `split_hash`, `protocol_id`, `evaluation_split`, `cohort`, `cohort_size`, `candidate_policy`, `seen_policy`, `seed`, `config_hash`, `metric_status`, `metrics` | Mỗi model có run ID riêng; hash/protocol phải khớp meta |
| `recommendations` — array | `user_id`, `model_id`, `run_id`, `fallback_status`, `items` | Base chỉ một danh sách cho mỗi user/model trong snapshot để lựa chọn UI không nhập nhằng |
| Mỗi `items` record | `course_id`, `rank`, `score`, `reason_codes`, `evidence`, `prerequisite_status` | Thứ hạng do pipeline tính; lý do và bằng chứng để UI đọc |
| `paths` — array | Hiện để `[]` | Loader base từ chối path có nội dung; schema path sẽ mở rộng và kiểm tra khi P1 đạt |

`model_id` dùng `popularity`, `content`, `bpr`, `hybrid`; có thể thêm `hybrid_prerequisite` khi P1 đạt. `metric_status` là `measured` hoặc `not_available`; trường hợp chưa chạy thì `metrics=null`, không dùng số 0. Metric map dùng tên chuẩn như `NDCG@10`, `Recall@10`, `HitRate@10`, `Coverage@10`. Khi `evaluation_split=demo`, không gắn metric offline cho ranking live.

ID/tên là string, danh sách ID/lý do/evidence là array, rank là số nguyên từ 1, score/metric là số hữu hạn, seed có thể null với model không dùng ngẫu nhiên. `generated_at` ghi thời gian ISO-8601 có timezone. Mỗi bước path có `concept_id`, tên, trạng thái tiếp xúc và danh sách course tham khảo; P1 ghi graph version cùng nguồn cạnh trong artifact/run manifest.

Trong chế độ `offline`, `profile_course_ids` chỉ từ train; `observed_course_ids` là train ở valid, train+valid ở test. Như vậy UI biết phần đã quan sát để loại khóa nhưng không hiểu nhầm valid đã được dùng học profile. Chế độ `demo` có thể dùng lịch sử người chọn, nhưng phải ghi nguồn profile và không nhận là benchmark offline.

`prerequisite_status` dùng bốn giá trị: `missing_exposure` (còn tiền đề chưa thấy tiếp xúc), `no_missing_exposure` (tiền đề được quan sát đều có dấu hiệu tiếp xúc), `no_observed_prerequisite` (graph có mapping nhưng chưa thấy cạnh tiền đề), `unknown` (không đủ graph/mapping). Không trạng thái nào có nghĩa “đã thành thạo”. Path dùng `ok`, `unknown`, `cycle_blocked` hoặc `truncated`; có tối đa 20 concept theo quy tắc ở [05](05_evaluation.md).

**Khi load phải kiểm tra:** schema/version, ID tham chiếu, run đúng dataset/split, rank/khóa không trùng, score hữu hạn, khóa đã quan sát không nằm trong Top-K. Cache gắn với snapshot/user/model/run; đổi snapshot không được giữ kết quả cũ. Mismatch là lỗi rõ ràng, không tự chuyển sang dữ liệu giả.

Mẫu có thể chỉ có một model và metric chưa chạy. UI chỉ hiện lựa chọn thực sự có kết quả. Không cần mọi trường phụ hay đầy đủ graph để kiểm contract; hiện ưu tiên lõi model/đánh giá, tích hợp hiển thị ở M10 tuần 5.

## 7. Mẫu kiểm tra cần có

Fixture ghi nhãn **SYNTHETIC**, dùng ID/tên giả. Mẫu UI có ít nhất ba hồ sơ, trường hợp mới, ranking ngắn và thiếu graph. Mẫu logic dữ liệu có ID mồ côi, mảng lệch, timestamp lỗi/hòa, enrollment trùng và target cold; mẫu graph có A→B→C, nhãn 0/-1, self-loop, cycle và concept không nối được.

Fixture chứng minh xử lý đúng các tình huống; chưa chứng minh model tốt trên MOOCCubeX. Khi thay schema, cập nhật tài liệu này, fixture, exporter và loader trong cùng PR.
