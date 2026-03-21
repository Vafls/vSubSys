"""
vLaunch GUI  —  graphical desktop shell
════════════════════════════════════════
Process model:

    kernel.py  ──(spawns)──►  gui.py          (this file, child process)
                                   └──(spawns)──►  .vysico app   (grandchild)

gui.py is launched by kernel.py as a child subprocess.
It CANNOT be run directly — three guard layers prevent it:
    1. _VLAUNCH_STARTED env var must be "1"
    2. _VLAUNCH_GUI     env var must be "1"
    3. ktoken file on disk must match _VLAUNCH_TOKEN env var

Kernel dependency:
    • gui.py reads BASE_DIR from env (VLAUNCH_HOME)
    • A QTimer heartbeat (every 2 s) checks if the kernel PID
      (_VLAUNCH_KERNEL_PID) is still alive.  If the kernel exits for any
      reason, the heartbeat calls QApplication.quit() and gui.py exits too.

App launching:
    • gui.py spawns each .vysico as a grandchild subprocess using the same
      inline-script approach as Kernel.launch_pkg(), but in its own process
      context.  It does NOT call back into the kernel process.
    • A QTimer polls grandchild exit codes every 2 s to update the dock.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Launch guards  — must be the very first executable code
# ─────────────────────────────────────────────────────────────────────────────
import os
import sys


def _die(msg: str) -> None:
    print(f"\033[1;31m[gui] FATAL: {msg}\033[0m", file=sys.stderr, flush=True)
    sys.exit(1)


if os.environ.get("_VLAUNCH_STARTED") != "1":
    _die("gui.py cannot be run directly.\n"
         "       Launch via: python kernel/kernel.py --gui=1")

if os.environ.get("_VLAUNCH_GUI") != "1":
    _die("gui.py must be spawned by kernel.py (_VLAUNCH_GUI not set).")

_BASE_DIR   = os.environ.get("VLAUNCH_HOME", "")
_token_path = os.path.join(_BASE_DIR, "var", "run", "ktoken")

if not os.path.isfile(_token_path):
    _die("Session token file missing — kernel not running or token revoked.")

with open(_token_path) as _fh:
    _stored_token = _fh.read().strip()

if os.environ.get("_VLAUNCH_TOKEN", "") != _stored_token:
    _die("Session token mismatch — unauthorised GUI launch rejected.")

_KERNEL_PID = int(os.environ.get("_VLAUNCH_KERNEL_PID", "0"))

# ─────────────────────────────────────────────────────────────────────────────
# Standard imports  (after guards pass)
# ─────────────────────────────────────────────────────────────────────────────
import random
import signal
import subprocess
import string
import time
import zipfile

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QPushButton, QFrame, QSpacerItem, QSizePolicy, QMenu, QAction,
    QListWidget, QScrollArea, QGridLayout, QMessageBox,
)
from PyQt5.QtCore import Qt, QSize, QPoint, QTimer, QDateTime
from PyQt5.QtGui import (
    QPixmap, QCursor, QPainter, QIcon,
    QColor, QLinearGradient, QBrush,
)

signal.signal(signal.SIGINT, signal.SIG_DFL)

# ─────────────────────────────────────────────────────────────────────────────
# Path helpers
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR: str = _BASE_DIR
_HERE         = os.path.dirname(os.path.abspath(__file__))   # kernel/


def get_path(*p: str) -> str:
    return os.path.join(BASE_DIR, *p)


# ─────────────────────────────────────────────────────────────────────────────
# Kernel-alive check
# ─────────────────────────────────────────────────────────────────────────────

def _kernel_alive() -> bool:
    """Return True if the kernel process (_KERNEL_PID) is still running."""
    if _KERNEL_PID <= 0:
        return False
    try:
        os.kill(_KERNEL_PID, 0)
        return True
    except OSError:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Venv python (mirrors Kernel._venv_python)
# ─────────────────────────────────────────────────────────────────────────────

def _venv_python() -> str:
    for c in (get_path(".venv", "bin", "python"),
              get_path(".venv", "Scripts", "python.exe")):
        if os.path.isfile(c):
            return c
    return sys.executable


# ─────────────────────────────────────────────────────────────────────────────
# .vysico metadata reader
# ─────────────────────────────────────────────────────────────────────────────

def _read_meta(path: str) -> dict | None:
    try:
        with zipfile.ZipFile(path, "r") as z:
            names      = z.namelist()
            raw        = z.read("build.info.py").decode("utf-8", errors="replace")
            ns: dict   = {}
            exec(compile(raw, "build.info.py", "exec"), ns)  # noqa: S102
            name       = ns.get("name", os.path.splitext(os.path.basename(path))[0])
            icon_bytes = z.read("icon.png") if "icon.png" in names else None
        return {"name": name, "icon_bytes": icon_bytes}
    except Exception as exc:
        print(f"[gui] meta error {path}: {exc}", flush=True)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Inline .vysico launcher  (mirrors Kernel._launch_inline)
# ─────────────────────────────────────────────────────────────────────────────

def _launch_vysico(vysico_path: str) -> dict | None:
    """
    Spawn a .vysico app as a grandchild subprocess.

    Critical ordering inside the runner script:
      1. QApplication created FIRST — before any vrun code runs.
         vrun templates build QWidget at module level, so QApplication
         must already exist or Qt will abort with
         "Must construct a QApplication before a QWidget".
      2. exec(vrun) — widgets are created, windows shown.
      3. Heartbeat QTimer started — kills app if kernel dies.
      4. app.exec_() — Qt event loop runs until all windows closed.
      5. on_program_exit() → repack → cleanup.
    """
    if not os.path.isfile(vysico_path):
        print(f"[gui] launch: not found: {vysico_path!r}", flush=True)
        return None

    env = os.environ.copy()
    env.update({
        "_VLAUNCH_STARTED":    "1",
        "_VLAUNCH_TOKEN":      _stored_token,
        "_VLAUNCH_KERNEL_PID": str(_KERNEL_PID),
        "VLAUNCH_HOME":        BASE_DIR,
    })

    python = _venv_python()

    lines = [
        "import zipfile, os, sys, shutil, random, string, signal, traceback",
        "signal.signal(signal.SIGINT, signal.SIG_DFL)",
        "BASE_DIR    = " + repr(BASE_DIR),
        "VYSICO      = " + repr(vysico_path),
        "KERNEL_PID  = " + str(_KERNEL_PID),
        "",
        "def _kernel_alive():",
        "    try: os.kill(KERNEL_PID, 0); return True",
        "    except OSError: return False",
        "",
        # ── 1. Extract ──────────────────────────────────────────────────────
        "suffix = ''.join(random.choices(string.digits, k=10))",
        "aid    = os.path.splitext(os.path.basename(VYSICO))[0] + '_' + suffix",
        "extr   = os.path.join(BASE_DIR, 'apps', 'temp', aid)",
        "os.makedirs(extr, exist_ok=True)",
        "with zipfile.ZipFile(VYSICO) as zf:",
        "    zf.extractall(extr)",
        "vrun = os.path.join(extr, 'base.vrun')",
        "",
        # ── 2. QApplication BEFORE anything else ────────────────────────────
        "os.environ.setdefault('QTWEBENGINE_DISABLE_SANDBOX', '1')",
        "from PyQt5.QtWidgets import QApplication",
        "from PyQt5.QtCore import QTimer",
        "_app = QApplication.instance() or QApplication(sys.argv)",
        "_app.setQuitOnLastWindowClosed(True)",
        "",
        # ── 3. Close callback ────────────────────────────────────────────────
        "_closed = [False]",
        "def _cb(a=None):",
        "    if _closed[0]: return",
        "    _closed[0] = True",
        "    _app.quit()",
        "",
        # ── 4. Execution namespace ───────────────────────────────────────────
        "ns = {",
        "    '__name__':           '__main__',",
        "    '__file__':           vrun,",
        "    'APP_DIR':            extr,",
        "    'APP_ID':             aid,",
        "    'KERNEL':             None,",
        "    'PARENT_WINDOW':      None,",
        "    'APP_CLOSE_CALLBACK': _cb,",
        "    'HOME_DIR':           os.path.join(BASE_DIR, 'home'),",
        "}",
        "",
        # ── 5. Execute base.vrun ─────────────────────────────────────────────
        "with open(vrun, encoding='utf-8', errors='replace') as fh:",
        "    code = fh.read()",
        "try:",
        "    exec(compile(code, vrun, 'exec'), ns)",
        "except SystemExit: pass",
        "except Exception as e:",
        "    print('[app] base.vrun error:', e, flush=True)",
        "    traceback.print_exc()",
        "",
        # ── 6. Kernel heartbeat → start BEFORE event loop ───────────────────
        "def _hb():",
        "    if not _kernel_alive(): _app.quit()",
        "_ht = QTimer()",
        "_ht.timeout.connect(_hb)",
        "_ht.start(2000)",
        "",
        # ── 7. Qt event loop ─────────────────────────────────────────────────
        "_app.exec_()",
        "",
        # ── 8. Cleanup ───────────────────────────────────────────────────────
        "on_exit = ns.get('on_program_exit')",
        "if callable(on_exit):",
        "    try: on_exit()",
        "    except Exception as e: print('[app] on_exit error:', e, flush=True)",
        "try:",
        "    with zipfile.ZipFile(VYSICO, 'w', zipfile.ZIP_DEFLATED) as zf:",
        "        for root, _, files in os.walk(extr):",
        "            for f in files:",
        "                fp = os.path.join(root, f)",
        "                zf.write(fp, os.path.relpath(fp, extr))",
        "except Exception as e: print('[app] repack error:', e, flush=True)",
        "shutil.rmtree(extr, ignore_errors=True)",
    ]
    script = "\n".join(lines)

    try:
        proc = subprocess.Popen([python, "-c", script], env=env)
    except Exception as exc:
        print(f"[gui] Popen failed: {exc}", flush=True)
        return None

    meta = _read_meta(vysico_path)
    name = meta["name"] if meta else os.path.splitext(os.path.basename(vysico_path))[0]
    return {
        "proc":    proc,
        "name":    name,
        "path":    vysico_path,
        "pid":     proc.pid,
        "started": time.time(),
        "id":      f"{name}_{proc.pid}",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Title-bar factory (used by LockScreen and KernelWindow only)
# ─────────────────────────────────────────────────────────────────────────────

def _tbar(title: str, window: QWidget, on_close) -> QWidget:
    bar = QWidget()
    bar.setFixedHeight(30)
    bar.setStyleSheet("background:#1a1a1a;")
    lay = QHBoxLayout(bar); lay.setContentsMargins(8, 0, 0, 0)
    lbl = QLabel(title); lbl.setStyleSheet("color:white;font-size:12px;")
    lay.addWidget(lbl); lay.addStretch()
    for text, slot, style in (
        ("−", window.showMinimized,     "background:#333;color:white;border:none;"),
        ("□", lambda w=window: w.showNormal() if w.isMaximized() else w.showMaximized(),
                                         "background:#333;color:white;border:none;"),
        ("✕", on_close,                  "background:#c0392b;color:white;border:none;"),
    ):
        b = QPushButton(text); b.setFixedSize(30, 30); b.setStyleSheet(style)
        b.clicked.connect(slot); lay.addWidget(b)
    bar._dp = None
    def _p(ev):
        if ev.button() == Qt.LeftButton: bar._dp = ev.globalPos()
    def _m(ev):
        if bar._dp:
            window.move(window.pos() + (ev.globalPos() - bar._dp))
            bar._dp = ev.globalPos()
    def _r(ev):
        if ev.button() == Qt.LeftButton: bar._dp = None
    bar.mousePressEvent   = _p
    bar.mouseMoveEvent    = _m
    bar.mouseReleaseEvent = _r
    return bar


# ─────────────────────────────────────────────────────────────────────────────
# Lock Screen
# ─────────────────────────────────────────────────────────────────────────────

class LockScreen(QMainWindow):
    _AW = 80
    _AH = 80

    def __init__(self) -> None:
        super().__init__()
        self._dragging = False
        self._drag_y   = 0
        self._arr_orig = 0

        self.setWindowFlags(Qt.FramelessWindowHint)

        central = QWidget(self)
        self.setCentralWidget(central)

        # Background
        self._bg = QLabel(central)
        self._bg.setScaledContents(True)
        self._bg.setPixmap(self._load_bg())

        # Dark overlay
        self._overlay = QWidget(central)
        self._overlay.setStyleSheet("background:rgba(0,0,0,110);")

        # Clock panel
        self._panel = QWidget(central)
        self._panel.setStyleSheet(
            "QWidget{background:rgba(0,0,0,155);border-radius:18px;}"
        )
        pl = QVBoxLayout(self._panel); pl.setContentsMargins(28, 18, 28, 18); pl.setSpacing(4)

        self._time_lbl = QLabel()
        self._time_lbl.setStyleSheet(
            "color:white;font-size:68px;font-weight:200;"
            "background:transparent;letter-spacing:4px;"
        )
        self._time_lbl.setAlignment(Qt.AlignCenter)

        self._date_lbl = QLabel()
        self._date_lbl.setStyleSheet(
            "color:rgba(230,230,230,210);font-size:20px;font-weight:300;"
            "background:transparent;"
        )
        self._date_lbl.setAlignment(Qt.AlignCenter)

        # Username from global.cfg (kernel already wrote env via its own config)
        _gcfg = get_path("kernel", "config", "global.cfg")
        _user = "user"
        if os.path.isfile(_gcfg):
            for line in open(_gcfg, encoding="utf-8"):
                if line.startswith("profile_1_name"):
                    _user = line.split("=", 1)[1].strip(); break

        self._user_lbl = QLabel(_user)
        self._user_lbl.setStyleSheet(
            "color:rgba(200,200,200,200);font-size:14px;font-weight:300;background:transparent;"
        )
        self._user_lbl.setAlignment(Qt.AlignCenter)

        pl.addWidget(self._time_lbl)
        pl.addWidget(self._date_lbl)
        pl.addWidget(self._user_lbl)

        # Unlock arrow
        self._arrow = QWidget(central)
        self._arrow.setStyleSheet(
            "QWidget{background:rgba(255,255,255,30);"
            "border:2px solid rgba(255,255,255,130);border-radius:40px;}"
        )
        self._arrow.setFixedSize(self._AW, self._AH)
        al = QVBoxLayout(self._arrow); al.setContentsMargins(0, 0, 0, 0); al.setSpacing(2)
        up = QLabel("↑"); up.setAlignment(Qt.AlignCenter)
        up.setStyleSheet("color:white;font-size:30px;background:transparent;border:none;")
        hint = QLabel("unlock"); hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet("color:rgba(255,255,255,180);font-size:9px;background:transparent;border:none;")
        al.addWidget(up); al.addWidget(hint)

        # Kernel heartbeat — if kernel dies, close lock screen and exit
        self._hb_timer = QTimer(self)
        self._hb_timer.timeout.connect(self._check_kernel)
        self._hb_timer.start(2000)

        QTimer(self, timeout=self._update_time).start(1000)
        QTimer(self, timeout=self._rand_clock).start(10_000)
        self._update_time()
        self._set_cursor()

        # showFullScreen AFTER all widgets are constructed
        self.showFullScreen()

    # ── kernel heartbeat ──────────────────────────────────────────────────────

    def _check_kernel(self) -> None:
        if not _kernel_alive():
            print("[gui] kernel died — exiting", flush=True)
            QApplication.quit()

    # ── background ────────────────────────────────────────────────────────────

    def _load_bg(self) -> QPixmap:
        path = get_path("source", "lock_screen_wallpaper.png")
        if os.path.isfile(path):
            px = QPixmap(path)
            if not px.isNull():
                return px
        px = QPixmap(1920, 1080)
        p  = QPainter(px)
        g  = QLinearGradient(0, 0, 1920, 1080)
        g.setColorAt(0.0, QColor(10, 15, 40))
        g.setColorAt(0.5, QColor(20, 30, 80))
        g.setColorAt(1.0, QColor(40, 10, 60))
        p.fillRect(0, 0, 1920, 1080, QBrush(g)); p.end()
        return px

    def resizeEvent(self, ev) -> None:
        super().resizeEvent(ev)
        W, H = self.width(), self.height()
        self._bg.setGeometry(0, 0, W, H)
        self._overlay.setGeometry(0, 0, W, H)
        self._panel.adjustSize()
        pw = max(self._panel.width(), 360); ph = max(self._panel.height(), 150)
        self._panel.resize(pw, ph); self._panel.move((W - pw) // 2, H // 5)
        ax = (W - self._AW) // 2; ay = H - self._AH - 50
        self._arrow.move(ax, ay); self._arr_orig = ay

    def _update_time(self) -> None:
        now = QDateTime.currentDateTime()
        self._time_lbl.setText(now.toString("hh:mm"))
        self._date_lbl.setText(now.toString("dddd, d MMMM yyyy"))
        self._panel.adjustSize()
        self._panel.resize(max(self._panel.width(), 360), max(self._panel.height(), 150))

    def _rand_clock(self) -> None:
        W, H = self.width(), self.height()
        pw   = self._panel.width(); ph = self._panel.height()
        self._panel.move(
            random.randint(0, max(0, W - pw)),
            random.randint(0, max(0, H - ph - self._AH - 60)),
        )

    def _set_cursor(self) -> None:
        path = get_path("source", "pointer.png")
        if not os.path.isfile(path): return
        try:
            px = QPixmap(path)
            px = px.scaled(px.width() // 5, px.height() // 5,
                           Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setCursor(QCursor(px))
        except Exception:
            pass

    # ── swipe unlock ─────────────────────────────────────────────────────────

    def mousePressEvent(self, ev) -> None:
        if ev.button() == Qt.LeftButton and self._arrow.geometry().contains(ev.pos()):
            self._dragging = True; self._drag_y = ev.y()

    def mouseMoveEvent(self, ev) -> None:
        if not self._dragging: return
        dy = self._drag_y - ev.y()
        if dy > 0:
            self._arrow.move(self._arrow.x(), max(0, self._arr_orig - dy))

    def mouseReleaseEvent(self, ev) -> None:
        if not self._dragging: return
        self._dragging = False
        if self._arrow.y() < self.height() // 3:
            self._unlock()
        else:
            self._arrow.move((self.width() - self._AW) // 2, self._arr_orig)

    def keyPressEvent(self, ev) -> None:
        if ev.key() in {Qt.Key_Enter, Qt.Key_Return, Qt.Key_Space}:
            self._unlock()

    def _unlock(self) -> None:
        self._hb_timer.stop()
        self.close()
        global _desktop
        _desktop = KernelWindow()
        _desktop.show()


# ─────────────────────────────────────────────────────────────────────────────
# Desktop (KernelWindow)
# ─────────────────────────────────────────────────────────────────────────────

class KernelWindow(QMainWindow):
    """
    vLaunch desktop shell.

    Runs entirely in this subprocess.  App launching spawns grandchildren
    via _launch_vysico().  A 2 s kernel-heartbeat timer exits the whole
    desktop if the kernel process disappears.
    """

    _POLL_MS   = 2000
    _WARDEN_MS = 10_000

    def __init__(self) -> None:
        super().__init__()
        # { app_id: tracking_dict }
        self._apps: dict = {}
        self._open_wins: dict = {}

        self.setWindowTitle("vLaunch Desktop")
        self.setWindowFlags(Qt.FramelessWindowHint)

        desk = QWidget(self)
        self._desk_lay = QVBoxLayout(desk)
        self._desk_lay.setContentsMargins(10, 10, 10, 10)
        self.setCentralWidget(desk)

        self._load_icons()
        self._build_dock()

        # Timers
        QTimer(self, timeout=self._update_clock).start(1000)
        QTimer(self, timeout=self._update_wifi ).start(5000)
        QTimer(self, timeout=self._update_batt ).start(self._WARDEN_MS)
        QTimer(self, timeout=self._poll_apps  ).start(self._POLL_MS)

        # Kernel heartbeat
        self._hb = QTimer(self)
        self._hb.timeout.connect(self._check_kernel)
        self._hb.start(2000)

        self._update_clock(); self._update_wifi(); self._update_batt()
        self._set_cursor()

        # showFullScreen AFTER all widgets
        self.showFullScreen()

    # ── kernel heartbeat ──────────────────────────────────────────────────────

    def _check_kernel(self) -> None:
        if not _kernel_alive():
            print("[gui] kernel died — desktop exiting", flush=True)
            # Terminate all running apps
            for info in self._apps.values():
                try: info["proc"].terminate()
                except Exception: pass
            QApplication.quit()

    # ── cursor ────────────────────────────────────────────────────────────────

    def _set_cursor(self) -> None:
        path = get_path("source", "pointer.png")
        if not os.path.isfile(path): return
        try:
            px = QPixmap(path)
            px = px.scaled(px.width() // 5, px.height() // 5,
                           Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setCursor(QCursor(px))
        except Exception:
            pass

    # ── desktop icons ─────────────────────────────────────────────────────────

    def _load_icons(self) -> None:
        apps_dir = get_path("apps", "user_apps")
        if not os.path.isdir(apps_dir): return
        for fname in sorted(os.listdir(apps_dir)):
            if not fname.endswith(".vysico"): continue
            path = os.path.join(apps_dir, fname)
            meta = _read_meta(path)
            if meta:
                self._add_icon(meta["name"], meta["icon_bytes"], path)

    def _add_icon(self, label: str, icon_bytes: bytes | None,
                  vysico_path: str) -> None:
        lay = QVBoxLayout(); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(3)

        icon_lbl = QLabel(self)
        if icon_bytes:
            px = QPixmap()
            if px.loadFromData(icon_bytes) and not px.isNull():
                icon_lbl.setPixmap(px.scaled(56, 56, Qt.KeepAspectRatio,
                                             Qt.SmoothTransformation))
            else:
                icon_lbl.setText("🗎"); icon_lbl.setStyleSheet("font-size:36px;")
        else:
            icon_lbl.setText("🗎"); icon_lbl.setStyleSheet("font-size:36px;")

        text_lbl = QLabel(label, self)
        text_lbl.setStyleSheet("color:white;font-size:11px;")
        text_lbl.setAlignment(Qt.AlignCenter); text_lbl.setWordWrap(True)

        lay.addWidget(icon_lbl, alignment=Qt.AlignCenter)
        lay.addWidget(text_lbl)

        frame = QFrame(self); frame.setLayout(lay); frame.setFixedWidth(80)
        frame.setCursor(Qt.PointingHandCursor)
        frame.setStyleSheet(
            "QFrame:hover{background:rgba(255,255,255,20);border-radius:8px;}"
        )
        frame.mousePressEvent = lambda _ev, p=vysico_path: self._launch(p)
        self._desk_lay.insertWidget(0, frame, alignment=Qt.AlignTop | Qt.AlignLeft)

    # ── app launch ────────────────────────────────────────────────────────────

    def _launch(self, vysico_path: str) -> None:
        info = _launch_vysico(vysico_path)
        if info:
            self._apps[info["id"]] = info
            print(f"[gui] launched {info['name']!r} pid={info['pid']}", flush=True)
            self._update_dock()
        else:
            QMessageBox.critical(self, "Launch Error",
                                 f"Failed to start:\n{vysico_path}")

    # ── app poll ─────────────────────────────────────────────────────────────

    def _poll_apps(self) -> None:
        dead = [aid for aid, info in self._apps.items()
                if info["proc"].poll() is not None]
        for aid in dead:
            name = self._apps.pop(aid)["name"]
            print(f"[gui] {name!r} exited", flush=True)
        if dead:
            self._update_dock()

    # ── dock ─────────────────────────────────────────────────────────────────

    def _build_dock(self) -> None:
        self._dock = QFrame(self)
        self._dock.setFixedHeight(60)
        self._dock.setStyleSheet("background:#1e1e1e;")
        self._desk_lay.addStretch()
        self._desk_lay.addWidget(self._dock)

        self._dl = QHBoxLayout(self._dock)
        self._dl.setContentsMargins(10, 5, 10, 5)

        self._start_btn = QPushButton("⊞  Menu")
        self._start_btn.setFixedSize(100, 40)
        self._start_btn.setStyleSheet(
            "QPushButton{background:#444;color:white;border-radius:6px;font-size:13px;}"
            "QPushButton:hover{background:#555;}"
        )
        self._start_btn.clicked.connect(self._start_menu)
        self._dl.addWidget(self._start_btn)
        self._dl.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self._batt_lbl  = QLabel(); self._batt_lbl.setStyleSheet("color:white;font-size:12px;")
        self._clock_lbl = QLabel(); self._clock_lbl.setStyleSheet("color:white;font-size:13px;")
        self._wifi_lbl  = QLabel(); self._wifi_lbl.setStyleSheet("color:white;font-size:12px;")
        for w in (self._batt_lbl, self._clock_lbl, self._wifi_lbl):
            self._dl.addWidget(w)

        self._notif_lbl = QLabel("0")
        self._notif_lbl.setFixedSize(28, 28)
        self._notif_lbl.setAlignment(Qt.AlignCenter)
        self._notif_lbl.setStyleSheet(
            "QLabel{background:#e74c3c;color:white;border-radius:14px;font-weight:bold;}"
        )
        self._notif_lbl.mousePressEvent = self._toggle_notif
        self._dl.addWidget(self._notif_lbl)

        self._notif_panel = None
        self._notif_list  = None
        self._notif_count = 0

    def _update_dock(self) -> None:
        protected = {self._start_btn, self._batt_lbl,
                     self._clock_lbl, self._wifi_lbl, self._notif_lbl}
        for i in reversed(range(self._dl.count())):
            w = self._dl.itemAt(i).widget()
            if w and w not in protected:
                w.deleteLater()
        for aid, info in self._apps.items():
            btn = QPushButton(info["name"])
            btn.setFixedSize(110, 40)
            btn.setStyleSheet(
                "QPushButton{background:#444;color:white;border-radius:4px;"
                "font-size:11px;}QPushButton:hover{background:#555;}"
            )
            self._dl.insertWidget(1, btn)

    # ── applets ───────────────────────────────────────────────────────────────

    def _update_clock(self) -> None:
        n = QDateTime.currentDateTime()
        self._clock_lbl.setText(n.toString("hh:mm") + "\n" + n.toString("ddd dd MMM"))

    def _update_wifi(self) -> None:
        status = "📶 ?"
        try:
            import psutil
            status = "📶 —"
            for iface in psutil.net_if_addrs():
                if "wi-fi" in iface.lower() or "wlan" in iface.lower():
                    s = psutil.net_if_stats().get(iface)
                    status = "📶 ON" if (s and s.isup) else "📶 NC"; break
        except Exception:
            pass
        self._wifi_lbl.setText(status)

    def _update_batt(self) -> None:
        txt = ""
        try:
            import psutil
            b = psutil.sensors_battery()
            if b:
                txt = f"🔋{b.percent:.0f}%{'⚡' if b.power_plugged else ''}"
            cpu = psutil.cpu_percent(interval=0)
            txt = (txt + f"  CPU:{cpu:.0f}%").strip()
        except Exception:
            pass
        self._batt_lbl.setText(txt)

    def _toggle_notif(self, _ev) -> None:
        if self._notif_panel and self._notif_panel.isVisible():
            self._notif_panel.hide(); return
        panel = QWidget(self)
        panel.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        panel.setGeometry(self.width() - 300, 0, 300, self.height())
        panel.setStyleSheet("background:#1e1e1e;border-left:1px solid #444;")
        lay = QVBoxLayout(panel)
        hdr = QLabel("Notifications")
        hdr.setStyleSheet("color:white;font-size:14px;padding:8px;")
        lay.addWidget(hdr)
        self._notif_list = QListWidget(panel)
        self._notif_list.setStyleSheet(
            "QListWidget{background:#1e1e1e;color:#ccc;border:none;}"
            "QListWidget::item{padding:8px;border-bottom:1px solid #333;}"
        )
        lay.addWidget(self._notif_list)

        # dmesg tail from disk
        dmesg_path = get_path("var", "log", "dmesg.log")
        if os.path.isfile(dmesg_path):
            with open(dmesg_path, encoding="utf-8") as fh:
                tail = "".join(fh.readlines()[-8:])
            sep = QLabel("── dmesg ──"); sep.setStyleSheet("color:#555;font-size:10px;padding:4px;")
            lay.addWidget(sep)
            dtxt = QLabel(tail); dtxt.setStyleSheet("color:#777;font-size:10px;font-family:Consolas;padding:4px;")
            dtxt.setWordWrap(True); lay.addWidget(dtxt)

        self._notif_panel = panel; panel.show()

    # ── start menu ────────────────────────────────────────────────────────────

    def _start_menu(self) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu{background:#2c2c2c;color:white;border:1px solid #555;}"
            "QMenu::item:selected{background:#3a3a3a;}"
        )
        for label, slot in (
            ("Launchpad", self._launchpad),
            ("Shutdown",  self._shutdown),
            ("Restart",   self._restart),
        ):
            a = QAction(label, self); a.triggered.connect(slot); menu.addAction(a)
        menu.exec_(self.mapToGlobal(QPoint(10, self.height() - 50)))

    def _shutdown(self) -> None:
        for info in self._apps.values():
            try: info["proc"].terminate()
            except Exception: pass
        QApplication.quit()

    def _restart(self) -> None:
        self._shutdown()
        subprocess.Popen([sys.executable] + sys.argv, env=os.environ)

    # ── launchpad ─────────────────────────────────────────────────────────────

    def _launchpad(self) -> None:
        key = "Launchpad"
        if key in self._open_wins:
            w = self._open_wins[key]
            if hasattr(w, "raise_"):
                w.raise_(); w.activateWindow()
            return

        win = QWidget(self)
        win.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        win.setWindowTitle(key); win.setFixedSize(1280, 720)
        win.setStyleSheet("background:#f0f0f0;border-radius:12px;border:2px solid #d0d0d0;")
        sc = QApplication.desktop().screenGeometry()
        win.move((sc.width()-win.width())//2, (sc.height()-win.height())//2)

        lay = QVBoxLayout(win); lay.setContentsMargins(20, 20, 20, 20)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none;background:transparent;")
        content = QWidget(); grid = QGridLayout(content)
        grid.setAlignment(Qt.AlignTop | Qt.AlignHCenter); grid.setSpacing(28)
        self._fill_launchpad(content, grid)
        scroll.setWidget(content); lay.addWidget(scroll)

        def _close():
            win.close(); self._open_wins.pop(key, None)

        cb = QPushButton("Close Launchpad"); cb.setFixedSize(160, 40)
        cb.setStyleSheet(
            "QPushButton{background:#e74c3c;color:white;border-radius:8px;font-weight:bold;}"
            "QPushButton:hover{background:#c0392b;}"
        )
        cb.clicked.connect(_close); lay.addWidget(cb, alignment=Qt.AlignCenter)
        self._open_wins[key] = win
        win.show()

    def _fill_launchpad(self, parent: QWidget, grid: QGridLayout) -> None:
        apps_dir = get_path("apps", "user_apps")
        if not os.path.isdir(apps_dir): return
        row, col, cols = 0, 0, 6
        for fname in sorted(os.listdir(apps_dir)):
            if not fname.endswith(".vysico"): continue
            path = os.path.join(apps_dir, fname)
            meta = _read_meta(path)
            if not meta: continue

            cell = QWidget(parent); cell.setFixedSize(120, 140)
            cl   = QVBoxLayout(cell); cl.setAlignment(Qt.AlignCenter); cl.setSpacing(6)

            btn = QPushButton(); btn.setFixedSize(100, 100)
            if meta["icon_bytes"]:
                px = QPixmap()
                if px.loadFromData(meta["icon_bytes"]) and not px.isNull():
                    btn.setIcon(QIcon(px)); btn.setIconSize(QSize(80, 80))
            btn.setStyleSheet(
                "QPushButton{background:white;border-radius:14px;border:2px solid #ddd;}"
                "QPushButton:hover{background:#e8e8e8;}"
            )
            btn.clicked.connect(lambda _, p=path: (
                self._launch(p),
                self._open_wins.get("Launchpad") and self._open_wins["Launchpad"].close()
            ))

            lbl = QLabel(meta["name"]); lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("font-size:12px;color:#333;"); lbl.setWordWrap(True)

            cl.addWidget(btn); cl.addWidget(lbl)
            grid.addWidget(cell, row, col)
            col += 1
            if col >= cols: col, row = 0, row + 1


# ─────────────────────────────────────────────────────────────────────────────
# Entry point  (this runs because kernel.py spawns: python gui.py)
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"[gui] starting  kernel_pid={_KERNEL_PID}", flush=True)

    if not _kernel_alive():
        _die("Kernel process is not running — aborting GUI start.")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    lock = LockScreen()
    lock.show()

    sys.exit(app.exec_())


_desktop = None   # set by LockScreen._unlock

if __name__ == "__main__":
    main()
