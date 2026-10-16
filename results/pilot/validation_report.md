# Pilot thật — so sánh validation và khóa P0

Ngày đo: 16/10/2026. Dữ liệu, cách chọn 10.000 người và split được mô tả ở
[dataset_report](dataset_report.md). Đây là kết quả **validation**, chưa phải
test cuối và chưa chứng minh hiệu quả học tập. Task 13 mới được mở test sau
khi kiểm tra cấu hình đã khóa.

**Trạng thái: đã khóa cấu hình P0 sau validation và audit.** Đây là khóa dữ
liệu/protocol/model để mở test; chưa phải nghiệm thu toàn bộ P0.

## Cách so sánh công bằng

Bốn model cùng dùng `leave_last_two_out_v1`, seed model `17`, 9.909 người
có target warm và 2.586 khóa từng xuất hiện trong train. Mỗi người có một
target validation; mọi model xếp hạng toàn bộ candidate, loại khóa đã có
trong train rồi lấy Top-10. Hòa điểm được xếp theo `course_id` tăng dần.
Model và hồ sơ Content chỉ dùng train. Không thêm valid vào hồ sơ hoặc train.
HitRate@10 và Recall@10 bằng nhau vì mỗi người chỉ có một target.

Content dùng TF-IDF `name + about`, char n-gram 2–4, min_df=1. Có 400.950
đặc trưng và 859.171 phần tử khác 0; không có khóa train vector rỗng.
Hybrid chuẩn hóa min–max trên toàn bộ candidate của từng người trước khi
lọc seen, rồi tính `alpha * BPR + (1-alpha) * Content`.

## Tìm cấu hình BPR trong ngân sách

Một epoch là một lượt học qua train. Embedding là vector số biểu diễn người
và khóa; số chiều càng lớn thì có thêm tham số cần học. Learning rate quy
định mức điều chỉnh tham số mỗi bước.

Khai báo trước ba cấu hình, dưới mức tối đa sáu của kế hoạch; không thử thêm
sau khi xem test. Cùng seed 17, CPU, batch 2.048, tối đa 10 epoch,
early stopping theo warm validation NDCG@10, stopping_step=2. Adapter dùng
chính ranking/metric/policy của dự án để chọn tensor tốt nhất rồi lưu checkpoint.
Điều kiện dừng của RecBole là quá 2 lần giảm liên tiếp; bằng điểm đặt lại bộ đếm.

| Lần | Embedding | Learning rate | Epoch tốt nhất / đã chạy | NDCG@10 | Thời gian CLI (giây) | RSS lấy mẫu (byte) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 32 | 0,001 | 10 / 10 | 0,0574574866 | 307,68 | 481.726.464 |
| 2 | 64 | 0,001 | 10 / 10 | 0,0613409454 | 307,21 | 504.586.240 |
| 3 — chọn | 32 | 0,01 | 10 / 10 | 0,0774493614 | 293,92 | 493.481.984 |

Cả ba lần thành công; không có lần train lỗi bị bỏ khỏi bảng. Cả ba chạm
giới hạn 10 epoch trước khi điều kiện dừng kích hoạt; đây là tìm kiếm có giới
hạn, không phải bằng chứng đã hội tụ hoặc tham số tối ưu. Checkpoint lần3
được dùng lại nguyên vẹn cho batch bốn model, không huấn luyện lại.
Negative sampling là uniform trong train universe, loại positive train của user;
không dùng tập held-out để quyết định negative.

## Bảng kết quả trong batch chung

| Model | NDCG@10 | HitRate/Recall@10 | Precision@10 | Coverage@10 | Giây đánh giá |
| --- | ---: | ---: | ---: | ---: | ---: |
| MostPopular | 0,0532997424 | 0,0896155011 | 0,0089615501 | 0,0123743233 | 16,86 |
| Content TF-IDF | 0,0823037349 | 0,1347260067 | 0,0134726007 | 0,9226604795 | 194,15 |
| BPR đã chọn | 0,0774493614 | 0,1395700878 | 0,0139570088 | 0,6774941995 | 28,91 |
| Hybrid alpha 0,25 | 0,1085083331 | 0,1782218185 | 0,0178221819 | 0,8364269142 | 256,36 |

NDCG ưu tiên đưa khóa đúng lên đầu danh sách; HitRate là tỷ lệ người có target
trong Top-10. Precision chia số khóa đúng cho 10. Coverage là tỷ lệ khóa trong
candidate universe xuất hiện ít nhất một lần ở Top-10 của cả cohort.

Thời gian từng dòng là thời gian evaluator, không gồm toàn bộ fit/đọc/ghi;
BPR dùng checkpoint đã train. RSS là tổng working set lấy mẫu mỗi 0,2 giây,
có thể tính trùng trang nhớ chia sẻ và bỏ lỡ đỉnh ngắn. Các số thời gian là
đo wall-time trên máy phát triển có công việc khác chạy cùng, không phải
benchmark phần cứng tách biệt.

Grid alpha validation:

| Alpha | NDCG@10 |
| --- | ---: |
| 0 | 0,0823037349 |
| 0,25 | 0,1085083331 |
| 0,5 | 0,1040513657 |
| 0,75 | 0,0928847806 |
| 1 | 0,0774493614 |

Alpha càng lớn thì BPR đóng góp càng nhiều. Chọn alpha 0,25 theo NDCG@10
validation lớn nhất (nếu hòa, chọn alpha nhỏ hơn). Hybrid có NDCG cao hơn
Content trong pilot này, nhưng Coverage thấp hơn. Không diễn giải kết quả
validation đã dùng để chọn alpha thành kết quả test hoặc bằng chứng tổng quát.

## Kiểm tra checkpoint

