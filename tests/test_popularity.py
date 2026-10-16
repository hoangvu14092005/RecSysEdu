import numpy as np
import pandas as pd
import pytest

from recsysedu.evaluation.ranking import rank_candidates
from recsysedu.models.popularity import fit_popularity


def test_popularity_counts_train_only_and_scores_unseen_candidates():
    train = pd.DataFrame({
        'user_id': ['U_1', 'U_1', 'U_2'],
        'course_id': ['C_2', 'C_1', 'C_2'],
        'valid_target': ['C_3', 'C_3', 'C_1'],
        'test_target': ['C_1', 'C_1', 'C_3'],
    })
    model = fit_popularity(train, ('C_1', 'C_2', 'C_3'))

    first = model.score('U_1', ('C_1', 'C_2', 'C_3'))
    second = model.score('U_2', ('C_1', 'C_2', 'C_3'))
    assert first.course_ids == ('C_1', 'C_2', 'C_3')
    np.testing.assert_array_equal(first.scores, [1.0, 2.0, 0.0])
    np.testing.assert_array_equal(second.scores, first.scores)
    assert first.evidence == {}
    with pytest.raises(ValueError, match='unknown candidate'):
        model.score('U_1', ('C_1', 'C_missing'))


def test_popularity_ties_are_resolved_by_shared_ranker():
    train = pd.DataFrame({'user_id': ['U_1', 'U_1'], 'course_id': ['C_2', 'C_1']})
    model = fit_popularity(train, ('C_1', 'C_2', 'C_3'))

    ranked = rank_candidates(model.score('U_1', ('C_3', 'C_2', 'C_1')), set(), k=3)
    assert [item.course_id for item in ranked] == ['C_1', 'C_2', 'C_3']
    assert [item.score for item in ranked] == [1.0, 1.0, 0.0]


def test_popularity_never_reads_valid_or_test_targets():
    class TrainOnly:
        columns = ['user_id', 'course_id']

        def __getitem__(self, column):
            if column not in self.columns:
                raise AssertionError(f'unexpected target access: {column}')
            return pd.Series(['U_1'] if column == 'user_id' else ['C_1'])

        def __len__(self):
            return 1

    model = fit_popularity(TrainOnly(), ('C_1', 'C_2'))
    np.testing.assert_array_equal(model.score('U_1', ('C_1', 'C_2')).scores, [1.0, 0.0])
