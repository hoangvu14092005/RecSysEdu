# RecSysEdu — LearnPath trên MOOCCubeX

RecSysEdu là đồ án hệ gợi ý khóa học. Hệ thống dùng lịch sử đăng ký của người
học để tạo danh sách tối đa 10 khóa học, sau đó so sánh bốn cách gợi ý:
MostPopular, Content TF-IDF, BPR và Hybrid.

Giao diện LearnPath chỉ đọc kết quả đã tính sẵn. Việc chọn người học hoặc mô
hình trên giao diện không huấn luyện lại mô hình.

```text
course.json + user.json
          │
          ▼
  Làm sạch thành Parquet
          │
          ▼
 Chia train / valid / test
          │
          ▼
 Huấn luyện và đánh giá 4 model
          │
          ▼
  Snapshot JSON ──► Streamlit
                    ├─ Gợi ý học tập
                    └─ Model Lab
```

## Có thể làm gì với repository này?

- Mở giao diện bằng snapshot thật đã được bàn giao trong Git LFS.
- Xem lịch sử học và Top-10 gợi ý của từng model.
- Xem metric, cohort, seed, hash và tải kết quả CSV trong Model Lab.
- Chạy lại test và kiểm tra định dạng artifact.
- Khảo sát, xử lý và chia lại dữ liệu bằng CLI.
- Tạo thí nghiệm validation mới theo cùng data contract và protocol.

Repository chứa source, raw `course/user`, dữ liệu Parquet của pilot, split,
checkpoint và kết quả đã dùng để nghiệm thu. Các file lớn được quản lý bằng
Git LFS. Đây không phải toàn bộ 296 triệu log hành vi của MOOCCubeX.

## Bắt đầu nhanh trên Windows

### 1. Chuẩn bị

Cần cài:

