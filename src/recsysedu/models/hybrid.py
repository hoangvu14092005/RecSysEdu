"""Validation-selected blend: alpha * BPR + (1 - alpha) * Content.

Each component is min–max normalized over the supplied full candidate list,
before the shared evaluator masks seen courses. No fitting or test access occurs here.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import dataclass
from numbers import Real
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

from recsysedu.adapters.recbole import UnknownBPRUserError
from recsysedu.contracts import Recommender, ScoreResult


def _alpha(value: object) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError('alpha must be a finite real number in [0, 1]')
    result = float(value)
    if not np.isfinite(result) or not 0 <= result <= 1:
        raise ValueError('alpha must be a finite real number in [0, 1]')
    return result


def _aligned(result: ScoreResult, candidates: tuple[str, ...]) -> ScoreResult:
    if not isinstance(result, ScoreResult) or result.course_ids != candidates:
        raise ValueError('component scores must preserve candidate IDs and order')
    # Revalidate at the component boundary, including length and finite numbers.
    return ScoreResult(result.course_ids, result.scores, result.fallback_status, result.evidence)


def _normalize(scores: np.ndarray) -> np.ndarray:
    values = scores.astype(np.float64)
    if not len(values) or values.max() == values.min():
        return np.zeros(len(values), dtype=np.float64)
    # Scale first to avoid overflow for finite values near float64 extremes.
    scaled = values / np.abs(values).max()
    return (scaled - scaled.min()) / (scaled.max() - scaled.min())


@dataclass(frozen=True)
class HybridModel:
    content: Recommender
    bpr: Recommender
    alpha: float
    popularity: Recommender

    def __post_init__(self) -> None:
        object.__setattr__(self, 'alpha', _alpha(self.alpha))

    def score(self, user_id: str, candidate_ids: Sequence[str]) -> ScoreResult:
        candidates = tuple(candidate_ids)
        content = _aligned(self.content.score(user_id, candidates), candidates)
        try:
            bpr = _aligned(self.bpr.score(user_id, candidates), candidates)
        except UnknownBPRUserError:
            if content.fallback_status == 'none':
                source, status = content, 'content_unknown_bpr_user'
            else:
                source = _aligned(self.popularity.score(user_id, candidates), candidates)
                status = 'popularity_unknown_bpr_user_empty_content'
            scores = _normalize(source.scores)
            evidence = {item: tuple(source.evidence.get(item, ())) + (
                f'hybrid_alpha:{self.alpha}', f'fallback:{status}') for item in candidates}
            return ScoreResult(candidates, scores, status, evidence)
        content_scores, bpr_scores = _normalize(content.scores), _normalize(bpr.scores)
        scores = (1 - self.alpha) * content_scores + self.alpha * bpr_scores
        status = 'none' if content.fallback_status == 'none' else f'content:{content.fallback_status}'
        evidence = {item: tuple(dict.fromkeys(
            tuple(content.evidence.get(item, ())) + tuple(bpr.evidence.get(item, ()))
        )) + (f'hybrid_alpha:{self.alpha}',
              f'content_normalized:{float(content_scores[index])}',
              f'bpr_normalized:{float(bpr_scores[index])}')
                    for index, item in enumerate(candidates)}
        return ScoreResult(candidates, scores, status, evidence)


def select_alpha(validation_runs: Mapping[float, Mapping], alphas: Sequence[float], *,
                 artifact_path: Path | None = None) -> float:
    """Select validation NDCG@10, breaking exact ties by smallest alpha.

    `validation_runs` maps each requested alpha to the shared evaluator's run
    manifest. All runs must be measured validation runs with compatible identity
    and policy. Optional artifact_path records the decision and hashes of its inputs.
    """
    grid = tuple(_alpha(value) for value in alphas)
    if not grid or len(set(grid)) != len(grid):
        raise ValueError('alphas must be non-empty and unique')
    if not isinstance(validation_runs, Mapping):
        raise ValueError('validation_runs must map alpha to run manifests')
    if any(isinstance(key, (bool, np.bool_)) for key in validation_runs):
        raise ValueError('run alpha keys must be real numbers, not booleans')
    if set(validation_runs) != set(grid):
        raise ValueError('validation_runs must cover exactly the requested alphas')
    compatible = ('dataset_hash', 'split_hash', 'protocol_id', 'seed', 'cohort_size',
                  'candidate_universe_size', 'candidate_policy', 'profile_policy',
                  'seen_policy', 'tie_break_policy')
    baseline = None
    rows = []
    for alpha in sorted(grid):
        run = validation_runs[alpha]
        if not isinstance(run, Mapping):
            raise ValueError('validation run must be a manifest mapping')
        if (run.get('evaluation_split') != 'valid' or run.get('metric_status') != 'measured'
                or run.get('k') != 10 or run.get('primary_metric') != 'NDCG@10'):
            raise ValueError('alpha selection requires measured validation NDCG@10 runs')
        if any(name not in run for name in compatible):
            raise ValueError('validation run missing compatibility identity or policy')
        identity = {name: run[name] for name in compatible}
        if baseline is None:
            baseline = identity
        elif identity != baseline:
            raise ValueError('validation runs have incompatible identity or policy')
        run_id = run.get('run_id')
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError('validation run missing run_id')
        metrics = run.get('metrics')
        ndcg = metrics.get('NDCG@10') if isinstance(metrics, Mapping) else None
        if (isinstance(ndcg, (bool, np.bool_)) or not isinstance(ndcg, Real)
                or not np.isfinite(ndcg) or not 0 <= ndcg <= 1):
            raise ValueError('validation NDCG@10 must be finite and in [0, 1]')
        encoded = json.dumps(dict(run), ensure_ascii=False, sort_keys=True,
                             separators=(',', ':'), allow_nan=False).encode('utf-8')
        rows.append(dict(alpha=alpha, run_id=run_id, ndcg=float(ndcg),
                         manifest_hash=hashlib.sha256(encoded).hexdigest()))
    winner = min(rows, key=lambda row: (-row['ndcg'], row['alpha']))
    if artifact_path is not None:
        output = Path(artifact_path)
        if output.exists():
            raise ValueError(f'selection artifact already exists: {output}')
        report = dict(schema_version=1, evaluation_split='valid', primary_metric='NDCG@10',
                      formula='alpha * normalized_bpr + (1 - alpha) * normalized_content',
                      normalization='per_user_full_candidates_minmax_constant_zero',
                      selected_alpha=winner['alpha'],
                      selected_ndcg=winner['ndcg'], validation_runs=rows, **baseline)
        # Ranking tie policy and selection tie policy describe different decisions.
        report['ranking_tie_break_policy'] = report.pop('tie_break_policy')
        report['selection_tie_break_policy'] = 'ndcg_desc_alpha_asc'
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.hybrid-', dir=output.parent) as temporary:
            stage = Path(temporary) / 'selection.json'
            stage.write_text(json.dumps(report, ensure_ascii=False, indent=2,
                                         allow_nan=False) + '\n', encoding='utf-8')
            if output.exists():
                raise ValueError(f'selection artifact already exists: {output}')
            stage.rename(output)
    return winner['alpha']
