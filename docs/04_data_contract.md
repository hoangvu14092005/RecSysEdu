# 04 — Quy ước dữ liệu và file bàn giao

Cập nhật 16/10/2026. Contract P0 này đã được dùng trên dữ liệu thật: prepare
quét toàn raw, chọn 10.000 người; split, bốn model, validation/test và exporter
đã chạy. Snapshot real schema1 và clean-environment check đã qua. Xem
[dataset](../results/pilot/dataset_report.md), [test cuối](../results/final/report.md),
[tái lập](../results/reproduction.md). Các mục P1 được ghi rõ là chưa hoạt động.
Người data/model/UI dùng tên trường dưới đây để ghép phần việc.

## 1. Cần lấy file nào từ MOOCCubeX?

| File nguồn | Dùng để làm gì? | Trạng thái hiện tại |
| --- | --- | --- |
| `entities/user.json` | Người học và lịch sử đăng ký | Đã tải; lưu phẳng `data/raw/user.json` |
| `entities/course.json` | ID, tên, nội dung/lĩnh vực khóa | Đã tải; lưu phẳng `data/raw/course.json` |
| `relations/course-field.json` | Bổ sung lĩnh vực nếu cần sau đối chiếu | Chưa dùng; P0 lấy `course.json:field` |
| `entities/concept.json`, `relations/concept-course.txt` | Concept và khóa có concept đó | Chưa có; P1 dừng |
| `prerequisites/cs.json` | Quan hệ kiến thức trước–sau trong CS | Chưa có; P1 dừng |
| User-video/user-problem | Hành vi chi tiết | P2, chưa tải cho lõi |

