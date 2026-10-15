# 07 — Dữ liệu lưu ở đâu cho gọn?

Cập nhật: 09/10/2026. Raw user/course đã tải về SSD, tổng 851.441.849 bytes (~812 MiB); chưa đo RAM/temp của pipeline Parquet hoặc train. Không cần tải hơn 296 triệu log để bắt đầu. Xem [audit thật](../results/data_audit.md). Người mới đọc [trang bắt đầu](README.md); tên cột/file do [04](04_data_contract.md) quy định.

## 1. Chia thành ba tầng

Coi raw như bản gốc, processed như bản đã làm sạch để tính toán, và serving như một gói nhỏ để mở giao diện. Mỗi tầng có mục đích khác nhau; không cần nhập toàn bộ raw vào PostgreSQL/MySQL.

```text
SSD local: raw + manifest
        ↓ Python đọc từng phần, DuckDB lọc/thống kê
Parquet: interactions, catalog, train/valid/test
        ↓ Model và evaluator
Checkpoint + kết quả từng run
        ↓ Xuất một snapshot nhỏ
JSON: demo_bundle → Streamlit LearnPath
```

**Parquet** là định dạng file bảng theo cột. **DuckDB** là công cụ truy vấn file; có thể đọc trực tiếp Parquet và lọc/chọn cột, nên không bắt buộc giữ thêm một bản đầy đủ trong `.duckdb`. [DuckDB Parquet](https://duckdb.org/docs/current/data/parquet/overview).

## 2. Chọn chỗ lưu từng loại

| Loại dữ liệu | Nơi/định dạng | Bàn giao cần kèm gì? |
| --- | --- | --- |
| Raw user/course, P1 raw nếu dùng | `data/raw/` trên SSD | URL, ngày tải, bytes, SHA-256; giữ nguyên file |
| Interactions/catalog/splits | `data/processed/<dataset_version>/`, Parquet | Dataset/split manifest và config làm sạch/chia |
| Concept/mapping/edges — P1 | Parquet; edge list nhỏ khi tiện | Namespace ID, nhãn đã lọc, graph audit |
| Vector Content thưa | `.npz` + ID map/feature config | Map hàng/cột, version, tham chiếu catalog |
| Bản input RecBole | `data/recbole/`, TSV `.inter` | Xuất từ cùng split; không chia lại |
| Model | `artifacts/<run_id>/` | Checkpoint, ID map, config, feature/graph reference, môi trường |
| Metric/ranking/logs | `results/<run_id>/`, CSV/JSON/Parquet | Run manifest; không ghi đè run cũ |
| Dữ liệu mở UI | `artifacts/demo/<snapshot_id>/demo_bundle.json` | Một gói nhỏ tương thích theo contract 04 |
| Fixture giả | `tests/fixtures/`, CSV/JSON nhỏ | Nhãn SYNTHETIC; đưa vào Git để UI/test dùng ngay |

Ma trận Content có nhiều số 0 có thể lưu sparse `.npz`, thay vì biến thành bảng đặc lớn. [SciPy save_npz](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.save_npz.html). RecBole nhận atomic files `.inter`; adapter phải xuất TSV từ Parquet, không giả định thư viện đọc Parquet trực tiếp. [RecBole atomic files](https://recbole.io/docs/user_guide/data/atomic_files.html).

## 3. Có cần xử lý toàn bộ 296 triệu hành vi?

Không cần cho P0. Bắt đầu user/course để lấy đăng ký và nội dung; log xem video/làm bài là P2. MOOCCubeX công bố user khoảng 770M, course 43M; đó là kích thước danh mục nguồn, chưa là bytes đã tải hoặc dung lượng sau xử lý của dự án. [Danh mục dữ liệu](https://github.com/THU-KEG/MOOCCubeX).

Chọn subset sau khi biết người học có bao nhiêu khóa hợp lệ. Mục tiêu thử 10.000–30.000 người có thể điều chỉnh bằng số đo; không chọn người theo test score. CS ưu tiên cho graph, không lọc cứng toàn benchmark nếu làm mất lịch sử.

## 4. Dung lượng/RAM cần tính bằng số đo

Không chốt “100 GB tối thiểu” chỉ từ quy mô công bố. Tính:

```text
Chỗ trống cần = raw thực tải + processed/splits + bản export RecBole
              + temp peak + checkpoint/results giữ lại + phần dự phòng
```

Pilot nhỏ phải ghi thời gian, RAM cao nhất, temp disk cao nhất và số dòng/byte output. Sau đó chọn subset, số run giữ lại và chỗ sao lưu. Đặt temp ở ổ đủ trống; đừng chia Parquet theo từng user hoặc tạo quá nhiều file trước khi có nhu cầu truy vấn.

DuckDB có thể dùng đĩa tạm cho một số công việc vượt RAM, nhưng không bảo đảm mọi query đều chạy được. Không kéo toàn dataset sang pandas/NetworkX nếu vượt bộ nhớ; lọc/chọn cột/aggregate trước. Train model cũng cần RAM/VRAM riêng. [DuckDB workload tuning](https://duckdb.org/docs/current/guides/performance/how_to_tune_workloads).

P1 chỉ nạp graph đã lọc cần cho bài toán; file edge nhỏ không đồng nghĩa object graph nhỏ. Đo RAM thật trước tăng quy mô. [NetworkX DiGraph](https://networkx.org/documentation/stable/reference/classes/digraph.html).

## 5. Cùng làm và sao lưu thế nào?

GitHub chứa source, config, dependency lock, tài liệu, fixture synthetic và báo cáo phù hợp. Raw/processed/checkpoint lớn để trên SSD và sao lưu ở ổ khác, Drive hoặc bucket riêng tư theo nhu cầu. Manifest/runbook ghi cách lấy và checksum; không nhúng tài khoản vào repo.

Nếu dùng Colab, chép subset cần chạy vào ổ phiên làm việc rồi train; lưu checkpoint/kết quả quan trọng về nơi bền vững trước khi kết thúc. Không giữ bản duy nhất trên ổ tạm.

UI chỉ cần fixture hoặc snapshot demo; người nhận không cần tải toàn raw. Chốt đường dẫn tương đối theo root; config local chứa đường dẫn máy cá nhân. Quy trình PR và phạm vi file theo [CONTRIBUTING](../CONTRIBUTING.md).

## 6. Khi nào mới thêm PostgreSQL/React/FastAPI?

Chỉ xem xét khi có nhu cầu web nhiều người dùng, hồ sơ được cập nhật online hoặc cần tái hiện chính xác UI riêng. Khi đó PostgreSQL lưu metadata/profile/Top-K/path nhỏ; raw/processed vẫn ở kho file. Đây là thay đổi phạm vi có thêm importer, migration, API và frontend, không phải bước cần làm hôm nay.

Kết quả phục vụ web cần cùng run/dataset/profile version; xuất và kiểm tra một snapshot hoàn chỉnh trước khi đổi bản đang dùng. Precompute Top-10 hợp với hồ sơ cố định. Đổi lịch sử/sở thích/alpha cần tính lại hoặc fallback rõ, không tự có ranking mới từ cache cũ. Model Lab bấm train còn cần job/status riêng, ngoài MVP.

Không cần Hadoop/Spark/MongoDB trong hướng hiện tại. PostgreSQL có khả năng tổ chức bảng lớn; lý do chưa dùng cho raw là giảm phần nhập liệu/vận hành không cần cho đồ án, không phải kết luận nó không xử lý được dữ liệu lớn. [PostgreSQL partitioning](https://www.postgresql.org/docs/current/ddl-partitioning.html).

## 7. Việc cần làm ở M1–M2

Tải user/course và ghi manifest → kiểm format/ID/thời gian → làm sạch/xuất Parquet → dùng DuckDB thống kê → chia tập → xuất một bộ RecBole nhỏ/thử loader. Cần khớp số dòng, ID/kiểu dữ liệu, checksum, quy tắc split; RAM/temp/thời gian được ghi. Đây là kế hoạch pilot, chưa phải benchmark đã chạy.
