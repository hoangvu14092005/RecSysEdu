# 09 — Cài, chạy và bàn giao RecSysEdu

Cập nhật 16/10/2026. Các khối lệnh là **hướng dẫn cho người nhận**, không phải
nhật ký khẳng định mọi lệnh đã được chạy trên máy mới. Bằng chứng đã thực thi
ở [tái lập](../results/reproduction.md), [test cuối](../results/final/report.md)
và [nghiệm thu](../reports/acceptance.md).

## 1. Cài từ Git

PowerShell tại root; cần Python 3.10, Internet và dung lượng cho Torch CPU.

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-win-py310.lock.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m recsysedu.cli --help
```

Lock chứa RecBole 1.2.1, Torch 2.5.1+cpu, NumPy 1.26.4 và các thư viện data/demo.
Bản tái lập đã thử trên Windows/Python 3.10.11; chưa chứng nhận Linux/macOS,
GPU hoặc môi trường cài theo khoảng version thay cho lock.

## 2. Mở demo

Không có artifact thật thì dùng fixture trong Git:

```powershell
.\.venv\Scripts\python.exe -m recsysedu.cli demo validate
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.headless true
```

Mở `http://127.0.0.1:8501`. Nhãn **DỮ LIỆU MẪU** phải hiện. Fixture chỉ kiểm
giao diện, không phải kết quả mô hình. Dừng bằng Ctrl+C.

Đã nhận snapshot thật thì đối chiếu SHA-256 với báo cáo trước khi mở:

```powershell
Get-FileHash artifacts/demo/v1/demo_bundle.json -Algorithm SHA256
.\.venv\Scripts\python.exe -m recsysedu.cli demo validate --bundle artifacts/demo/v1/demo_bundle.json
$env:RECSYSEDU_BUNDLE = 'artifacts/demo/v1/demo_bundle.json'
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.headless true
```

Chọn hồ sơ/model ở sidebar. Model Lab có metric/cohort/seed/hash và nút CSV.
Score chỉ là điểm xếp hạng. App không train khi click. Nếu snapshot thiếu/sai,
app dừng và hiện lỗi; không tự thay fixture. Để chủ động quay về mẫu, chạy
`Remove-Item Env:RECSYSEDU_BUNDLE` khi biến tồn tại rồi khởi động lại app.

## 3. Những file cần bàn giao riêng

Git **không chứa** raw, Parquet, learner IDs, checkpoint, feature hoặc snapshot thật.
Chỉ muốn xem kết quả: nhận `artifacts/demo/v1/demo_bundle.json` và đúng hash.
Muốn kiểm/load lại mô hình: nhận đầy đủ các thư mục dưới đây, giữ nguyên đường dẫn
tương đối từ root và kiểm hash trước khi dùng:

- `data/processed/mooccubex-pilot-v1/`: dataset manifest và toàn bộ Parquet.
- `data/splits/mooccubex-pilot-v1-split-v1/`: split manifest, train/valid/test,
  cohort và universe Parquet.
- `results/local/pilot-final/valid/valid-2e93583494064297adaa556b9bc21d64/`:
  toàn bộ batch validation đã khóa, gồm checkpoint/ID map/Content/alpha/ranking.
- Batch test được nêu chính xác trong [test cuối](../results/final/report.md).
- `results/local/pilot-search/bpr-3/valid-cbcf720e67144f10a735e06b0a717763/`:
  giữ để chạy lại validation theo config có `manifest_path` gốc.
- `artifacts/demo/v1/demo_bundle.json`: snapshot đã xuất.

Khi chuyển máy, **không sửa immutable manifest để đổi output_root**; code kiểm
vị trí thực tế của batch đã chuyển. Đường dẫn ghi trong manifest là nhật ký
nguồn gốc. Giữ toàn bộ thư mục, không chỉ chép `.pth`. Không đẩy các file này
lên repo công khai. Cần xác minh điều kiện sử dụng dữ liệu trước khi chia sẻ.

## 4. Tạo một thí nghiệm mới từ raw

Đây là hướng dẫn chạy lại, **không phải tái sử dụng freeze cũ cho dữ liệu mới**.

```powershell
.\.venv\Scripts\python.exe -m recsysedu.cli data download --config configs/data.yaml
.\.venv\Scripts\python.exe -m recsysedu.cli data audit
.\.venv\Scripts\python.exe -m recsysedu.cli data prepare --config configs/prepare.yaml
.\.venv\Scripts\python.exe -m recsysedu.cli data split --config configs/split.yaml
```

Raw gồm course/user ~851 MB; không cần toàn bộ log hành vi. Downloader kiểm
bytes/hash, giữ `.part` nếu hỏng và tải lại file dở từ đầu ở lần sau. Manifest
hash nhận diện bản đã tải, không phải chữ ký chứng thực từ nguồn.

`prepare.yaml` dùng 10.000 người/seed 20261016, thời gian `source_local_naive`.
Đó là giả định giữ thứ tự trong từng người, không phải bằng chứng timezone.
Không tự chuyển UTC. Output đã tồn tại không bị ghi đè. Muốn thí nghiệm mới,
tạo version/output riêng trong bản sao config.

Trước validation mới, sao chép `final_experiments.yaml`, đặt `frozen: false`,
bỏ freeze/validation_dir cũ, chọn output mới và bỏ manifest_path BPR cũ nếu
muốn train lại. Giữ budget/seed/protocol ghi trước. Ví dụ lệnh sau **cần config
mới đã soạn**, không chạy trực tiếp trên config frozen để chọn tham số lại:

```powershell
.\.venv\Scripts\python.exe -m recsysedu.cli experiments --split valid --config configs/my_experiment.yaml
```

Chỉ sau kiểm hash/protocol/ranking và chọn bằng validation mới tạo freeze mới
từ `freeze_candidate` cùng SHA-256 của experiment manifest. Chạy test một lần
cho freeze đó. Đừng đổi alpha hoặc BPR sau khi xem test. Lệnh frozen test của
bản bàn giao đã được chạy; kết quả lưu sẵn trong báo cáo.

## 5. Kiểm tra khi sửa source

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src app tests
.\.venv\Scripts\python.exe -m pip check
git diff --check
```

Fixture/integration khác benchmark thật. Test tự động không chứng minh người
học được lợi. Sửa cleaning/split/protocol/model phải đánh giá artifact nào mất
hiệu lực và tạo run mới; không sửa số liệu báo cáo bằng tay.

## 6. Chia việc trên GitHub

Mỗi người nhận một module/đầu ra theo [CONTRIBUTING](../CONTRIBUTING.md).
Commit source/config/test/docs nhỏ. Không `git add -f` raw/checkpoint/Parquet.
Kiểm `git status --short`, `git diff --cached --stat` và ignore trước khi push.
Trạng thái push/remote được người thực hiện xác nhận riêng; báo cáo thí nghiệm
không tự chứng minh GitHub đã nhận commit.

P1 hiện `P1_STOP_INSUFFICIENT_EVIDENCE`: chưa có ba nguồn concept/mapping/
prerequisite để audit thật. Muốn tiếp tục phải lấy nguồn, kiểm ID/label/cycle/
coverage rồi duyệt plan riêng; chưa triển khai rerank/path trong P0.
