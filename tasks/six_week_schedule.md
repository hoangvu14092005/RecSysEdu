# Kế hoạch chi tiết hoàn thành RecSysEdu trong sáu tuần

Ngày cập nhật: 09/10/2026. Đây là kế hoạch thực hiện, chưa phải tiến độ đã đạt. Dự án đã có base và raw user/course; chưa có split, mô hình train hoặc metric thật. Người dùng yêu cầu khối lượng dự án khoảng ba tháng được tổ chức để hoàn thành trong sáu tuần; lịch không giả định số thành viên. Căn cứ phương pháp và ưu tiên hiện tại ở [10](../docs/10_course_direction.md): data/model/đánh giá trước, giao diện tối thiểu ở tuần 5.

## Kết quả cần bàn giao

Trong sáu tuần, hoàn thành một đồ án course recommendation có dữ liệu thật, mô hình, demo và thực nghiệm tái lập. Cách rút ngắn là dùng framework có sẵn, giới hạn phạm vi và đưa việc kiểm tra rủi ro lên sớm. Không có cơ sở để bảo đảm cùng toàn bộ phạm vi ba tháng khi chưa biết năng lực thực thi; các cổng nghiệm thu dưới đây xác định có thể giữ hay phải giảm phần mở rộng.

| Mức | Phải có gì | Bằng chứng |
| --- | --- | --- |
| P0 bắt buộc | Dataset sạch và split; MostPopular, Content-based, BPR, Hybrid; Top-10; demo; bảng so sánh | Raw/split manifest, model artifact, metric và hướng dẫn chạy |
| P1 mục tiêu đầy đủ | Prerequisite rerank, learning path concept, explanation có căn cứ | Graph audit, thí nghiệm có/không rerank, 3–5 case |
| P2 sau sáu tuần | LightGCN, video/bài tập, knowledge tracing, hệ thống production | Không nằm trên đường hoàn thành lịch này |

Nếu P1 thiếu dữ liệu, bàn giao P0 và ghi rõ phần learning path chưa đạt. Nếu BPR không chạy, đó là thiếu P0, phải báo thay vì gọi một hệ chỉ có Content-based là hoàn thành toàn kế hoạch. Hybrid không thắng BPR vẫn đạt nếu việc triển khai và so sánh đúng.

## Quy ước thực hiện

Sáu tuần tương ứng **30 ngày làm việc chính**. Hai ngày còn lại mỗi tuần dành cho nghỉ hoặc bù việc; không tính chúng như năng lực bắt buộc để làm thêm tính năng. Ngày D01–D30 là ngày tương đối, chưa gắn ngày lịch vì người dùng chưa chọn ngày bắt đầu.

Một hàng trong lịch là mục tiêu cuối ngày, có thể chia thành nhiều phiên nhỏ. Nếu chưa đạt nghiệm thu, ghi việc chưa xong và áp dụng nhánh xử lý; không đi tiếp theo ngày rồi đánh dấu đã hoàn thành. Ngày thực hiện không thay thế quan hệ phụ thuộc.

Các đường dẫn ở bảng là **artifact dự kiến**; chưa tồn tại. Processed chuẩn dùng Parquet dưới thư mục dataset version do config chọn; CSV/JSON dùng cho fixture và báo cáo nhỏ. Quy ước file ở [tài liệu 04](../docs/04_data_contract.md). Các lệnh trong [plan](plan.md) là CLI sẽ xây. Trong giai đoạn phát triển, lệnh evaluate phải hỗ trợ `--split valid`; chỉ mở test chính thức sau khi khóa cấu hình ở D25. Test fixture kiểm tra logic vẫn chạy từ tuần đầu.

## Tóm tắt sáu tuần

