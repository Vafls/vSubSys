"""
violence_sysinit.py  —  vLaunch system initializer + GUI bridge
════════════════════════════════════════════════════════════════
Two responsibilities:

  1. SystemInit  — creates sandbox directories and default .vysico packages
                   on first boot.  Called by Kernel.boot().

  2. GuiBridge   — the ONLY authorised path from kernel.py to gui.py.
                   kernel.py calls GuiBridge(kernel).launch() instead of
                   importing gui.py directly, so the bridge acts as the
                   logical and security boundary between the kernel and the
                   graphical shell.

Flow:
    kernel.py  ──►  GuiBridge(kernel).launch()
                         │
                         ├─ validates session token
                         ├─ creates QApplication
                         ├─ imports gui (injecting kernel + BASE_DIR + token)
                         ├─ creates LockScreen(kernel)
                         └─ enters Qt event loop
"""

import io
import importlib
import os
import sys
import time
import zipfile

# Injected by kernel.py at module-load time
BASE_DIR: str = os.environ.get("VLAUNCH_HOME") or os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)


def get_path(*p: str) -> str:
    return os.path.join(BASE_DIR, *p)


# ─────────────────────────────────────────────────────────────────────────────
# GUI Bridge
# ─────────────────────────────────────────────────────────────────────────────

class GuiBridge:
    """
    Authorised bridge from kernel.py to gui.py.

    Usage (inside kernel.py's _start_gui):
        sysinit_mod = kernel.load_module("violence_sysinit")
        sysinit_mod.GuiBridge(kernel).launch()
    """

    def __init__(self, kernel):
        self._kernel = kernel

    def launch(self) -> None:
        """
        Validate the session, create the Qt application, inject the kernel
        into gui.py, and start the event loop.
        Raises RuntimeError if the session token is invalid.
        """
        # ── 1. Token validation ───────────────────────────────────────────────
        token_file = get_path("var", "run", "ktoken")
        env_token  = os.environ.get("_VLAUNCH_TOKEN", "")

        if not os.path.isfile(token_file):
            raise RuntimeError("GuiBridge: session token missing — kernel not running")

        with open(token_file) as fh:
            stored = fh.read().strip()

        if not env_token or env_token != stored:
            raise RuntimeError("GuiBridge: token mismatch — GUI launch rejected")

        # ── 2. Qt setup ───────────────────────────────────────────────────────
        try:
            from PyQt5.QtWidgets import QApplication
        except ImportError:
            raise RuntimeError("GuiBridge: PyQt5 not installed")

        import signal
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        # Mark the env so gui.py's launch guard passes
        os.environ["_VLAUNCH_STARTED"] = "1"
        os.environ["_VLAUNCH_GUI"]      = "1"

        # ── 3. Import gui.py ──────────────────────────────────────────────────
        kernel_dir = os.path.dirname(os.path.abspath(__file__))
        gui_path   = os.path.join(kernel_dir, "gui.py")

        if not os.path.isfile(gui_path):
            raise RuntimeError(f"GuiBridge: gui.py not found at {gui_path!r}")

        spec    = importlib.util.spec_from_file_location("gui", gui_path)
        gui_mod = importlib.util.module_from_spec(spec)

        # Inject kernel context BEFORE exec_module so gui.py can use them
        # at module level (e.g. during class definitions that call get_path)
        gui_mod.BASE_DIR = BASE_DIR
        gui_mod.get_path = get_path
        gui_mod.KERNEL   = self._kernel

        spec.loader.exec_module(gui_mod)

        # ── 4. Qt event loop ──────────────────────────────────────────────────
        app = QApplication.instance() or QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)

        lock = gui_mod.LockScreen(self._kernel)
        lock.show()

        sys.exit(app.exec_())


# ─────────────────────────────────────────────────────────────────────────────
# vrun templates (embedded in every system .vysico package)
# ─────────────────────────────────────────────────────────────────────────────

