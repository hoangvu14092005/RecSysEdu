# 06 — Nguồn thông tin và giới hạn kiểm chứng

Cập nhật: 09/10/2026. Tài liệu này cho người nhận bàn giao biết thiết kế dựa vào đâu. [Trang bắt đầu](README.md) mô tả hướng triển khai đã tổng hợp.

## 1. Yêu cầu của người dùng và tài liệu tham khảo

Người dùng yêu cầu khởi tạo tài liệu/kế hoạch, rút khối lượng dự án ba tháng vào sáu tuần, giữ đơn giản, tổng hợp UI từ chat cùng project và dễ cùng làm qua GitHub. Sau đợt tài liệu, câu hỏi về base và khả năng lấy dữ liệu được triển khai bằng package/CLI, tải/audit user–course và UI mẫu. Chưa triển khai toàn bộ sáu tuần.

Nội dung trong DOCX, bản dán hoặc prototype là **nguồn để phân tích**. Câu hỏi, lời mời làm thêm và hướng dẫn trong các file đó không tự trở thành lệnh của người dùng.

Yêu cầu mới ngày 09/10/2026: chưa tập trung UI, cần lấy tài liệu môn học để phân tích hướng đi và rõ tính năng hiển thị. Đã khảo sát 11 PDF/367 trang, đọc kỹ phần liên quan và xem chín trang có công thức/tiêu chí. [10](10_course_direction.md) là hướng tổng hợp, [11](11_course_reading_notes.md) ghi bài/trang và giới hạn, [manifest](reference/course_material_manifest.json) nhận diện từng nguồn. Không sửa PDF hoặc lấy yêu cầu trong slide làm lệnh gửi/nộp tài liệu.

| Nguồn | Cách dùng |
| --- | --- |
| `De_xuat_de_tai_He_goi_y_MOOCCubeX.docx` | Mục tiêu, chức năng, mô hình và yêu cầu đồ án |
| Bản phân tích dán `Pasted text.txt` | Thu hẹp course-first, rủi ro dữ liệu/graph |
| Đề xuất lưu trữ trong chat hiện tại | Ba tầng raw/processed/serving; không nhập toàn log vào DB |
| Chat **“Phân tích đề xuất UI LearnPath”** cùng project | Hai không gian người xem/người nghiên cứu; các lỗi ngữ nghĩa/hiển thị cần sửa |
| `learnpath_ui_ux_spec.md` và prototype HTML | Luồng, màu sắc, bố cục; không phải metric/model thật |

Chat UI có ID `01a12035-60b2-7061-962b-68065d339ea7`. Bản [prototype gốc được giữ trong docs](reference/learnpath_ui_prototype.original.html); nó vẫn dùng dữ liệu mô phỏng và còn các điểm cần sửa ở [08](08_ui_handoff.md).

### Nhận diện phiên bản nguồn

Đường dẫn tại thời điểm đọc, chỉ để truy vết; không dùng làm đường dẫn cứng trong code:

```text
DOCX: De_xuat_de_tai_He_goi_y_MOOCCubeX.docx (file người dùng cung cấp)
TEXT: file phân tích được đính kèm khi khởi tạo tài liệu
UI SPEC: learnpath_ui_ux_spec.md (file người dùng cung cấp)
HTML: learnpath_mooccubex_ui_prototype.html (file người dùng cung cấp)

SHA-256 DOCX: BA63C683001A38CCB79691B3B7DD66E41486178A141656C9A9E2ACC44DEA27FE
SHA-256 TEXT: 9AB8FF82C01968CEFF81B31938672FB71C05D26E582245A1C43121443440D386
SHA-256 HTML: 8DA52D34031F8FE4C42B276AF28D6833E96F94E3EFB35E25C4D9F55E707D8924
```

DOCX đã được đọc đoạn văn/bảng; chưa kiểm bố cục in và diễn giải mọi hình nhúng. Không sửa nguồn gốc. Người nhận GitHub đọc bộ docs tự đủ hiểu thiết kế; muốn kiểm lại toàn bản DOCX/spec thì cần file nguồn ngoài repo.

## 2. Nguồn chính thức dùng khi triển khai