| Tuần | Mục tiêu | Điều phải nhìn thấy cuối tuần | Mã task |
| --- | --- | --- | --- |
| 1 | Làm dữ liệu dùng được; thử môi trường BPR sớm | Dataset/split v1 và báo cáo tương thích nhỏ | M0–M2; kiểm tra môi trường ban đầu M6 |
| 2 | Có hai baseline và evaluator đúng | Validation metric, Top-10 và hồ sơ mẫu | M3–M4 |
| 3 | BPR và Hybrid chạy được | Checkpoint reload, tuning log, bốn model cùng protocol | M6–M7 |
| 4 | Phân tích lõi và khảo sát kiến thức tiên quyết | Phân tích lỗi/nhóm lịch sử; graph audit, rerank/path nếu đủ nguồn hoặc báo giới hạn | M5, M8, M9a, M9b; phân tích M11 |
| 5 | Tích hợp sản phẩm và khóa thực nghiệm | Demo thật, runbook draft và cấu hình cuối | M10; chuẩn bị M11 |
| 6 | Đánh giá cuối và bàn giao | Test metrics, báo cáo, demo và tái lập môi trường sạch | M11–M12 |

## Tuần một D01 đến D05

**Mục tiêu:** dữ liệu đã kiểm tra, không bị chặn muộn bởi môi trường BPR. Giữ phạm vi enrollment và course catalog.

| Ngày | Việc cụ thể | Đầu ra dự kiến | Nghiệm thu cuối ngày |
| --- | --- | --- | --- |
| D01 | Chốt course-first, protocol và schema/fixture UI; tạo package, CLI help, môi trường; ghi phần cứng và version | `pyproject.toml`, `results/environment.md`, fixture manifest | Import/help chạy; fixture ghi SYNTHETIC; một lỗi không làm hỏng dữ liệu gốc |
| D02 | Tải user/course; lưu URL, size, SHA-256; đọc sample; xác định JSON Lines/array và schema | `data/raw/raw_manifest.json`, `results/source_schema.md` | Có sample parse được; hai mảng course/time được kiểm tra; không tải toàn log bài tập/video |
| D03 | Audit ID join, timestamp/timezone, độ dài mảng, trùng enrollment, số lịch sử/user; coverage/chất lượng name/about và field | `results/data_audit.md`, `results/data_audit.json` | Báo số đo thật và các nhóm lỗi; chọn quy tắc timezone hoặc ghi unresolved; không bịa số user khả dụng |
| D04 | Chuẩn hóa enrollment/catalog; lưu rejects. Thử RecBole bằng fixture nhỏ: import, load pre-split, train ngắn, reload | `data/processed/interactions.parquet`, `courses.parquet`, `results/bpr_environment.md` | Output không còn ID mồ côi/duplicate; spike BPR pass hoặc có lỗi tái hiện và cách xử lý; chưa tính là xong M6 |
| D05 | Chọn subset dựa vào audit; chia temporal train/valid/test, warm/cold cohort; đóng băng dataset v1 | `data/processed/split_manifest.json`, `train.parquet`, `valid.parquet`, `test.parquet` | Không giao nhau cặp user–course; thời gian hợp lệ; ghi target cold/ties; checksum ổn định |

**Cổng G1:** dữ liệu và split hợp lệ; rủi ro môi trường BPR đã lộ ra. Nếu timestamp chưa dùng được, chưa phát hành temporal split; cần đổi protocol rõ ràng hoặc sửa parser. Nếu CS quá thưa, giữ catalog rộng cho ranking và chỉ giới hạn CS cho graph về sau.

**Việc viết báo cáo trong tuần:** hoàn thiện bối cảnh, mục tiêu, nguồn dữ liệu và bảng thống kê sau lọc. Chưa ghi kết quả model.

## Tuần hai D06 đến D10

**Mục tiêu:** từ dữ liệu thật sinh gợi ý và đo được; evaluator làm trước thuật toán phức tạp.

