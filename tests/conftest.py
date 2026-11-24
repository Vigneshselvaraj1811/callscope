import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

import callscope


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        status = 404 if self.path.startswith("/missing") else 200
        body = b'{"ok": true}'
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture(scope="session")
def http_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


@pytest.fixture(autouse=True)
def instrumented():
    callscope.install(report=False)
    yield
    callscope.uninstall()
