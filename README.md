# RecSysEdu — LearnPath trên MOOCCubeX

RecSysEdu là đồ án gợi ý tối đa 10 khóa học từ lịch sử đăng ký của người học.
Dự án so sánh bốn mô hình: MostPopular, Content TF-IDF, BPR và Hybrid.

```text
MOOCCubeX course/user
        ↓
Parquet → train/valid/test
        ↓
4 model → đánh giá → snapshot JSON
        ↓
Streamlit: Gợi ý học tập | Model Lab
```

Giao diện chỉ đọc kết quả đã tính sẵn, không huấn luyện model khi người dùng
thao tác.

## Bắt đầu

### Yêu cầu

- Windows và Python 3.10.
- Git và [Git LFS](https://git-lfs.com/).
- Khoảng 5 GB dung lượng trống.

Git LFS lưu các file lớn như raw JSON, Parquet và checkpoint. Repository hiện
đã chứa dữ liệu và artifact của pilot; đây không phải toàn bộ 296 triệu log
hành vi của MOOCCubeX.

### Cài đặt

```powershell
git lfs install
git clone https://github.com/hoangvu14092005/RecSysEdu.git
Set-Location RecSysEdu
git lfs pull

py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-win-py310.lock.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe -m pip check
```

### Mở demo bằng kết quả thật

```powershell
.\.venv\Scripts\python.exe -m recsysedu.cli demo validate --bundle artifacts/demo/v1/demo_bundle.json
$env:RECSYSEDU_BUNDLE = 'artifacts/demo/v1/demo_bundle.json'
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.headless true
```

Mở <http://127.0.0.1:8501>. Dừng server bằng `Ctrl+C`.

Nếu file dữ liệu chỉ chứa dòng bắt đầu bằng
`version https://git-lfs.github.com`, chạy lại `git lfs pull`.

## Lệnh kiểm tra

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src app tests
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

Xem các lệnh pipeline:

```powershell
.\.venv\Scripts\python.exe -m recsysedu.cli --help
```

Hướng dẫn tải, xử lý, chia dữ liệu và chạy thí nghiệm nằm trong
[runbook](docs/09_runbook.md).

## Cấu trúc chính

| Đường dẫn | Nội dung |
| --- | --- |
| `src/recsysedu/data/` | Code tải, kiểm tra, làm sạch và chia dữ liệu |
| `src/recsysedu/models/` | MostPopular, Content và Hybrid |
| `src/recsysedu/adapters/` | Kết nối RecBole/BPR |
| `src/recsysedu/evaluation/` | Ranking và metric |
| `src/recsysedu/experiments/` | Điều phối các lần chạy |
| `src/recsysedu/demo/` | Xuất và kiểm tra snapshot |
| `app/` | Giao diện Streamlit |
| `data/` | Raw, processed và split |
| `results/` | Metric, ranking và checkpoint |
| `artifacts/demo/v1/` | Snapshot giao cho UI |

`src/recsysedu/data/` chứa **code xử lý dữ liệu**; `data/` ở root chứa
**file dữ liệu**.

## Trạng thái hiện tại

- Pilot: 10.000 người học, 2.586 khóa học ứng viên.
- Đã chạy bốn model trên cùng protocol và tạo snapshot thật cho ba hồ sơ.
- Kết quả và giới hạn: [báo cáo test cuối](results/final/report.md).
- Bằng chứng bàn giao: [acceptance](reports/acceptance.md).
- Graph/lộ trình học đang dừng vì thiếu nguồn concept và prerequisite đủ tin cậy.

`configs/final_experiments.yaml` là cấu hình đã khóa. Khi thử tham số mới,
hãy tạo config và output mới, chọn bằng validation và không dùng test để tinh
chỉnh model.

## Team bắt đầu từ đâu?

1. Đọc README và chạy được demo thật.
2. Đọc [kiến trúc](docs/03_architecture.md).
3. Chọn phần việc và đọc tài liệu tương ứng:

   | Phần việc | Tài liệu |
   | --- | --- |
   | Data | [Data contract](docs/04_data_contract.md) |
   | Model/Evaluation | [Evaluation protocol](docs/05_evaluation.md) |
   | UI | [UI handoff](docs/08_ui_handoff.md) |
   | Cài đặt/bàn giao | [Runbook](docs/09_runbook.md) |

4. Xem [trạng thái công việc](tasks/todo.md).
5. Tạo nhánh `feature/<ten-viec>`, chạy kiểm tra và mở Pull Request theo
   [CONTRIBUTING](CONTRIBUTING.md).

Môi trường đã được kiểm tra trên Windows/Python 3.10.11. Linux, macOS và GPU
chưa nằm trong phạm vi nghiệm thu.