| Ngày | Việc cụ thể | Đầu ra dự kiến | Nghiệm thu cuối ngày |
| --- | --- | --- | --- |
| D06 | Viết metric và candidate/seen policy; kiểm tra rank 1, rank 2, miss, danh sách ngắn | `tests/test_evaluation.py`, evaluator | Metric khớp tính tay; Recall=Hit với một target; test target không bị mask |
| D07 | Xây MostPopular từ train; xuất Top-10 và validation metrics | `results/popularity/valid_metrics.csv`, run manifest | Không có seen/duplicate/padding; ba user có bảng ranking truy vết được |
| D08 | Làm sạch name/about; TF-IDF cụm ký tự, fit trên metadata universe train; audit field bổ sung | `artifacts/content/text_features`, vectorizer/feature manifest, `results/feature_audit.md` | Ngôn ngữ/fit scope/config rõ; vector rỗng được đếm; ID round-trip đúng |
| D09 | Tạo profile train-only; Content cosine; thêm popularity fallback và reason codes | `results/content/valid_metrics.csv`, recommendations | Không dùng valid/test làm profile; profile rỗng có fallback; score hữu hạn |
| D10 | So hai baseline trên cùng cohort; sửa lỗi protocol nếu có rồi phát hành dataset/protocol v1 cuối tuần | `results/baseline_report.md`, `protocol_manifest.json` | Có bảng NDCG/Hit/Coverage; khác biệt được giải thích; mọi hàng dùng cùng hash |

**Cổng G2:** MostPopular và Content chạy trên dữ liệu thật; evaluator đúng. Không yêu cầu Content thắng popularity. Nếu evaluator sai, sửa trước BPR và chạy lại cả hai; chưa thêm graph để lấp phần thực nghiệm thiếu.

**Việc viết báo cáo trong tuần:** phương pháp baseline, protocol và kết quả validation sơ bộ. Test giữ nguyên, chưa mở để tuning.

**Hiện chưa phát triển thêm UI:** base fixture đã có; tuần 1–4 tập trung data/evaluator/model và mô tả kết quả cần hiển thị theo [08](../docs/08_ui_handoff.md). M10 ghép demo tối thiểu và kiểm kết quả thật ở tuần 5. Căn cứ phương pháp trong [10](../docs/10_course_direction.md).

## Tuần ba D11 đến D15

**Mục tiêu:** hoàn thành lõi đề tài: bốn model và một đường chạy thống nhất.

| Ngày | Việc cụ thể | Đầu ra dự kiến | Nghiệm thu cuối ngày |
| --- | --- | --- | --- |
| D11 | Export atomic files RecBole; kiểm tra loader row counts và mapping ID | `data/recbole/mooc/`, `artifacts/bpr/id_map.json` | Pre-split không bị đổi; ID gốc↔nội bộ đúng; padding bị loại |
| D12 | Train BPR ở quy mô nhỏ từ dữ liệu hợp lệ; load checkpoint và chạy evaluator chung | BPR smoke log/checkpoint, validation score | Train/load/score chạy thật; score reload khớp tolerance đã ghi; dùng đúng seen policy |
| D13 | Chạy BPR trên subset chính; tìm cấu hình trong budget nhỏ; lưu validation search | `results/bpr/search.csv`, selected checkpoint | Chọn theo validation; sampler/seed được ghi; không chạy grid không giới hạn |
| D14 | Chuẩn hóa CF/content cùng candidate list; tune alpha; kiểm tra score hằng và alpha 0/1 | `results/hybrid/search.csv`, `configs/hybrid_resolved.yaml` | Alpha 0/1 khớp thành phần; không dùng test chọn trọng số; fallback không dùng CF ngẫu nhiên |
| D15 | Chạy lại bốn model trên validation; đối chiếu artifact, latency và kết quả; khóa lõi v1 | `results/core_report.md`, `artifacts/core_manifest.json` | Dataset/protocol khớp; BPR reload được; có kết luận kể cả Hybrid không cải thiện |

**Budget đề xuất, có thể giảm sau đo D12:** BPR tối đa 6 cấu hình ban đầu, một seed cho mỗi cấu hình; early stopping dựa trên validation. Chọn một cấu hình rồi tối đa ba seed cho báo cáo cuối nếu thời gian chạy cho phép. Alpha thử `{0, 0.25, 0.5, 0.75, 1}`. Không nhận đây là bộ tham số tối ưu khi chưa chạy.