# Shared title-bar helper — no parent arg so addWidget() reparents correctly
_TBAR = r'''
def _tbar(title, win, on_close):
    from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
    from PyQt5.QtCore import Qt
    bar = QWidget()
    bar.setFixedHeight(30)
    bar.setStyleSheet("background:#1a1a1a;")
    L = QHBoxLayout(bar); L.setContentsMargins(8, 0, 0, 0)
    lbl = QLabel(title); lbl.setStyleSheet("color:white;font-size:12px;")
    L.addWidget(lbl); L.addStretch()
    for t, s, c in (
        ("−", win.showMinimized,        "background:#333;color:white;border:none;"),
        ("□", lambda: win.showNormal() if win.isMaximized() else win.showMaximized(),
                                         "background:#333;color:white;border:none;"),
        ("✕", on_close,                  "background:#c0392b;color:white;border:none;"),
    ):
        b = QPushButton(t); b.setFixedSize(30, 30); b.setStyleSheet(c)
        b.clicked.connect(s); L.addWidget(b)
    bar._dp = None
    def _p(e):
        if e.button() == Qt.LeftButton: bar._dp = e.globalPos()
    def _m(e):
        if bar._dp:
            win.move(win.pos() + (e.globalPos() - bar._dp)); bar._dp = e.globalPos()
    bar.mousePressEvent = _p; bar.mouseMoveEvent = _m
    return bar
'''

# Close-once pattern:
#   • win.hide()  →  visual disappear immediately
#   • APP_CLOSE_CALLBACK  →  kernel repacks + cleans temp
#   • QApplication.quit() →  subprocess/event-loop exits
_CLOSE = r'''
from PyQt5.QtWidgets import QApplication as _QApp

_closed = [False]

def _on_close():
    if _closed[0]: return
    _closed[0] = True
    try: win.hide()
    except Exception: pass
    if _close:
        try: _close(_aid)
        except Exception: pass
    _QApp.quit()

def _accept_close(e):
    e.accept()
    if not _closed[0]:
        _closed[0] = True
        if _close:
            try: _close(_aid)
            except Exception: pass
        _QApp.quit()
'''

# ── Per-app vrun bodies ───────────────────────────────────────────────────────

TERMINAL_VRUN = _TBAR + _CLOSE + r'''
import os, getpass
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt

_par    = globals().get("PARENT_WINDOW")
_close  = globals().get("APP_CLOSE_CALLBACK")
_aid    = globals().get("APP_ID", "")
_home   = globals().get("HOME_DIR", os.path.expanduser("~"))
_kern   = globals().get("KERNEL")
_appdir = globals().get("APP_DIR", "")
cwd     = [_home]; su = [False]

win = QWidget(_par)
win.setWindowFlags(Qt.FramelessWindowHint)
win.setWindowTitle("Terminal"); win.setGeometry(300, 300, 800, 560)
win.setStyleSheet("background:black;color:#00ff00;font-family:Consolas;font-size:12px;")
lay = QVBoxLayout(win); lay.setContentsMargins(4, 4, 4, 4); lay.setSpacing(4)
lay.addWidget(_tbar("Terminal", win, _on_close))
out = QLabel("vLaunch Terminal  |  type 'help'\n")
out.setStyleSheet("color:#00ff00;padding:4px;"); out.setWordWrap(True)
out.setAlignment(Qt.AlignTop | Qt.AlignLeft)
inp = QLineEdit()
inp.setStyleSheet("background:#002200;color:#00ff00;border:1px solid #00aa00;")
lay.addWidget(out); lay.addWidget(inp)

def _sandbox(path):
    full = os.path.normpath(os.path.join(cwd[0], path))
    return full if full.startswith(_home) else None

def _run(cmd):
    p2 = cmd.split(None, 1); verb = p2[0].lower(); arg = p2[1] if len(p2) > 1 else ""
    if verb == "help":
        return "help  exit  clear  whoami  pwd  cd  ls  su" + (
            "\n[su] del <file>" if su[0] else "")
    if verb == "exit":   _on_close(); return ""
    if verb == "clear":  out.setText(""); return ""
    if verb == "whoami":
        if _kern: return _kern.get_cfg("profile_1_name", "user")
        return getpass.getuser()
    if verb == "pwd": return cwd[0]
    if verb == "cd":
        t = _sandbox(arg or _home)
        if t and os.path.isdir(t): cwd[0] = t; return f"→ {cwd[0]}"
        return "Not found or access denied"
    if verb == "ls":
        try: return "  ".join(os.listdir(cwd[0])) or "(empty)"
        except Exception as e: return str(e)
    if verb == "su":
        from PyQt5.QtWidgets import QInputDialog, QLineEdit as _QL
        correct = _kern.get_cfg("profile_1_pass") if _kern else ""
        pw, ok = QInputDialog.getText(win, "Auth", "Password:", _QL.Password)
        if ok and pw == correct: su[0] = True; return "Superuser activated"
        return "Authentication failed"
    if verb == "del":
        if not su[0]: return "su first"
        t = _sandbox(arg)
        if t and os.path.isfile(t): os.remove(t); return f"Deleted: {t}"
        return "Not found or access denied"
    return f"Unknown: {verb}"

def _exec():
    cmd = inp.text().strip(); inp.clear()
    if not cmd: return
    out.setText(out.text() + f"\n{cwd[0]}> {cmd}")
    r = _run(cmd)
    if r: out.setText(out.text() + "\n" + r)

inp.returnPressed.connect(_exec)
win.closeEvent = _accept_close
win.show()

def on_program_exit(): pass
'''

