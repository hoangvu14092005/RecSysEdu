import subprocess
import sys

import yaml

from recsysedu.cli import main
from recsysedu.data.prepare import prepare_dataset


def test_cli_help_is_available():
    result = subprocess.run([sys.executable, '-m', 'recsysedu.cli', '--help'],
                            capture_output=True, text=True)
    assert result.returncode == 0
    assert 'data' in result.stdout
    assert 'demo' in result.stdout


def test_invalid_config_fails_cleanly():
    result = subprocess.run([sys.executable, '-m', 'recsysedu.cli', 'data', 'audit',
                             '--config', 'file_that_does_not_exist.yaml'],
                            capture_output=True)
    assert result.returncode == 1
    assert b'Traceback' not in result.stderr


def test_malformed_json_array_reports_clean_error(tmp_path, capsys):
    (tmp_path / 'course.json').write_text('[{"id":"C_1"}', encoding='utf-8')
    (tmp_path / 'user.json').write_text('[]', encoding='utf-8')
    config = tmp_path / 'config.yaml'
    config.write_text(f'raw_dir: {tmp_path.as_posix()}\naudit_output: unused.json\n',
                      encoding='utf-8')
    assert main(['data', 'audit', '--config', str(config)]) == 1
    assert 'course.json' in capsys.readouterr().err


def test_prepare_cli_writes_versioned_dataset(tmp_path, capsys):
    (tmp_path / 'course.json').write_text('[{"id":"C_1"}]', encoding='utf-8')
    (tmp_path / 'user.json').write_text('[]', encoding='utf-8')
    config = tmp_path / 'prepare.yaml'
    config.write_text(yaml.safe_dump(dict(
        raw_dir=str(tmp_path), output_dir=str(tmp_path / 'output'), dataset_version='cli-v1',
        time_basis='source_local_naive', sample_users=0, seed=20261016)), encoding='utf-8')
    assert main(['data', 'prepare', '--config', str(config)]) == 0
    output = capsys.readouterr().out
    assert 'cli-v1' in output and str(tmp_path / 'output') in output
    assert (tmp_path / 'output/dataset_manifest.json').exists()


def test_prepare_cli_invalid_config_has_no_traceback(tmp_path, capsys):
    for config_value in [[], {}, {'time_basis': 'Mars/Unknown'},
                         dict(raw_dir=str(tmp_path), output_dir='unused', dataset_version='v1',
                              time_basis=None, sample_users='ten', seed=1)]:
        config = tmp_path / 'prepare.yaml'
        config.write_text(yaml.safe_dump(config_value), encoding='utf-8')
        assert main(['data', 'prepare', '--config', str(config)]) == 1
        assert 'Traceback' not in capsys.readouterr().err


def test_prepare_cli_refuses_short_sample_without_publication(tmp_path, capsys):
    (tmp_path / 'course.json').write_text(
        '[{"id":"C_1"},{"id":"C_2"},{"id":"C_3"}]', encoding='utf-8')
    (tmp_path / 'user.json').write_text(
        '{"id":"U_1","course_order":[1,2,3],'
        '"enroll_time":["2020-01-01","2020-02-01","2020-03-01"]}', encoding='utf-8')
    config = tmp_path / 'prepare.yaml'
    config.write_text(yaml.safe_dump(dict(
        raw_dir=str(tmp_path), output_dir=str(tmp_path / 'output'), dataset_version='cli-v1',
        time_basis='source_local_naive', sample_users=2, seed=20261016)), encoding='utf-8')
    assert main(['data', 'prepare', '--config', str(config)]) == 1
    error = capsys.readouterr().err
    assert 'sample_users=2' in error and 'eligible_user_count=1' in error
    assert 'Traceback' not in error
    assert not (tmp_path / 'output').exists()


def test_split_cli_reports_version_and_separate_warm_cohort_sizes(tmp_path, capsys):
    (tmp_path / 'course.json').write_text(
        '\n'.join(f'{{"id":"C_{i}"}}' for i in range(1, 5)), encoding='utf-8')
    (tmp_path / 'user.json').write_text('\n'.join([
        '{"id":"U_1","course_order":["C_1","C_2","C_4"],'
        '"enroll_time":["2020-01-01","2020-02-01","2020-03-01"]}',
        '{"id":"U_2","course_order":["C_2","C_3","C_4"],'
        '"enroll_time":["2020-01-01","2020-02-01","2020-03-01"]}',
    ]), encoding='utf-8')
    prepared = tmp_path / 'prepared'
    prepare_dataset(tmp_path / 'course.json', tmp_path / 'user.json', prepared,
                    dataset_version='cli-dataset-v1', time_basis='source_local_naive',
                    sample_users=0, seed=1)
    config = tmp_path / 'split.yaml'
    config.write_text(yaml.safe_dump(dict(
        prepared_dir=str(prepared), output_dir=str(tmp_path / 'split'),
        split_version='cli-split-v1', seed=1)), encoding='utf-8')
    assert main(['data', 'split', '--config', str(config)]) == 0
    output = capsys.readouterr().out
    assert 'cli-split-v1' in output
    assert 'valid=1' in output and 'test=0' in output
    assert (tmp_path / 'split/split_manifest.json').exists()


def test_split_cli_malformed_manifest_exits_one_without_traceback(tmp_path, capsys):
    prepared = tmp_path / 'prepared'
    prepared.mkdir()
    (prepared / 'dataset_manifest.json').write_text('{bad json', encoding='utf-8')
    config = tmp_path / 'split.yaml'
    config.write_text(yaml.safe_dump(dict(
        prepared_dir=str(prepared), output_dir=str(tmp_path / 'split'),
        split_version='cli-split-v1', seed=1)), encoding='utf-8')
    assert main(['data', 'split', '--config', str(config)]) == 1
    error = capsys.readouterr().err
    assert 'manifest' in error and 'Traceback' not in error
    assert not (tmp_path / 'split').exists()