**Cổng G3:** đủ bốn model, cùng cách đánh giá, thời gian chạy đo được. Nếu BPR vẫn lỗi, dành ngày dự phòng sửa trước khi mở nhánh graph; giảm P1 trước, không bỏ BPR khỏi P0 mà vẫn báo đạt.

**Việc viết báo cáo trong tuần:** mô tả BPR, công thức Hybrid, bảng validation và các trường hợp mô hình không cá nhân hóa tốt.

## Tuần bốn D16 đến D20

**Mục tiêu:** đưa kiến thức tiên quyết vào một cách có bằng chứng, giữ được lõi đang chạy.

| Ngày | Việc cụ thể | Đầu ra dự kiến | Nghiệm thu cuối ngày |
| --- | --- | --- | --- |
| D16 | Tải concept/course mapping và prerequisite CS; kiểm tra chiều, namespace ID, coverage | `results/concept_mapping_audit.md` | Biết số course/concept join được; không đổi ID bằng phỏng đoán |
| D17 | Xây graph với nhãn 1; tách nhãn 0/unknown, self-loop và cycle | `artifacts/graph/`, `results/graph_audit.md` | Cạnh đúng A→B; cycle/unknown được báo; không tự xóa cạnh để che lỗi |
| D18 | Tạo exposure từ train; tính direct missing ratio; tune penalty trên valid | `results/prerequisite/search.csv`, rerank artifact | Lambda=0 trả Hybrid; thiếu graph là unknown; metric ranking và graph tách riêng |
| D19 | Tạo path concept bằng ancestor và topo; gắn course tham khảo; xử lý cycle/truncated | `results/path_cases.md`, path outputs | Path có thứ tự đúng; 3–5 case có provenance nếu dữ liệu đủ; không gọi enrollment là mastery |
| D20 | Đo có/không rerank cùng cohort; chốt có đưa P1 vào sản phẩm cuối không | `results/knowledge_report.md`, feature freeze v1 | Có coverage/mẫu số và trade-off; phần không đủ bằng chứng ghi chưa đạt |

**Không bắt buộc thêm concept vào Content-based:** mapping dùng trước cho graph/explanation. Content TF-IDF tên/mô tả là cấu hình chính; field bổ sung nếu có. Chỉ thử concept feature khi graph/lõi đã đạt, không làm phát sinh vòng tuning lớn.

**Cổng G4:** chỉ bật P1 khi pipeline graph hợp lệ và có case thật kiểm tra được. Nếu không đủ mapping/graph, demo báo chưa có thông tin; không điền một path thủ công rồi gắn nhãn từ model. Có thể bàn giao P0 nhưng phải ghi thiếu P1.

**Việc viết báo cáo trong tuần:** phương pháp graph, giới hạn exposure, ablation và case study. Việc giảm missing ratio chưa chứng minh học tốt hơn.

## Tuần năm D21 đến D25

**Mục tiêu:** biến artifact đã kiểm chứng thành sản phẩm dễ dùng; khóa mọi lựa chọn trước test cuối.

| Ngày | Việc cụ thể | Đầu ra dự kiến | Nghiệm thu cuối ngày |
| --- | --- | --- | --- |
| D21 | Xuất demo_bundle.json và hoàn thiện loader kiểm tra schema/ID/version, Top-K, reason và fallback | `src/recsysedu/demo/artifacts.py`, demo service | Sai hash/schema bị chặn; kết quả không phụ thuộc biến trạng thái user trước |
| D22 | Tích hợp Streamlit hai tab: Gợi ý học tập và Model Lab; đọc snapshot thật, giữ user/model dùng chung | `app/streamlit_app.py`, demo core | Ba profile xem được; Model Lab có run metadata; không train khi click; mẫu/thật hiện rõ |
| D23 | Hiển thị explanation từ tương đồng nội dung/điểm thành phần có nguồn; path nếu G4 đạt; hồ sơ mới | Demo đầy đủ theo phạm vi đạt | Không bịa hàng xóm BPR hoặc phần trăm phù hợp; unknown/fallback và nguồn lý do rõ |
| D24 | Kiểm tra trên trình duyệt: đổi user/model, cache, thiếu artifact, ít candidate; đo thời gian phản hồi | `results/demo_checks.md`, `results/performance.md` | Luồng không crash; không hiện lịch sử test dưới nhãn offline; log có thời gian thực |
| D25 | Khóa config, cohort, seeds, alpha/lambda, phạm vi P1; hoàn thiện runbook draft | `configs/final_experiments.yaml`, `artifacts/release_manifest.json`, runbook draft | Có checklist phát hành và version; test chưa được dùng cho lựa chọn |

