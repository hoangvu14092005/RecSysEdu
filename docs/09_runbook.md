# 09 — Chạy base và bàn giao cho người khác

Cập nhật 09/10/2026. Các lệnh dưới đây chạy từ root repository bằng PowerShell. Base đã thử trên Windows, Python 3.10.11; chưa kiểm Linux/macOS hay môi trường BPR.

## 1. Cài một lần

Người nhận source không cần dữ liệu thật để chạy giao diện mẫu. Cần Python 3.10 và kết nối Internet để cài thư viện.

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-win-py310.lock.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe -m recsysedu.cli --help
```

Nếu có `.venv` đang dùng thì bỏ bước tạo. Dùng trực tiếp Python trong `.venv` giúp không phụ thuộc việc bật môi trường ở từng cửa sổ terminal. Lock ghi phiên bản base đã cài, không chứa đường dẫn máy người viết; chưa bao gồm RecBole/PyTorch/NetworkX.

Muốn thử trên môi trường khác, cài `python -m pip install -e ".[dev,demo,data]"` trong môi trường riêng, rồi chạy kiểm tra dưới đây. Nhánh cài theo khoảng version này chưa được thử lại trên hệ điều hành khác.

## 2. Mở LearnPath

```powershell
.\.venv\Scripts\python.exe -m recsysedu.cli demo validate
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.headless true
```

Mở `http://127.0.0.1:8501`. Có hai tab: **Gợi ý học tập** và **Model Lab**. Sidebar chọn ba hồ sơ và hai danh sách gợi ý minh họa. Cửa sổ hẹp cần mở sidebar để chọn, đóng lại để xem tab. Nhãn **DỮ LIỆU MẪU** luôn hiện; bảng Model Lab báo chưa có metric. Nhấn Ctrl+C ở terminal để dừng server.

Fixture nằm ở `tests/fixtures/demo_bundle.json`. Mọi thứ trong fixture là giả, không lấy hồ sơ người học thật. Điểm/lý do do người viết mẫu tạo để kiểm UI; hai nhãn model không có nghĩa đã train MostPopular/Content.

Khi có snapshot model thật, kiểm tra trước rồi truyền đường dẫn qua biến môi trường:

```powershell
.\.venv\Scripts\python.exe -m recsysedu.cli demo validate --bundle artifacts/demo/v1/demo_bundle.json
$env:RECSYSEDU_BUNDLE = 'artifacts/demo/v1/demo_bundle.json'
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.headless true
```

Đường dẫn ví dụ `artifacts/demo/v1/` chưa có bản thật. Khi quay về fixture, dùng `Remove-Item Env:RECSYSEDU_BUNDLE` nếu biến tồn tại. File sai hoặc thiếu phải hiện lỗi; app không tự thay bằng dữ liệu mẫu.

## 3. Lấy dữ liệu thật

Chỉ người phụ trách dữ liệu/model cần bước này. Config `configs/data.yaml` chỉ chọn course/user, không tải kho log video/bài tập.

```powershell
.\.venv\Scripts\python.exe -m recsysedu.cli data download --config configs/data.yaml
```

Đầu ra ở `data/raw/`: `course.json`, `user.json`, `raw_manifest.json`. Bản đã tải tổng ~851 MB. URL thuộc kho MOOCCubeX chính thức; manifest ghi bytes, SHA-256 và thời điểm tải. Hash dùng nhận diện bản đã nhận, chưa phải checksum do bên nguồn chứng thực.

Nếu file hoàn chỉnh đã có và khớp manifest, lệnh kiểm hash rồi giữ file. Nếu tải mất kết nối, giữ `.part`, chạy lại sẽ tải từ đầu file đó; chưa có resume/retry tự động. File hoàn chỉnh khác manifest bị từ chối ghi đè. Muốn giữ bản khác, tạo config riêng với `raw_dir` khác.

## 4. Kiểm tra dữ liệu

```powershell
# Khảo sát nhanh 10.000 hồ sơ đầu; đây không phải mẫu ngẫu nhiên
.\.venv\Scripts\python.exe -m recsysedu.cli data audit --max-users 10000 --output results/local/pilot_audit.json

# Quét toàn bộ
.\.venv\Scripts\python.exe -m recsysedu.cli data audit
```

Lệnh toàn bộ đã thử: 3.330.294 người, 3.781 khóa, khoảng 27 giây trên máy hiện tại. Đọc JSON ở `results/local/data_audit.json`; bản dễ hiểu ở [báo cáo audit](../results/data_audit.md). Audit đọc từng bản ghi, nhưng vẫn giữ tập ID user trong RAM để kiểm trùng; chưa đo RAM cao nhất, không nhận bộ nhớ cố định.

ID số trong lịch sử chỉ nối sang mã `C_<số>` tồn tại trong catalog. Timestamp được kiểm/đếm mà không tự gán múi giờ. `source_timezone: null` hiện là trạng thái chưa chốt; thay config này chưa khiến audit chuyển thời gian. Chưa có lệnh prepare/split để tạo Parquet.

## 5. Kiểm tra base

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src app tests
.\.venv\Scripts\python.exe -m pip check
```

Kết quả tại lần bàn giao này: 28 tests pass, lint pass, dependency check pass. [Báo cáo kiểm chứng](../results/base_verification.md) phân biệt test tự động, audit thật và UI đã thao tác trên trình duyệt. Chưa thử BPR hoặc chứng minh hiệu quả gợi ý.

## 6. Ghép việc qua GitHub

Hiện đã init Git local và có commit baseline; chưa có remote GitHub. Lưu source, lock, configs, docs, fixture và báo cáo tổng hợp. `/data/`, `/artifacts/`, `.venv/`, cache và `results/local/` được ignore; `src/recsysedu/data/` vẫn phải có trong Git.

```powershell
git status --short --untracked-files=all
git check-ignore data/raw/user.json .venv/Scripts/python.exe
```

Người nhận UI chạy fixture; người nhận dữ liệu dùng downloader để lấy đúng bản rồi đối chiếu hash. Không gửi raw vào commit. Chưa tạo repository GitHub, push hay phát hành dữ liệu trong đợt này. Quy ước nhận task/PR ở [CONTRIBUTING](../CONTRIBUTING.md).

## 7. Việc tiếp theo

Đọc [10 — Hướng theo môn học](10_course_direction.md). Chốt timezone có nguồn hoặc một giả định nghiên cứu ghi rõ; kiểm name/about, field bổ sung và subset, rồi xây M2 chuẩn hóa Parquet/split. Sau đó M3 MostPopular + evaluator, M4 Content TF-IDF, M6 BPR, M7 Hybrid. Hiện chỉ phân tích thông tin cần hiển thị; ghép kết quả thật ở M10 tuần 5, chưa phát triển thêm UI.