SETTINGS_VRUN = _TBAR + _CLOSE + r'''
import os, sys, platform
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt

_par   = globals().get("PARENT_WINDOW")
_close = globals().get("APP_CLOSE_CALLBACK")
_aid   = globals().get("APP_ID", "")
_kern  = globals().get("KERNEL")

win = QWidget(_par)
win.setWindowFlags(Qt.FramelessWindowHint)
win.setWindowTitle("Settings"); win.setGeometry(300, 200, 820, 560)
win.setStyleSheet("background:white;")
ml = QVBoxLayout(win); ml.setContentsMargins(0, 0, 0, 0)
ml.addWidget(_tbar("Settings", win, _on_close))
body = QHBoxLayout(); ml.addLayout(body)
sidebar = QVBoxLayout(); sidebar.setContentsMargins(0, 0, 0, 0); sidebar.setSpacing(2)
content = QWidget(); content_lay = QVBoxLayout(content)
sw = QWidget(); sw.setLayout(sidebar); sw.setFixedWidth(200)
sw.setStyleSheet("background:#f0f0f0;"); body.addWidget(sw); body.addWidget(content)

def _clr():
    for i in reversed(range(content_lay.count())):
        w = content_lay.itemAt(i).widget()
        if w: w.setParent(None)

def _sysinfo():
    import psutil
    _clr(); parts = []
    for p in psutil.disk_partitions():
        try:
            u = psutil.disk_usage(p.mountpoint)
            parts.append(f"{p.device}  {u.total//(1024**3)} GB  free: {u.free//(1024**3)} GB")
        except: parts.append(f"{p.device} (no access)")
    if _kern:
        snap = _kern.warden_tick()
        parts += ["",
                  f"Kernel:   {_kern.get_cfg('sys_version', _kern.VERSION)}",
                  f"CPU:      {snap['cpu_pct']:.1f}%",
                  f"RAM:      {snap['ram_used_mb']:.0f}/{snap['ram_total_mb']:.0f} MB",
                  f"Disk (sandbox): {snap['disk_used_mb']:.1f} MB",
                  f"Python:   {sys.version.split()[0]}",
                  f"Platform: {platform.system()} {platform.release()}"]
    lbl = QLabel("\n".join(parts)); lbl.setStyleSheet("font-size:13px;padding:12px;")
    lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
    content_lay.addWidget(lbl); content_lay.addStretch()

def _users():
    _clr()
    if not _kern:
        content_lay.addWidget(QLabel("No kernel connection")); return
    for u in _kern.users().list_users():
        g = ", ".join(u["groups"]) or "-"
        lbl = QLabel(f"  {u['name']:20s}  uid={u['uid']:4d}  groups: {g}")
        lbl.setStyleSheet("font-size:12px; font-family: Consolas;")
        content_lay.addWidget(lbl)
    content_lay.addStretch()

bst = ("QPushButton{padding:10px 16px;background:#f5f5f5;border:none;"
       "text-align:left;font-size:13px;}QPushButton:hover{background:#e0e0e0;}")
for lbl2, slot in (("System Info", _sysinfo), ("Users", _users)):
    b = QPushButton(lbl2, sw); b.setStyleSheet(bst); b.clicked.connect(slot)
    sidebar.addWidget(b)
sidebar.addStretch(); _sysinfo()
win.closeEvent = _accept_close
win.show()

def on_program_exit(): pass
'''

