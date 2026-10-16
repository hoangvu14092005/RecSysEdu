# Kiểm tra dữ liệu tri thức P1

Ngày kiểm tra: 16/10/2026. **Kiểm tra dữ liệu graph thật: chưa chạy (`not run`).**
P0 (gợi ý khóa học bằng Popularity, Content, BPR và Hybrid) tiếp tục độc lập.
Chưa có bằng chứng để bật cảnh báo tiền đề hoặc tạo lộ trình học.

## Những nguồn đang có và đang thiếu

Đã kiểm tra thư mục `data/raw/` của checkout chính
`D:/VuLapTrinh2/RecSysEdu` và worktree `pipeline-first/RecSysEdu`.
Checkout chính có `course.json` (44.660.123 byte), `user.json`
(806.781.726 byte), `raw_manifest.json` (776 byte). Worktree chưa có
`data/raw/`. Không tìm thấy ba nguồn graph sau trong hai kho dữ liệu này:

| Nguồn cần | Dùng để làm gì | Tình trạng thực tế |
| --- | --- | --- |
| `entities/concept.json` | Danh sách mã kiến thức để đối chiếu | Chưa có |
| `relations/concept-course.txt` | Nối kiến thức với khóa học | Chưa có |
| `prerequisites/cs.json` | Quan hệ kiến thức trước–sau có nhãn | Chưa có |

Việc tìm file chỉ bao phủ hai kho dữ liệu dự án trên, không khẳng định file
không tồn tại ở máy khác. Chưa tải thêm graph trong bước này.
Văn bản `course.prerequisites` không được thay thế cho ba nguồn trên.

Đã đối chiếu cấu trúc với nguồn chính thức:
[concept](https://github.com/THU-KEG/MOOCCubeX/blob/main/docs/concept-en.md),
[prerequisite](https://github.com/THU-KEG/MOOCCubeX/blob/main/docs/prerequisites-en.md),
[script concept–course](https://github.com/THU-KEG/MOOCCubeX/blob/main/scripts/concept_course.py).
Đây là đối chiếu tài liệu, chưa phải đo dữ liệu tải về.

## Công cụ đã triển khai

`audit_knowledge_sources(concepts_path, mapping_path, prerequisites_path,
courses_path=...)` đọc file, trả về báo cáo dạng dictionary, không sửa nguồn.
Ba đối số đầu là bắt buộc; `courses_path` là catalog khóa học tùy chọn.
Cần truyền thêm catalog để xác nhận mã khóa học có tồn tại hay không.
Nếu thiếu catalog, độ phủ khóa học và danh sách khóa không nối được là `null`,
trạng thái `not_available`, và công cụ giữ P1 ở trạng thái dừng.

Ví dụ khi đã lấy được đủ file thật, chạy bằng Python:

```python
import json
from pathlib import Path
from recsysedu.knowledge import audit_knowledge_sources

raw = Path('data/raw')
report = audit_knowledge_sources(
    raw / 'entities/concept.json',
    raw / 'relations/concept-course.txt',
    raw / 'prerequisites/cs.json',
    courses_path=raw / 'entities/course.json',
)
print(json.dumps(report, ensure_ascii=False, indent=2))
```

Nếu catalog đang lưu phẳng ở `data/raw/course.json`, truyền đúng đường dẫn đó.
Không tự dò đường dẫn hoặc đoán quy tắc chuyển mã.

Công cụ ghi rõ hash SHA-256, kích thước, đường dẫn từng nguồn; số concept;
số cặp concept–course, cặp trùng, cặp hợp lệ và độ phủ; nhãn dương, nhãn 0,
nhãn chưa rõ; mã không nối được; self-loop và các cụm có chu trình.
Độ phủ concept lấy số concept có ít nhất một cặp hợp lệ chia tổng catalog
concept; độ phủ course dùng cùng cách tính trên catalog khóa học.
Khi thiếu catalog course, số cặp mới chỉ được đối chiếu phía concept.

Chỉ `ground_truth` dạng số bằng 1 được nhận là cạnh dương. Nhãn 0 không là
cạnh; -1, thiếu nhãn, chuỗi `"1"`, boolean và nhãn khác đều là chưa rõ.
`text_predict` và `graph_predict` không thay nhãn xác nhận.
So mã bằng chuỗi chính xác; không tự nối theo tên hoặc bỏ tiền tố.

`usable_edges` chỉ là các cạnh dương có hai đầu trong catalog và không tự
nối, phục vụ kiểm tra cấu trúc; chưa phải graph được phát hành cho ứng dụng.
**Các cạnh tạo chu trình vẫn được giữ nguyên** trong danh sách này.
`cycles` liệt kê từng cụm liên thông mạnh có hơn một concept (mọi concept
trong cụm đều có thể đi vòng về nhau), không liệt kê mọi vòng đơn vì số vòng
có thể rất lớn. Self-loop được báo riêng, không đưa vào `usable_edges`.

Công cụ dừng nếu thiếu catalog course, nguồn rỗng, không có cặp nối/cạnh dương,
ID không nối được, concept tiền đề chưa nối khóa học, nhãn lạ, self-loop hoặc
chu trình. Khi không có lỗi này, `P1_READY_FOR_SEPARATE_PLAN` chỉ có nghĩa là
đủ để **lập kế hoạch P1 riêng**; chưa chứng minh độ phủ đủ cho người dùng hay
quan hệ tiên quyết đúng về học thuật. Kế hoạch sau phải chốt phạm vi và mức
độ phủ chấp nhận được. Không có ngưỡng độ phủ tự đặt trong đợt triển khai này.

## Bằng chứng và quyết định

Các kiểm thử dùng dữ liệu nhỏ do test tạo ra để kiểm chứng parser, nhãn,
độ phủ, mã không nối được, self-loop, chu trình, nguồn lỗi/thiếu và đồ thị dài.
Kết quả test chỉ chứng minh công cụ hoạt động trên các tình huống đó.
**Không có số đo độ phủ, số cạnh hay số chu trình của MOOCCubeX thật trong báo cáo này.**

Muốn mở P1: lấy đủ ba nguồn, giữ nguồn gốc/hash, chạy công cụ với catalog course,
xem các mã không nối được và cách xử lý chu trình, rồi lập kế hoạch riêng.
Không thêm reranking hoặc lộ trình học trong Task 12.

Quyết định cuối: **`P1_STOP_INSUFFICIENT_EVIDENCE`** — thiếu cả ba nguồn graph,
nên chưa đo được độ phủ mapping, nhãn và tính hợp lệ của đồ thị thật.
