# Pilot MOOCCubeX thật — dữ liệu và split

Đo ngày 16/10/2026. Đây là dữ liệu thật từ hai file `course.json`, `user.json`,
không phải fixture. Chỉ xử lý đăng ký khóa học; không tải 296 triệu log hành vi.
Kết quả model ở [validation_report](validation_report.md).

## Nguồn và quyền sử dụng

Hai URL trong raw manifest khớp link tải của
[MOOCCubeX chính thức](https://github.com/THU-KEG/MOOCCubeX):
[course](https://lfs.aminer.cn/misc/moocdata/data/mooccube2/entities/course.json),
[user](https://lfs.aminer.cn/misc/moocdata/data/mooccube2/entities/user.json).
File đã tải ngày 09/10/2026; prepare đọc lại và kiểm hash trước/sau xử lý.
Hash do dự án tự đo để nhận diện bản tải, không phải checksum có chứng thực từ nguồn.
Repo nguồn có [GPL-3.0](https://github.com/THU-KEG/MOOCCubeX/blob/main/LICENSE).
HEAD nguồn lúc kiểm tra: `ff6fb71304b4eaadde51956b7977d49c72a3ac1e`.
Chưa xác minh giấy phép riêng áp dụng cho từng file dữ liệu; báo cáo không coi
giấy phép code là sự cho phép phát hành hồ sơ người học. Raw, ID người học,
Parquet, checkpoint và ranking cá nhân chỉ giữ local, ngoài Git.

| File | Byte | SHA-256 |
| --- | ---: | --- |
| course.json | 44.660.123 | `ed7fba469a102a825afd5369da8b4fabc1f24fc1b9a13bdec1106bec27b052fc` |
| user.json | 806.781.726 | `614c5f2753cc23f344bd51968f052564cfbe61694cd3eb7bccb0756a529f61c9` |

## Làm sạch và chọn pilot

Prepare quét cả 3.330.294 hồ sơ, nối khóa học vào catalog, kiểm timestamp,
giữ lần đăng ký hợp lệ sớm nhất khi trùng và cách ly lỗi. Có 680.131 người có
ít nhất ba khóa khác nhau hợp lệ; reservoir sampling seed `20261016` chọn
đúng 10.000 người. Pilot có **126.827 tương tác**, catalog 3.781 khóa.

| Chỉ tiêu trên toàn raw đã quét | Số lượng |
| --- | ---: |
| Slot đăng ký nguồn | 11.807.090 |
| Tương tác hợp lệ trước/sau gộp trùng | 11.523.119 / 11.523.119 |
| Slot có khóa không nằm trong catalog | 283.971 |
| Người thiếu ba khóa hợp lệ | 2.650.163 |
| Dòng rejects (hai loại lỗi trên) | 2.934.134 |
| Khóa có tên / about không rỗng trong catalog | 3.781 / 3.692 |

Các số reject là số trên toàn raw, không phải riêng 10.000 người pilot.
Không ghi nhận lỗi timestamp hoặc duplicate trong lần chạy này. Metadata
không rỗng không đồng nghĩa nội dung đầy đủ hoặc được kiểm duyệt.

Timestamp dùng giả định versioned `source_local_naive`: giữ đồng hồ nguồn,
chỉ so thứ tự trong cùng người; chưa tuyên bố múi giờ nguồn hay UTC.

## Split và kiểm tra

`leave_last_two_out_v1`: khóa cuối là test, áp chót là valid, trước đó là train.
**35 người** có timestamp hòa ở ranh giới bị loại (180 tương tác), còn 9.965
người. Kiểm tra train/valid/test không chồng cặp user–course và thứ tự thời gian
tăng nghiêm ngặt; candidate universe đúng tập khóa xuất hiện trong train.

| Phần | Số dòng/người |
| --- | ---: |
| Train | 106.717 tương tác |
| Valid | 9.965 target; 9.909 warm, 56 cold |
| Test (chỉ thống kê split, chưa đánh giá) | 9.965 target; 9.858 warm, 107 cold |
| Candidate universe | 2.586 khóa |

Warm nghĩa là target có tương tác train ở ít nhất một người. Benchmark
validation dùng đúng 9.909 người warm; không đổi cohort theo kết quả model.
Ở validation, profile và seen mask chỉ lấy train. Test vẫn được giữ kín về metric.

## Dung lượng và thời gian đo được

| Artifact local | Byte |
| --- | ---: |
| processed/courses.parquet | 650.662 |
| processed/interactions.parquet | 2.677.217 |
| processed/cohort_users.parquet | 61.389 |
| processed/rejects.parquet | 24.945.557 |
| split/train.parquet | 2.850.991 |
| split/valid.parquet | 405.874 |
| split/test.parquet | 407.292 |
| split/valid_cohort.parquet | 403.075 |
| split/test_cohort.parquet | 402.744 |
| split/candidate_universe.parquet | 16.553 |

Máy Windows, Python 3.10.11, RAM vật lý 34.086.969.344 byte (~31,75 GiB), CPU.
Prepare lần đầu: **35,66 giây**. Chạy lặp độc lập cùng raw/seed/config:
**37,90 giây**, cả dataset manifest và mọi hash đầu ra giống hệt.
Split: **1,30 giây**. Ước lượng RAM đỉnh lấy tổng RSS tiến trình con mỗi 0,2 giây:
prepare lặp **640.491.520 byte**, split **250.871.808 byte**.
Đây là lấy mẫu RSS, có thể bỏ lỡ đỉnh rất ngắn; không phải bộ nhớ GPU hay
giới hạn RAM bảo đảm. Lần prepare đầu chỉ đo launcher, nên không dùng số RAM
đó làm bằng chứng; số prepare ở đây đến từ lần lặp đã sửa bộ đo cây tiến trình.

## Nhận diện bản dữ liệu

- Dataset version: `mooccubex-pilot-v1`.
- Dataset hash: `215b235068a4282a49b02ab0c0ac65608f096828d1fc97ac6c1a30b0a936720c`.
- Split version: `mooccubex-pilot-v1-split-v1`.
- Split hash: `7285739e66981088817fd2c11419caaf36f2cf4f197798403468cd989f263617`.
- Interactions Parquet SHA-256: `6e534dec34cc2a680c120f8d51f73eaebdbeae644e546a893f83216082e8af42`.
- Courses Parquet SHA-256: `ee424bfdb579e42920ce4d279a67739188f725c2cbe229b5e1cee3c0a0f399fb`.

Manifest đầy đủ nằm local trong `data/processed/mooccubex-pilot-v1/` và
`data/splits/mooccubex-pilot-v1-split-v1/`. Manifest raw/dataset có đường dẫn
máy chạy nên không commit. Nếu chạy ở máy khác, dataset hash chứa provenance
đường dẫn có thể đổi; so raw hash, cấu hình, số dòng và từng hash Parquet để
kiểm nội dung trước khi tạo freeze mới.

## Chạy lại

Từ root, Python môi trường dự án, sau khi đã tải raw vào `data/raw/`:

```powershell
python -m recsysedu.cli data prepare --config configs/prepare.yaml
python -m recsysedu.cli data split --config configs/split.yaml
```

Output đã có sẽ bị từ chối ghi đè; dùng thư mục/version mới cho lần độc lập.
Lần đo này chỉ đổi raw_dir bằng config local để đọc nguyên file gốc có sẵn,
không sao chép hay chỉnh sửa raw.
