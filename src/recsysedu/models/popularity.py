"""Most-popular baseline scored from train enrollments."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from recsysedu.contracts import ScoreResult


@dataclass(frozen=True)
class PopularityModel:
    """User-independent course enrollment counts for a declared universe."""

    universe: tuple[str, ...]
    counts: tuple[float, ...]
    _count_by_course: Mapping[str, float] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, '_count_by_course', MappingProxyType(
            dict(zip(self.universe, self.counts))))

    def score(self, user_id: str, candidate_ids: Sequence[str]) -> ScoreResult:
        """Return train enrollment counts aligned with the requested candidates."""
        del user_id
        candidates = tuple(candidate_ids)
        unknown = set(candidates) - self._count_by_course.keys()
        if unknown:
            raise ValueError('unknown candidate IDs')
        return ScoreResult(candidates, np.array([self._count_by_course[item]
                                                 for item in candidates]))


def fit_popularity(train: pd.DataFrame, universe: Sequence[str]) -> PopularityModel:
    """Count train enrollments only, in the declared sorted course universe."""
    courses = tuple(universe)
    if (not courses or
            any(not isinstance(course, str) or not course.strip() for course in courses) or
            courses != tuple(sorted(set(courses)))):
        raise ValueError('universe must contain unique, non-empty sorted course IDs')
    if not {'user_id', 'course_id'} <= set(train.columns):
        raise ValueError('train must contain user_id and course_id columns')

    counts = Counter(train['course_id'])
    outside = set(counts) - set(courses)
    if outside:
        raise ValueError(f'train contains courses outside universe: {sorted(outside)}')
    return PopularityModel(courses, tuple(float(counts[course]) for course in courses))