SNAKE_VRUN = _TBAR + _CLOSE + r'''
import random
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import *

_par   = globals().get("PARENT_WINDOW")
_close = globals().get("APP_CLOSE_CALLBACK")
_aid   = globals().get("APP_ID", "")

GW, GH, BLK = 1000, 660, 20
win = QWidget(_par)
win.setWindowFlags(Qt.FramelessWindowHint)
win.setWindowTitle("Snake"); win.setFixedSize(GW, GH)
win.setStyleSheet("background:black;")
lay = QVBoxLayout(win); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(0)
lay.addWidget(_tbar("Snake", win, _on_close))
canvas = QLabel(); canvas.setStyleSheet("background:black;"); lay.addWidget(canvas)
TH = 30
st = dict(body=[[GW//2, GH//2]], length=1, dx=0, dy=0,
          fx=random.randint(0,(GW//BLK)-1)*BLK,
          fy=random.randint(0,((GH-TH)//BLK)-1)*BLK, timer=None)

def _draw():
    px = QPixmap(canvas.size()); px.fill(Qt.black); p = QPainter(px)
    for sx, sy in st["body"]: p.fillRect(sx, sy, BLK, BLK, Qt.green)
    p.fillRect(st["fx"], st["fy"], BLK, BLK, Qt.red); p.end(); canvas.setPixmap(px)

def _reset():
    st.update(body=[[GW//2, GH//2]], length=1, dx=0, dy=0,
              fx=random.randint(0,(GW//BLK)-1)*BLK,
              fy=random.randint(0,(canvas.height()//BLK)-1)*BLK)
    st["timer"].start(100)

def _tick():
    hx = st["body"][-1][0]+st["dx"]; hy = st["body"][-1][1]+st["dy"]
    ch = canvas.height()
    if hx<0 or hx>=GW or hy<0 or hy>=ch:
        st["timer"].stop(); QMessageBox.information(win,"Game Over","You lost!"); _reset(); return
    st["body"].append([hx,hy])
    if len(st["body"])>st["length"]: st["body"].pop(0)
    if [hx,hy] in st["body"][:-1]:
        st["timer"].stop(); QMessageBox.information(win,"Game Over","You lost!"); _reset(); return
    if hx==st["fx"] and hy==st["fy"]:
        st["length"]+=1
        st["fx"]=random.randint(0,(GW//BLK)-1)*BLK
        st["fy"]=random.randint(0,(ch//BLK)-1)*BLK
    _draw()

def _key(ev):
    k=ev.key()
    if   k==Qt.Key_Left  and st["dx"]==0: st.update(dx=-BLK,dy=0)
    elif k==Qt.Key_Right and st["dx"]==0: st.update(dx=BLK, dy=0)
    elif k==Qt.Key_Up    and st["dy"]==0: st.update(dx=0,  dy=-BLK)
    elif k==Qt.Key_Down  and st["dy"]==0: st.update(dx=0,   dy=BLK)

t = QTimer(win); t.timeout.connect(_tick); t.start(100); st["timer"] = t
win.setFocusPolicy(Qt.StrongFocus); win.keyPressEvent = _key
win.closeEvent = _accept_close
win.show()

def on_program_exit():
    if st["timer"]: st["timer"].stop()
'''

STORE_VRUN = _TBAR + _CLOSE + r'''
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt

_par   = globals().get("PARENT_WINDOW")
_close = globals().get("APP_CLOSE_CALLBACK")
_aid   = globals().get("APP_ID", "")

win = QWidget(_par)
win.setWindowFlags(Qt.FramelessWindowHint)
win.setWindowTitle("App Store"); win.setGeometry(300, 200, 800, 560)
win.setStyleSheet("background:white;")
lay = QVBoxLayout(win); lay.setContentsMargins(0, 0, 0, 0)
lay.addWidget(_tbar("App Store", win, _on_close))
search = QLineEdit(); search.setPlaceholderText("Search apps…")
search.setStyleSheet("padding:6px;font-size:13px;border:1px solid #ccc;margin:8px;")
lay.addWidget(search)
app_list = QListWidget(); stacked = QStackedWidget(); stacked.addWidget(app_list)
for i in range(1, 11): app_list.addItem(QListWidgetItem(f"App {i}"))

def _details(item):
    w = QWidget(); il = QVBoxLayout(w)
    back = QPushButton("← Back"); back.setFixedSize(80, 36)
    back.clicked.connect(lambda: stacked.setCurrentWidget(app_list))
    il.addWidget(back, alignment=Qt.AlignLeft)
    il.addWidget(QLabel(f"Description of {item.text()}"), alignment=Qt.AlignCenter)
    dl = QPushButton("Download")
    dl.setStyleSheet("background:#6272a4;color:white;border:none;padding:8px;border-radius:6px;")
    il.addWidget(dl, alignment=Qt.AlignCenter)
    stacked.addWidget(w); stacked.setCurrentWidget(w)

app_list.itemClicked.connect(_details); lay.addWidget(stacked)
win.closeEvent = _accept_close
win.show()

def on_program_exit(): pass
'''

