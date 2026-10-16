import copy
import json
from pathlib import Path

import pytest

from recsysedu.demo.artifacts import load_bundle, validate_bundle

FIXTURE = Path(__file__).parent / 'fixtures' / 'demo_bundle.json'


def test_fixture_is_synthetic_with_three_profiles_and_no_fake_metrics():
    bundle = load_bundle(FIXTURE)
    assert bundle['meta']['data_mode'] == 'synthetic'
    assert len(bundle['users']) == 3
    assert all(run['metric_status'] == 'not_available' for run in bundle['runs'])
    assert any(not user['observed_course_ids'] for user in bundle['users'])


@pytest.mark.parametrize('fault', ['seen', 'unknown', 'rank', 'nan', 'run_hash', 'model'])
def test_loader_rejects_inconsistent_artifacts(fault):
    bundle = copy.deepcopy(json.loads(FIXTURE.read_text(encoding='utf-8')))
    item = bundle['recommendations'][0]['items'][0]
    if fault == 'seen':
        item['course_id'] = bundle['users'][0]['observed_course_ids'][0]
    elif fault == 'unknown':
        item['course_id'] = 'C_does_not_exist'
    elif fault == 'rank':
        item['rank'] = 99
    elif fault == 'nan':
        item['score'] = float('nan')
    elif fault == 'run_hash':
        bundle['runs'][0]['dataset_hash'] = 'another_dataset'
    elif fault == 'model':
        bundle['recommendations'][0]['model_id'] = 'bpr'
    with pytest.raises(ValueError):
        validate_bundle(bundle)


@pytest.mark.parametrize('fault', ['meta', 'bool_schema', 'model_object', 'status_object',
                                 'large_score', 'ambiguous_run', 'unsupported_paths', 'missing_seed'])
def test_malformed_and_ambiguous_bundles_fail_cleanly(fault):
    bundle = copy.deepcopy(json.loads(FIXTURE.read_text(encoding='utf-8')))
    if fault == 'meta':
        bundle['meta'] = []
    elif fault == 'bool_schema':
        bundle['meta']['schema_version'] = True
    elif fault == 'model_object':
        bundle['runs'][0]['model_id'] = {}
    elif fault == 'status_object':
        bundle['recommendations'][0]['items'][0]['prerequisite_status'] = {}
    elif fault == 'large_score':
        bundle['recommendations'][0]['items'][0]['score'] = 10 ** 1000
    elif fault == 'ambiguous_run':
        run = copy.deepcopy(bundle['runs'][0])
        run['run_id'] = 'other-run'
        bundle['runs'].append(run)
        rec = copy.deepcopy(bundle['recommendations'][0])
        rec['run_id'] = run['run_id']
        bundle['recommendations'].append(rec)
    elif fault == 'missing_seed':
        del bundle['runs'][0]['seed']
    else:
        bundle['paths'] = [{'invalid': True}]
    with pytest.raises(ValueError):
        validate_bundle(bundle)


@pytest.mark.parametrize('fault', ['missing_evidence', 'mixed_policy', 'missing_user_ranking'])
def test_real_loader_requires_offline_evidence_and_complete_compatible_runs(
        demo_runs, tmp_path, fault):
    from recsysedu.demo.export import export_demo_bundle

    bundle = export_demo_bundle(demo_runs, ['U_0', 'U_3'], tmp_path / 'bundle.json')
    if fault == 'missing_evidence':
        del bundle['meta']['evidence_level']
    elif fault == 'mixed_policy':
        bundle['runs'][1]['evaluation_split'] = 'test'
    else:
        bundle['recommendations'].pop()
    with pytest.raises(ValueError):
        validate_bundle(bundle)
