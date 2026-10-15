# Cùng làm RecSysEdu qua GitHub

Repository đã có base Python/CLI/Streamlit, fixture nhỏ và raw đã audit; chưa có remote GitHub. Người nhận UI chỉ cần source và lock, không cần raw. Cài/chạy theo [runbook](docs/09_runbook.md); kiểm tra hiện có ở [báo cáo base](results/base_verification.md).

Ưu tiên hiện tại: đọc [hướng theo môn học](docs/10_course_direction.md), nhận việc data/split/evaluator/model trước. UI chỉ phân tích chức năng và đầu ra; các ví dụ giao việc UI dưới đây dành cho khi tích hợp M10, chưa là việc cần triển khai ngay.

## Bắt đầu từ một việc nhỏ

Đọc [README](README.md), [UI và bàn giao](docs/08_ui_handoff.md), rồi nhận một task trong [plan](tasks/plan.md). Mỗi issue có một người phụ trách, mục tiêu, file dự kiến, đầu vào, đầu ra và điều kiện xong. Task lớn có thể chia thành nhiều PR, mỗi PR có một phần kiểm tra được.

Ví dụ issue UI đầu tiên:

```text
Tên: Dựng tab Gợi ý học tập từ dữ liệu mẫu
Đầu vào: schema demo_bundle v1 + fixture SYNTHETIC đã chốt ở M0
Phạm vi: app/; cần đổi loader thì phối hợp người phụ trách loader
Đầu ra: chọn user/model, xem lịch sử, ranking và giải thích
Điều kiện xong: đổi lựa chọn đúng dữ liệu; mẫu luôn có nhãn;
               user mới/thiếu kết quả có thông báo; kèm ảnh màn hình
```

## Cách dùng Git gọn

Sau khi có repo GitHub, dùng `main` cho phiên bản ghép chung; mỗi việc có nhánh `feature/<task-ngan>`, rồi tạo Pull Request để người khác xem và ghép. Không cần GitFlow nhiều tầng hoặc repository riêng cho frontend/backend trong MVP.

Trước khi sửa file chung, kiểm tra issue/PR đang làm. Nếu thay schema, config hoặc dependency, ghi ảnh hưởng và cập nhật fixture/hướng dẫn trong cùng PR. Tránh commit gom nhiều việc không liên quan.

Nội dung PR tối thiểu:

```text
Giải quyết: <issue/task và hành vi đạt được>
Đầu vào/đầu ra: <fixture hoặc artifact, dataset/run version nếu có>
Đã kiểm tra: <lệnh thật và kết quả; thao tác UI nếu liên quan>
Còn thiếu: <giới hạn hoặc phụ thuộc chưa đạt>
```

Chỉ ghi đã test khi đã chạy. PR dùng fixture chưa được coi là chạy dữ liệu MOOCCubeX thật; code model chưa được coi là có kết quả huấn luyện.

## Những gì lưu trên GitHub

| Đưa vào Git | Lưu ngoài Git, ghi cách lấy trong manifest/runbook |
| --- | --- |
| Source, config, dependency lock, tài liệu | Raw MOOCCubeX và processed dataset lớn |
| Fixture synthetic nhỏ cho UI và tests | Checkpoint/feature/ranking dung lượng lớn |
| Báo cáo phù hợp phạm vi công bố, metric tổng hợp có nguồn | Dữ liệu hồ sơ thật; bản sao lưu và tài khoản truy cập |

Ở M0 tạo `.gitignore` cho raw, processed, checkpoints, cache, `.venv`, `.env`; không ignore toàn `tests/fixtures/` hay toàn `results/` khiến mất mẫu/báo cáo cần bàn giao. Không commit mật khẩu hoặc khóa truy cập.

Dùng đường dẫn tương đối theo root trong code/config; đường dẫn máy cá nhân đặt trong cấu hình local. Manifest ghi nguồn, version và checksum; file cần quyền truy cập ghi cách xin/lấy file, không nhúng thông tin đăng nhập.

## Người làm UI cần gì

Một fixture synthetic theo [quy ước dữ liệu, mục 6](docs/04_data_contract.md) và môi trường Python có dependency demo. Không cần tải toàn raw, train BPR hay dựng database. Khi model đã xuất snapshot thật, thay input và kiểm tra lại các trạng thái; không đổi UI sang đọc trực tiếp dữ liệu huấn luyện.

Để người khác chạy được, sau M0 bổ sung README với lệnh cài chính xác từ lock, vị trí fixture, cách mở demo và kết quả mong đợi. Tuần 5 bổ sung cách lấy snapshot thật; tuần 6 một người khác thực hiện runbook trên môi trường sạch.

## Điều kiện bàn giao cuối

Mã và dependency đã khóa; config/manifest tương thích; snapshot và hướng dẫn lấy artifact; lệnh chạy đã kiểm chứng; trạng thái task; kết quả thật và các phần chưa đạt được ghi rõ. Nhận bàn giao khi người khác chạy theo hướng dẫn được, không chỉ khi đã gửi link GitHub.
