# 05 — So sánh mô hình công bằng

Cập nhật 16/10/2026. Đây là **protocol P0 đang dùng**, đã có validation và test
thật, không còn là đề xuất chưa chạy. Xem [validation](../results/pilot/validation_report.md),
[test cuối](../results/final/report.md), [nghiệm thu](../reports/acceptance.md).
Metric đo tìm lượt đăng ký giữ lại; chưa đo năng lực hoặc lợi ích học tập.

Căn cứ môn học L8 và phần dự án lựa chọn ở [ghi chú nguồn, mục 4](11_course_reading_notes.md).
Enrollment là tín hiệu đăng ký, không có rating để coi MAE/RMSE là metric chính.
Coverage đo phủ catalog, không thay diversity bên trong từng danh sách.

## 1. Ví dụ và quy tắc bắt buộc

Một người đăng ký A→B→C→D ở các thời điểm khác nhau. A/B là train để học;
C là valid để chọn tham số; D là test cuối. Model/profile không nhìn C/D
khi học. Mục tiêu: khóa giữ lại có vào Top10, đứng ở vị trí nào?

Protocol ID là `leave_last_two_out_v1`. Sau làm sạch, cần ít nhất 3 khóa khác
nhau. Khóa cuối là test, áp chót valid, trước đó train. Ba mốc cuối phải tăng
nghiêm ngặt; timestamp hòa tại ranh giới bị cách ly và đếm, không dùng ID để
tạo thứ tự giả. Pilot chọn 10.000 người, seed 20261016; loại 35 người có thời
gian hòa tại ranh giới, còn 9.965 người temporal. Timestamp giữ source-local
naive, không chứng thực UTC.

| Giai đoạn | Model và profile lấy từ đâu? | Khóa loại khỏi Top10 |
| --- | --- | --- |
| Valid | Chỉ train | Train của người đó |
| Test | Giữ nguyên model/profile train đã khóa | Train + valid của người đó |

Valid ở test chỉ thêm vào seen mask, không retrain/cập nhật Content profile.
Muốn train+valid phải tạo protocol mới và chạy mọi model theo cùng quy tắc.

## 2. Cohort, candidate và ranking

Các điểm dưới đây là điều kiện benchmark bắt buộc, dùng chung cho bốn model:

- **Warm cohort:** user có train và target thuộc các khóa đã có tương tác train.
  Valid 9.909 người; test 9.858 người. Cold target valid 56/test 107 được báo riêng,
  không âm thầm đưa embedding chưa học vào benchmark.
- **Candidate universe:** đúng tập khóa có tương tác train, 2.586 khóa. Chấm
  toàn universe cho mỗi người, rồi mask seen theo bảng trên; không sampled
  negatives hoặc candidate union riêng cho một model.
- Model trả score đúng thứ tự candidate theo [contract](04_data_contract.md).
  Evaluator loại seen, xếp score giảm dần, hòa thì `course_id` tăng dần,
  lấy tối đa K=10. Không padding/ID lạ/trùng/NaN/inf.
- Ít hơn 10 candidate chưa thấy thì trả danh sách ngắn và đếm, không chèn khóa
  giả. Các run thật hiện không có short list/fallback trong warm cohort.

`full_train_universe`, `train_only`, `train` hoặc `train_plus_valid` là policy
được ghi trong run manifest. Đổi candidate/mask/cohort là đổi protocol, không
ghép trực tiếp với bảng P0 này. Benchmark warm chưa đánh giá người mới/khóa mới.

## 3. Metric và phép kiểm

| Metric | Ý nghĩa đơn giản |
| --- | --- |
| NDCG@10 — chính | Ưu tiên target xuất hiện gần đầu danh sách |
| HitRate@10 | Tỷ lệ người có target trong Top10 |
| Recall@10 | Tỷ lệ target giữ lại được tìm thấy |
| Precision@10 | Số target tìm thấy chia10 vị trí |
| Coverage@10 | Số khóa khác nhau được gợi ý chia universe2.586 |

Với một target/người, HitRate=Recall và Precision=HitRate/10; không gọi đó là
ba bằng chứng độc lập. Target rank1 có NDCG1; rank2 là1/log2(3)≈0,63093;
miss là0. Đây là ví dụ tính tay, không phải metric mô hình.

```text
Hit(u)        = 1 nếu target nằm trong Top10, ngược lại 0
Recall(u)     = số target tìm thấy / số target giữ lại
Precision(u)  = số target tìm thấy / 10, kể cả danh sách ngắn
DCG(u)        = tổng relevance(rank) / log2(rank+1)
NDCG(u)       = DCG(u) / IDCG(u)
Coverage      = kích thước hợp khóa đã gợi ý / kích thước universe chung
```

IDCG lấy từ ground truth hợp lệ, không lấy số hit của model; một target thì
IDCG=1 ngay cả khi miss. Trung bình NDCG/hit/recall/precision theo người với
trọng số bằng nhau. Coverage là hợp khóa toàn cohort, không trung bình coverage
của từng người. Định nghĩa nhiều-target cần protocol riêng nếu mở rộng.

