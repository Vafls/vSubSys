#!/usr/bin/env python3
"""
violence_boot.py — vLaunch Bootloader v3.0
═══════════════════════════════════════════

Boot-chain (fully logged, Cyrillic-safe):
  §1  Path validation  (BASE_DIR, KERNEL_PY, Cyrillic / space safety)
  §2  Dependency check (requirements.txt → importlib probe)
  §3  Venv setup       (create .venv if absent)
  §4  Dep install      (pip install -r requirements.txt into venv)
  §5  Plugin detection (QT_QPA_PLATFORM_PLUGIN_PATH candidates)
  §6  Kernel launch    (try every QPA strategy until KERNEL_READY)
"""

import colorsys
import importlib
import importlib.util
import math
import os
import platform
import select
import socket
import subprocess
import sys
import time
import venv as _venv_mod

from PyQt5.QtCore    import Qt, QCoreApplication, QTimer, QThread, pyqtSignal
from PyQt5.QtGui     import QColor, QFont, QPainter
from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

# ─────────────────────────────────────────────────────────────────────────────
# Paths  (raw bytes repr for Cyrillic-safe logging)
# ─────────────────────────────────────────────────────────────────────────────

_HERE        = os.path.dirname(os.path.abspath(__file__))
BASE_DIR     = os.path.dirname(_HERE)
KERNEL_PY    = os.path.join(BASE_DIR, "kernel", "kernel.py")
CFG_DIR      = os.path.join(BASE_DIR, "kernel", "config")
BOOT_LOG     = os.path.join(CFG_DIR, "boot.log")
GLOBAL_CFG   = os.path.join(CFG_DIR, "global.cfg")
REQUIREMENTS = os.path.join(BASE_DIR, "requirements.txt")
VENV_DIR     = os.path.join(BASE_DIR, ".venv")

