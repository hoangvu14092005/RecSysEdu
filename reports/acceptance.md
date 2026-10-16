# Nghiệm thu P0 — RecSysEdu

Ngày 16/10/2026. Bản này đánh giá sản phẩm offline theo
[thiết kế đã duyệt](../docs/superpowers/specs/2026-10-16-recsysedu-pipeline-first-design.md).
Không coi test tự động hoặc giao diện đẹp là bằng chứng học tập hiệu quả.

**Kết luận: P0 đạt phạm vi offline đã duyệt; P1 dừng có lý do.** Dữ liệu thật,
bốn model, test đã khóa, snapshot thật, trình duyệt và môi trường sạch đều có
bằng chứng dưới đây. Review toàn nhánh/tích hợp/push là bước riêng sau Task13.

| Cổng P0 | Trạng thái |
| --- | --- |
| Dataset/split versioned, đúng 10.000 người pilot, hash/invariant | Đạt; 9.965 người sau loại tie, 9.858 warm test |
| Bốn model cùng evaluator, BPR checkpoint reload | Đạt; train-only, K10, seed17; reload khớp |
| Validation chọn config rồi test một lần | Đạt; Hybrid alpha0,25; không tune theo test |
| Metric, low/high-history và lỗi | Đạt; Hybrid test NDCG0,0773727819; còn 8.513 miss |
| Snapshot real schema1, ít nhất3 hồ sơ | Đạt; 3×4 model, paths rỗng, loader qua |
| Demo thực trong browser/CSV/error states | Đạt; chi tiết dưới đây |
| Môi trường Python sạch từ lock | Đạt trên cùng máy Windows; fixture + checkpoint nhỏ + snapshot qua |
| Máy vật lý khác/đa nền tảng/production | Chưa kiểm; ngoài bằng chứng của bản bàn giao |

## Phạm vi bàn giao

| Phần | Bằng chứng |
| --- | --- |
| Raw, cleaning, dataset/split versioned | [Dataset report](../results/pilot/dataset_report.md) |
| Bốn model, cùng protocol, validation và freeze | [Validation report](../results/pilot/validation_report.md), [manifest công khai](../results/pilot/core_manifest.json) |
| Test cuối, phân tích nhóm và lỗi | [Final report](../results/final/report.md) |
| Môi trường sạch, checkpoint, snapshot | [Reproduction](../results/reproduction.md) |
| Lệnh cài/chạy và chuyển artifact | [Runbook](../docs/09_runbook.md) |
| P1 graph | [Audit](../results/graph_audit.md): **P1_STOP_INSUFFICIENT_EVIDENCE** |

## Kiểm giao diện đã thực thi

Root agent dùng trình duyệt thật trên server Streamlit đọc đúng snapshot hash
`3e80b5e90db8f2776ff7f5e58915696f45f9b552ee8b7f0fe2219ae20577e56e`:

- Cả 12 lựa chọn (ba hồ sơ × bốn model) hiển thị 10 dòng/rank và run ID đúng;
  top thay đổi theo model/hồ sơ. Nhãn offline/dataset/protocol/P1-limit có mặt.
- Model Lab hiển thị test/warm/full_train_universe/train_plus_valid cùng metric,
  seed/hash. Bấm tải CSV thực sự thành công. Đọc lại CSV bằng pandas: bốn dòng,
  cỡ mẫu9.858, run IDs và mọi metric khớp snapshot trong `1e-12`.
- CSV SHA-256: `ca9bf2d2587c4756f04449dd618905861a7713a575db35b4ff7a13f2a5eda406`.
- Fixture có nhãn **DỮ LIỆU MẪU** kiểm danh sách ngắn3 và fallback người mới.
  Một bản sao fixture synthetic riêng kiểm danh sách0: hiện không-history,
  fallback và thông báo không có khóa; không sửa snapshot thật để giả case này.
- Bundle real hỏng chỉ hiện lỗi schema; không có panel gợi ý hoặc tự fallback
  sang synthetic. Browser warning/error logs rỗng cho các lượt kiểm.

Quan sát trình duyệt xác nhận hành vi hiển thị/tải file. Tính hợp lệ model,
seen mask, uniqueness và metric được kiểm độc lập bằng artifact/test, không
suy ra từ việc nhìn màn hình.

## Artifact và hash bàn giao

Snapshot local `artifacts/demo/v1/demo_bundle.json` (246.003 byte); batch test
`results/local/pilot-final/test/test-b36cb3e524a346c8bb6a9935da76406a/` (30 file,
65.591.620 byte). Giữ cả thư mục khi chuyển; danh mục bắt buộc ở runbook.
Test manifest SHA-256: `d4eb81744e8dc962d09624c7d40286e491ec93f83358e2fcd8322d795622d08d`.
Dataset/split/config/checkpoint/lock hashes ở final/reproduction report. Các
file chứa hồ sơ/ranking/checkpoint chỉ lưu local, không commit GitHub.

## Giới hạn phải giữ khi trình bày

- P0 là benchmark offline và demo đọc file; chưa có phục vụ online nhiều người,
  tài khoản, API/database ứng dụng hoặc triển khai production.
- Một pilot 10.000 người, một seed model 17, ba BPR config tối đa 10 epoch và
  năm alpha. Chưa kiểm đa seed, độ tin cậy thống kê hay lợi ích học tập.
- Timestamp giữ source-local naive; catalog tĩnh; split từng người cho phép
  tương tác train của người khác nằm sau target của một người.
- Benchmark warm bỏ target cold khỏi metric và báo số lượng riêng. Không
  suy diễn kết quả này thành chất lượng cho người mới/khóa mới.
- Dữ liệu người học và artifact thật không có trong Git. Clone source không
  tự mở được snapshot thật hoặc chạy frozen test nếu chưa nhận artifact.
- P1 chưa audit thật vì thiếu concept, mapping, prerequisite; chưa rerank/path.
- Môi trường sạch trên cùng máy Windows khác với kiểm chứng máy vật lý mới.
  Linux/macOS/GPU và CI từ GitHub chưa được kiểm trong Task 13.

## Bàn giao cho người tiếp theo

1. Cài lock và chạy fixture theo runbook.
2. Nhận snapshot hoặc toàn bộ batch/data ngoài Git, đối chiếu hash trong
   final/reproduction/pilot report. Chỉ chuyển cho người được phép sử dụng dữ liệu.
3. Mở snapshot thật, xem nhãn offline, ba hồ sơ và bốn mô hình; hiểu lịch sử
   hiển thị train + valid nhưng profile model vẫn chỉ train.
4. Nếu sửa data/config/protocol, tạo validation và freeze mới. Không chọn
   cấu hình dựa vào test cuối đã công bố.
5. Giữ nhật ký lỗi và artifact gốc. Không sửa immutable manifest hoặc điền metric giả.

Trạng thái push GitHub và review toàn nhánh do bước tích hợp cuối xác nhận;
không được suy từ nghiệm thu dữ liệu/model ở tài liệu này.
