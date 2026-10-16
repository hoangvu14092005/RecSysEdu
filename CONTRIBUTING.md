# Cùng làm RecSysEdu qua GitHub

Repository đã có Python/CLI/Streamlit, dữ liệu pilot, snapshot thật và remote
GitHub. File lớn được quản lý bằng Git LFS. Cài/chạy theo [README](README.md) và
[runbook](docs/09_runbook.md); kiểm tra base ở
[báo cáo base](results/base_verification.md).

Trước khi nhận việc, đọc [trạng thái hiện tại](tasks/todo.md) và
[hướng theo môn học](docs/10_course_direction.md). Không lấy kế hoạch lịch sử
thay cho trạng thái đang được ghi trong `tasks/todo.md`.

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

Dùng `main` cho phiên bản ghép chung; mỗi việc có nhánh
`feature/<task-ngan>`, rồi tạo Pull Request để người khác xem và ghép. Không
cần GitFlow nhiều tầng hoặc repository riêng cho frontend/backend trong MVP.

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

| Git thông thường | Git LFS | Không commit |
| --- | --- | --- |
| Source, config, lock, tài liệu, báo cáo nhỏ | Raw pilot, Parquet, checkpoint, feature và ranking lớn | `.env`, mật khẩu, token, `.venv`, cache |
| Fixture nhỏ và test | Các đuôi/mẫu đã khai báo trong `.gitattributes` | File tạm `*.part` và dữ liệu không được phép chia sẻ |

Trước khi thêm file lớn, đọc `.gitattributes` và chạy `git lfs status`.
Không dùng `git add -f` để vượt `.gitignore`.

Dùng đường dẫn tương đối theo root trong code/config; đường dẫn máy cá nhân đặt trong cấu hình local. Manifest ghi nguồn, version và checksum; file cần quyền truy cập ghi cách xin/lấy file, không nhúng thông tin đăng nhập.

## Người làm UI cần gì

Một fixture synthetic theo [quy ước dữ liệu, mục 6](docs/04_data_contract.md) và môi trường Python có dependency demo. Không cần tải toàn raw, train BPR hay dựng database. Khi model đã xuất snapshot thật, thay input và kiểm tra lại các trạng thái; không đổi UI sang đọc trực tiếp dữ liệu huấn luyện.

Khi thay đổi cách cài, vị trí snapshot hoặc lệnh chạy, cập nhật README và
runbook trong cùng Pull Request. Người review cần chạy lại phần hướng dẫn bị
ảnh hưởng hoặc ghi rõ phần nào chưa thể xác minh.

## Điều kiện bàn giao cuối

Mã và dependency đã khóa; config/manifest tương thích; snapshot và hướng dẫn lấy artifact; lệnh chạy đã kiểm chứng; trạng thái task; kết quả thật và các phần chưa đạt được ghi rõ. Nhận bàn giao khi người khác chạy theo hướng dẫn được, không chỉ khi đã gửi link GitHub.
