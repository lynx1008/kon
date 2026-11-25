"""Desktop build of コン using the same HTML/CSS interface as the web version."""
from __future__ import annotations

import json
import platform
import threading
from pathlib import Path

import webview
from pynput import keyboard
from werkzeug.serving import make_server

from app import app

CONFIG_PATH = Path.home() / ".kon-config.json"


class HotkeyManager:
    def __init__(self, window):
        self.window = window
        self.listener = None

    def load_hotkey(self):
        default = "<cmd>+<alt>+p" if platform.system() == "Darwin" else "<ctrl>+<alt>+p"
        try:
            data = json.loads(CONFIG_PATH.read_text())
            return data.get("hotkey", default)
        except (OSError, json.JSONDecodeError):
            return default

    def start(self):
        self.stop()
        try:
            self.listener = keyboard.GlobalHotKeys({self.load_hotkey(): self.show_window})
            self.listener.start()
        except (OSError, RuntimeError, ValueError):
            # The app remains usable through its window if OS global hotkey
            # permission has not been granted yet.
            self.listener = None

    def show_window(self):
        self.window.restore()
        self.window.show()
        try:
            self.window.bring_to_front()
        except AttributeError:
            pass

    def stop(self):
        if self.listener:
            self.listener.stop()


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
    hotkeys = HotkeyManager(window)
    hotkeys.start()
    app.config["HOTKEY_RELOAD"] = hotkeys.start
    window.events.closed += lambda: server.stop()
    window.events.closed += lambda: hotkeys.stop()
    webview.start(debug=False)


if __name__ == "__main__":
    main()
