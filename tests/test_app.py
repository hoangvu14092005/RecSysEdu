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