Checkpoint SHA-256: `c4dbd2d88e71689b1d447f314fe6b9dc1a90af95499d2cafdba5eec03b36720a`.
ID-map SHA-256: `f0af46aaa5a1877b0e86078c46d315e639a4c46f7b0308a3fc0472a4e1f7ce99`.
Hai lần load cùng file tạo score NumPy giống hệt; toàn bộ tensor embedding
nạp vào scorer và model RecBole giống hệt. Đối chiếu độc lập với
RecBole `BPR.predict` sau nạp tensor và với phép nhân cộng float64: 5 người
× 2.586 candidate; sai số tuyệt đối lớn nhất NumPy/Torch là `9,54e-7`, so
với float64 là `7,02e-7`; tolerance công bố `rtol=1e-6, atol=2e-6`.
Thứ tự đầy đủ của cả 5 người giống nhau. Sai khác float32 nhỏ do thứ tự cộng;
không tuyên bố bit-exact giữa hai thư viện. Không thay tolerance của test fixture.

## Audit và bản cấu hình đã khóa

- Tám run lưu riêng (ba thành phần và năm alpha), mỗi run đủ 9.909 người,
  đúng 10 khóa khác nhau/người, không có khóa train lọt vào Top-10, không có
  ID ngoài candidate universe, score hữu hạn, rank liên tục và phá hòa đúng.
  Run Hybrid chính trỏ đến trial alpha 0,25, không nhân đôi kết quả đánh giá.
- Kiểm lại SHA-256 mọi artifact được manifest công bố. Dataset, split,
  protocol, seed, config, cohort, universe, profile và seen policy khớp.
- Tính độc lập lại từng metric của từng người từ target và thứ tự Top-10,
  so với Parquet và trung bình trong manifest; tính Coverage bằng hợp các
  khóa đã gợi ý. Tất cả khớp với sai số tuyệt đối tối đa cho phép `1e-12`.
- Alpha 0 khớp thứ tự Content và alpha 1 khớp BPR cho toàn bộ 9.909 người.
- Kiểm guard của freeze thành công mà không gọi chấm điểm test. Chưa có
  thư mục output test nào được tạo bởi Task 11.

Batch authority: `valid-2e93583494064297adaa556b9bc21d64`.
Toàn bộ lệnh cuối mất **1.526,85 giây (~25,45 phút)**; tổng RSS lấy mẫu đỉnh
**403.980.288 byte**. Một lần trước đó bị gián đoạn khi đang đánh giá alpha0,
chưa có experiment manifest; không dùng phần dở đó làm kết quả. Lần chạy lại
giữ nguyên checkpoint BPR đã chọn, không train thêm hoặc xem test.

| Nhận diện freeze | SHA-256 |
| --- | --- |
| Dataset | `215b235068a4282a49b02ab0c0ac65608f096828d1fc97ac6c1a30b0a936720c` |
| Split | `7285739e66981088817fd2c11419caaf36f2cf4f197798403468cd989f263617` |
| Effective config | `7e895cc5d88e203cf20c597c6ff349d16b5266910d148108ca4a3f1c22f603cc` |
| Validation experiment manifest | `379b3ae18de0b2a3859f705be5ce3727284d29fa4a8ddab1326982ba597d3baf` |

[Cấu hình cuối](../../configs/final_experiments.yaml) đặt `frozen: true`, trỏ
đúng batch và bốn hash trên. [Core manifest công khai](core_manifest.json)
chỉ lưu tham số/hash/metric tổng hợp, không chứa learner ID hoặc đường dẫn
tuyệt đối. Manifest/ranking/feature/checkpoint đầy đủ nằm local dưới
`results/local/pilot-final/valid/` và phải được chuyển riêng khi bàn giao;
clone Git không tự tải các artifact này. Nếu tạo dữ liệu mới ở máy khác,
phải chạy validation và tạo freeze mới, không sửa manifest cũ để ép khớp.

Batch ghi Git revision `e101b67b0911c0674b364fcc1e7a5bb1b6673645`,
`git_dirty: true` vì đang soạn cấu hình và báo cáo; không có thay đổi source
P0 chưa commit khi chạy. Python 3.10.11, NumPy 1.26.4, pandas 2.3.3,
scikit-learn 1.7.2, PyArrow 25.0.1, Torch 2.5.1+cpu, RecBole 1.2.1.
Sau Task 12, kiểm tra lại toàn nhánh: **262 test pass**, 64 cảnh báo upstream;
Ruff và `git diff --check` pass. Chưa xác nhận môi trường sạch bằng số này.

## Giới hạn và bước tiếp theo

- Chỉ một pilot, một seed, ba cấu hình BPR; chưa có khoảng tin cậy hay kiểm
  định thống kê. Mức hơn/kém chỉ là kết quả offline của cohort này.
- Split theo từng người vẫn cho phép train của người khác nằm sau target
  của một người; không phải đánh giá theo một mốc thời gian toàn hệ thống.
- Catalog tĩnh không mô tả thời điểm mở/đóng khóa; đăng ký không đo mức
  thành thạo, hoàn thành hoặc lợi ích học tập.
- Timestamp dùng giả định source-local naive; xem báo cáo dữ liệu.
- Chưa đánh giá test, chưa xuất snapshot thật hoặc xác nhận trình duyệt của
  snapshot đó, chưa tái lập trong môi trường sạch. Các việc này thuộc Task 13.
- Manifest/ranking/ID/checkpoint lớn chỉ giữ local. Git chỉ chứa báo cáo tổng
  hợp, hash và cấu hình; người nhận phải tải/tạo lại dữ liệu hoặc được bàn giao
  artifact riêng. Không coi giấy phép code nguồn là giấy phép phát hành hồ sơ.