CAMERA_VRUN = _TBAR + _CLOSE + r'''
import os, time
try: import cv2; _CV = True
except ImportError: _CV = False

from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import *

_par    = globals().get("PARENT_WINDOW")
_close  = globals().get("APP_CLOSE_CALLBACK")
_aid    = globals().get("APP_ID", "")
_home   = globals().get("HOME_DIR", os.path.expanduser("~"))
_kern   = globals().get("KERNEL")
_appdir = globals().get("APP_DIR", "")

_base = os.environ.get("VLAUNCH_HOME") or (
    os.path.normpath(os.path.join(_appdir,"..","..","..")) if _appdir else "")

def _cfg(xml):
    if _kern and hasattr(_kern,"get_path"): return _kern.get_path("kernel","config",xml)
    return os.path.join(_base,"kernel","config",xml) if _base else ""

recording=[False]; video_writer=[None]; tracking=[False]
cap = cv2.VideoCapture(0) if _CV else None
face_cc = cv2.CascadeClassifier(_cfg("haarcascade_frontalface_default.xml")) if _CV else None
hand_cc_path = _cfg("haarcascade_hand.xml")
hand_cc = cv2.CascadeClassifier(hand_cc_path) if (_CV and os.path.isfile(hand_cc_path)) else None

win = QWidget(_par)
win.setWindowFlags(Qt.FramelessWindowHint)
win.setWindowTitle("Camera"); win.setGeometry(300, 200, 840, 600)
win.setStyleSheet("background:white;")
lay = QVBoxLayout(win); lay.setContentsMargins(0, 0, 0, 0)
lay.addWidget(_tbar("Camera", win, _on_close))
video_lbl = QLabel()
if not _CV: video_lbl.setText("cv2 not installed"); video_lbl.setAlignment(Qt.AlignCenter)
lay.addWidget(video_lbl)
btn_row = QHBoxLayout()
snap_btn=QPushButton("📷 Photo"); rec_btn=QPushButton("⏺ Record"); trk_btn=QPushButton("👁 Off")
for b in (snap_btn,rec_btn,trk_btn): btn_row.addWidget(b)
lay.addLayout(btn_row)

def _frame():
    if not _CV or cap is None: return
    ret,frame=cap.read()
    if ret:
        if tracking[0]:
            gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
            if face_cc:
                for x,y,w,h in face_cc.detectMultiScale(gray,1.1,4):
                    cv2.rectangle(frame,(x,y),(x+w,y+h),(255,0,0),2)
            if hand_cc:
                for x,y,w,h in hand_cc.detectMultiScale(gray,1.1,4):
                    cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),2)
        rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB); h2,w2,ch=rgb.shape
        video_lbl.setPixmap(QPixmap.fromImage(QImage(rgb.data,w2,h2,ch*w2,QImage.Format_RGB888)))
        if recording[0] and video_writer[0]: video_writer[0].write(frame)
    QTimer.singleShot(10,_frame)

def _snap():
    if not _CV or cap is None: return
    ret,frame=cap.read()
    if ret: cv2.imwrite(os.path.join(_home,f"snapshot_{int(time.time())}.png"),frame)

def _rec():
    if not _CV or cap is None: return
    if not recording[0]:
        fn=os.path.join(_home,f"video_{int(time.time())}.avi")
        video_writer[0]=cv2.VideoWriter(fn,cv2.VideoWriter_fourcc(*"XVID"),20.,
                                        (int(cap.get(3)),int(cap.get(4))))
        recording[0]=True; rec_btn.setText("⏹ Stop")
    else:
        recording[0]=False; video_writer[0].release(); video_writer[0]=None
        rec_btn.setText("⏺ Record")

def _trk():
    tracking[0]=not tracking[0]; trk_btn.setText("👁 On" if tracking[0] else "👁 Off")

snap_btn.clicked.connect(_snap); rec_btn.clicked.connect(_rec); trk_btn.clicked.connect(_trk)
win.closeEvent = _accept_close
if _CV: _frame()
win.show()

def on_program_exit():
    if _CV and cap: cap.release()
    if recording[0] and video_writer[0]: video_writer[0].release()
'''

