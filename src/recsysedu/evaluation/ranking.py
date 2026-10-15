"""Evaluator-owned seen filtering and deterministic score ordering."""

from typing import Iterable

from recsysedu.contracts import RankedItem, ScoreResult
from recsysedu.evaluation.metrics import _ids, _validate_k


def rank_candidates(result: ScoreResult, seen_ids: Iterable[str], *, k: int
                    ) -> tuple[RankedItem, ...]:
    """Rank finite scores descending, breaking ties by source course ID ascending."""
    _validate_k(k)
    if not isinstance(result, ScoreResult):
        raise ValueError('model must return ScoreResult')
    # Revalidate at the consumption boundary, including scores of masked items.
    checked = ScoreResult(result.course_ids, result.scores, result.fallback_status,
                          result.evidence)
    seen = set(_ids(seen_ids, 'seen_ids'))
    scored = [(course_id, float(score)) for course_id, score in
              zip(checked.course_ids, checked.scores) if course_id not in seen]
    scored.sort(key=lambda pair: (-pair[1], pair[0]))
    return tuple(RankedItem(course_id, rank, score)
                 for rank, (course_id, score) in enumerate(scored[:k], 1))