os.makedirs(CFG_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────

def _log(msg: str, indent: int = 0):
    """Write timestamped message to boot.log and stdout."""
    ts     = time.strftime("%Y-%m-%d %H:%M:%S")
    prefix = "  " * indent
    line   = f"[{ts}] {prefix}{msg}\n"
    sys.stdout.write(line)
    sys.stdout.flush()
    with open(BOOT_LOG, "a", encoding="utf-8") as fh:
        fh.write(line)


def _log_path(label: str, path: str, indent: int = 1):
    """Log a path, showing both Unicode and raw bytes (catches encoding issues)."""
    exists  = os.path.exists(path)
    status  = "✓ exists" if exists else "✗ MISSING"
    raw_enc = path.encode(sys.getfilesystemencoding(), errors="replace")
    _log(f"{label}: {path!r}  [{status}]", indent)
    if any(b > 127 for b in raw_enc):
        _log(f"  (raw bytes: {raw_enc!r})", indent + 1)


def _log_step(n: str, title: str):
    _log(f"")
    _log(f"§{n}  {title}")
    _log(f"{'─' * 60}")


def _log_ok(msg: str,  indent: int = 2): _log(f"✓  {msg}", indent)
def _log_err(msg: str, indent: int = 2): _log(f"✗  {msg}", indent)
def _log_warn(msg: str,indent: int = 2): _log(f"⚠  {msg}", indent)
def _log_sub(msg: str, indent: int = 2): _log(f"•  {msg}", indent)


# ─────────────────────────────────────────────────────────────────────────────
# §1  Path validation
# ─────────────────────────────────────────────────────────────────────────────

def step1_validate_paths(log_cb) -> bool:
    _log_step("1", "Path validation")

    log_cb("Boot-loader location:", 1)
    _log_path("  __file__", os.path.abspath(__file__), 1)
    _log_path("  BASE_DIR", BASE_DIR, 1)
    _log_path("  KERNEL_PY", KERNEL_PY, 1)
    _log_path("  REQUIREMENTS", REQUIREMENTS, 1)
    _log_path("  VENV_DIR", VENV_DIR, 1)
    _log_path("  BOOT_LOG", BOOT_LOG, 1)

    # Cyrillic / space check
    has_non_ascii = any(ord(c) > 127 for c in BASE_DIR)
    has_space     = " " in BASE_DIR

    if has_non_ascii:
        _log_warn("BASE_DIR contains non-ASCII characters (Cyrillic, etc.)", 1)
        _log("Attempting os.chdir to BASE_DIR to verify filesystem access…", 2)
        try:
            orig = os.getcwd()
            os.chdir(BASE_DIR)
            os.chdir(orig)
            _log_ok(f"os.chdir to BASE_DIR succeeded", 2)
        except Exception as exc:
            _log_err(f"os.chdir FAILED: {exc}", 2)
            return False
    else:
        _log_ok("BASE_DIR is ASCII-clean", 1)

    if has_space:
        _log_warn("BASE_DIR contains spaces — subprocess args will use list form (safe)", 1)

    # Can we find sys.executable?
    _log_path("  sys.executable", sys.executable, 1)
    try:
        r = subprocess.run(
            [sys.executable, "--version"],
            capture_output=True, text=True, timeout=5,
        )
        _log_ok(f"sys.executable runs: {r.stdout.strip() or r.stderr.strip()}", 1)
    except Exception as exc:
        _log_err(f"sys.executable test failed: {exc}", 1)
        return False

    if not os.path.isfile(KERNEL_PY):
        _log_err(f"kernel.py not found at {KERNEL_PY!r}", 1)
        return False
    _log_ok("kernel.py found", 1)
    return True


# ─────────────────────────────────────────────────────────────────────────────
# §2  Dependency check
# ─────────────────────────────────────────────────────────────────────────────

_PKG_TO_IMPORT = {
    "PyQt5":                    "PyQt5",
    "PyQtWebEngine":            "PyQt5.QtWebEngineWidgets",
    "opencv-python":            "cv2",
    "opencv-python-headless":   "cv2",
    "Pillow":                   "PIL",
    "psutil":                   "psutil",
    "requests":                 "requests",
    "prompt_toolkit":           "prompt_toolkit",
}


def step2_check_deps(log_cb) -> list:
    """Return list of missing package names (in requirements.txt)."""
    _log_step("2", "Dependency check")

    if not os.path.isfile(REQUIREMENTS):
        _log_warn(f"requirements.txt not found at {REQUIREMENTS!r}", 1)
        return []

    _log_sub(f"Reading {REQUIREMENTS!r}", 1)
    missing = []
    with open(REQUIREMENTS, encoding="utf-8") as fh:
        lines = [l.strip() for l in fh if l.strip() and not l.startswith("#")]

    for line in lines:
        pkg = line.split("==")[0].split(">=")[0].split("<=")[0].split("~=")[0].strip()
        import_name = _PKG_TO_IMPORT.get(pkg, pkg.replace("-", "_").lower())
        found = importlib.util.find_spec(import_name) is not None
        if found:
            _log_ok(f"{pkg:30s} → import '{import_name}' OK", 2)
        else:
            _log_warn(f"{pkg:30s} → import '{import_name}' MISSING", 2)
            missing.append(pkg)

    if missing:
        _log_warn(f"{len(missing)} package(s) missing in system Python", 1)
    else:
        _log_ok("All requirements found in system Python", 1)

    return missing


# ─────────────────────────────────────────────────────────────────────────────
# §3  Venv setup
# ─────────────────────────────────────────────────────────────────────────────

def _venv_python() -> str:
    if platform.system() == "Windows":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python")


def _venv_pip() -> str:
    if platform.system() == "Windows":
        return os.path.join(VENV_DIR, "Scripts", "pip.exe")
    return os.path.join(VENV_DIR, "bin", "pip")


def step3_ensure_venv(log_cb) -> bool:
    _log_step("3", "Venv setup")
    _log_path("  VENV_DIR", VENV_DIR, 1)

    vp = _venv_python()
    if os.path.isfile(vp):
        _log_ok(f"Venv already exists → {vp!r}", 1)
        # Quick smoke-test
        try:
            r = subprocess.run(
                [vp, "--version"],
                capture_output=True, text=True, timeout=8,
            )
            _log_ok(f"Venv python runs: {(r.stdout + r.stderr).strip()}", 2)
            return True
        except Exception as exc:
            _log_warn(f"Venv python smoke-test failed: {exc} — will recreate", 2)

    _log_sub("Creating venv (stdlib venv.create)…", 1)
    try:
        _venv_mod.create(VENV_DIR, with_pip=True, clear=False)
        _log_path("  venv/python", _venv_python(), 1)
        _log_ok("venv.create() succeeded", 1)
        return True
    except Exception as exc:
        _log_err(f"venv.create() failed: {exc}", 1)

    # Fallback via subprocess
    for candidate in [sys.executable, "python3", "python"]:
        _log_sub(f"Fallback: {candidate} -m venv {VENV_DIR!r}", 1)
        try:
            r = subprocess.run(
                [candidate, "-m", "venv", VENV_DIR],
                capture_output=True, text=True, timeout=60,
            )
            if r.returncode == 0:
                _log_ok(f"Venv created via {candidate!r}", 1)
                return True
            _log_err(f"rc={r.returncode}: {(r.stdout + r.stderr).strip()[-200:]}", 2)
        except FileNotFoundError:
            _log_warn(f"{candidate!r} not found", 2)
        except Exception as exc:
            _log_err(str(exc), 2)

    _log_err("Could not create venv — kernel will run with system Python", 1)
    return False


# ─────────────────────────────────────────────────────────────────────────────
# §4  Install dependencies
# ─────────────────────────────────────────────────────────────────────────────

def step4_install_deps(log_cb) -> bool:
    _log_step("4", "Install dependencies into venv")

    pip = _venv_pip()
    _log_path("  pip", pip, 1)

    if not os.path.isfile(pip):
        _log_err("pip not found in venv — skipping install", 1)
        return False

    if not os.path.isfile(REQUIREMENTS):
        _log_warn(f"requirements.txt not found — skipping install", 1)
        return True

    _log_sub(f"pip install -r {REQUIREMENTS!r}", 1)
    try:
        r = subprocess.run(
            [pip, "install", "-r", REQUIREMENTS, "--quiet"],
            capture_output=True, text=True, timeout=300,
        )
        if r.returncode == 0:
            _log_ok("pip install succeeded", 1)
            return True
        out = (r.stdout + r.stderr).strip()
        _log_err(f"pip install rc={r.returncode}", 1)
        for line in out[-600:].splitlines():
            _log(f"  pip> {line}", 2)
        return False
    except subprocess.TimeoutExpired:
        _log_err("pip install timed out (300 s)", 1)
        return False
    except Exception as exc:
        _log_err(f"pip install exception: {exc}", 1)
        return False


# ─────────────────────────────────────────────────────────────────────────────
# §5  Qt plugin-path detection
# ─────────────────────────────────────────────────────────────────────────────

def step5_find_plugin_dirs(log_cb) -> list:
    _log_step("5", "Qt plugin-path detection")
    candidates = []

    # 1. PyQt5 loaded in this process
    _log_sub("Checking PyQt5 in current process", 1)
    try:
        import PyQt5
        root = os.path.dirname(PyQt5.__file__)
        for sub in ("Qt5/plugins", "Qt/plugins", "plugins"):
            p = os.path.join(root, sub)
            if os.path.isdir(p):
                candidates.append(p)
                _log_ok(f"Found: {p!r}", 2)
    except Exception as exc:
        _log_warn(f"PyQt5 import error: {exc}", 2)

    # 2. Venv python PyQt5
    _log_sub("Asking venv python for PyQt5 location", 1)
    vp = _venv_python()
    if os.path.isfile(vp):
        try:
            out = subprocess.check_output(
                [vp, "-c",
                 "import os, PyQt5; "
                 "root=os.path.dirname(PyQt5.__file__); "
                 "subs=['Qt5/plugins','Qt/plugins','plugins'];"
                 "[print(os.path.join(root,s)) for s in subs "
                 "if os.path.isdir(os.path.join(root,s))]"],
                stderr=subprocess.DEVNULL, text=True, timeout=10,
            ).strip()
            for p in out.splitlines():
                p = p.strip()
                if p and os.path.isdir(p) and p not in candidates:
                    candidates.insert(0, p)
                    _log_ok(f"Venv: {p!r}", 2)
        except Exception as exc:
            _log_warn(f"Venv PyQt5 probe failed: {exc}", 2)
    else:
        _log_warn("Venv python not found — skipping venv probe", 2)

    # 3. site-packages
    _log_sub("Scanning site-packages", 1)
    try:
        import site
        sp_list = site.getsitepackages()[:]
        try: sp_list.append(site.getusersitepackages())
        except Exception: pass
        for sp in sp_list:
            for pkg in ("PyQt5", "PyQt6"):
                for sub in (f"{pkg}/Qt5/plugins", f"{pkg}/Qt/plugins", f"{pkg}/plugins"):
                    p = os.path.join(sp, sub)
                    if os.path.isdir(p) and p not in candidates:
                        candidates.append(p)
                        _log_ok(f"site: {p!r}", 2)
    except Exception as exc:
        _log_warn(str(exc), 2)

    # 4. System paths
    _log_sub("Checking common system paths", 1)
    for prefix in ("/usr", "/usr/local"):
        for sub in ("qt5/plugins", "qt6/plugins"):
            p = os.path.join(prefix, sub)
            if os.path.isdir(p) and p not in candidates:
                candidates.append(p)
                _log_ok(f"sys: {p!r}", 2)

    # 5. Env override
    env_pp = os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH", "").strip()
    if env_pp:
        _log_sub(f"Env QT_QPA_PLATFORM_PLUGIN_PATH={env_pp!r}", 1)
        if os.path.isdir(env_pp):
            _log_ok("Path exists — prepending", 2)
            if env_pp not in candidates:
                candidates.insert(0, env_pp)
        else:
            _log_warn("Path does NOT exist on disk", 2)

    # Deduplicate
    seen: set = set()
    result: list = []
    for c in candidates:
        r = os.path.realpath(c)
        if r not in seen:
            seen.add(r); result.append(c)

    _log(f"  Total unique plugin dirs: {len(result)}", 1)
    return result


def _build_strategies(plugin_dirs: list) -> list:
    platforms = ["xcb", "wayland", "wayland-egl", "offscreen"]
    strategies: list = [{}]   # inherit-env first

    for pp in plugin_dirs:
        strategies.append({"QT_QPA_PLATFORM_PLUGIN_PATH": pp})
        for plat in platforms:
            strategies.append({"QT_QPA_PLATFORM_PLUGIN_PATH": pp,
                                "QT_QPA_PLATFORM": plat})

    for plat in platforms:
        strategies.append({"QT_QPA_PLATFORM": plat})

    seen_fs: list = []; deduped = []
    for s in strategies:
        fs = frozenset(s.items())
        if fs not in seen_fs:
            seen_fs.append(fs); deduped.append(s)
    return deduped


# ─────────────────────────────────────────────────────────────────────────────
# §6  Crash-line detection
# ─────────────────────────────────────────────────────────────────────────────

_FAIL_TOKENS = (
    "KERNEL_PANIC", "Fatal Python error", "Segmentation fault",
    "signal SIGABRT", "Aborted",
    "QXcbConnection: Could not connect",
    "could not connect to display",
    "ModuleNotFoundError", "ImportError",
)

def _is_crash(line: str) -> bool:
    lo = line.lower()
    return any(t.lower() in lo for t in _FAIL_TOKENS)


# ─────────────────────────────────────────────────────────────────────────────
# Setup worker thread
# ─────────────────────────────────────────────────────────────────────────────

class SetupWorker(QThread):
    log_line  = pyqtSignal(str)
    finished  = pyqtSignal(bool, str, list)   # (ok, venv_python, plugin_dirs)

    def _cb(self, msg: str, _indent: int = 0):
        self.log_line.emit(msg)

    def run(self):
        ok1 = step1_validate_paths(self._cb)
        if not ok1:
            self.finished.emit(False, sys.executable, [])
            return

        step2_check_deps(self._cb)
        step3_ensure_venv(self._cb)
        step4_install_deps(self._cb)
        plugin_dirs = step5_find_plugin_dirs(self._cb)

        vp = _venv_python()
        python = vp if os.path.isfile(vp) else sys.executable
        _log(f"  Kernel will use: {python!r}", 1)
        self.finished.emit(True, python, plugin_dirs)


# ─────────────────────────────────────────────────────────────────────────────
# Misc helpers
# ─────────────────────────────────────────────────────────────────────────────

def _check_internet() -> bool:
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2); return True
    except OSError:
        return False

