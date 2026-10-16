import hashlib
import json

import joblib
import numpy as np
import pandas as pd
import pytest
from scipy.sparse import load_npz

from recsysedu.models.content import ContentConfig, fit_content
from recsysedu.models.popularity import fit_popularity


def _case():
    courses = pd.DataFrame({
        'course_id': ['C_3', 'C_2', 'C_4', 'C_1'],
        'name': ['History', 'Python advanced', 'zzzzholdout', 'Python basics'],
        'about': ['Ancient history', 'Coding in Python', 'zzzzholdout', 'Learn Python coding'],
    })
    train = pd.DataFrame({
        'user_id': ['U_1', 'U_2', 'U_3'],
        'course_id': ['C_1', 'C_2', 'C_3'],
        'valid_target': ['C_3', 'C_3', 'C_2'],
    })
    fallback = fit_popularity(train, ('C_1', 'C_2', 'C_3'))
    return courses, train, fallback


def test_content_profile_uses_train_courses_only(tmp_path):
    courses, train, fallback = _case()
    model = fit_content(courses, train, ContentConfig(), tmp_path / 'features', fallback)
    original = model.score('U_1', ('C_2', 'C_3')).scores

    altered = train.copy()
    altered['valid_target'] = ['C_2', 'C_2', 'C_1']
    second = fit_content(courses, altered, ContentConfig(), tmp_path / 'other', fallback)
    np.testing.assert_allclose(second.score('U_1', ('C_2', 'C_3')).scores, original)
    assert model.course_ids == ('C_1', 'C_2', 'C_3')
    with pytest.raises(ValueError, match='unknown candidate'):
        model.score('U_1', ('C_4',))


def test_content_prefers_course_with_shared_character_ngrams(tmp_path):
    courses, train, fallback = _case()
    model = fit_content(courses, train, ContentConfig(), tmp_path / 'features', fallback)

    scored = model.score('U_1', ('C_3', 'C_2'))
    assert scored.course_ids == ('C_3', 'C_2')
    assert scored.scores[1] > scored.scores[0]
    assert scored.fallback_status == 'none'


def test_content_empty_profile_returns_popularity_fallback_status(tmp_path):
    courses, train, fallback = _case()
    courses.loc[courses.course_id == 'C_3', ['name', 'about']] = ['', None]
    model = fit_content(courses, train, ContentConfig(), tmp_path / 'features', fallback)

    for user_id in ('U_missing', 'U_3'):
        scored = model.score(user_id, ('C_2', 'C_1'))
        assert scored.fallback_status == 'popularity_empty_profile'
        np.testing.assert_array_equal(scored.scores,
                                      fallback.score(user_id, ('C_2', 'C_1')).scores)


def test_content_feature_manifest_preserves_course_order_and_config_hash(tmp_path):
    courses, train, fallback = _case()
    output = tmp_path / 'features'
    config = ContentConfig(analyzer='char', ngram_range=(2, 4), min_df=1)
    fit_content(courses, train, config, output, fallback)

    manifest = json.loads((output / 'feature_manifest.json').read_text(encoding='utf-8'))
    config_payload = {'analyzer': 'char', 'ngram_range': [2, 4], 'min_df': 1}
    expected_hash = hashlib.sha256(json.dumps(config_payload, sort_keys=True,
                                               separators=(',', ':')).encode()).hexdigest()
    assert manifest['course_ids'] == ['C_1', 'C_2', 'C_3']
    assert manifest['config_hash'] == expected_hash
    assert manifest['fit_scope'] == 'train_course_universe'
    assert manifest['text_columns'] == ['name', 'about']
    assert json.loads((output / 'course_order.json').read_text(encoding='utf-8')) == [
        'C_1', 'C_2', 'C_3']
    matrix = load_npz(output / 'course_features.npz')
    vectorizer = joblib.load(output / 'vectorizer.joblib')
    assert matrix.shape == (3, len(vectorizer.vocabulary_))
    assert 'zzzz' not in vectorizer.vocabulary_
    assert manifest['output_hashes']['course_features.npz']


def test_content_rejects_overwrite_and_incomplete_metadata(tmp_path):
    courses, train, fallback = _case()
    output = tmp_path / 'features'
    fit_content(courses, train, ContentConfig(), output, fallback)
    with pytest.raises(ValueError, match='exists'):
        fit_content(courses, train, ContentConfig(min_df=2), output, fallback)

    missing = courses[courses.course_id != 'C_2']
    with pytest.raises(ValueError, match='metadata'):
        fit_content(missing, train, ContentConfig(), tmp_path / 'missing', fallback)
    assert not (tmp_path / 'missing').exists()


def test_content_accepts_nullable_metadata_and_falls_back_when_all_text_is_empty(tmp_path):
    courses, train, fallback = _case()
    courses['name'] = pd.NA
    courses['about'] = None
    model = fit_content(courses, train, ContentConfig(), tmp_path / 'empty', fallback)

    scored = model.score('U_1', ('C_3', 'C_1'))
    assert scored.fallback_status == 'popularity_empty_profile'
    np.testing.assert_array_equal(scored.scores,
                                  fallback.score('U_1', ('C_3', 'C_1')).scores)
    manifest = json.loads((tmp_path / 'empty/feature_manifest.json').read_text(encoding='utf-8'))
    assert manifest['empty_vector_count'] == 3
    assert load_npz(tmp_path / 'empty/course_features.npz').shape == (3, 0)
