"""
sheila.py — vLaunch update checker module
Loaded by kernel.py via Kernel.load_module("sheila").
kernel.py injects BASE_DIR and get_path into this module's globals before calling
check_for_updates().
"""

import os
import sys
import webbrowser

# These are overridden by kernel.py at import time
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def get_path(*p): return os.path.join(BASE_DIR, *p)

ONLINE_URL = "https://raw.githubusercontent.com/Vafls/vSubSys_UPD/main/version_info.txt"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _read_version(text: str):
    for line in text.splitlines():
        if line.startswith("current_version"):
            try:
                return int(line.split("=", 1)[1].strip())
            except ValueError:
                pass
    return None


def _read_message(text: str) -> str:
    for line in text.splitlines():
        if line.startswith("to_print"):
            return line.split("=", 1)[1].strip()
    return "A new version is available."


def _local_version():
    path = get_path("version_info.txt")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return _read_version(fh.read())


def _fetch_online():
    """Returns (version, message) or (None, None) on failure."""
    try:
        import requests
        resp = requests.get(ONLINE_URL, timeout=6)
        if resp.status_code == 200:
            return _read_version(resp.text), _read_message(resp.text)
    except Exception as exc:
        print(f"[sheila] network error: {exc}")
    return None, None


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def check_for_updates(silent: bool = False) -> dict:
    """
    Check for updates.

    silent=True  → only log; do NOT show a Qt window (safe to call before
                   QApplication is created).
    silent=False → show a Qt dialog if an update is available.

    Returns {"update": bool, "version": int|None, "message": str}
    """
    local_ver           = _local_version()
    online_ver, message = _fetch_online()

    result = {"update": False, "version": online_ver, "message": message or ""}

    if online_ver is None or local_ver is None:
        return result

    if online_ver <= local_ver:
        return result

    result["update"] = True
    _log_update(online_ver, message or "")

    if not silent:
        _show_dialog(message or "A new version is available.")

    return result


def _log_update(version: int, message: str):
    hist = get_path("kernel", "config", "nt.history")
    os.makedirs(os.path.dirname(hist), exist_ok=True)
    entry = f"[sheila] update available: v{version} — {message}\n"
    existing = []
    if os.path.isfile(hist):
        with open(hist, encoding="utf-8") as fh:
            existing = fh.readlines()
    if entry not in existing:
        with open(hist, "a", encoding="utf-8") as fh:
            fh.write(entry)


def _show_dialog(message: str):
    """Show a frameless update notification window."""
    try:
        from PyQt5.QtWidgets import (
            QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
        )
        from PyQt5.QtCore import Qt

        app = QApplication.instance() or QApplication(sys.argv)

        win = QWidget()
        win.setFixedSize(420, 280)
        win.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        win.setStyleSheet("""
            QWidget          { background:#23272f; border-radius:16px; }
            QLabel           { color:#f8f8f2; font-size:16px; }
            QPushButton      { border:none; border-radius:8px; padding:10px 0;
                               font-size:14px; color:#fff; }
        """)

        lay = QVBoxLayout(win)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(18)

        lbl = QLabel(f"Update available:\n\n{message}")
        lbl.setWordWrap(True)
        lay.addWidget(lbl)

        dl = QPushButton("Download update")
        dl.setStyleSheet("QPushButton{background:#6272a4;}"
                         "QPushButton:hover{background:#7085b6;}")
        dl.clicked.connect(lambda: webbrowser.open(
            "https://vafls.github.io/vSubSys_UPD/"))
        lay.addWidget(dl)

        cancel = QPushButton("Remind me later")
        cancel.setStyleSheet("QPushButton{background:#44475a;}"
                             "QPushButton:hover{background:#5a5f73;}")
        cancel.clicked.connect(win.close)
        lay.addWidget(cancel)

        # Centre on screen
        from PyQt5.QtWidgets import QDesktopWidget
        geo = QDesktopWidget().screenGeometry()
        win.move((geo.width() - win.width()) // 2,
                 (geo.height() - win.height()) // 2)

        win.show()
        # Only exec_ if we created the QApplication ourselves
        if QApplication.instance() is app:
            app.exec_()

    except Exception as exc:
        print(f"[sheila] dialog error: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Stand-alone
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    result = check_for_updates(silent=False)
    if result["update"]:
        print(f"[sheila] Update available: {result['message']}")
    else:
        print("[sheila] System is up to date.")
    print("sheila: SUCCESS")
