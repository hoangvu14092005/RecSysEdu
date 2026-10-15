# Phiên triển khai tiếp theo sau base

Cập nhật 09/10/2026. Base đã chạy: package/CLI, tải và audit raw, UI hai tab dùng fixture. Chưa có lệnh prepare/split/train/evaluate. [Runbook](../docs/09_runbook.md) ghi lệnh thật; [báo cáo base](../results/base_verification.md) và [audit](../results/data_audit.md) ghi bằng chứng.

Theo yêu cầu mới, đọc [hướng theo môn học](../docs/10_course_direction.md) trước khi tiếp tục. Content chính dùng TF-IDF tên/mô tả; chưa phát triển thêm UI, chỉ chốt thông tin cần hiển thị.

## Mục tiêu phiên tiếp theo

Hoàn thiện điều kiện M1 rồi xây M2: bảng Parquet sạch, split tái lập, cohort và manifest. Chưa bắt đầu train khi dataset/split chưa đạt. Lịch vẫn là [30 ngày trong sáu tuần](six_week_schedule.md); BPR spike thử sớm, benchmark thật cần evaluator và baseline trước.

## Những việc cần làm theo thứ tự

1. Đọc [04 — contract](../docs/04_data_contract.md), [05 — evaluation](../docs/05_evaluation.md) và M1–M2 trong [plan](plan.md).
2. Xác minh timezone nguồn. Nếu không có căn cứ, ghi rõ giả định nghiên cứu/phạm vi; không tự lấy timezone của máy. Config hiện `source_timezone: null`.
3. Chuẩn hóa metadata name/about và khảo sát ngôn ngữ/vector rỗng cho TF-IDF. Field chỉ có ở 547/3.781 khóa, dùng bổ sung khi có nguồn; chưa ép benchmark toàn bộ thành CS. Graph CS có thể là cohort riêng.
4. Chọn pilot khoảng 10.000 người đủ lịch sử, seed cố định; nhóm 678.126 hồ sơ mới là ứng viên, còn phải kiểm target cold và điều kiện split.
5. Viết prepare/split, rejects và manifests theo contract. Test lỗi ID, timezone, target-cold, timestamp hòa, không giao nhau và không dùng dữ liệu tương lai; chỉ xuất split sau khi kiểm đạt.
6. Đo RAM, temp disk, thời gian và kích thước Parquet rồi quyết định tăng mẫu 30.000. Không cần train toàn 3,33 triệu hồ sơ ngay.

## Checkpoint đang có và còn thiếu

| Mốc | Trạng thái | Artifact |
| --- | --- | --- |
| K1 — base import/help/UI fixture | Có phần nền chạy được; M0 còn cf/graph và fixture nâng cao | Package, lock, tests, UI SYNTHETIC |
| K2 — raw manifest/full audit | Đã tải/quét; chưa chốt timezone/subset | Raw local + báo cáo audit |
| K3 — dataset/split khóa | Chưa làm | Parquet/split/cohort/manifest |
| Sau K3 | Chưa làm | MostPopular + evaluator rồi Content/BPR/Hybrid |

Hiện chỉ mô tả chức năng hiển thị ở tài liệu 08, không thêm code UI. Base giữ làm tham khảo; M10 ghép snapshot thật khi lõi đạt và kiểm toàn luồng.

## Mẫu giao việc tiếp theo

```text
Tiếp tục M1–M2 trong RecSysEdu từ base hiện có. Đọc audit thật, data contract
và evaluation protocol. Giữ raw/hash; xác minh timezone, field mapping và
chọn pilot có seed. Viết prepare/split Parquet, rejects/cohort/manifest.
Kiểm ID, timestamp hòa, target cold, không giao nhau và tái lập output.
Chưa train nếu split chưa đạt. Ghi lệnh, số đo và giới hạn; không tạo metric giả.
```