- [Git](https://git-scm.com/download/win) và [Git LFS](https://git-lfs.com/).
- Python 3.10. Bản đã kiểm tra dùng Python 3.10.11.
- Ít nhất khoảng 5 GB dung lượng trống cho repository, môi trường Python và
  file tạm.

Các lệnh bên dưới chạy bằng PowerShell.

### 2. Lấy mã nguồn và file lớn

```powershell
git lfs install
git clone https://github.com/hoangvu14092005/RecSysEdu.git
Set-Location RecSysEdu
git lfs pull
```

Nếu đã clone repository, chỉ cần chạy `git lfs install` và `git lfs pull` tại
thư mục root. Lệnh sau phải hiển thị các file được Git LFS quản lý:

```powershell
git lfs ls-files
```

### 3. Tạo môi trường và cài dependency

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-win-py310.lock.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe -m pip check
```

File lock cài cả Streamlit, DuckDB, RecBole và Torch CPU. Lần cài đầu cần
Internet và có thể mất vài phút.

### 4. Kiểm tra snapshot thật

```powershell
.\.venv\Scripts\python.exe -m recsysedu.cli demo validate --bundle artifacts/demo/v1/demo_bundle.json
```

Lệnh hợp lệ phải kết thúc mà không có traceback. Nếu file chỉ chứa vài dòng bắt
đầu bằng `version https://git-lfs.github.com`, Git LFS chưa tải nội dung; chạy
lại `git lfs pull`.

### 5. Mở LearnPath

```powershell
$env:RECSYSEDU_BUNDLE = 'artifacts/demo/v1/demo_bundle.json'
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.headless true
```

Mở <http://127.0.0.1:8501>. Dừng server bằng `Ctrl+C`.

Trên giao diện:

1. Chọn hồ sơ người học ở thanh bên.
2. Chọn một trong bốn model.
3. Tab **Gợi ý học tập** hiển thị lịch sử và danh sách Top-10.
4. Tab **Model Lab** hiển thị metric, thông tin lần chạy và nút tải CSV.

Nếu chỉ muốn kiểm tra giao diện bằng dữ liệu mẫu, xóa biến môi trường rồi mở
lại app:

```powershell
Remove-Item Env:RECSYSEDU_BUNDLE -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m recsysedu.cli demo validate
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.headless true
```

Giao diện khi đó phải có nhãn **DỮ LIỆU MẪU**. Fixture này chỉ dùng để thử UI,
không phải kết quả huấn luyện.

## Các lệnh thường dùng

Chạy tại root của repository:

| Việc cần làm | Lệnh |
| --- | --- |
| Xem toàn bộ CLI | `.\.venv\Scripts\python.exe -m recsysedu.cli --help` |
| Kiểm tra snapshot thật | `.\.venv\Scripts\python.exe -m recsysedu.cli demo validate --bundle artifacts/demo/v1/demo_bundle.json` |
| Chạy test | `.\.venv\Scripts\python.exe -m pytest -q` |
| Kiểm tra code | `.\.venv\Scripts\python.exe -m ruff check src app tests` |
| Kiểm tra dependency | `.\.venv\Scripts\python.exe -m pip check` |
| Kiểm tra định dạng Git | `git diff --check` |

## Chạy pipeline dữ liệu

Pipeline đã dùng cho bản bàn giao gồm bốn bước:

```powershell
.\.venv\Scripts\python.exe -m recsysedu.cli data download --config configs/data.yaml
.\.venv\Scripts\python.exe -m recsysedu.cli data audit
.\.venv\Scripts\python.exe -m recsysedu.cli data prepare --config configs/prepare.yaml
.\.venv\Scripts\python.exe -m recsysedu.cli data split --config configs/split.yaml
```

Ý nghĩa từng bước:

1. `download`: tải `course.json` và `user.json`, kiểm tra dung lượng/hash.
2. `audit`: khảo sát cấu trúc và chất lượng raw.
3. `prepare`: chọn pilot 10.000 người, làm sạch và xuất Parquet.
4. `split`: chia dữ liệu theo thời gian thành train, validation và test.

Output đã tồn tại sẽ không bị ghi đè. Khi muốn tạo dataset hoặc thí nghiệm mới,
hãy sao chép config, đổi tên version và đổi thư mục output. Không sửa manifest
cũ để biến một lần chạy mới thành lần chạy đã nghiệm thu.

## Chạy thí nghiệm model

`configs/final_experiments.yaml` là cấu hình đã khóa của kết quả cuối. Không
dùng test để thử tham số mới. Quy trình đúng là:

1. Sao chép config sang một file mới, ví dụ `configs/my_experiment.yaml`.
2. Đặt output mới và `frozen: false`.
3. Chạy trên validation để chọn tham số.
4. Chốt config và hash trước khi chạy test một lần.

Ví dụ chạy cả bốn model trên validation:

```powershell
.\.venv\Scripts\python.exe -m recsysedu.cli experiments --split valid --config configs/my_experiment.yaml
```

Muốn chạy riêng một model, xem tham số bằng:

```powershell
.\.venv\Scripts\python.exe -m recsysedu.cli evaluate --help
.\.venv\Scripts\python.exe -m recsysedu.cli train --help
```

Chi tiết cách tạo freeze, xuất snapshot và chuyển artifact nằm trong
[runbook](docs/09_runbook.md).

## Cấu trúc thư mục

```text
RecSysEdu/
├── app/                 # Giao diện Streamlit
├── src/recsysedu/       # CLI, pipeline dữ liệu, model và evaluator
├── configs/             # Cấu hình data, split và thí nghiệm
├── data/
│   ├── raw/             # course.json, user.json và manifest
│   ├── processed/       # Dữ liệu pilot đã làm sạch
│   └── splits/          # Train, valid, test và cohort
├── artifacts/demo/v1/  # Snapshot JSON mà giao diện đọc
├── results/             # Metric, ranking, checkpoint và báo cáo
├── tests/               # Test tự động
├── docs/                # Kiến trúc, data contract, protocol và kế hoạch
└── tasks/               # Kế hoạch và trạng thái công việc
```

Luồng phụ thuộc quan trọng là:

```text
data contract → prepare → split → model → evaluator → demo export → UI
```

Nếu thay đổi một bước ở bên trái, cần kiểm tra lại các artifact ở bên phải.
Ví dụ: đổi cách split có thể làm checkpoint, metric và snapshot cũ mất hiệu lực.

## Kết quả hiện tại

Pilot dùng 10.000 người học và 2.586 khóa học ứng viên. Cả bốn model dùng cùng
K=10 và cùng quy tắc loại khóa đã thấy.

| Nội dung | Giá trị |
| --- | ---: |
| Người dùng có thể đánh giá ở test | 9.858 |
| Cold target bị loại khỏi test | 107 |
| Hybrid NDCG@10 | 0,07737 |
| Hybrid Recall/HR@10 | 0,13644 |
| Hybrid Precision@10 | 0,01364 |
| Hybrid Coverage@10 | 0,83952 |

Các số trên là kết quả của một pilot với một seed. Đăng ký khóa học không chứng
minh người học đã hoàn thành hoặc thành thạo. Điểm model là điểm xếp hạng, không
phải xác suất học thành công. Xem nguồn số liệu tại
[báo cáo test cuối](results/final/report.md).

Phần graph/lộ trình học đang dừng ở trạng thái
`P1_STOP_INSUFFICIENT_EVIDENCE` vì chưa có đủ nguồn concept, ánh xạ
course-concept và prerequisite đáng tin cậy. Dự án không tạo graph giả để minh
họa như kết quả thật.

## Cách nhận và hoàn thành một việc

1. Đọc [trạng thái công việc](tasks/todo.md) và tài liệu của module liên quan.
2. Tạo nhánh ngắn từ `main`:

   ```powershell
   git switch main
   git pull --ff-only
   git switch -c feature/ten-viec-ngan
   ```

3. Chỉ sửa các file thuộc phạm vi việc đang làm.
4. Thêm hoặc cập nhật test nếu thay đổi hành vi.
5. Chạy các lệnh kiểm tra trong mục **Các lệnh thường dùng**.
6. Commit rõ mục đích, push nhánh và mở Pull Request.

Một Pull Request nên ghi đủ:

```text
Giải quyết: việc hoặc lỗi nào
Đầu vào/đầu ra: file, schema hoặc artifact bị ảnh hưởng
Đã kiểm tra: lệnh đã chạy và kết quả
Còn thiếu: giới hạn hoặc phụ thuộc chưa hoàn tất
```

File lớn đúng các mẫu trong `.gitattributes` phải đi qua Git LFS. Không commit
`.env`, mật khẩu, token, `.venv` hoặc cache. Xem thêm
[CONTRIBUTING](CONTRIBUTING.md).

## Lỗi thường gặp

### `py -3.10` không tìm thấy Python

Cài Python 3.10 và chọn tùy chọn thêm Python Launcher. Có thể kiểm tra bằng:

```powershell
py --list
```

### Snapshot hoặc Parquet chỉ là file chữ rất nhỏ

Git LFS chưa tải nội dung:

```powershell
git lfs install
git lfs pull
git lfs status
```

### Cổng 8501 đang được dùng

Chạy app ở cổng khác:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py --server.port 8502
```

Sau đó mở <http://127.0.0.1:8502>.

### App báo không tìm thấy bundle

Kiểm tra đang đứng ở root và file tồn tại:

```powershell
Test-Path artifacts/demo/v1/demo_bundle.json
git lfs pull
```

### Muốn quay về dữ liệu mẫu

```powershell
Remove-Item Env:RECSYSEDU_BUNDLE -ErrorAction SilentlyContinue
```

Khởi động lại Streamlit sau khi đổi biến môi trường.

## Tài liệu nên đọc theo thứ tự

| Khi cần hiểu | Tài liệu |
| --- | --- |
| Bài toán và phạm vi | [Hướng đồ án](docs/10_course_direction.md) |
| Kiến trúc tổng thể | [Kiến trúc](docs/03_architecture.md) |
| Cột dữ liệu và quy ước | [Data contract](docs/04_data_contract.md) |
| Cách chia và đánh giá | [Evaluation protocol](docs/05_evaluation.md) |
| Cài đặt, chạy lại và bàn giao | [Runbook](docs/09_runbook.md) |
| Giao diện đọc dữ liệu gì | [UI handoff](docs/08_ui_handoff.md) |
| Kết quả cuối | [Báo cáo test](results/final/report.md) |
| Bằng chứng nghiệm thu | [Acceptance](reports/acceptance.md) |
| Việc đang làm và việc đã dừng | [Todo](tasks/todo.md) |

Môi trường đã được kiểm tra trên Windows/Python 3.10.11. Linux, macOS và GPU
chưa nằm trong phạm vi nghiệm thu hiện tại.
