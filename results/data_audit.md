# Dữ liệu thật đã tải và quét

Ngày 09/10/2026. Đây là kết quả **audit raw toàn bộ**, chưa phải tập train/split hoặc kết quả thuật toán.

## 1. Đã lấy được gì?

Tải theo link trong [README MOOCCubeX](https://github.com/THU-KEG/MOOCCubeX). Chỉ lấy hai file cần cho bài toán gợi ý khóa học; chưa tải hơn 296 triệu hành vi chi tiết.

| File | Bytes | MB (1 MB = 1 triệu bytes) | SHA-256 |
| --- | ---: | ---: | --- |
| [course.json](https://lfs.aminer.cn/misc/moocdata/data/mooccube2/entities/course.json) | 44.660.123 | 44,66 | `ed7fba469a102a825afd5369da8b4fabc1f24fc1b9a13bdec1106bec27b052fc` |
| [user.json](https://lfs.aminer.cn/misc/moocdata/data/mooccube2/entities/user.json) | 806.781.726 | 806,78 | `614c5f2753cc23f344bd51968f052564cfbe61694cd3eb7bccb0756a529f61c9` |

Tổng 851.441.849 bytes (~812 MiB). File và manifest ở `data/raw/`, không đưa vào Git. Thời điểm tải ghi UTC trong manifest; lần chạy lại downloader đã đối chiếu checksum và giữ file. Đây là hash bản nhận được, không phải đối chiếu checksum công bố bởi bên nguồn.

## 2. Số liệu quét thực tế

Lệnh: `python -m recsysedu.cli data audit`, dùng Python của `.venv`. Cả hai file là JSON Lines. Báo cáo chi tiết tại `results/local/data_audit.json`; lần quét mất 27,36 giây trên máy hiện tại. Chưa đo RAM cao nhất/temp disk.

| Số đo | Kết quả |
| --- | ---: |
| Khóa trong catalog, ID duy nhất | 3.781 |
| Hồ sơ người học, ID duy nhất | 3.330.294 |
| Vị trí đăng ký trong `course_order` | 11.807.090 |
| Đăng ký nối được catalog và có thời gian parse được | 11.523.119 |
| Cặp user–course duy nhất sau kiểm tra | 11.523.119 |
| Đăng ký không có khóa tương ứng trong catalog tải về | 283.971 (2,41%) |
| Người có ít nhất ba khóa hợp lệ khác nhau | 680.131 |
| Người có ba mốc cuối tách biệt, ứng viên chia train/valid/test | 678.126 |
| Hồ sơ ≥3 khóa bị hòa thời gian ở ranh giới cuối | 2.005 |
| Khóa có trường `field` không rỗng | 547 / 3.781 (14,47%) |

Không phát hiện JSON lỗi, ID user/course trùng, mảng lệch độ dài, timestamp parse lỗi hoặc đăng ký trùng trong lần quét này. Nhận xét chỉ áp dụng hai file/hash trên; chưa kiểm video/concept/prerequisite.

README nguồn công bố 4.216 khóa. File tải thực tế có 3.781 khóa; chưa xác định nguyên nhân khác biệt. Dùng số thực quét trong báo cáo dự án, không tự thêm bản ghi cho đủ số công bố.

## 3. Hai điểm quan trọng trước khi train

**ID có hai cách viết.** Catalog dùng string `C_<số>`; lịch sử người học dùng integer. Audit tạo bảng nối từ catalog: integer chỉ được nhận nếu có mã tương ứng trong catalog. Có 11.523.119 lần nối dạng số thành công. ID lạ được đếm, không tạo khóa giả và không sửa raw. Raw số `584313` nối với catalog `C_584313` là ví dụ cấu trúc đã quan sát; không đưa tên/ID người học vào báo cáo.

**Timestamp chưa có timezone.** 11.807.090 thời gian parse được đều không có offset. Khoảng giá trị nguồn từ `2019-01-24T16:34:19` đến `2020-12-08T03:38:19`; chưa được chuyển thành UTC. `source_timezone: null`, `timezone_status=unresolved`, `temporal_dataset_ready=false`. Cần căn cứ nguồn hoặc ghi rõ giả định nghiên cứu trước khi phát hành timestamp Unix và temporal split.

678.126 hồ sơ là **ứng viên theo kiểm tra lịch sử/thời gian**, chưa là warm-user cohort cuối. Cần kiểm cold-item, subset và điều kiện split ở M2 trước khi nói bao nhiêu người đánh giá được. Mỗi user tối thiểu ba khóa vẫn có thể chỉ còn một khóa train; cần phân tích người ít/nhiều lịch sử.

## 4. Độ dài lịch sử sau nối

| Khóa hợp lệ khác nhau/người | Số người |
| --- | ---: |
| 0 | 119.246 |
| 1 | 2.037.151 |
| 2 | 493.766 |
| ≥3 | 680.131 |

Phân bố đầy đủ trong JSON local. Vì phần lớn chỉ có 1–2 khóa, không lấy ngẫu nhiên 10.000 người từ toàn raw rồi mặc định đều đủ đánh giá. Chọn ứng viên đủ lịch sử trước, giữ seed và danh sách ID nội bộ để tái lập.

## 5. Hướng triển khai sau audit

**Bổ sung khảo sát metadata ngày 09/10/2026:** quét toàn `course.json` cùng hash trên bằng reader JSON Lines; `name` đều là string và không rỗng ở 3.781 khóa; `about` không rỗng ở 3.692 (97,65%), kiểu string ở 3.779 và null ở 2. Có 3.398 tên và 3.227 mô tả chứa ký tự Hán. Số đếm, phương pháp và source hash trong [bản audit metadata JSON](course_metadata_audit.json). Đây là coverage chuỗi raw, chưa là chất lượng text sau cleaning. Do field chỉ có 14,47%, đề xuất Content chính từ TF-IDF tên/mô tả thay field-only; field là bổ sung. Căn cứ ở [hướng theo môn học](../docs/10_course_direction.md).

1. Giữ nguyên raw/hash; giải quyết timezone và bổ sung nhãn lĩnh vực từ `relations/course-field.json` nếu nguồn nối hợp lệ. Chỉ 14,47% catalog có field hiện tại, nên chưa chốt benchmark chỉ CS.
2. Pilot khoảng 10.000 người đủ lịch sử với seed cố định, từ tập ứng viên trên. Báo catalog, số cold-item, độ thưa, field coverage và kích thước Parquet thực tế. Tăng 30.000 sau khi pipeline ổn; chưa cần train toàn 3,33 triệu người.
3. Viết cleaning/rejects/split + manifest, kiểm không giao nhau và không bịa thứ tự khi thời gian hòa.
4. Chạy MostPopular + evaluator trước, rồi Content/BPR/Hybrid cùng split. UI mẫu có thể làm độc lập ngay.

Không cần PostgreSQL/MySQL, Spark hoặc tải log bài tập ở base. [Runbook](../docs/09_runbook.md) có lệnh đã dùng; [todo](../tasks/todo.md) theo dõi bước tiếp theo.
