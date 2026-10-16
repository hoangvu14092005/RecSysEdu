# Kiểm chứng base RecSysEdu

Ngày 09/10/2026. Root `<REPO_ROOT>`. Đợt này dựng base và kiểm khả năng lấy dữ liệu, chưa hoàn thành P0 hoặc cả lịch sáu tuần.

## Đầu ra hiện có

- Package `recsysedu`, CLI help/download/audit/demo validate.
- Downloader tải từng file, chỉ công bố file sau khi đủ byte; ghi manifest/hash, tránh ghi đè file sẵn có.
- Reader JSON Lines/array và audit aggregate không xuất tên/ID người học; ID số nối sang mã catalog có thật, timestamp chưa tự gán timezone.
- Fixture UI SYNTHETIC: sáu khóa giả, ba hồ sơ, hai danh sách model minh họa, không có metric offline.
- Loader chặn ID lạ/seen/trùng, rank sai, số không hữu hạn, run/hash không khớp, lựa chọn nhập nhằng và field thiếu.
- Streamlit hai tab, lịch sử/đổi hồ sơ-model/giải thích, Model Lab có metadata run và xuất CSV; chưa hỗ trợ paths.
- Lock base và [runbook](../docs/09_runbook.md); Git init local, chưa commit/remote/push.

## Môi trường đã chạy

| Thành phần | Phiên bản |
| --- | --- |
| Hệ điều hành | Windows |
| Python môi trường riêng | 3.10.11 |
| Streamlit | 1.65.0 |
| DuckDB | 1.5.6 |
| PyArrow | 25.0.1 |
| ijson / PyYAML | 3.5.1 / 6.0.3 |
| pytest / Ruff | 9.1.1 / 0.16.10 |

Đã cài editable `.[dev,demo,data]` vào `.venv`. Lock từ môi trường này nằm ở `requirements-win-py310.lock.txt`, bỏ đường dẫn editable máy cá nhân. Cài library dữ liệu không đồng nghĩa pipeline Parquet đã viết. Chưa thử RecBole/PyTorch/graph hay cài lock trên máy người khác.

## Lệnh và kết quả

| Kiểm tra | Kết quả thực chạy |
| --- | --- |
| `python -m pytest -q` | 28 passed |
| `python -m ruff check src app tests` | All checks passed; rule cơ bản E4/E7/E9/F |
| `python -m pip check` | No broken requirements |
| `python -m recsysedu.cli --help` | CLI hoạt động |
| `python -m recsysedu.cli demo validate` | Fixture hợp lệ, synthetic/ba hồ sơ |
| `python -m recsysedu.cli data download` | Hai file thật tải xong; chạy lại giữ file sau kiểm hash |
| `python -m recsysedu.cli data audit` | Full raw audit 3.330.294 user/3.781 course, timezone unresolved |
| `git check-ignore` | Raw/.venv/local report bị ignore; source data không bị ignore |

Tests bao phủ HTTP trả HTML/tải thiếu/file có sẵn; parser/ID/mảng lệch/timestamp/tie; snapshot/seen/rank/hash/NaN/field thiếu; CLI lỗi; AppTest đổi hồ sơ/model và hai tab. Các lỗi được viết regression test và quan sát fail trước khi sửa. Đây là kiểm chứng base, chưa phải evaluator/model acceptance.

## Rà soát và giao diện thật

Một reviewer độc lập đọc toàn code base, tái hiện ba lỗi: ignore nhầm source data, thiếu seed gây lỗi UI, JSON array hỏng không được CLI bắt. Cả ba đã sửa; hai lỗi đầu vào có regression tests, ignore kiểm qua Git.

App được chạy tại `http://127.0.0.1:8501/` trên trình duyệt thật. Đã chuyển hai tab, chọn người mới, đổi MostPopular sang Content-based, thấy lịch sử rỗng và ranking cập nhật sau đóng sidebar ở cửa sổ hẹp. Model Lab báo chưa có metric; console không có warn/error trong lần kiểm. Đã mở giải thích và kiểm nhãn minh họa, lưu [ảnh base](screenshots/learnpath-base.jpg). Chưa kiểm đầy đủ accessibility hoặc mọi kích thước màn hình.

## Trạng thái task và giới hạn

M0 làm được package/CLI/env/fixture UI, còn fixture target-cold/graph-cycle và cf/graph chưa thử. M1 làm được download/full audit, còn timezone/subset. M10 làm trước phần UI fixture để có base nhìn được; chưa nghiệm thu tích hợp thật.

Chưa có prepare/split/train/evaluate, checkpoint BPR, metric model, graph/lộ trình hoặc bằng chứng cải thiện. [Audit thật](data_audit.md) và [todo](../tasks/todo.md) là nguồn trạng thái; không dùng việc UI mở được để nói hệ gợi ý đã hoàn thành.

Ruling đợt base: triển khai hai tab fixture sớm để người nhận UI có đầu vào kiểm được; không thay đổi yêu cầu bốn model hoặc cổng nghiệm thu. M0/M1 chưa tick hoàn tất do chưa đủ điều kiện. Không mở rộng đợt này sang toàn bộ plan sáu tuần.