**Cổng G5:** hết tính năng mới. Nếu demo chậm, cache artifact hiện có và đo lại; không đổi recommender/data split để làm giao diện nhanh hơn. Tối ưu candidate union chỉ là mở rộng có protocol riêng, không thay full ranking âm thầm.

**Việc viết báo cáo trong tuần:** kiến trúc sản phẩm, ảnh màn hình thật, kịch bản demo và runbook; chuẩn bị cấu trúc phần kết quả, chưa điền test metrics giả.

## Tuần sáu D26 đến D30

**Mục tiêu:** đo kết quả cuối, chứng minh chạy lại được và bàn giao. Không thêm thuật toán mới.

| Ngày | Việc cụ thể | Đầu ra dự kiến | Nghiệm thu cuối ngày |
| --- | --- | --- | --- |
| D26 | Chạy test chính thức cho bốn model và rerank nếu đạt; giữ config D25 | `results/final/metrics.csv`, run manifests | Cùng split/cohort/universe/mask; số liệu có nguồn; không tune theo test |
| D27 | Hoàn thiện các seed đã khóa; phân tích ít/nhiều lịch sử, coverage, error cases và P1 | `results/final/report.md`, per-user metrics | Ghi cỡ mẫu và số seed; một seed không được nhận là kết quả ổn định nhiều lần |
| D28 | Tạo môi trường sạch, cài từ lock và chạy lại preprocessing/model load/evaluation/demo | `results/reproduction.md` | Data/split hash khớp; metric/score trong tolerance định trước hoặc sai khác được giải thích |
| D29 | Hoàn thiện báo cáo, bảng/biểu đồ, README và kịch bản thuyết trình; quay demo nếu cần cho đồ án | `reports/final_report.md`, `reports/presentation_outline.md`, README | Mỗi kết luận gắn bảng hoặc case; thiếu P1 ghi rõ; không có số minh họa đóng vai metric |
| D30 | Diễn tập từ máy/môi trường bàn giao, kiểm checklist, đóng phiên bản cuối | `reports/acceptance.md`, gói bàn giao | Một người đọc runbook tái lập được; demo 3–5 hồ sơ; mọi lỗi còn lại có giới hạn rõ |

**Cổng G6:** bàn giao P0 đúng bằng chứng; P1 báo riêng đạt/chưa đạt. Nếu test phát hiện bug, sửa và chạy lại mọi model bị ảnh hưởng; ghi lần test bị vô hiệu và lý do. Không đổi tham số dựa trên test để tăng điểm. Nếu tuần sáu vẫn còn P0 chưa chạy, báo tiến độ chưa hoàn thành thay vì gọi là đã xong.

## Các thao tác dự kiến phải chạy được

CLI base hiện có download/audit/demo validate theo [runbook](../docs/09_runbook.md). Các lệnh prepare/split/train/evaluate trong lịch vẫn chưa xây. Khi viết evaluate, thêm `--split valid/test` và `--output` để tránh nhầm bộ dữ liệu hoặc ghi đè run. Dùng Python từ môi trường riêng của dự án.

