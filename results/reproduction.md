# Tái lập và kiểm tra bàn giao

Ngày 16/10/2026. **Đã tạo môi trường Python mới thực sự từ lock**, không sao
chép site-packages môi trường cũ. Windows/Python 3.10.11 trên cùng máy phát
triển; chưa thử một máy vật lý khác, Linux/macOS, GPU hoặc GitHub CI.

## Những lệnh đã thực thi

Từ root worktree; `PYTHONPATH` đặt rõ bằng đường dẫn `src` của worktree. Các
lệnh sau đã chạy, không phải chỉ là kế hoạch:

```powershell
py -3.10 -m venv .venv-repro
.\.venv-repro\Scripts\python.exe -m pip install -r requirements-win-py310.lock.txt
.\.venv-repro\Scripts\python.exe -m pip install -e . --no-deps
.\.venv-repro\Scripts\python.exe -m pip check
.\.venv-repro\Scripts\python.exe -m pytest tests/test_experiment_runner.py::test_frozen_test_reuses_selected_validation_checkpoint_and_alpha tests/test_demo_export.py::test_exporter_builds_real_bundle_from_compatible_runs -q
.\.venv-repro\Scripts\python.exe results/local/task13_reproduce.py
.\.venv-repro\Scripts\python.exe -m recsysedu.cli demo validate --bundle artifacts/demo/v1/demo_bundle.json
```

`pyvenv.cfg`: version 3.10.11, `include-system-site-packages=false`.
Install lock và editable exit 0; pip check **No broken requirements found**.
Đối chiếu `importlib.metadata.version` với toàn bộ **78 version khóa** bằng
`packaging.version.Version`: tất cả khớp. Lần so raw string ban đầu báo khác
ở thop: metadata `0.1.1-2209072238` và lock `0.1.1.post2209072238` tương đương
theo PEP440; đây không phải đổi dependency hoặc sửa lock.

Install có log riêng; khoảng cách creation→last-write của log là **447,036s**,
chỉ là khoảng thời gian ghi log, không tuyên bố stopwatch đầy đủ của cả venv +
install. Fixture báo **2 pass, 3 upstream warnings, 9,79s**. Chúng thực sự chạy
prepare→split→train bốn model→valid→freeze→test trên dữ liệu nhỏ và xuất snapshot
từ batch fixture. Các test này không mở lại full test MOOCCubeX.

## Checkpoint thật và frozen small case

Helper local `results/local/task13_reproduce.py` load đúng checkpoint trong
batch test đã khóa; load hai scorer độc lập. Ba hồ sơ snapshot có train history
1,3,1.109. Score đầy đủ 2.586 candidate, loại seen train+valid, so Top-10/score
với snapshot và so NDCG với per-user test Parquet: **exact scores và rankings**,
NDCG đều 0. Chạy ba case lần đầu qua trong 1,356s.

Mở rộng thêm một case chẩn đoán có hit đã lưu (không dùng để chọn config),
history 7 và NDCG=0,5/rank3. Chạy lại helper bốn case **1,487s**, tất cả qua.
Đây là kiểm lại vài score của checkpoint đã khóa, **không chạy lại full test**,
không huấn luyện hoặc tune sau khi xem test.

- Hai lần NumPy load/scoring và score đã lưu: tolerance 0, cùng environment/library.
- NDCG tính độc lập so artifact: absolute tolerance `1e-12`.
- Không suy rộng bit-exact giữa NumPy/Torch: validation đã đối chiếu upstream
  predict với `rtol=1e-6, atol=2e-6`, xem [validation](pilot/validation_report.md).
- Loader xác nhận snapshot `real`, schema1, ba profile/bốn model, no paths.

Các helper/log/json đầy đủ nằm `results/local/`, không trong Git vì có đường
dẫn/ID người học. Có thể nhận riêng để audit. Đoạn sau là **ví dụ tương đương
cho người nhận** kiểm ba case snapshot bằng API công khai; cần artifact đã chép
đủ. Nó không chạy full evaluator hoặc sửa config:

```python
import json
from pathlib import Path
import pandas as pd
from recsysedu.adapters.recbole import load_bpr_scorer
from recsysedu.demo.artifacts import load_bundle
from recsysedu.evaluation.ranking import rank_candidates

batch = Path('results/local/pilot-final/test/test-b36cb3e524a346c8bb6a9935da76406a')
bundle = load_bundle(Path('artifacts/demo/v1/demo_bundle.json'))
model = load_bpr_scorer(batch / 'artifacts/bpr/bpr_manifest.json')
universe = tuple(pd.read_parquet(
    'data/splits/mooccubex-pilot-v1-split-v1/candidate_universe.parquet').course_id)
for user in bundle['users']:
    actual = rank_candidates(model.score(user['user_id'], universe),
                             set(user['observed_course_ids']), k=10)
    expected = next(r['items'] for r in bundle['recommendations']
                    if r['user_id'] == user['user_id'] and r['model_id'] == 'bpr')
    assert [(x.course_id, x.score) for x in actual] == [
        (x['course_id'], x['score']) for x in expected]
```

## Hash và artifact cần giữ

| File/nhận diện | SHA-256 |
| --- | --- |
| `requirements-win-py310.lock.txt` | `1ea4c9807f56d9563e92a90431c59dcb76bc0e768c4a074121157e126a49e8d5` |
| BPR checkpoint | `c4dbd2d88e71689b1d447f314fe6b9dc1a90af95499d2cafdba5eec03b36720a` |
| BPR ID map | `f0af46aaa5a1877b0e86078c46d315e639a4c46f7b0308a3fc0472a4e1f7ce99` |
| Real snapshot | `3e80b5e90db8f2776ff7f5e58915696f45f9b552ee8b7f0fe2219ae20577e56e` |

Dataset/split/config/batch hashes ở [final report](final/report.md). Chuyển
đầy đủ dataset/split, validation batch, test batch và snapshot theo
[runbook](../docs/09_runbook.md). Giữ manifest nguyên vẹn. Clone Git không có
checkpoint/ranking/learner ID; chỉ source clone không đủ tái lập frozen run.

## Kiểm toàn nhánh và giới hạn bằng chứng

Môi trường dự án hiện có, explicit worktree PYTHONPATH:

```powershell
python -m pytest -q
python -m ruff check src app tests
python -m pip check
```

**262 pass,64 upstream warnings,40,82s; Ruff pass; pip check không có broken
requirements.** Môi trường cũ có cảnh báo metadata `-ympy` còn sót; môi trường
sạch không có cảnh báo đó. Không xóa cache/package cũ để làm sạch bằng chứng.
Các warning test là upstream RecBole/Pandas/Torch đã ghi trong log.

Tái lập này xác nhận cài dependency, fixture pipeline, load checkpoint, một
vài score và snapshot. **Chưa lặp toàn bộ raw prepare/full BPR search/full test
trên máy khác.** Prepare lặp cùng máy và nội dung/hash Parquet đã được xác
nhận trong Task11. Không khẳng định toàn bộ huấn luyện bit-exact trên phần cứng khác.
