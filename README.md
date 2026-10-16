# RecSysEdu — LearnPath trên MOOCCubeX

Gợi ý tối đa 10 khóa học từ lịch sử đăng ký và so sánh MostPopular, Content
TF-IDF, BPR, Hybrid. LearnPath chỉ xem kết quả đã tính; bấm trên giao diện
không huấn luyện lại mô hình.

```text
Raw course/user → Parquet → train/valid/test → bốn model → đánh giá
  → snapshot JSON → Streamlit: Gợi ý học tập | Model Lab
```

**Bản bàn giao 16/10/2026:** xem [nghiệm thu](reports/acceptance.md),
[test cuối](results/final/report.md), [tái lập](results/reproduction.md) và
[trạng thái công việc](tasks/todo.md). P1 graph/lộ trình dừng vì thiếu nguồn
dữ liệu thật. Không bật đường học giả để minh họa.

## Chạy thử sau khi clone

Các lệnh dưới đây là hướng dẫn cho người nhận, chạy PowerShell tại root.
Môi trường đã kiểm: Windows/Python 3.10.11; chưa kiểm Linux/macOS.

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-win-py310.lock.txt
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe -m recsysedu.cli demo validate
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.headless true
```

Mở `http://127.0.0.1:8501`. Mặc định là fixture **DỮ LIỆU MẪU**; không cần
raw. Clone Git chỉ có source, cấu hình, lock, fixture và báo cáo nhỏ. Raw,
Parquet, checkpoint và snapshot thật phải nhận riêng hoặc tạo lại.

Để mở snapshot thật đã nhận và đối chiếu hash trong báo cáo:

```powershell
.\.venv\Scripts\python.exe -m recsysedu.cli demo validate --bundle artifacts/demo/v1/demo_bundle.json
$env:RECSYSEDU_BUNDLE = 'artifacts/demo/v1/demo_bundle.json'
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.headless true
```

File thiếu/sai sẽ báo lỗi, không tự quay về mẫu. [Runbook](docs/09_runbook.md)
chỉ rõ cách lấy dữ liệu, chạy pipeline và chuyển artifact cho đồng đội.

## Cách đọc kết quả

Pilot chọn 10.000 người từ raw MOOCCubeX. Bốn model dùng chung 2.586 khóa
candidate, K=10 và cách phá hòa theo mã khóa. Model/hồ sơ chỉ học từ train.
Validation chọn tham số. Test giữ nguyên model và loại khóa đã thấy trong
train + valid. Không dùng kết quả test để chọn lại tham số.

Đăng ký không chứng minh thành thạo, hoàn thành hay học tốt hơn. Điểm model
không phải xác suất thành công. Một pilot/một seed chưa chứng minh kết quả
tổng quát. [Pilot](results/pilot/validation_report.md) lưu ba lần thử BPR và
năm trọng số Hybrid. [Graph audit](results/graph_audit.md) ghi rõ nguồn còn thiếu.

## Tài liệu cho người cùng làm

| Cần biết | Tài liệu |
| --- | --- |
| Bài toán và môn học | [Hướng đồ án](docs/10_course_direction.md), [ghi chú bài giảng](docs/11_course_reading_notes.md) |
| Kiến trúc, đầu vào/đầu ra | [Kiến trúc](docs/03_architecture.md), [data contract](docs/04_data_contract.md) |
| Cách đánh giá | [Protocol](docs/05_evaluation.md) |
| Cài/chạy/bàn giao | [Runbook](docs/09_runbook.md), [tái lập](results/reproduction.md) |
| Kế hoạch và trạng thái | [Plan đã duyệt](docs/superpowers/plans/2026-10-16-recsysedu-pipeline-first.md), [todo](tasks/todo.md) |
| Làm việc GitHub | [CONTRIBUTING](CONTRIBUTING.md) |

Giữ dự án gọn: Parquet/DuckDB xử lý offline, checkpoint cho model, Streamlit
đọc snapshot. PostgreSQL/FastAPI/React, log video/bài tập, LightGCN và graph/path
là mở rộng sau P0. Không commit dữ liệu người học hoặc artifact lớn vào GitHub.