```powershell
python -m recsysedu.cli data audit --config configs/data.yaml
python -m recsysedu.cli data prepare --config configs/data.yaml
python -m recsysedu.cli data split --config configs/split.yaml
python -m pytest tests/test_evaluation.py tests/test_split.py
python -m recsysedu.cli evaluate --model popularity --split valid --config configs/popularity.yaml --output results/popularity/valid
python -m recsysedu.cli evaluate --model content --split valid --config configs/content.yaml --output results/content/valid
python -m recsysedu.cli train --model bpr --config configs/bpr.yaml
python -m recsysedu.cli tune --model hybrid --config configs/hybrid.yaml
python -m recsysedu.cli graph audit --config configs/graph.yaml
python -m streamlit run app/streamlit_app.py
python -m recsysedu.cli experiments --config configs/final_experiments.yaml
```

Ngày D26 có `split=test` trong final config; các run phát triển mặc định valid và không tự chạy test. Run manifest ghi rõ split/history mode. Chi tiết numerical/data tests theo [plan](plan.md) và [protocol](../docs/05_evaluation.md).

## Cách giữ lịch sáu tuần

| Khi phát hiện chậm | Hành động cụ thể | Phần giữ lại |
| --- | --- | --- |
| Cuối tuần 1 chưa xong data | Dùng ngày dự phòng; giảm subset theo audit, không tải log mở rộng | Cleaning, provenance, split đúng |
| BPR runtime lớn | Giảm số cấu hình/seed theo budget đã ghi; dùng subset pilot hợp lệ rồi đánh giá lại phạm vi | BPR thật, validation-only tuning, protocol chung |
| Tuần 3 thiếu P0 | Dành tuần 4 sửa core, giảm P1 có thông báo | Bốn model, evaluator, demo và báo cáo |
| Graph không đủ dùng | Giữ unknown và case đã kiểm chứng; ghi P1 chưa đạt | Không bịa path hoặc mastery |
| Tuần 5 demo chưa ổn | Giảm trang/chức năng trang trí; giữ chọn user, lịch sử, Top-K và reason | End-to-end artifact thật |
| Muốn thêm model mới cuối kỳ | Đưa vào danh sách sau sáu tuần | Thời gian tái lập, báo cáo và bàn giao |

Không giảm chất lượng bằng bỏ seen mask, đổi test split hoặc xóa case thất bại. BPR/Hybrid, dữ liệu và demo là các phần quyết định tiến độ; màu sắc UI và mô hình nâng cao không nằm trên đường bắt buộc.

Nếu phải đổi subset hoặc cleaning rule sau khi đóng băng, phát hành dataset/split version mới và chạy lại mọi model so sánh trên version đó. Không ghép metric từ hai dataset vào một bảng. Việc sửa lỗi sau lần test chính thức phải được ghi trong lịch sử thực nghiệm.

## Cách theo dõi mỗi ngày

Cuối ngày ghi 5 dòng: việc hoàn thành; artifact; lệnh đã chạy/kết quả; vướng mắc; mục tiêu ngày tiếp theo. Mỗi cuối tuần xem cổng G tương ứng và cập nhật [todo](todo.md). Chỉ tick task khi đạt toàn bộ tiêu chí; chạy spike M6 sớm không đồng nghĩa đã hoàn thành benchmark BPR.

## Bàn giao tối thiểu cuối sáu tuần

- Mã nguồn, config và dependency lock; fixture nhỏ có nhãn.
- Raw/data/split manifest cùng cách lấy dữ liệu; không bắt buộc đóng gói lại toàn raw.
- Model/checkpoint, ID map, feature và run manifest đủ để chạy demo/evaluate.
- Bảng cuối cho MostPopular, Content, BPR, Hybrid; rerank nếu P1 đạt.
- Báo cáo, case study, runbook và kịch bản demo; trạng thái từng yêu cầu.
- Evidence tái lập môi trường sạch và các lỗi/giới hạn còn lại.

Ước lượng thực tế được cập nhật sau G1/G2 bằng thời gian đã đo. Mục tiêu rút ngắn là bảo vệ đường hoàn thành sản phẩm, không giả định mọi phần việc ba tháng đều tự giảm một nửa.
