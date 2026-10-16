# Test cuối — RecSysEdu P0

Ngày 16/10/2026. **Đã chạy đúng một lần full test sau freeze; exit 0.** Không
đổi dataset, seed, alpha, BPR hoặc protocol theo kết quả test. Không có lần
full test lỗi hoặc chạy lại. Checkpoint/Content giữ nguyên từ validation.

## Cách chạy và đọc số liệu

Lệnh thực thi từ root worktree với `PYTHONPATH` trỏ rõ vào `src` của worktree,
Python 3.10.11 môi trường dự án; wrapper đo thời gian/RSS gọi đúng command:

```powershell
python results/local/task11_measure.py final-test-once experiments --split test --config configs/final_experiments.yaml
```

Wrapper là helper local không ở Git, không phải công cụ bắt buộc của người nhận.
Command bên trong là `python -m recsysedu.cli experiments --split test --config
configs/final_experiments.yaml`. Không chạy lại chỉ để chọn tham số.

`leave_last_two_out_v1`, seed model 17, K=10, 2.586 candidate train. Model và
profile chỉ dùng train; seen mask = train + valid. Có 9.858 người warm, mỗi
người một target test. **107 target cold** không thuộc benchmark warm và được
báo riêng. Một target/người nên HitRate và Recall bằng nhau; Precision=HitRate/10.

| Model | NDCG@10 | HitRate/Recall@10 | Precision@10 | Coverage@10 | Giây evaluator |
| --- | ---: | ---: | ---: | ---: | ---: |
| MostPopular | 0,0470426496 | 0,0801379590 | 0,0080137959 | 0,0123743233 | 15,90 |
| Content TF-IDF | 0,0576570574 | 0,0987015622 | 0,0098701562 | 0,9238205723 | 192,55 |
| BPR | 0,0572938979 | 0,1059038344 | 0,0105903834 | 0,6782675947 | 28,71 |
| Hybrid alpha 0,25 | 0,0773727819 | 0,1364374112 | 0,0136437411 | 0,8395204950 | 279,34 |

Hybrid cao nhất về NDCG/HitRate toàn cohort này; Content phủ nhiều khóa hơn.
Đây là kết quả đo của một pilot/một seed, chưa có kiểm định thống kê. Test
thấp hơn validation; không thay alpha để che khác biệt này.

Toàn CLI **520,1935 giây** (~8,67 phút). RSS lấy mẫu cây tiến trình mỗi 0,2s:
**388.657.152 byte** đỉnh. Có thể tính trùng shared pages/bỏ lỡ đỉnh ngắn.
Đây là máy phát triển có cài môi trường sạch/test tự động chạy cùng, không
phải benchmark hiệu năng phần cứng độc lập.

## Nhóm ít/nhiều lịch sử

Chia nhóm để mô tả lỗi sau khi mở test, không dùng nhóm để chọn lại model:
ít=1–4 khóa train; giữa=5–19; nhiều=ít nhất 20. Coverage mỗi nhóm là hợp
khóa được gợi ý trong nhóm chia cùng 2.586 candidate, không lấy trung bình
coverage mỗi người. Nhóm ít có 6.110 người, giữa 2.285, nhiều 1.463.

| Nhóm | Model | NDCG@10 | HitRate/Recall@10 | Precision@10 | Coverage@10 |
| --- | --- | ---: | ---: | ---: | ---: |
| Ít | MostPopular | 0,06124613 | 0,09934534 | 0,00993453 | 0,00541377 |
| Ít | Content | 0,07142267 | 0,11816694 | 0,01181669 | 0,90680588 |
| Ít | BPR | 0,06776266 | 0,12062193 | 0,01206219 | 0,65506574 |
| Ít | Hybrid | 0,09546463 | 0,16464812 | 0,01646481 | 0,81129157 |
| Giữa | MostPopular | 0,03112943 | 0,05995624 | 0,00599562 | 0,00696056 |
| Giữa | Content | 0,05026210 | 0,09190372 | 0,00919037 | 0,65158546 |
| Giữa | BPR | 0,05556431 | 0,11203501 | 0,01120350 | 0,38283063 |
| Giữa | Hybrid | 0,06848169 | 0,12647702 | 0,01264770 | 0,59087394 |
| Nhiều | MostPopular | 0,01257813 | 0,03144224 | 0,00314422 | 0,01237432 |
| Nhiều | Content | 0,01171693 | 0,02802461 | 0,00280246 | 0,27184841 |
| Nhiều | BPR | 0,01627407 | 0,03485988 | 0,00348599 | 0,26566125 |
| Nhiều | Hybrid | 0,01570154 | 0,03417635 | 0,00341763 | 0,29543697 |