def _read_cfg() -> dict:
    out: dict = {}
    if os.path.isfile(GLOBAL_CFG):
        with open(GLOBAL_CFG, encoding="utf-8") as fh:
            for line in fh:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    out[k.strip()] = v.strip()
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Donut
# ─────────────────────────────────────────────────────────────────────────────

class DonutWidget(QWidget):
    W, H, PW, PH = 800, 460, 20, 20

    def __init__(self):
        super().__init__()
        self.SW=self.W//self.PW; self.SH=self.H//self.PH; self.SS=self.SW*self.SH
        self.A=self.B=self.hue=0.0; self.CHARS=".,-~:;=!*#$@"
        self.R1,self.R2,self.K2=10,20,200
        self.K1=self.SH*self.K2*3/(8*(self.R1+self.R2))
        self.output=[" "]*self.SS; self.zbuffer=[0.0]*self.SS

    @staticmethod
    def _hsv(h,s,v): return tuple(round(i*255) for i in colorsys.hsv_to_rgb(h,s,v))

    def tick(self):
        out=[" "]*self.SS; zb=[0.0]*self.SS
        cosA,sinA=math.cos(self.A),math.sin(self.A); cosB,sinB=math.cos(self.B),math.sin(self.B)
        for ti in range(0,628,10):
            for pi in range(0,628,3):
                ct=math.cos(ti);st=math.sin(ti);cp=math.cos(pi);sp=math.sin(pi)
                cx=self.R2+self.R1*ct;cy=self.R1*st
                x=cx*(cosB*cp+sinA*sinB*sp)-cy*cosA*sinB
                y=cx*(sinB*cp-sinA*cosB*sp)+cy*cosA*cosB
                z=self.K2+cosA*cx*sp+cy*sinA;ooz=1.0/z
                xp=int(self.SW/2+self.K1*ooz*x);yp=int(self.SH/2-self.K1*ooz*y)
                pos=xp+self.SW*yp
                if 0<=pos<self.SS:
                    L=(cp*ct*sinB-cosA*ct*sp-sinA*st+cosB*(cosA*st-ct*sinA*sp))
                    if ooz>zb[pos]: zb[pos]=ooz;li=max(0,int(L*8));out[pos]=self.CHARS[min(li,len(self.CHARS)-1)]
        self.output=out;self.zbuffer=zb;self.A+=0.15;self.B+=0.035;self.hue=(self.hue+0.005)%1.0
        self.update()

    def paintEvent(self,_):
        p=QPainter(self);p.setFont(QFont("Courier New",14))
        p.setPen(QColor(*self._hsv(self.hue,1,1)))
        for i in range(self.SH):
            for j in range(self.SW):
                ch=self.output[i*self.SW+j]
                p.drawText(j*self.PW+self.PW//2,i*self.PH+self.PH//2,ch)


# ─────────────────────────────────────────────────────────────────────────────
# Settings window
# ─────────────────────────────────────────────────────────────────────────────

class SettingsWindow(QWidget):
    def __init__(self, plugin_dirs, on_save, parent=None):
        super().__init__(parent)
        self._on_save=on_save; self._plugin_dirs=plugin_dirs
        self.setWindowFlags(Qt.FramelessWindowHint|Qt.Window)
        self.setFixedSize(640,500)
        self.setStyleSheet("QWidget{background:#12121e;color:white;font-size:12px;}"
                           "QLineEdit{background:#1e1e2e;border:1px solid #444;"
                           "border-radius:4px;padding:4px;color:white;}"
                           "QTextEdit{background:#0d0d1a;border:1px solid #333;"
                           "color:#aaa;font-family:Courier New;font-size:11px;}"
                           "QPushButton{border:none;border-radius:5px;padding:6px 12px;}")
        self._build(); self._center()

    def _center(self):
        geo=QApplication.desktop().screenGeometry()
        self.move((geo.width()-self.width())//2,(geo.height()-self.height())//2)

    def _build(self):
        lay=QVBoxLayout(self); lay.setContentsMargins(20,16,20,16); lay.setSpacing(10)
        trow=QHBoxLayout()
        trow.addWidget(QLabel("⚙  Bootloader Settings",styleSheet="font-size:15px;font-weight:bold;"))
        trow.addStretch()
        x=QPushButton("✕"); x.setFixedSize(26,26)
        x.setStyleSheet("background:#c0392b;color:white;"); x.clicked.connect(self.close)
        trow.addWidget(x); lay.addLayout(trow)

        lay.addWidget(QLabel("QT_QPA_PLATFORM_PLUGIN_PATH:"))
        row=QHBoxLayout()
        self._path_inp=QLineEdit()
        self._path_inp.setPlaceholderText("(auto-detect) or enter manually…")
        val=os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH","")
        if val: self._path_inp.setText(val)
        elif self._plugin_dirs: self._path_inp.setText(self._plugin_dirs[0])
        br=QPushButton("Browse…"); br.setStyleSheet("background:#444;color:white;")
        br.clicked.connect(self._browse); row.addWidget(self._path_inp); row.addWidget(br)
        lay.addLayout(row)

        lay.addWidget(QLabel("Detected candidates:"))
        det=QTextEdit(); det.setReadOnly(True); det.setFixedHeight(90)
        det.setPlainText("\n".join(self._plugin_dirs) or "None found."); lay.addWidget(det)

        lay.addWidget(QLabel("global.cfg:"))
        cv=QTextEdit(); cv.setReadOnly(True); cv.setFixedHeight(80)
        cv.setPlainText("\n".join(f"{k}={v}" for k,v in _read_cfg().items()) or "(not found)")
        lay.addWidget(cv)

        brow=QHBoxLayout()
        sv=QPushButton("✓ Apply & Close"); sv.setStyleSheet("background:#27ae60;color:white;")
        sv.clicked.connect(self._apply)
        cn=QPushButton("Cancel"); cn.setStyleSheet("background:#444;color:white;")
        cn.clicked.connect(self.close); brow.addWidget(sv); brow.addWidget(cn)
        lay.addLayout(brow)

    def _browse(self):
        d=QFileDialog.getExistingDirectory(self,"Qt plugins folder")
        if d: self._path_inp.setText(d)

    def _apply(self): self._on_save(self._path_inp.text().strip()); self.close()

    def mousePressEvent(self,ev):
        if ev.button()==Qt.LeftButton: self._dp=ev.globalPos()
    def mouseMoveEvent(self,ev):
        if hasattr(self,"_dp"):
            self.move(self.pos()+(ev.globalPos()-self._dp)); self._dp=ev.globalPos()


# ─────────────────────────────────────────────────────────────────────────────
# Main bootloader window
# ─────────────────────────────────────────────────────────────────────────────

class BootApp(QWidget):
    POLL_MS          = 300
    TIMEOUT_S        = 15
    LIVENESS_MS      = 2000

    def __init__(self):
        super().__init__()
        self._attempt=0; self._proc=None; self._poll_t=None
        self._aborted=False; self._deadline=0.0
        self._settings_win=None; self._kernel_python=sys.executable
        self._strategies=[]; self._plugin_dirs=[]; self._setup_done=False

        self._build_ui()

        _log("\n" + "═"*70)
        _log("vLaunch Bootloader v3.0  starting")
        _log("═"*70)
        _log(f"  boot path : {os.path.abspath(__file__)!r}")
        _log(f"  BASE_DIR  : {BASE_DIR!r}")
        _log(f"  internet  : {'yes' if _check_internet() else 'NO'}")

        self._run_setup()

    def _build_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setFixedSize(800,900); self._center()
        self.setStyleSheet("background:#0d0d1a;")
        main=QVBoxLayout(self); main.setContentsMargins(0,0,0,0); main.setSpacing(0)

        self._donut=DonutWidget(); self._donut.setFixedSize(800,460)
        main.addWidget(self._donut)

        self._console=QTextEdit(); self._console.setReadOnly(True)
        self._console.setFont(QFont("Courier New",9))
        self._console.setStyleSheet("background:#0d0d1a;color:#00ff88;border:none;padding:4px;")
        self._console.setFixedHeight(345); main.addWidget(self._console)

        row=QHBoxLayout(); row.setContentsMargins(6,4,6,6); row.setSpacing(6)
        self._inp=QLineEdit(); self._inp.setFont(QFont("Courier New",11))
        self._inp.setFixedHeight(36)
        self._inp.setStyleSheet("background:#111;color:#00ff88;border:1px solid #333;padding:4px;")
        self._inp.setPlaceholderText("boot>  (start | settings | log | retry | quit)")
        self._inp.mousePressEvent=self._on_inp_click
        self._inp.returnPressed.connect(self._on_cmd); row.addWidget(self._inp)
        cfg=QPushButton("⚙"); cfg.setFixedSize(36,36)
        cfg.setStyleSheet("QPushButton{background:#333;color:white;border:none;"
                          "font-size:16px;border-radius:4px;}"
                          "QPushButton:hover{background:#555;}")
        cfg.clicked.connect(self._open_settings); row.addWidget(cfg)
        main.addLayout(row)

        self._anim_t=QTimer(self); self._anim_t.timeout.connect(self._donut.tick)
        self._anim_t.start(1000//60)

    def _center(self):
        geo=QApplication.desktop().screenGeometry()
        self.move((geo.width()-self.width())//2,(geo.height()-self.height())//2)

    def _print(self, msg: str):
        self._console.append(msg)
        # _log already called from step functions; only emit here for UI feedback lines
        _log(msg)

    def _run_setup(self):
        self._print("Running boot-chain in background…")
        self._worker=SetupWorker()
        self._worker.log_line.connect(lambda m: self._console.append(m))
        self._worker.finished.connect(self._on_setup_done)
        self._worker.start()

    def _on_setup_done(self, ok: bool, python: str, plugin_dirs: list):
        self._kernel_python=python; self._plugin_dirs=plugin_dirs
        self._strategies=_build_strategies(plugin_dirs)
        _log_step("6", "Kernel launch")
        _log(f"  python: {python!r}", 1)
        _log(f"  strategies: {len(self._strategies)}", 1)
        self._setup_done=True
        self._print(f"Setup done — {len(self._strategies)} launch strategies — starting kernel…")
        self._launch_next()

    def _on_inp_click(self, ev): QLineEdit.mousePressEvent(self._inp, ev)

    def _on_cmd(self):
        cmd=self._inp.text().strip().lower(); self._inp.clear()
        if cmd in ("start","boot"):
            if not self._setup_done: self._print("Setup still running…"); return
            self._attempt=0; self._aborted=False; self._launch_next()
        elif cmd=="settings": self._open_settings()
        elif cmd=="log":
            try: self._console.append(open(BOOT_LOG,encoding="utf-8").read()[-4000:])
            except Exception as e: self._print(str(e))
        elif cmd=="retry":
            self._kill_proc(); self._attempt=0; self._aborted=False
            self._print("Retrying…"); self._launch_next()
        elif cmd in ("q","quit","exit"): QCoreApplication.quit()
        else: self._print(f"Unknown: {cmd!r}")

    def _open_settings(self):
        def _on_save(path):
            if path and os.path.isdir(path):
                if path not in self._plugin_dirs: self._plugin_dirs.insert(0,path)
                os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"]=path
                self._strategies=_build_strategies(self._plugin_dirs)
                self._attempt=0
                _log(f"Plugin path updated by user: {path!r}")
                self._print(f"Plugin path set: {path}")
            elif path: self._print(f"WARNING: not a directory: {path!r}")
        if self._settings_win and self._settings_win.isVisible():
            self._settings_win.raise_(); return
        self._settings_win=SettingsWindow(self._plugin_dirs,_on_save,parent=self)
        self._settings_win.show()

    def _launch_next(self):
        if self._aborted or not self._setup_done: return
        if self._attempt>=len(self._strategies): self._all_failed(); return

        strategy=self._strategies[self._attempt]; self._attempt+=1

        env=os.environ.copy(); env.update(strategy)
        env["VLAUNCH_HOME"]=BASE_DIR; env["_VLAUNCH_STARTED"]="0"

        changed={k:v for k,v in strategy.items() if os.environ.get(k)!=v}
        desc="  ".join(f"{k}={v}" for k,v in changed.items()) or "inherit env"

        _log(f"  [{self._attempt}/{len(self._strategies)}]  {desc}", 1)
        self._console.append(f"  [{self._attempt}/{len(self._strategies)}]  {desc}")

        python=self._kernel_python if os.path.isfile(self._kernel_python) else sys.executable
        _log(f"  Spawning: {python!r} {KERNEL_PY!r} -auth8354", 2)

        try:
            self._proc=subprocess.Popen(
                [python, KERNEL_PY, "-auth8354"],
                env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
            _log(f"  PID={self._proc.pid}", 2)
        except Exception as exc:
            _log_err(f"Popen failed: {exc}", 2)
            self._console.append(f"  ✗ Popen error: {exc}")
            QTimer.singleShot(300, self._launch_next); return

        self._deadline=time.time()+self.TIMEOUT_S
        if self._poll_t: self._poll_t.stop()
        self._poll_t=QTimer(self); self._poll_t.timeout.connect(self._poll)
        self._poll_t.start(self.POLL_MS)

    def _poll(self):
        if not self._proc: return
        try:
            rlist,_,_=select.select([self._proc.stdout],[],[],0)
            if rlist:
                line=self._proc.stdout.readline().rstrip()
                if line:
                    _log(f"  kernel> {line}", 3)
                    if "KERNEL_READY" in line:
                        self._poll_t.stop()
                        _log_ok("KERNEL_READY received — confirming liveness…", 2)
                        self._console.append("  KERNEL_READY — confirming liveness…")
                        QTimer.singleShot(self.LIVENESS_MS, self._confirm)
                        return
                    if _is_crash(line):
                        _log_err(f"Crash signal: {line}", 2)
                        self._console.append(f"  ✗ {line}")
                        self._poll_t.stop(); self._kill_proc()
                        QTimer.singleShot(300, self._launch_next); return
        except Exception: pass

        rc=self._proc.poll()
        if rc is not None:
            _log_err(f"Process exited rc={rc} before KERNEL_READY", 2)
            self._console.append(f"  ✗ exited rc={rc}")
            self._poll_t.stop(); QTimer.singleShot(200, self._launch_next); return

        if time.time()>self._deadline:
            if self._proc.poll() is None:
                _log_warn("Timeout but process alive — assuming OK", 2)
                self._console.append("  ⚠ timeout but process alive — assuming OK")
                self._poll_t.stop(); self._on_success()
            else:
                _log_err("Timeout + dead", 2)
                self._poll_t.stop(); QTimer.singleShot(200, self._launch_next)

    def _confirm(self):
        rc=self._proc.poll() if self._proc else -1
        if rc is None:
            _log_ok("Liveness confirmed → SUCCESS", 2)
            self._on_success()
        else:
            _log_err(f"Process died after KERNEL_READY rc={rc}", 2)
            self._console.append(f"  ✗ died after KERNEL_READY rc={rc}")
            self._kill_proc(); QTimer.singleShot(200, self._launch_next)

    def _kill_proc(self):
        if self._proc and self._proc.poll() is None:
            try: self._proc.terminate(); _log("  process terminated", 2)
            except Exception: pass
        self._proc=None

    def _on_success(self):
        _log("✓ BOOT_SUCCESS")
        self._console.append("✓  Kernel running — bootloader exiting.")
        self._aborted=True; QTimer.singleShot(600, QCoreApplication.quit)

    def _all_failed(self):
        _log("✗ BOOT_FAILURE: all strategies exhausted")
        self._console.append(
            f"\n✗  All {len(self._strategies)} strategies failed.\n"
            f"   Full log: {BOOT_LOG!r}\n\n"
            f"Manual:\n"
            f"  env QT_QPA_PLATFORM=xcb {self._kernel_python!r} {KERNEL_PY!r} --gui=1\n"
            f"  {self._kernel_python!r} {KERNEL_PY!r} --gui=0   ← TTY mode\n"
            "  Open ⚙ to set plugin path manually, then type 'retry'."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if not os.path.isfile(KERNEL_PY):
        print(f"BOOT ERROR: kernel not found: {KERNEL_PY!r}")
        sys.exit(1)
    app=QApplication(sys.argv)
    win=BootApp(); win.show()
    sys.exit(app.exec_())

if __name__=="__main__":
    main()
