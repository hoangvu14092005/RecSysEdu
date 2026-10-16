"""Course TF-IDF features and train-only user profiles."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import joblib
import numpy as np
import pandas as pd
import sklearn
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from recsysedu.contracts import Recommender, ScoreResult


def _json_hash(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(encoded.encode('utf-8')).hexdigest()


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _clean_text(value: object) -> str:
    if value is None or value is pd.NA or (isinstance(value, (float, np.floating))
                                         and np.isnan(value)):
        return ''
    if not isinstance(value, str):
        raise ValueError('course metadata name/about must be strings or null')
    return ' '.join(unicodedata.normalize('NFKC', value).split())


@dataclass(frozen=True)
class ContentConfig:
    analyzer: str = 'char'
    ngram_range: tuple[int, int] = (2, 4)
    min_df: int | float = 1

    def __post_init__(self) -> None:
        if self.analyzer not in ('char', 'char_wb', 'word'):
            raise ValueError('analyzer must be char, char_wb or word')
        pair = self.ngram_range
        if (not isinstance(pair, (list, tuple)) or len(pair) != 2 or
                any(type(item) is not int or item < 1 for item in pair) or pair[0] > pair[1]):
            raise ValueError('ngram_range must be two positive increasing integers')
        object.__setattr__(self, 'ngram_range', tuple(pair))
        min_df = self.min_df
        if not ((type(min_df) is int and min_df >= 1) or
                (type(min_df) is float and 0 < min_df <= 1)):
            raise ValueError('min_df must be a positive integer or a fraction in (0, 1]')

    def manifest_value(self) -> dict:
        return {'analyzer': self.analyzer, 'ngram_range': list(self.ngram_range),
                'min_df': self.min_df}


@dataclass(frozen=True)
class ContentModel:
    course_ids: tuple[str, ...]
    course_features: sparse.csr_matrix
    user_courses: Mapping[str, tuple[int, ...]]
    fallback: Recommender

    def score(self, user_id: str, candidate_ids: Sequence[str]) -> ScoreResult:
        candidates = tuple(candidate_ids)
        index = {course_id: position for position, course_id in enumerate(self.course_ids)}
        if len(set(candidates)) != len(candidates):
            raise ValueError('candidate IDs must be unique')
        if any(course_id not in index for course_id in candidates):
            raise ValueError('unknown candidate IDs')
        rows = self.user_courses.get(user_id, ())
        if rows and self.course_features.shape[1]:
            weights = sparse.csr_matrix((np.ones(len(rows)),
                                         (np.zeros(len(rows)), rows)),
                                        shape=(1, len(self.course_ids)))
            profile = normalize(weights @ self.course_features)
            if profile.nnz:
                chosen = self.course_features[[index[item] for item in candidates]]
                scores = np.asarray((profile @ chosen.T).toarray()).ravel()
                return ScoreResult(candidates, scores)
        fallback = self.fallback.score(user_id, candidates)
        if fallback.course_ids != candidates:
            raise ValueError('fallback course IDs do not match candidates')
        return ScoreResult(candidates, fallback.scores,
                           fallback_status='popularity_empty_profile',
                           evidence=fallback.evidence)


def fit_content(courses: pd.DataFrame, train: pd.DataFrame, config: ContentConfig,
                artifact_dir: Path, fallback: Recommender) -> ContentModel:
    """Fit on sorted train course IDs joined to metadata; publish a new artifact directory."""
    if not isinstance(config, ContentConfig):
        raise ValueError('config must be ContentConfig')
    if not {'course_id', 'name', 'about'} <= set(courses.columns):
        raise ValueError('course metadata must include course_id, name and about')
    if not {'user_id', 'course_id'} <= set(train.columns):
        raise ValueError('train must include user_id and course_id')
    output = Path(artifact_dir)
    if output.exists():
        raise ValueError(f'artifact_dir already exists: {output}')

    train_pairs = list(zip(train['user_id'], train['course_id']))
    if not train_pairs or any(not isinstance(user, str) or not user.strip() or
                              not isinstance(course, str) or not course.strip()
                              for user, course in train_pairs):
        raise ValueError('train must contain valid user and course IDs')
    course_ids = tuple(sorted({course for _, course in train_pairs}))
    if courses['course_id'].duplicated().any():
        raise ValueError('course metadata contains duplicate course IDs')
    catalog = courses.set_index('course_id')
    if any(course_id not in catalog.index for course_id in course_ids):
        raise ValueError('train course missing from metadata')
    texts = [_clean_text(catalog.at[course_id, 'name']) + ' ' +
             _clean_text(catalog.at[course_id, 'about']) for course_id in course_ids]
    texts = [text.strip() for text in texts]
    vectorizer = TfidfVectorizer(analyzer=config.analyzer, ngram_range=config.ngram_range,
                                 min_df=config.min_df, dtype=np.float64)
    if any(text for text in texts):
        try:
            features = vectorizer.fit_transform(texts).tocsr()
        except ValueError as exc:
            raise ValueError(f'cannot fit content vocabulary: {exc}') from exc
    else:
        features = sparse.csr_matrix((len(course_ids), 0), dtype=np.float64)

    course_index = {course_id: index for index, course_id in enumerate(course_ids)}
    histories: dict[str, list[int]] = {}
    for user_id, course_id in train_pairs:
        histories.setdefault(user_id, []).append(course_index[course_id])
    user_courses = {user_id: tuple(indices) for user_id, indices in histories.items()}

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.content-', dir=output.parent) as temporary:
        stage = Path(temporary) / 'features'
        stage.mkdir()
        joblib.dump(vectorizer, stage / 'vectorizer.joblib')
        sparse.save_npz(stage / 'course_features.npz', features)
        (stage / 'course_order.json').write_text(
            json.dumps(course_ids, ensure_ascii=False) + '\n', encoding='utf-8')
        files = ('vectorizer.joblib', 'course_features.npz', 'course_order.json')
        manifest = {
            'schema_version': 1,
            'course_ids': list(course_ids),
            'course_count': len(course_ids),
            'vocabulary_size': len(getattr(vectorizer, 'vocabulary_', {})),
            'empty_vector_count': int((features.getnnz(axis=1) == 0).sum()),
            'text_columns': ['name', 'about'],
            'cleaning_version': 'NFKC_whitespace_v1',
            'fit_scope': 'train_course_universe',
            'config': config.manifest_value(),
            'config_hash': _json_hash(config.manifest_value()),
            'catalog_text_hash': _json_hash(list(zip(course_ids, texts))),
            'sklearn_version': sklearn.__version__,
            'output_hashes': {name: _file_hash(stage / name) for name in files},
        }
        (stage / 'feature_manifest.json').write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        if output.exists():
            raise ValueError(f'artifact_dir already exists: {output}')
        stage.rename(output)
    return ContentModel(course_ids, features, user_courses, fallback)