BROWSER_VRUN = _TBAR + _CLOSE + r'''
import webbrowser as _wb
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QUrl

_par   = globals().get("PARENT_WINDOW")
_close = globals().get("APP_CLOSE_CALLBACK")
_aid   = globals().get("APP_ID", "")

_WE = False
try:
    import os; os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX","1")
    from PyQt5.QtWebEngineWidgets import QWebEngineView; _WE = True
except Exception: pass

if not _WE:
    msg=QMessageBox(); msg.setWindowTitle("Browser unavailable")
    msg.setText("QtWebEngine not available.\nOpen system browser?")
    msg.setStandardButtons(QMessageBox.Yes|QMessageBox.No)
    if msg.exec_()==QMessageBox.Yes: _wb.open("https://www.google.com")
else:
    win=QMainWindow(_par); win.setWindowFlags(Qt.FramelessWindowHint)
    win.setWindowTitle("V-Browser"); win.setGeometry(300,150,1100,740)
    tabs=QTabWidget(); tabs.setDocumentMode(True); tabs.setTabsClosable(True)
    win.setCentralWidget(tabs)
    navtb=QToolBar("Nav"); url_bar=QLineEdit(); win.addToolBar(navtb)
    def _cur(): return tabs.currentWidget()
    def _upd(u,b=None):
        if b is None or b is _cur(): url_bar.setText(u.toString()); url_bar.setCursorPosition(0)
    def _add(qurl=None,label="Blank"):
        if not isinstance(qurl,QUrl): qurl=QUrl("")
        b=QWebEngineView(); b.setUrl(qurl); i=tabs.addTab(b,label); tabs.setCurrentIndex(i)
        b.urlChanged.connect(lambda u,_b=b:_upd(u,_b))
        b.loadFinished.connect(lambda _,ii=i,_b=b:tabs.setTabText(ii,_b.page().title()))
    def _nav():
        url=url_bar.text()
        if not url.startswith("http"): url="http://"+url
        _cur().setUrl(QUrl(url))
    tabs.tabCloseRequested.connect(lambda i: tabs.removeTab(i) if tabs.count()>1 else None)
    tabs.currentChanged.connect(lambda _:_upd(_cur().url(),_cur()) if _cur() else None)
    url_bar.returnPressed.connect(_nav)
    ha=QAction("🏠",win); ha.triggered.connect(lambda:_cur().setUrl(QUrl("https://www.google.com")))
    na=QAction("＋",win); na.triggered.connect(_add)
    navtb.addAction(ha); navtb.addAction(na); navtb.addWidget(url_bar)
    _tw=QWidget(); _tl_=QHBoxLayout(_tw); _tl_.setContentsMargins(4,0,0,0)
    _tl_.addWidget(QLabel("V-Browser",styleSheet="color:white;font-size:12px;")); _tl_.addStretch()
    _xb=QPushButton("✕"); _xb.setFixedSize(30,30)
    _xb.setStyleSheet("background:#c0392b;color:white;border:none;")
    _xb.clicked.connect(_on_close); _tl_.addWidget(_xb); navtb.addWidget(_tw)
    _add(QUrl("https://www.google.com"),"Homepage")
    win.closeEvent=_accept_close; win.show()

def on_program_exit(): pass
'''

