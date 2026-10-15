import subprocess
import sys

import yaml

from recsysedu.cli import main


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