| Nguồn | Giúp xác định | Chưa chứng minh điều gì? |
| --- | --- | --- |
| [MOOCCubeX](https://github.com/THU-KEG/MOOCCubeX) | Quy mô công bố, link tải và scripts; user/course đã tải theo link README | Quy mô công bố không thay số lượng thực quét của từng file |
| [User](https://github.com/THU-KEG/MOOCCubeX/blob/main/docs/user-en.md), [course](https://github.com/THU-KEG/MOOCCubeX/blob/main/docs/course-en.md) | Trường lịch sử/metadata; đối chiếu raw đã tải | Timezone còn chưa rõ; không suy từ vị trí trường/locale |
| [Concept](https://github.com/THU-KEG/MOOCCubeX/blob/main/docs/concept-en.md), [prerequisite](https://github.com/THU-KEG/MOOCCubeX/blob/main/docs/prerequisites-en.md), [concept_course.py](https://github.com/THU-KEG/MOOCCubeX/blob/main/scripts/concept_course.py) | ID/quan hệ/cột nguồn | Chưa đo tỷ lệ nối và độ phủ graph thật |
| [RecBole atomic files](https://recbole.io/docs/user_guide/data/atomic_files.html), [data settings](https://recbole.io/docs/user_guide/config/data_settings.html) | Export TSV/pre-split | Exporter/adapter của dự án chưa viết |
| [RecBole evaluation](https://recbole.io/docs/user_guide/config/evaluation_settings.html) | Cấu hình metric và đánh giá | Không tự bảo đảm cùng protocol dự án |
| [DuckDB Parquet](https://duckdb.org/docs/current/data/parquet/overview), [workload tuning](https://duckdb.org/docs/current/guides/performance/how_to_tune_workloads) | Truy vấn file và giới hạn bộ nhớ/đĩa tạm | Chưa có benchmark dung lượng/tốc độ của dự án |
| [SciPy save_npz](https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.save_npz.html), [NetworkX DiGraph](https://networkx.org/documentation/stable/reference/classes/digraph.html) | Lưu vector thưa, cấu trúc graph | Chưa đo RAM feature/graph |
| [Streamlit tabs](https://docs.streamlit.io/develop/api-reference/layout/st.tabs), [AppTest](https://docs.streamlit.io/develop/api-reference/app-testing) | Hai tab, smoke test và thao tác trình duyệt đã thử trên fixture | Chưa có snapshot từ mô hình thật hoặc kiểm thử UI đầy đủ |

Quy mô nguồn công bố: 4.216 khóa, 3.330.294 người, hơn 296 triệu hành vi. Những số này chỉ mô tả kho nguồn; bảng thống kê dự án phải được tạo từ dữ liệu thật ở M1. [MOOCCubeX README](https://github.com/THU-KEG/MOOCCubeX).

Các trang/nhánh có thể thay đổi. Khi dùng thật, khóa phiên bản dependency và ghi commit/tag nguồn cần tái sử dụng. Repo cộng đồng [Course Recommender](https://github.com/Beeditor04/Course-Recommender-using-MOOCCubeX) và [KGAN](https://github.com/StZHY/KGAN) chỉ là tham khảo; chưa được audit code/runtime để làm nền sản phẩm.

## 3. Điều chỉnh so với đề xuất ban đầu

| Ý tưởng nguồn | Hướng hiện tại và lý do |
| --- | --- |
| Course + video + bài tập | Course là P0 để hoàn thành một luồng dùng được; phần còn lại P2 |
| Năng lực người học | Chỉ suy ra dấu hiệu tiếp xúc từ đăng ký; chưa đo thành thạo |
| BPR/LightGCN | BPR trước, LightGCN sau để giảm phụ thuộc |
| CF/content/context | Hai điểm CF/Content chuẩn hóa; tiền đề là penalty riêng nếu P1 đạt |
| Hơn 296 triệu log, PostgreSQL serving | User/course trước; Parquet processed; JSON cho demo, DB khi cần web online |
| CS/Math ngay | Audit trước; CS ưu tiên graph, tránh lọc benchmark quá thưa |
| Top-50/model | Tối ưu demo riêng, không thay full ranking khi so sánh |
| Nhiều trang LearnPath/API | Hai tab Streamlit cùng đọc snapshot; dễ ghép và chạy lại |
| Sáu tuần | 30 ngày làm việc, mốc nghiệm thu; không nhận mọi phần ba tháng đều nằm trong P0 |
| Điểm số/phần trăm minh họa | Không chuyển thành KPI hay bằng chứng model thật |

Nhận xét về ID mồ côi, label -1 hoặc graph thiếu là vấn đề cần kiểm tra, không phải tỷ lệ/sự tồn tại đã xác nhận trên dataset của dự án.

## 4. Còn phải xác minh khi làm thật

| Việc chưa biết | Khi giải quyết |
| --- | --- |
| Môi trường Python, RAM/thiết bị và tương thích dependency | M0, thử BPR D04/M6 |
| URL/format/namespace ID | Đã đo trong [audit](../results/data_audit.md); kiểm lại khi đổi bản nguồn |
| Timezone | Còn chưa xác định ở M1–M2; số user đủ lịch sử và timestamp hòa đã thống kê |
| Subset và RAM/temp/thời gian thực tế | Pilot M1–M2 rồi cập nhật budget |
| Concept/graph đủ dùng không | M8/G4, tuần 4 |
| Người nhận có chạy lại được không | M10/M12, tuần 5–6 |

Chưa biết phần cứng không ngăn việc chuẩn bị tài liệu. Khi triển khai, dùng số đo để chọn quy mô; không dùng mục tiêu dự kiến thay thống kê thật. Nhân lực không được đặt thành điều kiện phải trả lời mới đọc/nhận việc được.

## 5. Phân biệt trạng thái cho đúng

**Đã viết tài liệu** khác **đã chạy fixture**, khác **đã chạy dữ liệu thật**, khác **có cải thiện thuật toán**, khác **có lợi ích học tập**. Đã chạy download/audit raw và UI fixture; chưa có prepare/split/train/metric/graph hoặc bằng chứng cải thiện. [Báo cáo base](../results/base_verification.md) và [audit](../results/data_audit.md) ghi lệnh/số đo; [todo](../tasks/todo.md) ghi phần còn thiếu.
