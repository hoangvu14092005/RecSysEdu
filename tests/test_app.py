from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = Path(__file__).parents[1] / 'app' / 'streamlit_app.py'


def test_demo_shows_two_tabs_and_synthetic_warning():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception
    assert [tab.label for tab in app.tabs] == ['Gợi ý học tập', 'Model Lab']
    assert any('dữ liệu mẫu' in warning.value.lower() for warning in app.warning)


def test_changing_profile_and_model_updates_ranking():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.selectbox(key='user').select('U_demo_new').run()
    assert not app.exception
    assert any('chưa có lịch sử' in info.value.lower() for info in app.info)
    app.selectbox(key='model').select('content').run()
    assert not app.exception
    assert any('Cấu trúc dữ liệu' in text.value for text in app.text)
    assert app.selectbox(key='user').value == 'U_demo_new'


def test_real_exported_snapshot_shows_provenance_and_switches_rankings(
        demo_runs, tmp_path, monkeypatch):
    from recsysedu.demo.export import export_demo_bundle

    path = tmp_path / 'bundle.json'
    export_demo_bundle(demo_runs, ['U_0', 'U_3'], path)
    monkeypatch.setenv('RECSYSEDU_BUNDLE', str(path))
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception and not app.warning
    assert any('snapshot-test-fixture' in x.value for x in app.caption)
    assert any('offline' in x.value.lower() for x in app.info)
    assert not any('KẾT QUẢ THẬT' in x.value for x in app.info)
    assert any('Run ID' in frame.value.columns for frame in app.dataframe)
    app.selectbox(key='user').select('U_3').run()
    assert any('#1  Python basic' in x.value for x in app.text)
    app.selectbox(key='model').select('content').run()
    assert not app.exception
    assert any('#1  History modern' in x.value for x in app.text)


def test_broken_real_bundle_is_error_without_fixture_fallback(tmp_path, monkeypatch):
    path = tmp_path / 'broken.json'
    path.write_text('{"meta": {"data_mode": "real"}}', encoding='utf-8')
    monkeypatch.setenv('RECSYSEDU_BUNDLE', str(path))
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert app.error and not app.exception
    assert not app.tabs and not app.warning and not app.selectbox
