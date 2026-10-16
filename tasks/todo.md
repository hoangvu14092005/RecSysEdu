# Tiến độ RecSysEdu

Ngày cập nhật: 16/10/2026. Dấu `[x]` chỉ ghi việc có bằng chứng; mã task tương ứng [plan](plan.md).

## Hàng đợi hiện tại — triển khai Pipeline-first

Theo [kế hoạch đã duyệt](../docs/superpowers/plans/2026-10-16-recsysedu-pipeline-first.md).
Các mục ngày 09/10 bên dưới là nhật ký lịch sử; dùng bảng này để biết trạng thái hiện tại.

| Task | Trạng thái và đầu ra | Bằng chứng / bước còn lại |
| --- | --- | --- |
| 0–10 | Đã triển khai, kiểm thử và review từng task: contract, prepare/split, evaluator, bốn model, runner, snapshot exporter | Fixture/integration đã chạy; không đồng nghĩa demo thật và test cuối đã nghiệm thu |
| 11 | Đã chạy pilot 10.000 người, bốn model và năm alpha; khóa cấu hình sau audit | [Dữ liệu](../results/pilot/dataset_report.md), [validation](../results/pilot/validation_report.md), [core manifest](../results/pilot/core_manifest.json); 9.909 warm valid, 2.586 candidate; chưa mở test |
| 12 | Đã triển khai công cụ audit; dữ liệu graph thật chưa chạy vì thiếu cả ba nguồn | [Quyết định P1_STOP_INSUFFICIENT_EVIDENCE](../results/graph_audit.md); không bật rerank/path |
| 13 | Chưa chạy; freeze Task 11 đã sẵn sàng để review | Test cuối, snapshot thật, xem trình duyệt, môi trường sạch và báo cáo bàn giao |
| GitHub | Chờ kiểm tra cuối toàn nhánh | Sau khi xong, đưa về main và push remote người dùng đã chỉ định |

Phân biệt: code đã viết, fixture chạy được, dữ liệu thật đã chạy và hiệu quả
được chứng minh là bốn mức bằng chứng khác nhau. Không tick toàn bộ cổng sáu
tuần chỉ vì thư viện và bộ kiểm thử đã chạy.

## Đợt khởi tạo tài liệu

- [x] Xác nhận root ban đầu trống, chưa có `.git`.
- [x] Đọc nội dung đoạn văn/bảng DOCX và toàn bộ bản phân tích dán.
- [x] Đối chiếu schema và framework từ nguồn chính thức.
- [x] Người dùng chọn tài liệu và kế hoạch trước.
- [x] Viết phân tích, yêu cầu, kiến trúc, data contract, protocol, nguồn và ADR đề xuất.
- [x] Viết plan có dependencies, đầu ra, nghiệm thu và lệnh dự kiến.
- [x] Kiểm tra bộ tài liệu ban đầu: 11 file Markdown, 26 liên kết file nội bộ và 14 task có trường nghiệm thu/kiểm tra; không có lỗi kiểm tra cấu trúc ở lần đó.
- [x] Viết lịch sáu tuần với 30 ngày làm việc, artifact/nghiệm thu từng ngày và phương án xử lý chậm tiến độ; chưa thực hiện lịch.
- [x] Kiểm tra bản lịch mới: đủ D01–D30, sáu cổng nghiệm thu, 14 M-task và 36 liên kết file nội bộ trong 12 file Markdown; không có lỗi cấu trúc.
- [x] Phân tích phương án lưu trữ: raw ngoài DB, Parquet/DuckDB cho dữ liệu lớn, snapshot nhỏ cho demo; PostgreSQL khi cần backend.
- [x] Đọc chat “Phân tích đề xuất UI LearnPath” cùng project và đặc tả UI nguồn; tổng hợp hai tab và các điểm cần sửa.
- [x] Viết contract snapshot UI đề xuất và hướng dẫn cùng làm qua GitHub; cập nhật yêu cầu/kiến trúc/lịch. Chưa triển khai UI hoặc tạo remote.
- [x] Kiểm tra bản tổng hợp: 15 file Markdown, 60 liên kết nội bộ, đủ 14 M-task và D01–D30; prototype tham khảo có checksum trùng nguồn. Đây là kiểm tra tài liệu, chưa phải kiểm thử ứng dụng.
- [x] Viết lại toàn bộ docs theo cùng hướng: P0 bốn model, Parquet processed, hai tab Streamlit, contract UI ở tài liệu 04; thêm trang bắt đầu/thuật ngữ dễ hiểu.
- [x] Đồng bộ README, CONTRIBUTING, plan, kickoff và lịch sáu tuần với bản tổng hợp; chưa thực thi task phần mềm.
- [x] Kiểm tra bản docs thống nhất: 10 Markdown trong docs, 16 Markdown toàn root, 94 liên kết nội bộ, 14 M-task và D01–D30; checksum ba nguồn khớp, không có lỗi cấu trúc. Chưa kiểm thử ứng dụng/model.
- [x] Bắt đầu triển khai base theo yêu cầu kiểm tra base/lấy dữ liệu; giữ hướng đơn giản và không mở rộng sang toàn dự án.

## Base đã làm ngày 09/10/2026

