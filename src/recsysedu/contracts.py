"""Shared model scoring and run identity contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Mapping, Protocol, Sequence

import numpy as np


def _require_non_empty_string(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


@dataclass(frozen=True)
class ScoreResult:
    """Scores aligned positionally with source course IDs in candidate order."""

    course_ids: tuple[str, ...]
    scores: np.ndarray
    fallback_status: str = "none"
    evidence: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.course_ids, tuple):
            raise ValueError("course_ids must be a tuple of source ID strings")
        for course_id in self.course_ids:
            _require_non_empty_string(course_id, "course_id")
        if len(set(self.course_ids)) != len(self.course_ids):
            raise ValueError("course_ids must not contain duplicates")
        if not isinstance(self.scores, np.ndarray):
            raise ValueError("scores must be a NumPy array")
        if self.scores.ndim != 1 or len(self.scores) != len(self.course_ids):
            raise ValueError("scores must be one-dimensional and match course_ids length")
        if self.scores.dtype.kind not in "iuf" or not np.isfinite(self.scores).all():
            raise ValueError("scores must contain only finite real numbers")
        _require_non_empty_string(self.fallback_status, "fallback_status")
        scores = self.scores.copy()
        scores.setflags(write=False)
        object.__setattr__(self, "scores", scores)


@dataclass(frozen=True)
class RankedItem:
    course_id: str
    rank: int
    score: float

    def __post_init__(self) -> None:
        _require_non_empty_string(self.course_id, "course_id")
        if isinstance(self.rank, bool) or not isinstance(self.rank, int) or self.rank < 1:
            raise ValueError("rank must be an integer from one")
        if isinstance(self.score, bool) or not isinstance(self.score, (int, float)):
            raise ValueError("score must be a finite real number")
        try:
            finite = isfinite(self.score)
        except OverflowError as exc:
            raise ValueError("score must be a finite real number") from exc
        if not finite:
            raise ValueError("score must be a finite real number")


@dataclass(frozen=True)
class RunIdentity:
    run_id: str
    model_id: str
    dataset_hash: str
    split_hash: str
    protocol_id: str
    seed: int | None

    def __post_init__(self) -> None:
        for name in ("run_id", "model_id", "dataset_hash", "split_hash", "protocol_id"):
            _require_non_empty_string(getattr(self, name), name)
        if self.seed is not None and (isinstance(self.seed, bool) or not isinstance(self.seed, int)):
            raise ValueError("seed must be an integer or None")


class Recommender(Protocol):
    def score(self, user_id: str, candidate_ids: Sequence[str]) -> ScoreResult: ...
