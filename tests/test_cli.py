import subprocess
import sys

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