IDE_VRUN = _TBAR + _CLOSE + r'''
import os, zipfile
from PyQt5.QtWidgets import *
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont

_par    = globals().get("PARENT_WINDOW")
_close  = globals().get("APP_CLOSE_CALLBACK")
_aid    = globals().get("APP_ID", "")
_home   = globals().get("HOME_DIR", os.path.expanduser("~"))
_kern   = globals().get("KERNEL")
_appdir = globals().get("APP_DIR", "")

_base = os.environ.get("VLAUNCH_HOME") or (
    os.path.normpath(os.path.join(_appdir,"..","..","..")) if _appdir else "")

def _gp(*p):
    if _kern and hasattr(_kern,"get_path"): return _kern.get_path(*p)
    return os.path.join(_base,*p) if _base else os.path.join(*p)

win=QWidget(_par); win.setWindowFlags(Qt.FramelessWindowHint)
win.setWindowTitle("v_IDE"); win.setGeometry(200,150,1100,700); win.setStyleSheet("background:white;")
lay=QVBoxLayout(win); lay.setContentsMargins(0,0,0,0)
lay.addWidget(_tbar("v_IDE",win,_on_close))
mb=QMenuBar(win); lay.addWidget(mb)
body=QHBoxLayout()
sidebar=QListWidget(); sidebar.setFixedWidth(220)
sidebar.setStyleSheet("QListWidget{border-right:1px solid #ccc;background:#f4f4f4;font-size:13px;}"
    "QListWidget::item{padding:8px;}QListWidget::item:selected{background:#007aff;color:white;}")
editor_tabs=QTabWidget(); editor_tabs.setTabsClosable(True)
editor_tabs.tabCloseRequested.connect(editor_tabs.removeTab)
body.addWidget(sidebar); body.addWidget(editor_tabs); lay.addLayout(body)
status=QLabel("Ready"); status.setStyleSheet("padding:4px;background:#f0f0f0;color:#666;font-size:11px;")
lay.addWidget(status)
cur_folder=[None]

def _pop(folder):
    sidebar.clear(); cur_folder[0]=folder
    for root,_,files in os.walk(folder):
        for f in files:
            sidebar.addItem(QListWidgetItem(os.path.relpath(os.path.join(root,f),folder)))
    status.setText(f"Project: {os.path.basename(folder)}")

def _open_file(item):
    if not cur_folder[0]: return
    fp=os.path.join(cur_folder[0],item.text())
    try:
        with open(fp,encoding="utf-8",errors="replace") as fh: txt=fh.read()
    except Exception as e: QMessageBox.warning(win,"Error",str(e)); return
    ed=QPlainTextEdit(); ed.setPlainText(txt); ed.setFont(QFont("Consolas",11))
    editor_tabs.addTab(ed,item.text())
    def _save(ev):
        if ev.key()==Qt.Key_S and ev.modifiers()&Qt.ControlModifier:
            with open(fp,"w",encoding="utf-8") as fh: fh.write(ed.toPlainText())
            status.setText(f"Saved: {item.text()}")
        else: QPlainTextEdit.keyPressEvent(ed,ev)
    ed.keyPressEvent=_save

sidebar.itemDoubleClicked.connect(_open_file)

def _new():
    name,ok=QInputDialog.getText(win,"New Project","Name:")
    if not ok or not name.strip(): return
    base=_gp("apps","user_apps"); path=os.path.join(base,name.strip())
    if os.path.exists(path): QMessageBox.warning(win,"Error","Already exists!"); return
    os.makedirs(os.path.join(path,"license"),exist_ok=True)
    os.makedirs(os.path.join(path,"src"),exist_ok=True)
    tpl=('# base.vrun\nfrom PyQt5.QtWidgets import *\nfrom PyQt5.QtCore import Qt\n'
         'from PyQt5.QtWidgets import QApplication as _QApp\n'
         '_par=globals().get("PARENT_WINDOW")\n_close=globals().get("APP_CLOSE_CALLBACK")\n'
         '_aid=globals().get("APP_ID","")\n_closed=[False]\n'
         'def _on_close():\n    if _closed[0]: return\n    _closed[0]=True\n'
         '    try: win.hide()\n    except: pass\n    if _close: _close(_aid)\n    _QApp.quit()\n'
         'def _accept_close(e):\n    e.accept()\n    if not _closed[0]: _on_close()\n'
         'win=QWidget(_par)\nwin.setWindowFlags(Qt.FramelessWindowHint)\n'
         'win.setGeometry(300,200,600,400)\n'
         'lay=QVBoxLayout(win)\nlay.addWidget(QLabel("Hello from MyApp!"))\n'
         'cb=QPushButton("Close"); cb.clicked.connect(_on_close); lay.addWidget(cb)\n'
         'win.closeEvent=_accept_close\nwin.show()\ndef on_program_exit(): pass\n')
    with open(os.path.join(path,"base.vrun"),"w") as f: f.write(tpl)
    with open(os.path.join(path,"build.info.py"),"w") as f:
        f.write(f'name = "{name.strip()}"\nicon = "icon.png"\n')
    with open(os.path.join(path,"dep.txt"),"w") as f: f.write("# deps\n")
    open(os.path.join(path,"icon.png"),"wb").close()
    _pop(path); QMessageBox.information(win,"Done",f"Created:\n{path}")

def _open():
    folder=QFileDialog.getExistingDirectory(win,"Open Project",_gp("apps","user_apps"))
    if folder: _pop(folder)

def _compile():
    if not cur_folder[0]: QMessageBox.warning(win,"Error","Open a project first"); return
    folder=cur_folder[0]
    miss=([f for f in ["base.vrun","build.info.py","dep.txt","icon.png"]
           if not os.path.isfile(os.path.join(folder,f))]+
          [d for d in ["license","src"] if not os.path.isdir(os.path.join(folder,d))])
    if miss: QMessageBox.warning(win,"Error","Missing: "+", ".join(miss)); return
    name=os.path.basename(folder)
    out=os.path.join(_gp("apps","user_apps"),name+".vysico")
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as zf:
        for root,_,files in os.walk(folder):
            for f in files:
                fp=os.path.join(root,f); zf.write(fp,os.path.relpath(fp,folder))
    status.setText(f"Compiled → {out}")
    QMessageBox.information(win,"Done",f"Output:\n{out}")

for lbl2,slot in (("New project",_new),("Open project",_open),("Compile → .vysico",_compile)):
    a=QAction(lbl2,win); a.triggered.connect(slot); mb.addAction(a)

win.closeEvent=_accept_close
win.show()

def on_program_exit(): pass
'''


