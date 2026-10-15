import hashlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from recsysedu.data.download import download_file


@pytest.fixture
def source_server():
    payload = b'{"id":"C_demo"}\n'

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = b'<html>not a dataset</html>' if self.path == '/html' else payload
            self.send_response(200)
            self.send_header('Content-Length', str(len(body) + (10 if self.path == '/short' else 0)))
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(body)
            self.close_connection = True

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_port}', payload
    server.shutdown()
    server.server_close()
    thread.join()


def test_download_publishes_complete_file_with_checksum(source_server, tmp_path):
    base, payload = source_server
    dest = tmp_path / 'course.json'
    result = download_file(base + '/ok', dest)
    assert dest.read_bytes() == payload
    assert result['bytes'] == len(payload)
    assert result['sha256'] == hashlib.sha256(payload).hexdigest()
    assert not dest.with_suffix('.json.part').exists()


def test_html_is_not_published_as_dataset(source_server, tmp_path):
    base, _ = source_server
    dest = tmp_path / 'course.json'
    with pytest.raises(ValueError, match='JSON'):
        download_file(base + '/html', dest)
    assert not dest.exists()


def test_truncated_response_is_not_published(source_server, tmp_path):
    base, _ = source_server
    dest = tmp_path / 'user.json'
    with pytest.raises((ValueError, OSError)):
        download_file(base + '/short', dest)
    assert not dest.exists()


def test_existing_file_is_preserved(source_server, tmp_path):
    base, _ = source_server
    dest = tmp_path / 'course.json'
    dest.write_text('existing local data', encoding='utf-8')
    with pytest.raises(FileExistsError):
        download_file(base + '/ok', dest)
    assert dest.read_text(encoding='utf-8') == 'existing local data'
