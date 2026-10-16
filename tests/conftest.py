"""Small real pipeline artifacts shared by snapshot and app boundary tests."""

import json

import pytest

from recsysedu.data.prepare import prepare_dataset
from recsysedu.data.split import build_temporal_split
from recsysedu.experiments.runner import evaluate_model


@pytest.fixture
def demo_runs(tmp_path):
    courses, users = tmp_path / 'course.json', tmp_path / 'user.json'
    courses.write_text(json.dumps([
        {'id': f'C_{i}', 'name': name, 'about': name, 'field': ['Computer science']}
        for i, name in enumerate(('Python basic', 'Python advanced', 'Calculus',
                                   'History ancient', 'History modern'), 1)
    ]), encoding='utf-8')
    users.write_text(json.dumps([
        dict(id=f'U_{i}', course_order=order,
             enroll_time=['2020-01-01', '2020-02-01', '2020-03-01'])
        for i, order in enumerate(([1, 2, 3], [2, 3, 1], [3, 1, 2], [4, 5, 1], [5, 4, 2]))
    ]), encoding='utf-8')
    prepared, split = tmp_path / 'prepared', tmp_path / 'split'
    prepare_dataset(courses, users, prepared, dataset_version='snapshot-test-fixture',
                    time_basis='source_local_naive', sample_users=0, seed=17)
    build_temporal_split(prepared / 'interactions.parquet', prepared / 'courses.parquet',
                         split, split_version='snapshot-test-split', seed=17)
    config = dict(prepared_dir=str(prepared), split_dir=str(split), seed=17,
                  content={'analyzer': 'char', 'ngram_range': [2, 4], 'min_df': 1})
    result = []
    for model in ('popularity', 'content'):
        root = tmp_path / model
        evaluate_model(config, model_id=model, split='valid', output_root=root)
        batch = next(root.iterdir())
        manifest = json.loads((batch / 'experiment_manifest.json').read_text('utf-8'))
        result.append(batch / manifest['runs'][model])
    return result
