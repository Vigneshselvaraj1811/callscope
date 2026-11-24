"""A tiny app with a classic N+1 bug and a duplicated API call.

Run it:  callscope run examples/demo.py
"""

import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests

import callscope


class FakeAPI(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *args):
        pass


def setup_db():
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
    db.execute("CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, total REAL)")
    db.executemany("INSERT INTO users VALUES (?, ?)", [(i, f"user{i}") for i in range(8)])
    db.executemany("INSERT INTO orders VALUES (NULL, ?, ?)", [(i % 8, i * 1.5) for i in range(40)])
    return db


def list_users(db, api):
    users = db.execute("SELECT id, name FROM users").fetchall()
    result = []
    for user_id, name in users:
        # N+1: one query per user instead of a single JOIN / GROUP BY
        total = db.execute(
            "SELECT SUM(total) FROM orders WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        result.append((name, total))
    requests.get(f"{api}/exchange-rate?api_key=sk_live_123")
    requests.get(f"{api}/exchange-rate?api_key=sk_live_123")  # duplicate call
    return result


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeAPI)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    api = f"http://127.0.0.1:{server.server_address[1]}"

    db = setup_db()
    with callscope.scope("GET /users"):
        list_users(db, api)
    server.shutdown()
