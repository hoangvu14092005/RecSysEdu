"""Read-only audit of exact MOOCCubeX concept IDs and labelled prerequisites."""

import hashlib
from pathlib import Path

from recsysedu.data.audit import iter_records


def _source(path):
    path = Path(path)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return {'path': str(path.resolve()), 'bytes': path.stat().st_size,
            'sha256': digest.hexdigest()}


def _id(value, location):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f'ID phải là chuỗi không rỗng, không thêm khoảng trắng: {location}')
    return value


def _catalog(path):
    ids = set()
    for row, record in enumerate(iter_records(Path(path)), 1):
        key = _id(record.get('id'), f'{path}:{row}')
        if key in ids:
            raise ValueError(f'ID catalog trùng: {path}:{row}: {key}')
        ids.add(key)
    return ids


def _cycle_components(edges):
    """Iterative Kosaraju: report cyclic SCCs, not exponentially many simple cycles."""
    forward, reverse = {}, {}
    for start, end in edges:
        forward.setdefault(start, set()).add(end)
        forward.setdefault(end, set())
        reverse.setdefault(end, set()).add(start)
        reverse.setdefault(start, set())
    visited, order = set(), []
    for root in sorted(forward):
        if root in visited:
            continue
        visited.add(root)
        stack = [(root, iter(sorted(forward[root])))]
        while stack:
            node, children = stack[-1]
            child = next(children, None)
            if child is None:
                order.append(node)
                stack.pop()
            elif child not in visited:
                visited.add(child)
                stack.append((child, iter(sorted(forward[child]))))
    visited, cycles = set(), []
    for root in reversed(order):
        if root in visited:
            continue
        visited.add(root)
        stack, component = [root], []
        while stack:
            node = stack.pop()
            component.append(node)
            for child in reverse[node]:
                if child not in visited:
                    visited.add(child)
                    stack.append(child)
        if len(component) > 1:
            cycles.append(sorted(component))
    return sorted(cycles)


def audit_knowledge_sources(concepts_path, mapping_path, prerequisites_path, *,
                            courses_path=None) -> dict:
    """Audit files without modifying them or guessing ID/name equivalence.

    Concepts/courses use raw JSONL or JSON arrays with ``id``. Mapping is headerless
    ``concept_id TAB course_id``. Prerequisites use ``c1``, ``c2``, ``ground_truth``.
    Course linkage requires the optional catalog; without it the gate stays closed.
    ``usable_edges`` means positive, known, non-self edges for topology inspection;
    cycles remain in that list and prevent readiness. It is not a released graph.
    Missing/malformed inputs raise rather than masquerading as measured zero rows.
    """
    paths = {'concepts': concepts_path, 'mapping': mapping_path,
             'prerequisites': prerequisites_path}
    if courses_path is not None:
        paths['courses'] = courses_path
    sources = {name: _source(path) for name, path in paths.items()}
    concepts = _catalog(concepts_path)
    courses = _catalog(courses_path) if courses_path is not None else None
    pairs, mapping_rows = set(), 0
    with Path(mapping_path).open(encoding='utf-8-sig') as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            parts = line.rstrip('\r\n').split('\t')
            if len(parts) != 2:
                raise ValueError(f'concept-course cần đúng hai cột TAB: {line_number}')
            pair = tuple(_id(value, f'concept-course:{line_number}') for value in parts)
            mapping_rows += 1
            pairs.add(pair)
    unknown_concepts = sorted({concept for concept, _ in pairs} - concepts)
    unknown_courses = (sorted({course for _, course in pairs} - courses)
                       if courses is not None else None)
    valid_pairs = {(concept, course) for concept, course in pairs
                   if concept in concepts and (courses is None or course in courses)}
    mapped_concepts = {concept for concept, _ in valid_pairs}
    mapped_courses = {course for _, course in valid_pairs}
    labels = dict(positive=0, zero=0, unknown=0)
    unknown_label_rows, prerequisite_ids = [], set()
    positive_edges, positive_rows = set(), 0
    for row, record in enumerate(iter_records(Path(prerequisites_path)), 1):
        start = _id(record.get('c1'), f'prerequisites:{row}:c1')
        end = _id(record.get('c2'), f'prerequisites:{row}:c2')
        prerequisite_ids.update((start, end))
        label = record.get('ground_truth')
        if type(label) in (int, float) and label == 1:
            labels['positive'] += 1
            positive_rows += 1
            positive_edges.add((start, end))
        elif type(label) in (int, float) and label == 0:
            labels['zero'] += 1
        else:
            labels['unknown'] += 1
            unknown_label_rows.append(row)
    self_loops = sorted(edge for edge in positive_edges if edge[0] == edge[1])
    usable = {edge for edge in positive_edges
              if edge[0] in concepts and edge[1] in concepts and edge[0] != edge[1]}
    cycles = _cycle_components(usable)
    unmapped_prerequisites = sorted(prerequisite_ids - concepts)
    no_course_mapping = sorted(prerequisite_ids - mapped_concepts)
    reasons = []
    for condition, reason in [
        (not concepts, 'empty_concept_catalog'),
        (courses is None, 'course_catalog_not_available'),
        (courses is not None and not courses, 'empty_course_catalog'),
        (not valid_pairs, 'no_valid_concept_course_mapping'),
        (not usable, 'no_usable_positive_edges'),
        (bool(unknown_concepts), 'unmapped_mapping_concepts'),
        (bool(unknown_courses), 'unmapped_mapping_courses'),
        (bool(unmapped_prerequisites), 'unmapped_prerequisite_concepts'),
        (bool(no_course_mapping), 'prerequisite_concepts_without_course_mapping'),
        (bool(labels['unknown']), 'unknown_prerequisite_labels'),
        (bool(self_loops), 'positive_self_loops'),
        (bool(cycles), 'positive_cycles'),
    ]:
        if condition:
            reasons.append(reason)
    return {
        'audit_status': 'measured', 'sources': sources,
        'id_policy': 'exact_string_match_no_name_or_numeric_inference',
        'concept_count': len(concepts), 'course_count': len(courses) if courses is not None else None,
        'mapping': {
            'rows': mapping_rows, 'unique_pairs': len(pairs),
            'duplicate_rows': mapping_rows - len(pairs), 'valid_pairs': len(valid_pairs),
            'mapped_concepts': len(mapped_concepts), 'mapped_courses': len(mapped_courses),
            'concept_coverage': len(mapped_concepts) / len(concepts) if concepts else None,
            'course_coverage': len(mapped_courses) / len(courses) if courses else None,
            'course_catalog_status': 'measured' if courses is not None else 'not_available',
        },
        'labels': labels, 'unknown_label_rows': unknown_label_rows,
        'positive_unique_edges': len(positive_edges),
        'duplicate_positive_rows': positive_rows - len(positive_edges),
        'self_loops': [list(edge) for edge in self_loops],
        'cycles': cycles, 'cycle_semantics': 'strongly_connected_components_size_greater_than_one',
        'usable_edges': [list(edge) for edge in sorted(usable)],
        'unmapped_ids': {'mapping_concepts': unknown_concepts, 'mapping_courses': unknown_courses,
                         'prerequisite_concepts': unmapped_prerequisites},
        'prerequisite_concepts_without_course_mapping': no_course_mapping,
        'decision': ('P1_STOP_INSUFFICIENT_EVIDENCE' if reasons
                     else 'P1_READY_FOR_SEPARATE_PLAN'),
        'decision_reasons': reasons,
    }
