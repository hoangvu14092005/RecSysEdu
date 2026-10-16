import json

import pytest

from recsysedu.knowledge.audit import audit_knowledge_sources


def sources(tmp_path, edges, mapping='A\tC_1\nB\tC_2\nC\tC_2\n'):
    paths = [tmp_path / name for name in ('concept.json', 'concept-course.txt', 'cs.json')]
    paths[0].write_text('\n'.join(json.dumps({'id': key}) for key in 'ABC'), encoding='utf-8')
    paths[1].write_text(mapping, encoding='utf-8')
    paths[2].write_text(json.dumps(edges), encoding='utf-8')
    courses = tmp_path / 'course.json'
    courses.write_text(json.dumps([{'id': 'C_1'}, {'id': 'C_2'}]), encoding='utf-8')
    return paths, courses


def edge(start, end, label=1):
    return {'c1': start, 'c2': end, 'ground_truth': label, 'graph_predict': 1}


def test_chain_coverage_and_source_preservation(tmp_path):
    paths, courses = sources(tmp_path, [edge('A', 'B'), edge('B', 'C')])
    before = [path.read_bytes() for path in [*paths, courses]]
    report = audit_knowledge_sources(*paths, courses_path=courses)
    assert report['labels'] == {'positive': 2, 'zero': 0, 'unknown': 0}
    assert report['usable_edges'] == [['A', 'B'], ['B', 'C']]
    assert report['mapping']['concept_coverage'] == 1
    assert report['mapping']['course_coverage'] == 1
    assert report['cycles'] == []
    assert report['decision'] == 'P1_READY_FOR_SEPARATE_PLAN'
    assert [path.read_bytes() for path in [*paths, courses]] == before
    assert all(source['sha256'] for source in report['sources'].values())


def test_only_numeric_label_one_is_usable_even_when_predictions_are_positive(tmp_path):
    paths, courses = sources(tmp_path, [edge('A', 'B'), edge('B', 'C', 0),
                                        edge('C', 'A', -1), edge('C', 'B', '1'),
                                        edge('A', 'C', True)])
    report = audit_knowledge_sources(*paths, courses_path=courses)
    assert report['labels'] == {'positive': 1, 'zero': 1, 'unknown': 3}
    assert report['usable_edges'] == [['A', 'B']]
    assert report['unknown_label_rows'] == [3, 4, 5]
    assert report['decision'] == 'P1_STOP_INSUFFICIENT_EVIDENCE'


def test_cycles_are_reported_without_removing_their_edges(tmp_path):
    paths, courses = sources(tmp_path, [edge('A', 'B'), edge('B', 'C'), edge('C', 'A'),
                                        edge('A', 'A')])
    report = audit_knowledge_sources(*paths, courses_path=courses)
    assert report['self_loops'] == [['A', 'A']]
    assert report['cycles'] == [['A', 'B', 'C']]
    assert report['usable_edges'] == [['A', 'B'], ['B', 'C'], ['C', 'A']]
    assert report['decision'] == 'P1_STOP_INSUFFICIENT_EVIDENCE'


def test_unmapped_ids_and_duplicate_mapping_are_explicit(tmp_path):
    paths, courses = sources(tmp_path, [edge('A', 'missing'), edge('B', 'C')],
                             'A\tC_1\nA\tC_1\nunknown\tC_2\nB\tC_missing\n')
    report = audit_knowledge_sources(*paths, courses_path=courses)
    assert report['unmapped_ids'] == {'mapping_concepts': ['unknown'],
                                      'mapping_courses': ['C_missing'],
                                      'prerequisite_concepts': ['missing']}
    assert report['mapping']['duplicate_rows'] == 1
    assert report['mapping']['valid_pairs'] == 1
    assert report['mapping']['concept_coverage'] == pytest.approx(1 / 3)
    assert report['mapping']['course_coverage'] == .5
    assert report['usable_edges'] == [['B', 'C']]
    assert report['decision'] == 'P1_STOP_INSUFFICIENT_EVIDENCE'


def test_no_catalog_never_claims_course_validation_or_readiness(tmp_path):
    paths, _ = sources(tmp_path, [edge('A', 'B')])
    report = audit_knowledge_sources(*paths)
    assert report['mapping']['course_catalog_status'] == 'not_available'
    assert report['mapping']['course_coverage'] is None
    assert report['unmapped_ids']['mapping_courses'] is None
    assert report['decision'] == 'P1_STOP_INSUFFICIENT_EVIDENCE'


@pytest.mark.parametrize('bad_mapping', ['A C_1\n', 'A\tC_1\textra\n', '\tC_1\n'])
def test_malformed_mapping_fails_closed(tmp_path, bad_mapping):
    paths, courses = sources(tmp_path, [], bad_mapping)
    with pytest.raises(ValueError, match='concept-course'):
        audit_knowledge_sources(*paths, courses_path=courses)


def test_empty_sources_do_not_pass_gate(tmp_path):
    paths, courses = sources(tmp_path, [], '')
    paths[0].write_text('[]', encoding='utf-8')
    report = audit_knowledge_sources(*paths, courses_path=courses)
    assert report['mapping']['concept_coverage'] is None
    assert report['decision'] == 'P1_STOP_INSUFFICIENT_EVIDENCE'


def test_missing_file_is_an_error_not_a_measured_empty_graph(tmp_path):
    paths, _ = sources(tmp_path, [])
    paths[2].unlink()
    with pytest.raises(FileNotFoundError):
        audit_knowledge_sources(*paths)


def test_long_graph_audit_does_not_depend_on_python_recursion_limit(tmp_path):
    keys = [f'K_{index}' for index in range(1500)]
    edges = [edge(start, end) for start, end in zip(keys, keys[1:])]
    edges.append(edge(keys[-1], keys[0]))
    paths, courses = sources(tmp_path, edges, ''.join(f'{key}\tC_1\n' for key in keys))
    paths[0].write_text(json.dumps([{'id': key} for key in keys]), encoding='utf-8')
    report = audit_knowledge_sources(*paths, courses_path=courses)
    assert len(report['usable_edges']) == 1500
    assert report['cycles'] == [sorted(keys)]


@pytest.mark.parametrize('records', [[{'name': 'missing id'}], [{'id': 'A'}, {'id': 'A'}]])
def test_invalid_or_duplicate_catalog_ids_are_not_silently_merged(tmp_path, records):
    paths, courses = sources(tmp_path, [])
    paths[0].write_text(json.dumps(records), encoding='utf-8')
    with pytest.raises(ValueError, match='ID'):
        audit_knowledge_sources(*paths, courses_path=courses)
