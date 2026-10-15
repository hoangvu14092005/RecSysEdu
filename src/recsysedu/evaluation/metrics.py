"""Binary relevance metrics; all users receive equal weight in aggregation."""

from math import log2
from typing import Iterable


def _validate_k(k: int) -> None:
    if type(k) is not int or k < 1:
        raise ValueError('k must be a positive integer')


def _ids(values: Iterable[str], name: str) -> tuple[str, ...]:
    ids = tuple(values)
    if any(not isinstance(item, str) or not item.strip() for item in ids):
        raise ValueError(f'{name} must contain non-empty source IDs')
    if len(set(ids)) != len(ids):
        raise ValueError(f'{name} must not contain duplicate IDs')
    return ids


def metrics_at_k(ranked_ids: Iterable[str], target_ids: Iterable[str],
                 universe_size: int, *, k: int) -> dict[str, float]:
    """Compute one user's metrics, truncating ranking at K.

    Precision always divides by K, including short lists. Coverage here describes
    one user's list; run coverage must use the union of recommendations instead
    of averaging these per-user values. Targets must already be warm and unseen.
    """
    _validate_k(k)
    ranked = _ids(ranked_ids, 'ranked_ids')
    targets = set(_ids(target_ids, 'target_ids'))
    if type(universe_size) is not int or universe_size < 1:
        raise ValueError('universe_size must be a positive integer')
    if not targets or max(len(ranked), len(targets)) > universe_size:
        raise ValueError('ranking and non-empty targets must fit the universe')
    top = ranked[:k]
    hits = sum(item in targets for item in top)
    dcg = sum(1 / log2(rank + 1) for rank, item in enumerate(top, 1) if item in targets)
    ideal = sum(1 / log2(rank + 1) for rank in range(1, min(k, len(targets)) + 1))
    return {
        f'NDCG@{k}': dcg / ideal,
        f'HitRate@{k}': float(hits > 0),
        f'Recall@{k}': hits / len(targets),
        f'Precision@{k}': hits / k,
        f'Coverage@{k}': len(top) / universe_size,
    }