- [x] Init Git local; chưa commit, chưa gắn remote hoặc push.
- [x] Package, CLI help, môi trường `.venv` Python 3.10.11 và lock cho Windows Python 3.10.
- [x] Downloader ghi `.part`, kiểm số byte và SHA-256, giữ nguyên file hoàn chỉnh khi chạy lại.
- [x] Tải thật course/user, tổng 851.441.849 bytes; chạy lại downloader xác nhận checksum.
- [x] Parser streaming JSON Lines/array; audit toàn 3.330.294 người và 3.781 khóa; nối ID số sang mã có trong catalog.
- [x] Fixture SYNTHETIC, loader kiểm ID/rank/seen/hash và app hai tab; mẫu không có metric giả.
- [x] Chạy kiểm thử tự động, lint và pip check; xem [báo cáo base](../results/base_verification.md).
- [x] Ghi [audit thật](../results/data_audit.md) và [runbook](../docs/09_runbook.md) cho người nhận.
- [ ] M0 còn fixture target-cold/graph-cycle cho task tiếp theo và nhóm dependency cf/graph chưa thử.
- [ ] M1 còn xác định timezone, chất lượng metadata và subset trước khi chốt dataset; không bắt buộc lọc CS cho benchmark chính.
- [ ] Chưa prepare/split, chưa train/evaluate và chưa có ranking thật; không đánh dấu M0/M1/M10 hoàn tất chỉ vì base chạy.

## Phân tích theo tài liệu môn học ngày 09/10/2026

- [x] Khảo sát 11 PDF/367 trang; đọc kỹ phần liên quan và xem trực quan chín trang chứa tiêu chí/công thức. Ghi trang/hash trong [manifest](../docs/reference/course_material_manifest.json).
- [x] Viết [hướng đồ án](../docs/10_course_direction.md) và [ghi chú nguồn](../docs/11_course_reading_notes.md); tách căn cứ trong bài giảng khỏi lựa chọn của dự án.
- [x] Kiểm metadata: 3.781 khóa có tên, 3.692 có about không rỗng, 547 có field; số raw không thay kiểm tra chất lượng sau cleaning.
- [x] Đề xuất Content TF-IDF tên/mô tả, BPR từ đăng ký, Hybrid và evaluator chung; thay ưu tiên field-only theo [ADR-002](../docs/decisions/ADR-002-course-grounded-direction.md).
- [x] Viết lại [08](../docs/08_ui_handoff.md) thành chức năng/thông tin cần hiển thị; đồng bộ docs/plan/lịch, chưa sửa code UI hoặc train mô hình.
- [x] Kiểm tra 22 Markdown/176 liên kết file nội bộ, 11 PDF/367 trang và source hash, tham chiếu chín trang trực quan, D01–D30 và 14 M-task; không có lỗi. Quét lại metadata khớp số đã ghi. Đây là kiểm tra tài liệu/nguồn, chưa kiểm thử thuật toán.

## Triển khai theo lịch

Lịch công việc hằng ngày ở [six_week_schedule](six_week_schedule.md). Các cổng G dưới đây là mục tiêu chưa đạt.

- [ ] G1 cuối tuần 1 — Dataset/split v1; thử môi trường BPR nhỏ.
- [ ] G2 cuối tuần 2 — Hai baseline có validation và evaluator đúng.
- [ ] G3 cuối tuần 3 — Bốn model cùng protocol, checkpoint load được.
- [ ] G4 cuối tuần 4 — Xác định P1 graph/path đạt hay thiếu dữ liệu.
- [ ] G5 cuối tuần 5 — Demo thật và khóa cấu hình; hết tính năng mới.
- [ ] G6 cuối tuần 6 — Test cuối, tái lập và bàn giao.

- [ ] M0 — Môi trường và fixture SYNTHETIC.
- [ ] M1 — Raw acquisition và data audit.
- [ ] M2 — Chuẩn hóa, split và cohort.
- [ ] Checkpoint A — Dataset và protocol hợp lệ.
- [ ] M3 — MostPopular và evaluator chung.
- [ ] M4 — Content TF-IDF tên/mô tả + cosine.
- [ ] Checkpoint B — Hai baseline cùng protocol.
- [ ] M5 — Feature concept nếu đủ dữ liệu; có thể hoãn với lý do.
- [ ] M6 — BPR/RecBole, ID map và reload checkpoint.
- [ ] M7 — Hybrid tune validation.
- [ ] Checkpoint C — Bốn model có kết quả tái lập.
- [ ] M8 — Graph audit và coverage.
- [ ] M9a — Prerequisite reranking.
- [ ] M9b — Learning path concept.
- [ ] Checkpoint D — Graph/path có bằng chứng và giới hạn.
- [ ] M10 — Demo đọc artifact.
- [ ] M11 — Thực nghiệm cuối và phân tích.
- [ ] M12 — Tái lập trong môi trường sạch.
- [ ] Checkpoint E — Bàn giao theo yêu cầu và trạng thái thật.

## Cách cập nhật sau mỗi task

Ghi task ID, thời gian, input/output hash, lệnh đã chạy và kết quả, file artifact, lỗi/giới hạn, bước tiếp theo. “Viết xong code” khác “đã chạy fixture”, khác “đã chạy dữ liệu thật”, khác “đã chứng minh cải thiện”. Nếu task hoãn, ghi hoãn và lý do; không đánh dấu hoàn thành.