Nhóm nhiều lịch sử có kết quả thấp rõ rệt; BPR nhỉnh hơn Hybrid về NDCG nhóm
này. Vì vậy không tuyên bố Hybrid thắng cho mọi người. Hồ sơ trung bình nội
dung có thể trộn nhiều chủ đề, nhưng dữ liệu này chưa chứng minh nguyên nhân.
Muốn kiểm giả thuyết phải có thí nghiệm validation mới.

## Trường hợp thất bại và audit

- Số người **không có target trong Top-10**: MostPopular 9.068; Content 8.885;
  BPR 8.814; Hybrid 8.513. Ngay cả Hybrid vẫn bỏ lỡ đa số target.
- Cả bốn run có đủ 9.858 người, mỗi người đúng 10 khóa khác nhau; không cần
  fallback hoặc danh sách ngắn trong cohort thật này. Điều đó không chứng
  minh cold-start hoạt động tốt: người mới không thuộc benchmark này.
- Chọn ba hồ sơ theo độ dài train tăng dần tại vị trí đầu/giữa/cuối, trước
  khi xem từng hit: 1, 3 và 1.109 khóa train. Đây là ví dụ ít/điển hình/cực
  nhiều lịch sử, không phải ba người đại diện thống kê cho toàn dân số.
  BPR đều miss ở ba ví dụ. Không đổi hồ sơ để chỉ trưng bày trường hợp thành công.
- Kiểm độc lập toàn bộ hash trong experiment manifest, từng thứ tự/rank,
  khóa thuộc universe, không seen train+valid, tie-break score giảm/mã tăng.
  Tính lại NDCG/hit/recall/precision từng người từ target và ranking rồi so
  Parquet/trung bình; Coverage từ hợp các khóa. Sai số cho phép `1e-12`;
  tất cả qua. Không dùng evaluator làm oracle cho phép tính lại metric.

## Artifact và nhận diện

Batch local đầy đủ: `results/local/pilot-final/test/test-b36cb3e524a346c8bb6a9935da76406a/`.
Snapshot: `artifacts/demo/v1/demo_bundle.json`, **246.003 byte**, schema 1,
`data_mode=real`, ba hồ sơ × bốn model, `paths=[]`; exporter và loader đều qua.
Các file này không nằm trong Git; phải nhận riêng cùng dataset/split/valid batch.

| Thành phần | SHA-256 |
| --- | --- |
| Dataset | `215b235068a4282a49b02ab0c0ac65608f096828d1fc97ac6c1a30b0a936720c` |
| Split | `7285739e66981088817fd2c11419caaf36f2cf4f197798403468cd989f263617` |
| Effective config | `7e895cc5d88e203cf20c597c6ff349d16b5266910d148108ca4a3f1c22f603cc` |
| Validation manifest | `379b3ae18de0b2a3859f705be5ce3727284d29fa4a8ddab1326982ba597d3baf` |
| Test experiment manifest | `d4eb81744e8dc962d09624c7d40286e491ec93f83358e2fcd8322d795622d08d` |
| BPR checkpoint | `c4dbd2d88e71689b1d447f314fe6b9dc1a90af95499d2cafdba5eec03b36720a` |
| Demo bundle | `3e80b5e90db8f2776ff7f5e58915696f45f9b552ee8b7f0fe2219ae20577e56e` |

Git revision trong batch: `ae8958107820cb0c25a56d1cf09f4c62982952e7`,
`git_dirty=true` do sửa wording báo cáo trước khi chạy; không thay source P0.
Model component hashes giữ nguyên validation. Python 3.10.11, NumPy1.26.4,
scikit-learn1.7.2, Torch2.5.1+cpu, RecBole1.2.1.

P0 là xếp hạng đăng ký offline. Không đo mastery, completion hay learning gain.
Giới hạn timezone/catalog/per-user split/một seed vẫn giữ nguyên. P1 dừng vì
thiếu ba nguồn graph. Xem [tái lập](../reproduction.md), [nghiệm thu](../../reports/acceptance.md)
và [runbook](../../docs/09_runbook.md) trước khi dùng hoặc sửa bản này.