Code `evaluation/metrics.py`, `ranking.py`, `run.py` dùng chung mọi model.
Task13 tính độc lập lại metric từ target/thứ tự đã lưu và so per-user Parquet/
aggregate với sai số tối đa1e-12; kiểm seen/universe/rank/score/hash toàn batch.
Đối chiếu RecBole chỉ có nghĩa khi cùng ID/candidate/mask; metric RecBole mặc
định không được dùng thay bảng chung. [Thiết lập upstream](https://recbole.io/docs/user_guide/config/evaluation_settings.html).

## 4. Chọn tham số trước test

Validation đã chạy ba cấu hình BPR dưới budget tối đa6, seed17,CPU,batch2048,
tối đa10 epoch, early stopping warm valid NDCG@10/stopping_step2. RecBole đếm
lần thấp hơn best achieved; bằng best đặt lại bộ đếm. Cả ba chạm10 epoch,
không khẳng định hội tụ. Chọn embedding32/lr0,01 bằng valid.

Negative sampling uniform trong train universe, loại positive train của người;
không dùng valid/test target để chỉnh sampler. Hybrid min–max trên full universe
trước seen mask, thử alpha `[0,0.25,0.5,0.75,1]` bằng valid; chọn0,25. Alpha0/1
đã kiểm khớp ranking Content/BPR toàn valid cohort.

Freeze khóa dataset/split/config/hash validation manifest. Sau đó full test
chạy **đúng một lần** ngày16/10/2026, không tune theo test. Model/profile vẫn
train-only, dùng nguyên checkpoint/Content đã chọn. [Final report](../results/final/report.md)
lưu kết quả, hash, runtime và lỗi; `configs/final_experiments.yaml` là authority
frozen. Người nhận không chạy lại test để tìm config thắng hơn.

Lịch D25 freeze/D26 test, tối đa3 seed và lambda tiền đề là **đề xuất lịch sử**;
bản thực thi có một seed, không P1/lambda. Không có mean/std đa seed, khoảng
tin cậy hoặc kiểm định thống kê. Không diễn giải chênh lệch như thắng chắc chắn.

## 5. Phân tích lịch sử sau test — không phải protocol chọn mẫu

Final report mô tả ba nhóm theo số khóa **train**:

| Nhóm mô tả | Số khóa train | Số người warm test |
| --- | ---: | ---: |
| Ít | 1–4 | 6.110 |
| Giữa | 5–19 | 2.285 |
| Nhiều | Từ20 | 1.463 |

Đây là phân tích lỗi **sau khi mở test**, không dùng để tune alpha/BPR hoặc
lọc cohort benchmark. Cả9.858 người vẫn ở bảng tổng. Coverage nhóm dùng hợp
gợi ý trong nhóm chia cùng universe2.586. Phương án cũ ít1–3/nhiều từ4 chỉ là
đề xuất lịch sử, chưa phải contract và không phải ngưỡng đã dùng trong final report.

Hybrid đứng đầu NDCG toàn cohort nhưng không thắng BPR ở nhóm nhiều lịch sử;
giữ kết quả đó. Ba hồ sơ demo lấy theo min/median/max history, không chọn chỉ
các hit; xem mô tả giới hạn đại diện ở final report. Không suy ra nguyên nhân
thấp điểm chỉ từ nhóm; kiểm giả thuyết cần thí nghiệm validation mới.

## 6. Artifact đã phát hành

Trong `<batch>/<run_dir>/` (lấy đường dẫn từ `experiment_manifest.json`):

| File | Nội dung |
| --- | --- |
| `run_manifest.json` | Identity/hash/policy/cohort/model config/metrics/runtime/output hashes |
| `metrics.csv` | Một dòng metric tổng hợp của run |
| `per_user_metrics.parquet` | Target, history count, fallback, số gợi ý và metric từng người |
| `recommendations.jsonl` | Ranking/source IDs/rank/score/evidence từng người |

Batch ở `results/local/pilot-final/<valid hoặc test>/<batch_id>/`, ngoài Git.
`experiment_manifest.json` ràng buộc dataset/split/config/component và inventory
hash. BPR có checkpoint/ID map/manifest; Content có vectorizer/sparse features/
manifest. Tên batch exact/hash/cách chuyển ở final report và [runbook](09_runbook.md).

Exporter chỉ nhận các run được chọn của batch tương thích và kiểm hash trước
khi tạo `artifacts/demo/v1/demo_bundle.json`. UI chỉ hiển thị metric đã đo, không
điền0 cho chưa có số liệu. Snapshot thật có history offline; source clone mặc
định là fixture synthetic. Kiểm browser/CSV khác với kiểm tính đúng model.

## 7. P1 và giới hạn còn lại

`knowledge/audit.py` đã kiểm fixture label/ID/coverage/self-loop/cycle. Thiếu
ba nguồn graph thật nên [P1_STOP_INSUFFICIENT_EVIDENCE](../results/graph_audit.md),
real audit chưa chạy. Penalty tiền đề, lambda, topo/path20 concept là ý tưởng
lịch sử chưa triển khai; cần dữ liệu/audit và plan/schema mới. P0 `paths=[]`,
prerequisite unknown. Enrollment không chứng minh tiếp xúc concept hoặc mastery.

Per-user split vẫn cho phép train của người khác nằm sau target của một người;
catalog tĩnh chưa có availability theo thời gian. Một pilot/một seed chưa
chứng minh tổng quát, cold-start hoặc learning gain. Muốn global-time/retrain/
dataset mới phải validation/freeze và chạy lại mọi model theo protocol mới;
giữ bảng cũ để truy vết thay vì sửa số liệu cũ.