`user.json` mô tả hai mảng `course_order` và `enroll_time` tương ứng theo vị trí: khóa thứ i có thời gian thứ i. Phải kiểm tra độ dài trước khi ghép. [Schema user](https://github.com/THU-KEG/MOOCCubeX/blob/main/docs/user-en.md).

`course.json` có `id`, `name`, `about`, `field`, `prerequisites`, `resource`. Văn bản prerequisite của khóa được giữ riêng, không tự chuyển thành cạnh graph. [Schema course](https://github.com/THU-KEG/MOOCCubeX/blob/main/docs/course-en.md).

Concept–course là hai cột `concept_id`, TAB, `course_id`; kiểm tra bản tải trước khi parse. [Script nguồn](https://github.com/THU-KEG/MOOCCubeX/blob/main/scripts/concept_course.py). Prerequisite có `c1` là kiến thức cần trước, `c2` là kiến thức sau; graph chỉ nhận `ground_truth=1`. [Schema prerequisite](https://github.com/THU-KEG/MOOCCubeX/blob/main/docs/prerequisites-en.md).

Hai file tải ngày 09/10/2026 là JSON Lines. Catalog có ID string `C_<số>`;
`course_order` trong user dùng integer. Prepare chỉ nối số với **mã có thật
trong catalog**; string đã đúng mã nối nguyên trạng; bool/float/ID lạ bị cách ly.
Không sửa raw hoặc tạo khóa thay thế. Xem [audit](../results/data_audit.md).
Timestamp không có offset; pilot đã khóa giả định `source_local_naive`, giữ
thứ tự trong từng người. Chưa xác minh timezone nguồn, không tuyên bố UTC.

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

### Feature Content — đã triển khai

`models/content.py` lưu `vectorizer.joblib`, `course_features.npz`,
`course_order.json`, `feature_manifest.json` trong `artifacts/content/` của
batch. Manifest ghi course order, config/hash, `catalog_text_hash`, cleaning
version, fit scope universe train và số vector rỗng; runner ràng buộc dataset/
split qua experiment manifest. Văn bản được làm sạch từ `name + about`, không
phát hành thêm file cleaned-text riêng. Profile chỉ từ train. Pilot dùng char
ngram 2–4/min_df 1; snapshot chỉ nhận ranking/evidence, không nhận ma trận TF-IDF.

### P1: nguồn audit; chưa có bảng graph phục vụ

`knowledge/audit.py` đọc concept JSON, mapping hai cột TAB và prerequisite JSON;
muốn kiểm course coverage phải truyền thêm catalog khóa học. Audit báo cặp
trùng, ID lạ, label, self-loop và SCC/cycle; không phát hành bảng graph/path.
Đề xuất lịch sử về bảng concept/edge phục vụ sẽ cần contract/plan riêng.

Đối chiếu ID chính xác. Chỉ `ground_truth` dạng số bằng 1 là cạnh dương; 0 không
là cạnh; -1/chuỗi/bool/thiếu nhãn là unknown. Prediction không thay nhãn xác nhận.
Chu trình được giữ và báo; không xóa lặng lẽ. [Audit thật chưa chạy](../results/graph_audit.md)
do thiếu ba nguồn; P1 dừng, chưa có penalty/rerank/path.

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

Split đã triển khai, ghi thư mục riêng `data/splits/<split_version>/` gồm
`train.parquet`, `valid.parquet`, `test.parquet`, `valid_cohort.parquet`,
`test_cohort.parquet`, `candidate_universe.parquet`, `split_manifest.json`.
Cohort đánh giá có `user_id`, `course_id`, `target_in_train`; chỉ giữ target
warm. Split ghi số cold/tie và kiểm time_basis với schema timestamp. Không
có concept/mapping/edge artifact phục vụ P1 trong bản này.

Audit ghi số user/course, số đăng ký trước/sau lọc, lỗi theo loại, người có ít nhất ba khóa khác nhau, mốc thời gian, độ phủ lĩnh vực và graph. Độ thưa tính bằng `1 - số cặp user–course / (số user * số course)`; phải nói rõ catalog ở mẫu số.

Raw manifest ghi URL, ngày tải, bytes, SHA-256. Split manifest ghi dataset version, hash input/config/output, seed, quy tắc chia và số target cold/timestamp hòa. Nếu đổi cleaning/subset/split, phát hành version mới và chạy lại các model so sánh.

## 5. Bản xuất cho RecBole

Adapter đã chạy thật, xuất từ **cùng split Parquet** vào
`<atomic_dir>/recsysedu/recsysedu.train.inter`, `recsysedu.valid.inter`,
`recsysedu.test.inter` cùng `<atomic_dir>/export_manifest.json`. Header TSV UTF-8:

```text
user_id:token<TAB>item_id:token<TAB>timestamp:float
```

`<TAB>` là tab thật; `item_id` giữ course ID nguồn. Config dùng
`benchmark_filename: [train, valid, test]`; adapter kiểm số dòng/ID và không
cho thư viện chia lại benchmark. Timestamp số giữ thứ tự, không chứng thực
timezone UTC cho nguồn naive. BPR artifact gồm `bpr.pth`, `id_maps.json`,
`bpr_manifest.json`; padding/ID nội bộ không lọt vào score ID nguồn.
[Atomic files](https://recbole.io/docs/user_guide/data/atomic_files.html),
[data settings](https://recbole.io/docs/user_guide/config/data_settings.html).

### Giao diện chấm điểm và artifact evaluator

Contract đang dùng trong `contracts.py` là
`score(user_id, candidate_ids) -> ScoreResult(course_ids, scores, fallback_status, evidence)`.
`course_ids`: tuple string đúng thứ tự candidate; `scores`: NumPy 1D cùng độ
dài, hữu hạn; `fallback_status`: string; `evidence`: mapping course ID sang
tuple string. Evaluator chịu mask seen/Top10/tie-break, không giao cho model.

Mỗi `<batch>/<run_dir>/` chứa `run_manifest.json`, `metrics.csv`,
**`per_user_metrics.parquet`**, `recommendations.jsonl`. Parquet có `user_id`,
`target_id`, `recommendation_count`, `train_history_count`, `fallback_status`
và năm cột metric chuẩn. Ranking JSONL có `user_id`, `target_ids`, fallback,
`items` gồm ID/rank/score/evidence. `<batch>/experiment_manifest.json` kiểm
toàn bộ inventory/hash, component, selected alpha và source copies. Tên
`run_dir` lấy từ `runs` trong manifest; không giả định mọi Hybrid nằm `runs/hybrid`.

## 6. `demo_bundle.json` — file model giao cho UI

Đây là snapshot nhỏ, không chứa toàn train/checkpoint. Exporter `demo/export.py`
và loader `demo/artifacts.py` đã chạy thật. Một snapshot dùng cùng dataset,
split, config, cohort và history policy; exporter chỉ nhận run đã được chọn
trong batch hoàn tất và kiểm lại hash trước phát hành. Snapshot thật hiện ở
`artifacts/demo/v1/demo_bundle.json` ngoài Git, ba hồ sơ/bốn model; hash ở final report.

| Phần | Trường chính | Ý nghĩa |
| --- | --- | --- |
| `meta` — object | `schema_version`, `snapshot_id`, `data_mode`, `evidence_level`, `dataset_version`, `dataset_hash`, `split_hash`, `protocol_id`, `history_mode`, `generated_at` | Real P0 bắt buộc `evidence_level=offline_run`, `history_mode=offline`; synthetic có nhãn riêng |
| `users` — array | `user_id`, `display_name`, `observed_course_ids`, `profile_course_ids` | Lịch sử hiển thị/loại khỏi gợi ý và lịch sử thực sự dùng tạo profile |
| `courses` — array | `course_id`, `name`, `fields` | Catalog nhỏ đủ để hiển thị lịch sử, ranking và path |
| `runs` — array | `run_id`, `model_id`, `dataset_hash`, `split_hash`, `protocol_id`, `evaluation_split`, `cohort`, `cohort_size`, `candidate_policy`, `seen_policy`, `seed`, `config_hash`, `metric_status`, `metrics` | Mỗi model có run ID riêng; hash/protocol phải khớp meta |
| `recommendations` — array | `user_id`, `model_id`, `run_id`, `fallback_status`, `items` | Base chỉ một danh sách cho mỗi user/model trong snapshot để lựa chọn UI không nhập nhằng |
| Mỗi `items` record | `course_id`, `rank`, `score`, `reason_codes`, `evidence`, `prerequisite_status` | Thứ hạng do pipeline tính; lý do và bằng chứng để UI đọc |
| `paths` — array | Hiện để `[]` | Loader base từ chối path có nội dung; schema path sẽ mở rộng và kiểm tra khi P1 đạt |

Exporter real P0 chỉ nhận `popularity`, `content`, `bpr`, `hybrid`, split valid
hoặc test. Loader còn nhãn dự phòng `hybrid_prerequisite`, nhưng chưa có model
P1 hoặc real export cho nhãn đó. `metric_status` là `measured`/`not_available`;
chưa đo thì `metrics=null`, không điền0. Năm key chuẩn: `NDCG@10`, `Recall@10`,
`HitRate@10`, `Precision@10`, `Coverage@10`. Chế độ demo/synthetic không nhận
metric offline cho ranking live; không phải luồng sản phẩm thật đã nghiệm thu.

ID/tên là string; danh sách ID/lý do/evidence là array; rank là số nguyên từ1;
score/metric hữu hạn; seed có thể null với model không ngẫu nhiên.
`generated_at` là ISO-8601 có timezone. **`paths=[]` là contract v1 hiện tại**;
mọi path có nội dung bị từ chối, chưa có schema bước path hoạt động.

Trong chế độ `offline`, `profile_course_ids` chỉ từ train; `observed_course_ids` là train ở valid, train+valid ở test. Như vậy UI biết phần đã quan sát để loại khóa nhưng không hiểu nhầm valid đã được dùng học profile. Chế độ `demo` có thể dùng lịch sử người chọn, nhưng phải ghi nguồn profile và không nhận là benchmark offline.

Loader giữ bốn nhãn prerequisite: `missing_exposure`, `no_missing_exposure`,
`no_observed_prerequisite`, `unknown`. **Exporter P0 luôn ghi `unknown`**;
không dùng nhãn dự phòng như bằng chứng đã có graph. Không nhãn nào có nghĩa
thành thạo. Ý tưởng lịch sử về path20 concept/cycle/truncated chưa triển khai
và cần schema/plan riêng, không phải cam kết của v1.

**Khi load phải kiểm tra:** schema/version, ID tham chiếu, run đúng dataset/split, rank/khóa không trùng, score hữu hạn, khóa đã quan sát không nằm trong Top-K. Cache gắn với snapshot/user/model/run; đổi snapshot không được giữ kết quả cũ. Mismatch là lỗi rõ ràng, không tự chuyển sang dữ liệu giả.

Fixture có thể ít model/metric chưa đo. UI chỉ hiện lựa chọn thực sự có kết
quả. Snapshot thật và hai tab đã tích hợp/kiểm trình duyệt; giới hạn bằng chứng
ở [nghiệm thu](../reports/acceptance.md). Artifact người học không commit Git.

## 7. Mẫu kiểm tra đã có

Fixture trong Git ghi nhãn **SYNTHETIC**, dùng ID/tên giả. Mẫu UI có ba hồ sơ,
người mới, ranking ngắn và thiếu graph. Test prepare/split có ID mồ côi, mảng
lệch, timestamp lỗi/hòa, enrollment trùng, target cold; test audit graph có
A→B→C, nhãn 0/-1, self-loop, cycle và concept không nối được. Kiểm browser
danh sách rỗng dùng bản sao fixture synthetic riêng, không sửa snapshot thật.

Fixture chứng minh xử lý đúng các tình huống; chưa chứng minh model tốt trên MOOCCubeX. Khi thay schema, cập nhật tài liệu này, fixture, exporter và loader trong cùng PR.
