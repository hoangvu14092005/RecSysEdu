# RecSysEdu — LearnPath trên MOOCCubeX

Dự án gợi ý **khóa học** từ lịch sử đăng ký: xem Top-10, lý do gợi ý và kết quả so sánh mô hình. RecSysEdu là tên mã nguồn; LearnPath là tên giao diện demo.

**Cập nhật 09/10/2026: đã có base chạy được và đã tải/audit dữ liệu user–course thật.** Giao diện hiện dùng mẫu SYNTHETIC; chưa có split, mô hình đã train hoặc metric thật. Hướng triển khai vẫn gọn trong sáu tuần, dễ cùng làm qua GitHub.

**Ưu tiên hiện tại: làm rõ phương pháp, chưa phát triển thêm UI.** Đọc [hướng đồ án theo tài liệu môn học](docs/10_course_direction.md) trước: Content từ tên/mô tả + BPR từ hành vi → Hybrid → đánh giá chung. [Ghi chú 11 bài giảng](docs/11_course_reading_notes.md) có trang nguồn; [tính năng cần hiển thị](docs/08_ui_handoff.md) mô tả thông tin và điều kiện, chưa chốt bố cục.

## Chạy base ngay

Từ root, dùng PowerShell và Python 3.10. Bản đã thử trên Windows dùng Python 3.10.11:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-win-py310.lock.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.headless true
```

Mở `http://127.0.0.1:8501`. Không cần tải raw để xem mẫu. Nếu `.venv` đã có thì bỏ bước tạo môi trường. Hướng dẫn tải/audit/kiểm tra và cách đổi snapshot ở [runbook](docs/09_runbook.md).

Đã tải `course.json` 44,66 MB và `user.json` 806,78 MB từ nguồn MOOCCubeX. Audit thấy **3.781 khóa, 3.330.294 người, 11.523.119 lượt đăng ký nối được**; 678.126 hồ sơ có ít nhất ba khóa với ranh giới thời gian tách biệt. Xem [báo cáo dữ liệu thật](results/data_audit.md); chưa phát hành tập huấn luyện do cần chốt múi giờ nguồn.

## Bắt đầu ở đâu?

Đọc [Bắt đầu đọc tài liệu](docs/README.md) để hiểu toàn dự án trong vài phút. Sau đó đọc phần việc mình nhận:

| Cần làm | Tài liệu chính |
| --- | --- |
| Hiểu bài toán/phạm vi | [01 — Hướng đi](docs/01_analysis.md), [02 — Yêu cầu](docs/02_requirements.md) |
| Chia mã và ghép các phần | [03 — Kiến trúc](docs/03_architecture.md) |
| Dữ liệu/model xuất file cho UI | [04 — Quy ước dữ liệu](docs/04_data_contract.md) |
| Train/so sánh mô hình | [05 — Đánh giá](docs/05_evaluation.md) |
| Kiểm căn cứ và giới hạn | [06 — Nguồn](docs/06_sources.md) |
| Bố trí dữ liệu trên máy/kho chia sẻ | [07 — Lưu trữ](docs/07_storage_analysis.md) |
| Hiểu chức năng cần hiển thị và bàn giao | [08 — Tính năng](docs/08_ui_handoff.md), [CONTRIBUTING](CONTRIBUTING.md) |
| Hiểu lý do chọn công nghệ/phương pháp | [ADR-001](docs/decisions/ADR-001-scope-stack.md), [ADR-002](docs/decisions/ADR-002-course-grounded-direction.md) |

## Hướng triển khai chung

```text
Raw user/course trên SSD → làm sạch, Parquet/DuckDB → train/valid/test
    → MostPopular + Content + BPR + Hybrid → đánh giá và xuất snapshot
    → LearnPath: Gợi ý học tập | Model Lab → báo cáo và bàn giao
```

Graph/tiền đề/lộ trình là P1, chỉ bật khi dữ liệu đủ. Video/bài tập, LightGCN và web React/FastAPI/PostgreSQL là mở rộng sau sáu tuần. Demo hiện tại được đề xuất bằng Streamlit đọc file kết quả nhỏ; không train khi click.

Mẫu base giúp kiểm contract `demo_bundle.json` ở tài liệu 04; tích hợp chức năng hiển thị ở M10 sau khi có kết quả lõi. Đăng ký chưa chứng minh thành thạo; điểm gợi ý chưa phải xác suất học tốt; số liệu mẫu phải có nhãn.

## Kế hoạch sáu tuần

| Tuần | Kết quả cần có |
| --- | --- |
| 1 | Dữ liệu/split hợp lệ, fixture, thử môi trường BPR sớm |
| 2 | MostPopular và Content TF-IDF có kết quả valid và bằng chứng giải thích |
| 3 | BPR và Hybrid, đủ bốn model cùng cách đánh giá |
| 4 | Phân tích lỗi/kết quả lõi; khảo sát graph/lộ trình có điều kiện |
| 5 | Ghép UI thật, khóa config D25 |
| 6 | Test từ D26, báo cáo, chạy lại và bàn giao |

Việc theo ngày ở [lịch 30 ngày](tasks/six_week_schedule.md); tiêu chí kỹ thuật từng task ở [plan](tasks/plan.md); trạng thái thật ở [todo](tasks/todo.md); phiên code đầu ở [kickoff](tasks/kickoff.md).

## Cùng làm qua GitHub

Một repo, nhánh theo task và PR nhỏ. Git lưu source/config/lock/docs/fixture nhỏ; raw/processed/checkpoint lớn lưu ngoài Git kèm manifest và cách lấy. Nhận một task có đầu ra/điều kiện xong theo [CONTRIBUTING](CONTRIBUTING.md).

Root đã init Git và có package/CLI/app; chưa có commit hoặc remote GitHub. Raw, `.venv` và báo cáo local được `.gitignore` loại khỏi Git. Các lệnh prepare/split/train/evaluate trong kế hoạch vẫn là phần sẽ xây. [Bằng chứng base](results/base_verification.md) ghi rõ phần đã thử và phần còn thiếu.
