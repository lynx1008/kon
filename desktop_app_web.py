"""Desktop build of コン using the same HTML/CSS interface as the web version."""
from __future__ import annotations

import threading

import webview
from werkzeug.serving import make_server

from app import app


class LocalServer(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.server = make_server("127.0.0.1", 0, app)
        self.port = self.server.server_port

    def run(self):
        self.server.serve_forever()

    def stop(self):
        self.server.shutdown()


def main():
    server = LocalServer()
    server.start()
    window = webview.create_window(
        "コン",
        f"http://127.0.0.1:{server.port}/",
        width=1080,
        height=820,
        min_size=(520, 640),
        resizable=True,
        text_select=True,
    )
    window.events.closed += lambda: server.stop()
    webview.start(debug=False)


if __name__ == "__main__":
    main()