# ─────────────────────────────────────────────────────────────────────────────
# SystemInit
# ─────────────────────────────────────────────────────────────────────────────

class SystemInit:
    REQUIRED_DIRS = [
        ("apps","user_apps"),("apps","store_apps"),("apps","temp"),
        ("home",),("home","Documents"),("home","Pictures"),("home","Downloads"),
        ("kernel","config"),("var","log"),("var","run"),("etc","users"),
        ("tmp",),("usr","bin"),
    ]

    SYSTEM_APPS = {
        "terminal":  (TERMINAL_VRUN,  "app5.png"),
        "settings":  (SETTINGS_VRUN,  "settings.png"),
        "snake":     (SNAKE_VRUN,      "app7.png"),
        "app_store": (STORE_VRUN,      "app8.png"),
        "camera":    (CAMERA_VRUN,     "app4.png"),
        "v_browser": (BROWSER_VRUN,    "app1.png"),
        "v_ide":     (IDE_VRUN,        "app6.png"),
    }

    def __init__(self, kernel=None):
        self.kernel = kernel
        self.results: dict = {}

    def run(self) -> dict:
        self._log("sysinit starting")
        try:
            self._make_dirs()
            self._make_system_apps()
            self.results["status"] = "ok"
        except Exception as exc:
            self._log(f"ERROR: {exc}")
            self.results.update(status="fail", error=str(exc))
        self._log(f"sysinit done — {self.results}")
        return self.results

    def _log(self, msg: str):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [sysinit] {msg}", flush=True)

    def _make_dirs(self):
        for parts in self.REQUIRED_DIRS:
            os.makedirs(get_path(*parts), exist_ok=True)
        self._log("directory tree OK")

    def _make_system_apps(self):
        apps_dir = get_path("apps", "user_apps")
        for name, (vrun, icon_file) in self.SYSTEM_APPS.items():
            dest = os.path.join(apps_dir, f"{name}.vysico")
            if os.path.isfile(dest):
                continue
            icon_bytes = self._read_icon(icon_file)
            self._create_vysico(dest, name, vrun, icon_bytes)
            self._log(f"created {name}.vysico")

    def _read_icon(self, filename: str) -> bytes:
        path = get_path("source", filename)
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                return fh.read()
        return self._make_icon_png((80, 100, 180))

    def _create_vysico(self, dest: str, name: str, vrun_code: str, icon_bytes: bytes):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("base.vrun",     vrun_code)
            zf.writestr("build.info.py", f'name = "{name}"\nicon = "icon.png"\n')
            zf.writestr("dep.txt",       "# auto-generated\n")
            zf.writestr("icon.png",      icon_bytes)
            zf.writestr("license/LICENSE", "vLaunch subsystem app\n")
            zf.writestr("src/.gitkeep",  "")
        with open(dest, "wb") as fh:
            fh.write(buf.getvalue())

    @staticmethod
    def _make_icon_png(rgb: tuple) -> bytes:
        import struct, zlib
        w, h = 32, 32; r, g, b = rgb

        def chunk(name, data):
            c = struct.pack(">I", len(data)) + name + data
            return c + struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)

        raw = b""
        for _ in range(h):
            raw += b"\x00" + bytes([r, g, b] * w)
        return (b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw))
                + chunk(b"IEND", b""))


if __name__ == "__main__":
    r = SystemInit().run()
    print(f"violence_sysinit: {r['status']}")
