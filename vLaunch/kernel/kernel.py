#!/usr/bin/env python3
"""
vLaunch Kernel  v4.0
═════════════════════════════════════════════════════════════════════════════
BSD-inspired subsystem kernel with 100+ commands, sandbox resource management,
memory/CPU warden, user management, integrity checks, and kernel panic.
"""

import argparse, base64, binascii, configparser, csv, difflib, fnmatch
import getpass, glob, hashlib, importlib.util, io, json, logging, math
import os, platform, random, re, shlex, shutil, signal, socket
import sqlite3, stat, string, struct, subprocess, sys, textwrap
import time, traceback, zipfile
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

_BOOT_TIME: float = time.time()
_VERSION          = "4.0.0"

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────

_HERE    = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.environ.get("VLAUNCH_HOME") or os.path.dirname(_HERE)
MODULES  = os.path.join(_HERE, "modules")


def get_path(*p: str) -> str:
    return os.path.join(BASE_DIR, *p)


# Sandbox directory layout
SANDBOX_DIRS = {
    "home":     get_path("home"),
    "tmp":      get_path("tmp"),
    "var_log":  get_path("var", "log"),
    "var_run":  get_path("var", "run"),
    "var_spool":get_path("var", "spool"),
    "etc":      get_path("etc"),
    "etc_users":get_path("etc", "users"),
    "usr_bin":  get_path("usr", "bin"),
    "usr_lib":  get_path("usr", "lib"),
    "apps":     get_path("apps", "user_apps"),
    "apps_temp":get_path("apps", "temp"),
}
for _p in SANDBOX_DIRS.values():
    os.makedirs(_p, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────

_LOG_FILE = get_path("var", "log", "kernel.log")

logging.basicConfig(
    level=logging.DEBUG,
    format="[%(asctime)s] %(levelname)-8s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(_LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("kernel")


# ─────────────────────────────────────────────────────────────────────────────
# Session token
# ─────────────────────────────────────────────────────────────────────────────

_TOKEN_FILE = get_path("var", "run", "ktoken")


def _gen_token() -> str:
    raw = "".join(random.choices(string.ascii_letters + string.digits, k=64))
    return hashlib.sha256(raw.encode()).hexdigest()


def _write_token(t: str):
    os.makedirs(os.path.dirname(_TOKEN_FILE), exist_ok=True)
    with open(_TOKEN_FILE, "w") as fh:
        fh.write(t + "\n")
    try:
        os.chmod(_TOKEN_FILE, 0o600)
    except Exception:
        pass


def _revoke_token():
    try:
        os.remove(_TOKEN_FILE)
    except FileNotFoundError:
        pass


SESSION_TOKEN: str = _gen_token()
_write_token(SESSION_TOKEN)
os.environ["_VLAUNCH_STARTED"]    = "1"
os.environ["_VLAUNCH_TOKEN"]      = SESSION_TOKEN
os.environ["_VLAUNCH_KERNEL_PID"] = str(os.getpid())
os.environ["VLAUNCH_HOME"]        = BASE_DIR


# ─────────────────────────────────────────────────────────────────────────────
# Config helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_cfg(path: str) -> dict:
    cfg: dict = {}
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    cfg[k.strip()] = v.strip()
    return cfg


def _save_cfg(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    # Preserve comments: read existing, update values, write back
    existing: list = []
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            existing = fh.readlines()
    # Build index of existing keys
    written: set = set()
    result: list = []
    for line in existing:
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("#"):
            k = stripped.split("=", 1)[0].strip()
            if k in data:
                result.append(f"{k}={data[k]}\n")
                written.add(k)
            else:
                result.append(line)
        else:
            result.append(line)
    # Append new keys
    for k, v in data.items():
        if k not in written:
            result.append(f"{k}={v}\n")
    with open(path, "w", encoding="utf-8") as fh:
        fh.writelines(result)


_GLOBAL_CFG_PATH = get_path("kernel", "config", "global.cfg")
_LOCAL_CFG_PATH  = get_path("kernel", "config", "local.cfg")


# ─────────────────────────────────────────────────────────────────────────────
# Kernel Panic
# ─────────────────────────────────────────────────────────────────────────────

def kernel_panic(reason: str, fatal: bool = True) -> None:
    """
    Log a kernel panic, write to dmesg, flush all state, and optionally exit.
    Non-fatal panics are warnings; fatal panics terminate the process.
    """
    border = "!" * 72
    msg    = (
        f"\n{border}\n"
        f"KERNEL PANIC — {reason}\n"
        f"  time   : {datetime.now().isoformat()}\n"
        f"  pid    : {os.getpid()}\n"
        f"  base   : {BASE_DIR!r}\n"
        f"  fatal  : {fatal}\n"
        f"{border}\n"
    )
    print(msg, file=sys.stderr)
    log.critical(f"KERNEL PANIC: {reason}  fatal={fatal}")

    # Write to dmesg
    dmesg_path = get_path("var", "log", "dmesg.log")
    ts = time.strftime("%b %d %H:%M:%S")
    with open(dmesg_path, "a", encoding="utf-8") as fh:
        fh.write(f"{ts} kernel: PANIC: {reason}\n")

    # Print traceback if available
    tb = traceback.format_exc()
    if tb and tb.strip() != "NoneType: None":
        log.critical(f"Traceback:\n{tb}")

    if fatal:
        _revoke_token()
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
# Integrity checker
# ─────────────────────────────────────────────────────────────────────────────

def check_integrity(kernel=None) -> list:
    """
    Check sandbox filesystem integrity.
    Returns list of (severity, description) tuples.
    'critical' severity → kernel_panic()
    """
    issues: list = []

    def _issue(severity: str, msg: str):
        issues.append((severity, msg))
        if severity == "critical":
            log.critical(f"integrity: {msg}")
        elif severity == "error":
            log.error(f"integrity: {msg}")
        else:
            log.warning(f"integrity: {msg}")

    # Required directories
    for name, path in SANDBOX_DIRS.items():
        if not os.path.isdir(path):
            try:
                os.makedirs(path, exist_ok=True)
                _issue("warning", f"Missing dir recreated: {path!r}")
            except Exception as exc:
                _issue("critical", f"Cannot create required dir {path!r}: {exc}")

    # Required files
    required_files = [
        (get_path("kernel", "config", "global.cfg"), "global.cfg"),
        (get_path("kernel", "config", "local.cfg"),  "local.cfg"),
        (get_path("kernel", "kernel.py"),            "kernel.py"),
    ]
    for fpath, label in required_files:
        if not os.path.isfile(fpath):
            _issue("error", f"Required file missing: {label!r} ({fpath!r})")

    # Kernel self-hash check (compare against stored hash if exists)
    kernel_py = get_path("kernel", "kernel.py")
    hash_file = get_path("var", "run", "kernel.sha256")
    if os.path.isfile(kernel_py):
        with open(kernel_py, "rb") as fh:
            current_hash = hashlib.sha256(fh.read()).hexdigest()
        if os.path.isfile(hash_file):
            with open(hash_file) as fh:
                stored_hash = fh.read().strip()
            if current_hash != stored_hash:
                _issue("warning", "kernel.py hash changed since last boot")
        # Always update hash
        with open(hash_file, "w") as fh:
            fh.write(current_hash + "\n")

    # Token file still present?
    if not os.path.isfile(_TOKEN_FILE):
        _issue("critical", "Session token missing — possible unauthorised access")

    # Temp dir cleanup (stale extractions)
    tmp_dir = get_path("apps", "temp")
    if os.path.isdir(tmp_dir):
        for entry in os.listdir(tmp_dir):
            full = os.path.join(tmp_dir, entry)
            if os.path.isdir(full):
                age = time.time() - os.path.getmtime(full)
                if age > 3600:  # older than 1 hour
                    try:
                        shutil.rmtree(full)
                        _issue("info", f"Cleaned stale temp dir: {full!r}")
                    except Exception:
                        pass

    # Write integrity report
    report_path = get_path("var", "log", "integrity.log")
    with open(report_path, "a", encoding="utf-8") as fh:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        fh.write(f"\n[{ts}] Integrity check — {len(issues)} issue(s)\n")
        for sev, msg in issues:
            fh.write(f"  [{sev.upper():8s}] {msg}\n")

    # Trigger panic for critical issues
    critical = [m for s, m in issues if s == "critical"]
    if critical:
        kernel_panic("; ".join(critical), fatal=True)

    return issues


# ─────────────────────────────────────────────────────────────────────────────
# Sandbox Resource Controller  (sysctl tunables)
# ─────────────────────────────────────────────────────────────────────────────

_SANDBOX_DISK_MAX_GB = 60.0   # hard system-level cap

class SandboxRC:
    DEFAULTS = {
        "kern.maxproc":           "32",
        "kern.maxfiles":          "256",
        "kern.hostname":          "vSubSys",
        "kern.ostype":            "vLaunch",
        "kern.osversion":         _VERSION,
        "kern.securelevel":       "1",
        "vm.swap_enabled":        "0",
        "sandbox.disk_quota_gb":  "10",
        "sandbox.ram_watch_mb":   "512",
        "sandbox.cpu_warn_pct":   "80",
        "sandbox.net_access":     "1",
        "sandbox.allow_exec":     "1",
        "sandbox.max_log_mb":     "50",
    }

    def __init__(self):
        self._cfg_path = get_path("etc", "sysctl.conf")
        self._data: dict = dict(self.DEFAULTS)
        self._load()

    def _load(self):
        for k, v in _load_cfg(self._cfg_path).items():
            self._data[k] = v

    def _save(self):
        _save_cfg(self._cfg_path, self._data)

    def get(self, key: str, default: str = "") -> str:
        return self._data.get(key, default)

    def set(self, key: str, value: str) -> None:
        # Enforce disk quota cap
        if key == "sandbox.disk_quota_gb":
            try:
                requested = float(value)
                if requested > _SANDBOX_DISK_MAX_GB:
                    raise ValueError(
                        f"Disk quota cannot exceed {_SANDBOX_DISK_MAX_GB:.0f} GB "
                        f"(system-level sandbox restriction)"
                    )
            except ValueError as exc:
                raise
        self._data[key] = value
        self._save()
        log.info(f"sysctl: {key} = {value}")

    def all_tunables(self) -> dict:
        return dict(self._data)

    def disk_used_mb(self) -> float:
        total = 0
        for root, _, files in os.walk(BASE_DIR):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
        return total / (1024 * 1024)

    def disk_quota_bytes(self) -> int:
        return int(float(self.get("sandbox.disk_quota_gb", "10")) * 1024 * 1024 * 1024)

    def proc_count(self, running_apps: dict) -> int:
        return 1 + len(running_apps)


# ─────────────────────────────────────────────────────────────────────────────
# Memory / CPU Warden  (sandbox resource monitoring daemon)
# ─────────────────────────────────────────────────────────────────────────────

class MemoryWarden:
    """
    Monitors RAM, CPU, and sandbox disk usage.
    Runs as a periodic check (call .tick() in the main loop).
    Writes to warden.log and raises warnings.
    """
    HISTORY_LEN = 60   # keep last 60 samples

    def __init__(self, rc: SandboxRC):
        self.rc          = rc
        self._cpu_hist   = deque(maxlen=self.HISTORY_LEN)
        self._ram_hist   = deque(maxlen=self.HISTORY_LEN)
        self._disk_hist  = deque(maxlen=self.HISTORY_LEN)
        self._log_path   = get_path("var", "log", "warden.log")
        self._last_warn  = defaultdict(float)
        self._warn_cooldown = 60.0   # seconds between repeated warnings

    def tick(self) -> dict:
        """Sample resources and return current snapshot dict."""
        snap: dict = {"ts": time.time()}

        try:
            import psutil
            snap["cpu_pct"]   = psutil.cpu_percent(interval=0)
            mem               = psutil.virtual_memory()
            snap["ram_used_mb"]  = mem.used    / (1024 * 1024)
            snap["ram_total_mb"] = mem.total   / (1024 * 1024)
            snap["ram_pct"]      = mem.percent
            swap              = psutil.swap_memory()
            snap["swap_used_mb"] = swap.used / (1024 * 1024)
            snap["swap_pct"]     = swap.percent
        except ImportError:
            snap["cpu_pct"] = snap["ram_used_mb"] = snap["ram_total_mb"] = 0
            snap["ram_pct"] = snap["swap_used_mb"] = snap["swap_pct"] = 0

        snap["disk_used_mb"] = self.rc.disk_used_mb()
        snap["disk_quota_mb"] = float(self.rc.get("sandbox.disk_quota_gb", "10")) * 1024

        self._cpu_hist.append(snap["cpu_pct"])
        self._ram_hist.append(snap["ram_used_mb"])
        self._disk_hist.append(snap["disk_used_mb"])

        # Threshold checks
        cpu_warn   = float(self.rc.get("sandbox.cpu_warn_pct", "80"))
        ram_limit  = float(self.rc.get("sandbox.ram_watch_mb", "512"))
        disk_quota = snap["disk_quota_mb"]

        now = time.time()

        def _warn(key: str, msg: str):
            if now - self._last_warn[key] > self._warn_cooldown:
                self._last_warn[key] = now
                log.warning(f"warden: {msg}")
                with open(self._log_path, "a", encoding="utf-8") as fh:
                    fh.write(f"[{datetime.now().isoformat()}] WARN: {msg}\n")

        if snap["cpu_pct"] > cpu_warn:
            _warn("cpu", f"CPU at {snap['cpu_pct']:.1f}% (threshold {cpu_warn:.0f}%)")

        if snap["ram_used_mb"] > ram_limit:
            _warn("ram", f"RAM used {snap['ram_used_mb']:.0f} MB (watch threshold {ram_limit:.0f} MB)")

        if snap["disk_used_mb"] > disk_quota * 0.90:
            _warn("disk", f"Sandbox disk at {snap['disk_used_mb']:.1f} MB "
                  f"({snap['disk_used_mb']/disk_quota*100:.1f}% of {disk_quota:.0f} MB quota)")

        if snap["disk_used_mb"] > disk_quota:
            log.error(f"warden: DISK QUOTA EXCEEDED: {snap['disk_used_mb']:.1f} > {disk_quota:.0f} MB")

        return snap

    def report(self) -> str:
        """Return a text summary of recent resource history."""
        def _avg(d): return sum(d) / len(d) if d else 0
        lines = [
            "  Warden resource report",
            f"  CPU   avg(last {len(self._cpu_hist)}): {_avg(self._cpu_hist):.1f}%",
            f"  RAM   avg(last {len(self._ram_hist)}): {_avg(self._ram_hist):.1f} MB",
            f"  Disk  avg(last {len(self._disk_hist)}): {_avg(self._disk_hist):.1f} MB",
        ]
        return "\n".join(lines)

    def auto_configure(self, local_cfg_path: str) -> bool:
        """
        Check local.cfg for required warden fields.
        If any are missing, prompt the user to fill them in.
        Returns True if config is complete.
        """
        required = {
            "sandbox_ram_limit_mb": ("RAM watch threshold (MB)", "512"),
            "sandbox_cpu_warn_pct": ("CPU warning threshold (%)", "80"),
            "sandbox_disk_quota_gb": ("Sandbox disk quota (GB, max 60)", "10"),
        }
        current = _load_cfg(local_cfg_path)
        changed = False

        for key, (prompt, default) in required.items():
            if key not in current:
                print(f"\n  [warden] Missing config: {key}")
                try:
                    val = input(f"  Enter {prompt} [{default}]: ").strip()
                except (EOFError, KeyboardInterrupt):
                    val = ""
                val = val or default

                # Enforce disk quota cap
                if key == "sandbox_disk_quota_gb":
                    try:
                        if float(val) > _SANDBOX_DISK_MAX_GB:
                            print(f"  ! Max allowed quota is {_SANDBOX_DISK_MAX_GB:.0f} GB. "
                                  f"Setting to {_SANDBOX_DISK_MAX_GB:.0f}.")
                            val = str(_SANDBOX_DISK_MAX_GB)
                    except ValueError:
                        val = default

                current[key] = val
                changed = True
                log.info(f"warden auto-config: {key} = {val}")

        if changed:
            _save_cfg(local_cfg_path, current)
            # Mirror into sysctl tunables
            if "sandbox_ram_limit_mb"  in current:
                self.rc._data["sandbox.ram_watch_mb"]  = current["sandbox_ram_limit_mb"]
            if "sandbox_cpu_warn_pct"  in current:
                self.rc._data["sandbox.cpu_warn_pct"]  = current["sandbox_cpu_warn_pct"]
            if "sandbox_disk_quota_gb" in current:
                self.rc._data["sandbox.disk_quota_gb"] = current["sandbox_disk_quota_gb"]
            self.rc._save()

        return True


# ─────────────────────────────────────────────────────────────────────────────
# User Manager
# ─────────────────────────────────────────────────────────────────────────────

class UserManager:
    """
    Manages subsystem users stored in etc/users/passwd (JSON per user).
    Users are sandboxed — they have no relation to host OS users.
    """

    _PASSWD_FILE = get_path("etc", "users", "passwd.json")

    def __init__(self):
        self._users: dict = {}
        self._load()
        # Ensure root/admin always exists
        if "root" not in self._users:
            self._users["root"] = {
                "uid": 0, "gid": 0, "home": "/home/root",
                "shell": "/bin/sh", "groups": ["wheel", "admin"],
                "passwd_hash": "", "created": datetime.now().isoformat(),
            }
            self._save()

    def _load(self):
        if os.path.isfile(self._PASSWD_FILE):
            try:
                with open(self._PASSWD_FILE, encoding="utf-8") as fh:
                    self._users = json.load(fh)
            except Exception as exc:
                log.error(f"UserManager load error: {exc}")
                self._users = {}

    def _save(self):
        os.makedirs(os.path.dirname(self._PASSWD_FILE), exist_ok=True)
        with open(self._PASSWD_FILE, "w", encoding="utf-8") as fh:
            json.dump(self._users, fh, indent=2)
        try:
            os.chmod(self._PASSWD_FILE, 0o600)
        except Exception:
            pass

    def _hash(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def add_user(self, username: str, password: str, groups: list = None) -> bool:
        if username in self._users:
            return False
        uid  = max((u["uid"] for u in self._users.values()), default=999) + 1
        home = get_path("home", username)
        os.makedirs(home, exist_ok=True)
        self._users[username] = {
            "uid":         uid,
            "gid":         uid,
            "home":        home,
            "shell":       "/bin/sh",
            "groups":      groups or [],
            "passwd_hash": self._hash(password),
            "created":     datetime.now().isoformat(),
        }
        self._save()
        log.info(f"adduser: created {username!r} uid={uid}")
        return True

    def remove_user(self, username: str, remove_home: bool = False) -> bool:
        if username not in self._users:
            return False
        if username in ("root",):
            raise PermissionError("Cannot remove root user")
        home = self._users[username].get("home", "")
        del self._users[username]
        self._save()
        if remove_home and home and os.path.isdir(home):
            shutil.rmtree(home, ignore_errors=True)
        log.info(f"rmuser: removed {username!r}")
        return True

    def change_password(self, username: str, new_password: str) -> bool:
        if username not in self._users:
            return False
        self._users[username]["passwd_hash"] = self._hash(new_password)
        self._save()
        log.info(f"passwd: changed for {username!r}")
        return True

    def verify(self, username: str, password: str) -> bool:
        u = self._users.get(username)
        if not u: return False
        return u.get("passwd_hash") == self._hash(password)

    def list_users(self) -> list:
        result = []
        for name, u in self._users.items():
            result.append({
                "name":    name,
                "uid":     u["uid"],
                "gid":     u["gid"],
                "groups":  u.get("groups", []),
                "home":    u.get("home", ""),
                "created": u.get("created", ""),
            })
        return result

    def get_user(self, name: str) -> Optional[dict]:
        return self._users.get(name)

    def add_to_group(self, username: str, group: str) -> bool:
        u = self._users.get(username)
        if not u: return False
        if group not in u.get("groups", []):
            u.setdefault("groups", []).append(group)
            self._save()
        return True

    def remove_from_group(self, username: str, group: str) -> bool:
        u = self._users.get(username)
        if not u: return False
        u.setdefault("groups", [])
        if group in u["groups"]:
            u["groups"].remove(group)
            self._save()
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Kernel
# ─────────────────────────────────────────────────────────────────────────────

class Kernel:
    VERSION = _VERSION

    def __init__(self):
        self._global_cfg = _load_cfg(_GLOBAL_CFG_PATH)
        self._local_cfg  = _load_cfg(_LOCAL_CFG_PATH)
        self._running_apps: dict = {}
        self._rc      = SandboxRC()
        self._warden  = MemoryWarden(self._rc)
        self._users   = UserManager()
        self._aliases: dict = {}
        self._env:    dict = dict(os.environ)

        log.info(f"Kernel {_VERSION}  BASE_DIR={BASE_DIR!r}")
        log.info(f"  user={self.get_cfg('profile_1_name','?')}  "
                 f"hostname={self._rc.get('kern.hostname')}")

    def get_cfg(self, key: str, default: str = "") -> str:
        return self._global_cfg.get(key, default)

    def get_local(self, key: str, default: str = "") -> str:
        return self._local_cfg.get(key, default)

    def reload_cfg(self):
        self._global_cfg = _load_cfg(_GLOBAL_CFG_PATH)
        self._local_cfg  = _load_cfg(_LOCAL_CFG_PATH)
        log.info("Config reloaded")

    def get_path(self, *p) -> str:
        return get_path(*p)

    def load_module(self, name: str):
        for ext in (".py", ".kernel"):
            path = os.path.join(MODULES, name + ext)
            if os.path.isfile(path):
                spec = importlib.util.spec_from_file_location(name, path)
                mod  = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.BASE_DIR = BASE_DIR
                mod.get_path = get_path
                log.info(f"Module loaded: {name}")
                return mod
        log.warning(f"Module not found: {name}")
        return None

    def boot(self) -> bool:
        log.info("=== Boot sequence start ===")

        # Run integrity check first
        try:
            issues = check_integrity(self)
            errors = [m for s, m in issues if s in ("error", "critical")]
            if errors:
                log.error(f"Integrity: {len(errors)} error(s)")
            else:
                log.info("Integrity check: OK")
        except SystemExit:
            return False
        except Exception as exc:
            kernel_panic(f"integrity check exception: {exc}", fatal=False)

        # sysinit
        si_mod = self.load_module("violence_sysinit")
        if si_mod and hasattr(si_mod, "SystemInit"):
            r = si_mod.SystemInit(kernel=self).run()
            if r.get("status") == "fail":
                kernel_panic(f"sysinit failed: {r.get('error')}", fatal=True)
                return False
        else:
            log.warning("violence_sysinit not found")

        # Warden auto-configure
        self._warden.auto_configure(_LOCAL_CFG_PATH)
        self.reload_cfg()

        # Sheila (silent)
        self._run_sheila(silent=True)

        # dmesg
        self._dmesg(f"Kernel {_VERSION} booted  base={BASE_DIR!r}")
        self._dmesg(f"hostname={self._rc.get('kern.hostname')}  "
                    f"quota={self._rc.get('sandbox.disk_quota_gb')}GB")

        log.info("=== Boot sequence complete ===")
        return True

    def _run_sheila(self, silent: bool = True):
        sheila = self.load_module("sheila")
        if not sheila: return
        try:
            r = sheila.check_for_updates(silent=silent)
            if r.get("update"):
                log.info(f"sheila: update available — {r.get('message')}")
        except Exception as exc:
            log.error(f"sheila: {exc}")

    def check_updates(self, silent: bool = False):
        self._run_sheila(silent=silent)

    def _dmesg(self, msg: str):
        ts   = time.strftime("%b %d %H:%M:%S")
        path = get_path("var", "log", "dmesg.log")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(f"{ts} kernel: {msg}\n")

    def read_dmesg(self, lines: int = 40) -> str:
        path = get_path("var", "log", "dmesg.log")
        if not os.path.isfile(path): return "(empty)"
        with open(path, encoding="utf-8") as fh:
            return "".join(fh.readlines()[-lines:])

    def warden_tick(self) -> dict:
        return self._warden.tick()

    # ── .vysico launcher ──────────────────────────────────────────────────────

    def launch_pkg(self, vysico_path: str, headless: bool = False) -> Optional[str]:
        """
        Launch a .vysico package as a subprocess.

        Both GUI and headless modes use the same inline-script approach —
        no external app_runner.py is needed.

        GUI mode:   spawns a subprocess that creates its own QApplication.
        Headless:   spawns a subprocess with no Qt; stdout/stderr inherited.

        The subprocess is a grandchild of the kernel process, so if the kernel
        dies, the OS will eventually reap them (SIGHUP propagation on most Unix).
        """
        if not os.path.isfile(vysico_path):
            log.error(f"pkg: not found: {vysico_path!r}"); return None

        env = os.environ.copy()
        env.update({
            "_VLAUNCH_STARTED":    "1",
            "_VLAUNCH_TOKEN":      SESSION_TOKEN,
            "_VLAUNCH_KERNEL_PID": str(os.getpid()),
            "VLAUNCH_HOME":        BASE_DIR,
        })
        python = self._venv_python()
        return self._launch_inline(vysico_path, env, headless)

    def _launch_inline(self, vysico_path: str, env: dict,
                        headless: bool = False) -> Optional[str]:
        """
        Build a self-contained runner script and execute it as a subprocess.

        Both GUI and headless .vysico apps use the same runner — no external
        app_runner.py is needed.  The runner:
          1. Extracts the .vysico to apps/temp/<app_id>/
          2. Executes base.vrun in an injected namespace
          3. Runs the Qt event loop if QApplication was created (GUI apps)
          4. Ticks a heartbeat: if the kernel process dies → Qt quits
          5. Calls on_program_exit(), repacks .vysico, removes temp dir
        """
        python     = self._venv_python()
        kernel_pid = os.getpid()
        base_dir   = BASE_DIR

        # Build the runner script using join-lines to avoid escape/f-string issues
        lines = [
            "import zipfile, os, sys, shutil, random, string, signal",
            "signal.signal(signal.SIGINT, signal.SIG_DFL)",
            "BASE_DIR    = " + repr(base_dir),
            "VYSICO      = " + repr(vysico_path),
            "KERNEL_PID  = " + str(kernel_pid),
            "",
            "def _kernel_alive():",
            "    try: os.kill(KERNEL_PID, 0); return True",
            "    except OSError: return False",
            "",
            "suffix = ''.join(random.choices(string.digits, k=10))",
            "aid    = os.path.splitext(os.path.basename(VYSICO))[0] + '_' + suffix",
            "extr   = os.path.join(BASE_DIR, 'apps', 'temp', aid)",
            "os.makedirs(extr, exist_ok=True)",
            "",
            "with zipfile.ZipFile(VYSICO) as zf:",
            "    zf.extractall(extr)",
            "",
            "vrun = os.path.join(extr, 'base.vrun')",
            "_closed = [False]",
            "",
            "# Create QApplication BEFORE executing vrun so widgets can be",
            "# constructed at module level inside base.vrun",
            "try:",
            "    from PyQt5.QtWidgets import QApplication",
            "    from PyQt5.QtCore import QTimer",
            "    import os as _os",
            "    _os.environ.setdefault('QTWEBENGINE_DISABLE_SANDBOX', '1')",
            "    _app = QApplication.instance() or QApplication(sys.argv)",
            "    _app.setQuitOnLastWindowClosed(True)",
            "except ImportError:",
            "    _app = None",
            "",
            "def _cb(a=None):",
            "    if _closed[0]: return",
            "    _closed[0] = True",
            "    try:",
            "        from PyQt5.QtWidgets import QApplication as _QA",
            "        _QA.quit()",
            "    except Exception: pass",
            "",
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
            "with open(vrun, encoding='utf-8', errors='replace') as fh:",
            "    code = fh.read()",
            "",
            "try:",
            "    exec(compile(code, vrun, 'exec'), ns)",
            "except SystemExit: pass",
            "except Exception as e:",
            "    import traceback",
            "    print('[runner] base.vrun error:', e, flush=True)",
            "    traceback.print_exc()",
            "",
            "# Start Qt event loop (QApplication already exists)",
            "if _app:",
            "    try:",
            "        from PyQt5.QtCore import QTimer",
            "        def _hb():",
            "            if not _kernel_alive(): _app.quit()",
            "        _t = QTimer()",
            "        _t.timeout.connect(_hb)",
            "        _t.start(2000)",
            "    except Exception: pass",
            "    _app.exec_()",
            "",
            "# on_program_exit hook",
            "on_exit = ns.get('on_program_exit')",
            "if callable(on_exit):",
            "    try: on_exit()",
            "    except Exception as e:",
            "        print('[runner] on_exit error:', e, flush=True)",
            "",
            "# Repack .vysico",
            "try:",
            "    with zipfile.ZipFile(VYSICO, 'w', zipfile.ZIP_DEFLATED) as zf:",
            "        for root, _, files in os.walk(extr):",
            "            for f in files:",
            "                fp = os.path.join(root, f)",
            "                zf.write(fp, os.path.relpath(fp, extr))",
            "except Exception as e:",
            "    print('[runner] repack error:', e, flush=True)",
            "",
            "shutil.rmtree(extr, ignore_errors=True)",
        ]
        script = "\n".join(lines)

        try:
            proc = subprocess.Popen([python, "-c", script], env=env)
        except Exception as exc:
            log.error(f"launch_inline: Popen failed: {exc}"); return None

        meta = self._read_pkg_meta(vysico_path)
        name = meta.get("name", os.path.splitext(os.path.basename(vysico_path))[0])
        aid  = f"{name}_{''.join(random.choices(string.digits, k=6))}"
        self._running_apps[aid] = {
            "proc":    proc,
            "name":    name,
            "path":    vysico_path,
            "started": time.time(),
            "headless": headless,
        }
        log.info(f"pkg: launched {name!r} [{aid}] pid={proc.pid} "
                 f"({'headless' if headless else 'GUI'})")
        return aid

    def _read_pkg_meta(self, path: str) -> dict:
        try:
            with zipfile.ZipFile(path) as z:
                raw = z.read("build.info.py").decode("utf-8", errors="replace")
            ns: dict = {}
            exec(compile(raw, "build.info.py", "exec"), ns)
            return ns
        except Exception:
            return {}

    def kill_pkg(self, app_id: str, sig: int = signal.SIGTERM) -> bool:
        info = self._running_apps.get(app_id)
        if not info: return False
        try:
            info["proc"].send_signal(sig); return True
        except Exception as exc:
            log.error(f"kill_pkg: {exc}"); return False

    def poll_apps(self):
        dead = [a for a,i in self._running_apps.items() if i["proc"].poll() is not None]
        for a in dead:
            self._running_apps.pop(a)
            log.info(f"pkg exited: {a}")

    def get_running_apps(self) -> list:
        self.poll_apps()
        return [{"id":a,"name":i["name"],"pid":i["proc"].pid,
                 "started":i["started"],"headless":i["headless"],
                 "rc":i["proc"].returncode}
                for a,i in self._running_apps.items()]

    def _venv_python(self) -> str:
        for c in (get_path(".venv","bin","python"),
                  get_path(".venv","Scripts","python.exe")):
            if os.path.isfile(c): return c
        return sys.executable

    def uptime(self) -> float:
        return time.time() - _BOOT_TIME

    def rc(self) -> SandboxRC:
        return self._rc

    def warden(self) -> MemoryWarden:
        return self._warden

    def users(self) -> UserManager:
        return self._users



# ─────────────────────────────────────────────────────────────────────────────
# TUI Shell  (100+ BSD-style commands)
# ─────────────────────────────────────────────────────────────────────────────

class TUI:
    PROMPT_NORM = "\033[1;32m{user}@{host}\033[0m:\033[1;34m{cwd}\033[0m$ "
    PROMPT_ROOT = "\033[1;31mroot@{host}\033[0m:\033[1;34m{cwd}\033[0m# "
    MAX_HIST    = 500

    def __init__(self, kernel: Kernel):
        self.k      = kernel
        self.rc     = kernel.rc()
        self.warden = kernel.warden()
        self.um     = kernel.users()
        self._su    = False
        self._cwd   = get_path("home")
        self._hist: list  = []
        self._aliases: dict = {}
        self._env_vars: dict = {}
        self._jobs: dict  = {}   # background jobs
        self._last_snap: dict = {}
        self._warden_interval = 30   # seconds
        self._last_warden_tick = 0.0

        os.makedirs(self._cwd, exist_ok=True)
        os.chdir(self._cwd)

        # Register all commands
        self._cmds: dict = {
            # ── System info ──────────────────────────────────────────────────
            "uname":      self._c_uname,
            "hostname":   self._c_hostname,
            "date":       self._c_date,
            "cal":        self._c_cal,
            "uptime":     self._c_uptime,
            "dmesg":      self._c_dmesg,
            "sysctl":     self._c_sysctl,
            "systat":     self._c_systat,
            "vmstat":     self._c_vmstat,
            "memstat":    self._c_memstat,
            "swapinfo":   self._c_swapinfo,
            "iostat":     self._c_iostat,
            "cpuinfo":    self._c_cpuinfo,
            # ── Process management ────────────────────────────────────────────
            "ps":         self._c_ps,
            "top":        self._c_top,
            "kill":       self._c_kill,
            "pkill":      self._c_pkill,
            "pgrep":      self._c_pgrep,
            "nice":       self._c_nice,
            "renice":     self._c_renice,
            "jobs":       self._c_jobs,
            "bg":         self._c_bg,
            "fg":         self._c_fg,
            "wait":       self._c_wait,
            # ── Disk / filesystem ─────────────────────────────────────────────
            "df":         self._c_df,
            "du":         self._c_du,
            "ls":         self._c_ls,
            "ll":         self._c_ll,
            "la":         self._c_la,
            "cd":         self._c_cd,
            "pwd":        self._c_pwd,
            "cat":        self._c_cat,
            "more":       self._c_more,
            "less":       self._c_less,
            "head":       self._c_head,
            "tail":       self._c_tail,
            "touch":      self._c_touch,
            "mkdir":      self._c_mkdir,
            "rm":         self._c_rm,
            "cp":         self._c_cp,
            "mv":         self._c_mv,
            "ln":         self._c_ln,
            "find":       self._c_find,
            "locate":     self._c_locate,
            "stat":       self._c_stat,
            "file":       self._c_file,
            "chmod":      self._c_chmod,
            "chown":      self._c_chown,
            "quota":      self._c_quota,
            "fsck":       self._c_fsck,
            # ── Text tools ────────────────────────────────────────────────────
            "echo":       self._c_echo,
            "printf":     self._c_printf,
            "grep":       self._c_grep,
            "egrep":      self._c_egrep,
            "wc":         self._c_wc,
            "sort":       self._c_sort,
            "uniq":       self._c_uniq,
            "cut":        self._c_cut,
            "paste":      self._c_paste,
            "tr":         self._c_tr,
            "sed":        self._c_sed,
            "awk":        self._c_awk,
            "diff":       self._c_diff,
            "strings":    self._c_strings,
            "xxd":        self._c_xxd,
            "base64":     self._c_base64,
            "md5":        self._c_md5,
            "sha256":     self._c_sha256,
            "tee":        self._c_tee,
            "split":      self._c_split,
            # ── Network ───────────────────────────────────────────────────────
            "ifconfig":   self._c_ifconfig,
            "netstat":    self._c_netstat,
            "ping":       self._c_ping,
            "nslookup":   self._c_nslookup,
            "dig":        self._c_dig,
            "curl":       self._c_curl,
            "fetch":      self._c_fetch,
            # ── Config management ─────────────────────────────────────────────
            "cfg":        self._c_cfg,
            # ── Package management ────────────────────────────────────────────
            "pkg":        self._c_pkg,
            # ── User management ───────────────────────────────────────────────
            "adduser":    self._c_adduser,
            "rmuser":     self._c_rmuser,
            "passwd":     self._c_passwd,
            "usermod":    self._c_usermod,
            "id":         self._c_id,
            "groups":     self._c_groups,
            "who":        self._c_who,
            "w":          self._c_w,
            "last":       self._c_last,
            "users":      self._c_users,
            # ── Services ──────────────────────────────────────────────────────
            "service":    self._c_service,
            "rcctl":      self._c_rcctl,
            # ── Sandbox / warden ──────────────────────────────────────────────
            "warden":     self._c_warden,
            "sandbox":    self._c_sandbox,
            # ── Session ───────────────────────────────────────────────────────
            "whoami":     self._c_whoami,
            "su":         self._c_su,
            "history":    self._c_history,
            "alias":      self._c_alias,
            "unalias":    self._c_unalias,
            "set":        self._c_set,
            "export":     self._c_export,
            "unset":      self._c_unset,
            "printenv":   self._c_printenv,
            "env":        self._c_env,
            "which":      self._c_which,
            "type":       self._c_type,
            "sleep":      self._c_sleep,
            "watch":      self._c_watch,
            "bc":         self._c_bc,
            "yes":        self._c_yes,
            "true":       self._c_true,
            "false":      self._c_false,
            "banner":     self._c_banner,
            "clear":      self._c_clear,
            "cls":        self._c_clear,
            "poweroff":   self._c_poweroff,
            "halt":       self._c_poweroff,
            "reboot":     self._c_reboot,
            "shutdown":   self._c_shutdown,
            "exit":       self._c_poweroff,
            "logout":     self._c_poweroff,
            "help":       self._c_help,
            "?":          self._c_help,
            "man":        self._c_man,
            "info":       self._c_man,
        }

    # ── ANSI / helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _c(code: str, t: str) -> str: return f"\033[{code}m{t}\033[0m"
    def _ok(self,  t): print(self._c("32", t))
    def _err(self, t): print(self._c("31", t), file=sys.stderr)
    def _warn(self,t): print(self._c("33", t))
    def _info(self,t): print(self._c("36", t))
    def _bold(self,t): print(self._c("1",  t))

    def _resolve(self, path: str, must_exist: bool = False) -> Optional[str]:
        if os.path.isabs(path):
            full = os.path.normpath(path)
            # allow absolute within base
            if not path.startswith(BASE_DIR):
                # try mapping /home → BASE_DIR/home etc.
                remap = {"/home":get_path("home"), "/tmp":get_path("tmp"),
                         "/etc":get_path("etc"),   "/var":get_path("var"),
                         "/usr":get_path("usr")}
                for prefix, mapped in remap.items():
                    if path.startswith(prefix):
                        full = os.path.normpath(mapped + path[len(prefix):])
                        break
                else:
                    self._err(f"Permission denied: outside sandbox: {path!r}")
                    return None
        else:
            full = os.path.normpath(os.path.join(self._cwd, path))
        if not full.startswith(BASE_DIR):
            self._err(f"Permission denied: outside sandbox: {full!r}")
            return None
        if must_exist and not os.path.exists(full):
            self._err(f"{path!r}: No such file or directory")
            return None
        return full

    def _check_su(self, cmd: str) -> bool:
        if not self._su:
            self._err(f"{cmd}: Permission denied (su required)")
        return self._su

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        os.system("clear")   # clear terminal on kernel start
        user = self.k.get_cfg("profile_1_name", "user")
        host = self.rc.get("kern.hostname", "vSubSys")

        self._info(
            f"vLaunch Kernel {_VERSION}  [{self.rc.get('kern.ostype')} / {platform.system()}]"
        )
        self._info(f"  hostname: {host}   user: {user}   base: {BASE_DIR}")
        snap = self.warden.tick()
        self._info(
            f"  RAM: {snap['ram_used_mb']:.0f}/{snap['ram_total_mb']:.0f} MB  "
            f"CPU: {snap['cpu_pct']:.1f}%  "
            f"Disk: {snap['disk_used_mb']:.1f}/{snap['disk_quota_mb']:.0f} MB"
        )
        print()

        while True:
            # Periodic warden tick
            now = time.time()
            if now - self._last_warden_tick > self._warden_interval:
                self._last_warden_tick = now
                self._last_snap = self.warden.tick()

            try:
                rel = os.path.relpath(self._cwd, BASE_DIR)
                shown_cwd = "/" + rel if rel != "." else "/"
                tmpl  = self.PROMPT_ROOT if self._su else self.PROMPT_NORM
                prompt = tmpl.format(
                    user="root" if self._su else user,
                    host=host, cwd=shown_cwd
                )
                raw = input(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                self._warn("Use 'poweroff' to shut down.")
                continue

            if not raw: continue

            # Record history
            self._hist.append(raw)
            if len(self._hist) > self.MAX_HIST: self._hist.pop(0)
            try:
                with open(get_path("var","log","shell_history"), "a", encoding="utf-8") as fh:
                    fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {raw}\n")
            except Exception: pass

            # Expand aliases
            first_word = raw.split()[0]
            if first_word in self._aliases:
                raw = self._aliases[first_word] + raw[len(first_word):]

            try:
                parts = shlex.split(raw)
            except ValueError as exc:
                self._err(f"parse error: {exc}"); continue

            if not parts: continue
            verb = parts[0].lower()
            args = parts[1:]

            # Handle output redirection (simple >, >>)
            redirect_file = None
            redirect_append = False
            for i, a in enumerate(args):
                if a in (">", ">>") and i + 1 < len(args):
                    redirect_append = (a == ">>")
                    redirect_file = args[i + 1]
                    args = args[:i]
                    break

            handler = self._cmds.get(verb)
            if handler:
                if redirect_file:
                    rpath = self._resolve(redirect_file)
                    if rpath:
                        mode = "a" if redirect_append else "w"
                        old_stdout = sys.stdout
                        try:
                            with open(rpath, mode, encoding="utf-8") as fh:
                                sys.stdout = fh
                                handler(args)
                        except Exception as exc:
                            sys.stdout = old_stdout
                            self._err(str(exc))
                        finally:
                            sys.stdout = old_stdout
                else:
                    try:
                        handler(args)
                    except SystemExit:
                        break
                    except Exception as exc:
                        self._err(f"{verb}: {exc}")
                        log.exception(f"TUI {verb!r}")
            else:
                self._err(f"{verb}: command not found  (try 'help')")

    # ─────────────────────────────────────────────────────────────────────────
    # SYSTEM INFO commands
    # ─────────────────────────────────────────────────────────────────────────

    def _c_uname(self, args):
        "uname [-a|-s|-r|-m|-n|-p|-v]"
        a = set(args)
        all_ = "-a" in a or not a
        fields = []
        if all_ or "-s" in a: fields.append(self.rc.get("kern.ostype"))
        if all_ or "-n" in a: fields.append(self.rc.get("kern.hostname"))
        if all_ or "-r" in a: fields.append(self.rc.get("kern.osversion"))
        if all_ or "-v" in a: fields.append(f"build {_VERSION}")
        if all_ or "-m" in a: fields.append(platform.machine())
        if all_ or "-p" in a: fields.append(platform.processor() or "unknown")
        print(" ".join(fields))

    def _c_hostname(self, args):
        "hostname [name]"
        if args:
            if not self._check_su("hostname"): return
            self.rc.set("kern.hostname", args[0])
            self._ok(f"hostname → {args[0]!r}")
        else:
            print(self.rc.get("kern.hostname"))

    def _c_date(self, args):
        "date [+format]"
        fmt = args[0].lstrip("+") if args else "%a %b %d %H:%M:%S %Z %Y"
        try:
            print(datetime.now().strftime(fmt))
        except Exception:
            print(datetime.now().strftime("%a %b %d %H:%M:%S %Z %Y"))

    def _c_cal(self, args):
        "cal [month year]"
        import calendar
        if len(args) >= 2:
            try:
                m, y = int(args[0]), int(args[1])
                print(calendar.month(y, m))
                return
            except Exception:
                pass
        print(calendar.month(datetime.now().year, datetime.now().month))

    def _c_uptime(self, _):
        "uptime"
        s   = self.k.uptime()
        td  = timedelta(seconds=int(s))
        h,r = divmod(td.seconds, 3600); m,_ = divmod(r, 60)
        la  = ""
        try:
            l = os.getloadavg()
            la = f"  load: {l[0]:.2f} {l[1]:.2f} {l[2]:.2f}"
        except Exception: pass
        print(f" {datetime.now():%H:%M:%S} up {td.days}d {h:02d}:{m:02d},"
              f"  {len(self.k.get_running_apps())} pkg(s){la}")

    def _c_dmesg(self, args):
        "dmesg [-n N]"
        n = 40
        if "-n" in args:
            try: n = int(args[args.index("-n")+1])
            except Exception: pass
        print(self.k.read_dmesg(n), end="")

    def _c_sysctl(self, args):
        "sysctl [-a] | key | key=val (su)"
        if not args or "-a" in args:
            for k,v in sorted(self.rc.all_tunables().items()): print(f"{k}: {v}")
            return
        for tok in args:
            if "=" in tok:
                if not self._check_su("sysctl"): return
                k,v = tok.split("=",1)
                try: self.rc.set(k.strip(), v.strip()); print(f"{k.strip()}: {v.strip()}")
                except ValueError as e: self._err(str(e))
            else:
                v = self.rc.get(tok)
                if v: print(f"{tok}: {v}")
                else: self._err(f"sysctl: {tok!r}: unknown MIB")

    def _c_systat(self, _):
        "systat — live resource snapshot"
        snap = self.warden.tick()
        print(f"\n{'─'*56}")
        print(f"  systat — {datetime.now():%H:%M:%S}")
        print(f"{'─'*56}")
        print(f"  CPU     : {snap['cpu_pct']:>6.1f}%")
        print(f"  RAM     : {snap['ram_used_mb']:>8.1f} / {snap['ram_total_mb']:.0f} MB  ({snap['ram_pct']:.1f}%)")
        print(f"  Swap    : {snap['swap_used_mb']:>8.1f} MB  ({snap['swap_pct']:.1f}%)")
        print(f"  SBX disk: {snap['disk_used_mb']:>8.1f} / {snap['disk_quota_mb']:.0f} MB")
        print(f"  Uptime  : {timedelta(seconds=int(self.k.uptime()))}")
        print(f"  Procs   : {self.rc.proc_count(self.k._running_apps)}")
        print(f"{'─'*56}\n")

    def _c_vmstat(self, _):
        "vmstat — virtual memory statistics"
        snap = self.warden.tick()
        print(f"  procs   memory(MB)           swap(MB)")
        print(f"  {'r':>4} {'b':>4}  {'avm':>8} {'fre':>8}  {'used':>8} {'si':>8} {'so':>8}")
        try:
            import psutil
            vm = psutil.virtual_memory()
            sw = psutil.swap_memory()
            avm = vm.available // (1024*1024); fre = vm.free // (1024*1024)
            su_used = sw.used // (1024*1024)
            si = sw.sin // 1024; so = sw.sout // 1024
            r = len(self.k.get_running_apps())
            print(f"  {r:>4} {'0':>4}  {avm:>8} {fre:>8}  {su_used:>8} {si:>8} {so:>8}")
        except ImportError:
            self._warn("psutil required")

    def _c_memstat(self, _):
        "memstat — detailed memory breakdown"
        snap = self.warden.tick()
        print(f"\n  Memory statistics:")
        print(f"  {'Total':20s}: {snap['ram_total_mb']:.1f} MB")
        print(f"  {'Used':20s}: {snap['ram_used_mb']:.1f} MB  ({snap['ram_pct']:.1f}%)")
        free = snap['ram_total_mb'] - snap['ram_used_mb']
        print(f"  {'Free':20s}: {free:.1f} MB")
        print(f"  {'Swap used':20s}: {snap['swap_used_mb']:.1f} MB  ({snap['swap_pct']:.1f}%)")
        warn_mb = float(self.rc.get("sandbox.ram_watch_mb","512"))
        pct_of_watch = snap['ram_used_mb'] / warn_mb * 100 if warn_mb > 0 else 0
        print(f"  {'Watch threshold':20s}: {warn_mb:.0f} MB  (current: {pct_of_watch:.0f}% used)")
        print(self.warden.report())
        print()

    def _c_swapinfo(self, _):
        "swapinfo — swap space information"
        try:
            import psutil
            sw = psutil.swap_memory()
            print(f"  Device       Size(MB) Used(MB) Free(MB) Use%")
            total = sw.total//(1024*1024); used=sw.used//(1024*1024); free=sw.free//(1024*1024)
            print(f"  /dev/swap    {total:>8} {used:>8} {free:>8} {sw.percent:.0f}%")
        except ImportError:
            self._warn("psutil required")

    def _c_iostat(self, _):
        "iostat — I/O statistics"
        try:
            import psutil
            dc = psutil.disk_io_counters()
            if dc:
                print(f"  reads:  {dc.read_count:>12}  bytes: {dc.read_bytes//(1024*1024):>10} MB")
                print(f"  writes: {dc.write_count:>12}  bytes: {dc.write_bytes//(1024*1024):>10} MB")
            else:
                self._warn("No disk I/O counters available")
        except ImportError:
            self._warn("psutil required")

    def _c_cpuinfo(self, _):
        "cpuinfo — processor information"
        print(f"  Platform  : {platform.platform()}")
        print(f"  Processor : {platform.processor() or 'unknown'}")
        print(f"  Machine   : {platform.machine()}")
        try:
            import psutil
            print(f"  CPU cores : {psutil.cpu_count(logical=False)} physical / {psutil.cpu_count()} logical")
            freq = psutil.cpu_freq()
            if freq:
                print(f"  Frequency : {freq.current:.0f} MHz  (max {freq.max:.0f} MHz)")
            print(f"  CPU usage : {psutil.cpu_percent(interval=0.3):.1f}%")
        except ImportError:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # PROCESS commands
    # ─────────────────────────────────────────────────────────────────────────

    def _c_ps(self, args):
        "ps [-a|-x|-l]"
        show_host = "-x" in args
        long_fmt  = "-l" in args
        print(f"\n  {'PID':>7}  {'STAT':5}  {'TIME':>10}  {'CMD'}")
        print(f"  {os.getpid():>7}  {'S':5}  {timedelta(seconds=int(self.k.uptime()))}  kernel")
        for ap in self.k.get_running_apps():
            el = timedelta(seconds=int(time.time()-ap["started"]))
            fl = "H" if ap["headless"] else "G"
            st = (str(ap["rc"])[:1] if ap["rc"] is not None else "R") + fl
            print(f"  {ap['pid']:>7}  {st:5}  {el}  {ap['name']}")
        if show_host:
            print(f"\n  --- host (read-only, first 15) ---")
            try:
                import psutil
                for p in list(psutil.process_iter(["pid","name","status"]))[:15]:
                    try: print(f"  {p.pid:>7}  {p.status()[:5]:5}  {'':>10}  {p.name()}")
                    except Exception: pass
            except ImportError: self._warn("psutil required")
        print()

    def _c_top(self, args):
        "top — interactive process monitor (Ctrl-C to exit)"
        try:
            import psutil
            self._info("top — press Ctrl-C to exit")
            try:
                while True:
                    cpu = psutil.cpu_percent(interval=1)
                    mem = psutil.virtual_memory()
                    procs = sorted(
                        psutil.process_iter(["pid","name","cpu_percent","memory_percent","status"]),
                        key=lambda p: p.info.get("cpu_percent") or 0, reverse=True
                    )
                    os.system("clear")
                    print(f"  top — {datetime.now():%H:%M:%S}  CPU:{cpu:.1f}%  RAM:{mem.percent:.1f}%\n")
                    print(f"  {'PID':>7}  {'CPU%':>6}  {'MEM%':>6}  {'STAT':6}  NAME")
                    for p in procs[:20]:
                        try:
                            print(f"  {p.pid:>7}  {p.info['cpu_percent'] or 0:>6.1f}  "
                                  f"{p.info['memory_percent'] or 0:>6.2f}  "
                                  f"{p.info['status'][:6]:6}  {p.name()}")
                        except Exception: pass
            except KeyboardInterrupt: print()
        except ImportError: self._warn("psutil required")

    def _c_kill(self, args):
        "kill [-SIG] <app_id|PID>"
        sig_map = {"TERM":signal.SIGTERM,"KILL":signal.SIGKILL,"HUP":signal.SIGHUP,
                   "INT":signal.SIGINT,"STOP":signal.SIGSTOP,"CONT":signal.SIGCONT,
                   "9":signal.SIGKILL,"15":signal.SIGTERM,"1":signal.SIGHUP}
        sig = signal.SIGTERM; targets = []
        for a in args:
            if a.startswith("-"):
                sig = sig_map.get(a.lstrip("-").upper(), signal.SIGTERM)
            else: targets.append(a)
        if not targets: self._err("kill: missing operand"); return
        for t in targets:
            if t in self.k._running_apps:
                self.k.kill_pkg(t, sig)
                self._ok(f"kill: {sig.name} → {t!r}")
            elif t.isdigit():
                pid = int(t)
                sb_pids = {i["proc"].pid for i in self.k._running_apps.values()}
                if pid in sb_pids or self._su:
                    try: os.kill(pid, sig); self._ok(f"kill: {sig.name} → pid {pid}")
                    except Exception as e: self._err(f"kill: {e}")
                else: self._err(f"kill: {pid}: not a sandbox PID (need su)")
            else: self._err(f"kill: {t!r}: not found")

    def _c_pkill(self, args):
        "pkill <name_pattern>"
        if not args: self._err("pkill: pattern required"); return
        pattern = args[0]
        killed = 0
        for aid, info in list(self.k._running_apps.items()):
            if fnmatch.fnmatch(info["name"], pattern) or pattern in info["name"]:
                self.k.kill_pkg(aid)
                self._ok(f"pkill: {info['name']!r} [{aid}]"); killed += 1
        if not killed: self._warn(f"pkill: no match for {pattern!r}")

    def _c_pgrep(self, args):
        "pgrep <name_pattern>"
        if not args: self._err("pgrep: pattern required"); return
        pattern = args[0]; found = False
        for aid, info in self.k._running_apps.items():
            if fnmatch.fnmatch(info["name"], pattern) or pattern in info["name"]:
                print(f"  {info['proc'].pid:>7}  {info['name']}"); found = True
        if not found: self._warn(f"pgrep: no match for {pattern!r}")

    def _c_nice(self, args):
        "nice [-n increment] <pkg_name>"
        if not args: self._err("nice: missing args"); return
        n = 10
        if args[0] == "-n":
            try: n = int(args[1]); args = args[2:]
            except Exception: pass
        if not args: self._err("nice: missing command"); return
        self._info(f"nice: would set priority {n} for {args[0]!r} (informational)")

    def _c_renice(self, args):
        "renice <priority> <pid>"
        if len(args) < 2: self._err("renice: usage: renice <prio> <pid>"); return
        try:
            prio = int(args[0]); pid = int(args[1])
            os.setpriority(os.PRIO_PROCESS, pid, prio)
            self._ok(f"renice: pid {pid} → priority {prio}")
        except Exception as e: self._err(f"renice: {e}")

    def _c_jobs(self, _):
        "jobs — list background jobs"
        if not self._jobs:
            print("  (no background jobs)"); return
        for jid, info in self._jobs.items():
            rc = info["proc"].poll()
            st = "Running" if rc is None else f"Done({rc})"
            print(f"  [{jid}]  {st:12}  {info['cmd']}")

    def _c_bg(self, args):
        "bg [job_id] — resume job in background"
        jid = int(args[0]) if args else max(self._jobs.keys(), default=0)
        if jid in self._jobs:
            try: os.kill(self._jobs[jid]["proc"].pid, signal.SIGCONT)
            except Exception: pass
        else: self._err(f"bg: {jid}: no such job")

    def _c_fg(self, args):
        "fg [job_id] — bring job to foreground"
        jid = int(args[0]) if args else max(self._jobs.keys(), default=0)
        if jid in self._jobs:
            proc = self._jobs[jid]["proc"]
            try:
                os.kill(proc.pid, signal.SIGCONT)
                proc.wait()
                del self._jobs[jid]
            except Exception as e: self._err(str(e))
        else: self._err(f"fg: {jid}: no such job")

    def _c_wait(self, args):
        "wait [pid] — wait for process"
        if args:
            try: os.waitpid(int(args[0]), 0)
            except Exception as e: self._err(str(e))
        else:
            for info in self.k._running_apps.values():
                info["proc"].wait()

    # ─────────────────────────────────────────────────────────────────────────
    # DISK / FILESYSTEM commands
    # ─────────────────────────────────────────────────────────────────────────

    def _df_helper(self, human, paths):
        def _fmt(n):
            if not human: return str(n)
            for u in ("B","K","M","G","T"):
                if n < 1024: return f"{n:.1f}{u}"
                n /= 1024
            return f"{n:.1f}P"
        print(f"  {'Filesystem':32s}  {'Size':>8}  {'Used':>8}  {'Avail':>8}  Use%")
        try:
            import psutil
            seen: set = set()
            for path in paths:
                try:
                    u = psutil.disk_usage(path); k=(u.total,u.used)
                    if k in seen: continue; seen.add(k)
                    print(f"  {path:32s}  {_fmt(u.total):>8}  {_fmt(u.used):>8}  {_fmt(u.free):>8}  {u.percent:.0f}%")
                except Exception as e: self._err(f"df: {path}: {e}")
        except ImportError: self._warn("psutil required")

    def _c_df(self, args):
        "df [-h] [path]"
        h = "-h" in args; paths=[a for a in args if not a.startswith("-")] or [BASE_DIR]
        self._df_helper(h, paths)

    def _c_du(self, args):
        "du [-h] [-s] [path]"
        human="-h" in args; summ="-s" in args
        paths=[a for a in args if not a.startswith("-")] or [self._cwd]
        def _fmt(n):
            if not human: return f"{n//1024}K"
            for u in ("B","K","M","G"):
                if n<1024: return f"{n:.1f}{u}"; n/=1024
            return f"{n:.1f}T"
        for rawpath in paths:
            path=self._resolve(rawpath,must_exist=True)
            if not path: continue
            total=0
            for root,_,files in os.walk(path):
                sub=sum(os.path.getsize(os.path.join(root,f)) for f in files
                        if os.path.isfile(os.path.join(root,f)))
                total+=sub
                if not summ: print(f"  {_fmt(sub):>8}  {root}")
            if summ: print(f"  {_fmt(total):>8}  {path}")

    def _c_ls(self, args):
        "ls [-la] [path]"
        long_ = any(f in args for f in ("-l","-la","-al","-lh"))
        all_  = any(f in args for f in ("-a","-la","-al"))
        human = "-h" in args or "-lh" in args
        paths = [a for a in args if not a.startswith("-")] or [self._cwd]
        def _fmt(n):
            if not human: return str(n)
            for u in ("B","K","M","G"):
                if n<1024: return f"{n:.0f}{u}"; n/=1024
            return f"{n:.0f}T"
        for rawpath in paths:
            path=self._resolve(rawpath,must_exist=True)
            if not path: continue
            if os.path.isfile(path): entries=[path]
            else:
                try: entries=[os.path.join(path,e) for e in sorted(os.listdir(path))]
                except PermissionError: self._err(f"ls: {path}: Permission denied"); continue
            if not all_: entries=[e for e in entries if not os.path.basename(e).startswith(".")]
            if long_:
                for e in entries:
                    try:
                        s=os.stat(e); m=oct(s.st_mode)[-4:]; sz=_fmt(s.st_size)
                        dt=datetime.fromtimestamp(s.st_mtime).strftime("%b %d %H:%M")
                        n=os.path.basename(e); tag="/" if os.path.isdir(e) else ""
                        print(f"  {m}  {sz:>8}  {dt}  {n}{tag}")
                    except Exception: pass
            else:
                names=[]
                for e in entries:
                    n=os.path.basename(e)
                    if os.path.isdir(e): n=self._c("34;1",n+"/")
                    elif os.access(e,os.X_OK): n=self._c("32",n+"*")
                    names.append(n)
                print("  "+"  ".join(names))

    def _c_ll(self, args): "ll — ls -la"; self._c_ls(["-la"]+args)
    def _c_la(self, args): "la — ls -a"; self._c_ls(["-a"]+args)

    def _c_cd(self, args):
        "cd [path]"
        target=args[0] if args else get_path("home")
        full=self._resolve(target,must_exist=True)
        if not full: return
        if not os.path.isdir(full): self._err(f"cd: {target!r}: Not a directory"); return
        self._cwd=full; os.chdir(self._cwd)

    def _c_pwd(self,_): "pwd"; print(self._cwd)

    def _c_cat(self, args):
        "cat <file>…"
        if not args: self._err("cat: missing operand"); return
        for a in args:
            p=self._resolve(a,must_exist=True)
            if not p: continue
            try:
                with open(p,encoding="utf-8",errors="replace") as fh: print(fh.read(),end="")
            except Exception as e: self._err(f"cat: {a}: {e}")

    def _pager(self, text: str, lines_per_screen: int = 24):
        all_lines = text.splitlines(keepends=True)
        i = 0
        while i < len(all_lines):
            page = all_lines[i:i+lines_per_screen]
            print("".join(page), end="")
            i += lines_per_screen
            if i < len(all_lines):
                try:
                    k = input("--- More --- (q to quit) ").strip().lower()
                    if k == "q": break
                except (EOFError, KeyboardInterrupt): break

    def _c_more(self, args):
        "more <file>"
        if not args: self._err("more: missing file"); return
        p=self._resolve(args[0],must_exist=True)
        if not p: return
        with open(p,encoding="utf-8",errors="replace") as fh: self._pager(fh.read())

    def _c_less(self, args): "less <file>"; self._c_more(args)

    def _c_head(self, args):
        "head [-n N] <file>"
        n=10
        if "-n" in args:
            try: n=int(args[args.index("-n")+1]); args=args[args.index("-n")+2:]
            except Exception: pass
        files=[a for a in args if not a.startswith("-")]
        if not files: self._err("head: missing file"); return
        for f in files:
            p=self._resolve(f,must_exist=True)
            if not p: continue
            with open(p,encoding="utf-8",errors="replace") as fh:
                print("".join(fh.readlines()[:n]),end="")

    def _c_tail(self, args):
        "tail [-n N] [-f] <file>"
        n=10; follow="-f" in args
        if "-n" in args:
            try: n=int(args[args.index("-n")+1])
            except Exception: pass
        files=[a for a in args if not a.startswith("-")]
        if not files: self._err("tail: missing file"); return
        p=self._resolve(files[0],must_exist=True)
        if not p: return
        with open(p,encoding="utf-8",errors="replace") as fh: lines=fh.readlines()
        print("".join(lines[-n:]),end="")
        if follow:
            self._info("tail -f: Ctrl-C to stop")
            try:
                with open(p,encoding="utf-8",errors="replace") as fh:
                    fh.seek(0,2)
                    while True:
                        line=fh.readline()
                        if line: print(line,end="",flush=True)
                        else: time.sleep(0.1)
            except KeyboardInterrupt: pass

    def _c_touch(self, args):
        "touch <file>…"
        if not args: self._err("touch: missing operand"); return
        for a in args:
            p=self._resolve(a)
            if not p: continue
            Path(p).touch()

    def _c_mkdir(self, args):
        "mkdir [-p] <dir>…"
        par="-p" in args; dirs=[a for a in args if not a.startswith("-")]
        if not dirs: self._err("mkdir: missing operand"); return
        for d in dirs:
            p=self._resolve(d)
            if not p: continue
            try:
                os.makedirs(p) if par else os.mkdir(p)
                self._ok(f"mkdir: {p}")
            except FileExistsError:
                if not par: self._err(f"mkdir: {d}: File exists")
            except Exception as e: self._err(f"mkdir: {e}")

    def _c_rm(self, args):
        "rm [-r|-f] <path>…  (su)"
        if not self._check_su("rm"): return
        rec=any(f in args for f in ("-r","-rf","-fr","-r"))
        paths=[a for a in args if not a.startswith("-")]
        if not paths: self._err("rm: missing operand"); return
        for raw in paths:
            p=self._resolve(raw,must_exist=True)
            if not p: continue
            try:
                if os.path.isdir(p):
                    if rec: shutil.rmtree(p); self._ok(f"rm -r: {p}")
                    else: self._err(f"rm: {p}: Is a directory")
                else: os.remove(p); self._ok(f"rm: {p}")
            except Exception as e: self._err(f"rm: {e}")

    def _c_cp(self, args):
        "cp [-r] <src> <dst>  (su)"
        if not self._check_su("cp"): return
        rec="-r" in args; ta=[a for a in args if not a.startswith("-")]
        if len(ta)<2: self._err("cp: usage: cp <src> <dst>"); return
        src=self._resolve(ta[0],must_exist=True); dst=self._resolve(ta[1])
        if not src or not dst: return
        try:
            if os.path.isdir(src) and rec: shutil.copytree(src,dst)
            else: shutil.copy2(src,dst)
            self._ok(f"cp: {src} → {dst}")
        except Exception as e: self._err(f"cp: {e}")

    def _c_mv(self, args):
        "mv <src> <dst>  (su)"
        if not self._check_su("mv"): return
        if len(args)<2: self._err("mv: usage: mv <src> <dst>"); return
        src=self._resolve(args[0],must_exist=True); dst=self._resolve(args[1])
        if not src or not dst: return
        try: shutil.move(src,dst); self._ok(f"mv: {src} → {dst}")
        except Exception as e: self._err(f"mv: {e}")

    def _c_ln(self, args):
        "ln [-s] <target> <link>  (su)"
        if not self._check_su("ln"): return
        sym="-s" in args; ta=[a for a in args if not a.startswith("-")]
        if len(ta)<2: self._err("ln: usage: ln [-s] target link"); return
        tgt=self._resolve(ta[0]); lnk=self._resolve(ta[1])
        if not tgt or not lnk: return
        try:
            if sym: os.symlink(tgt,lnk)
            else: os.link(tgt,lnk)
            self._ok(f"ln: {'symlink' if sym else 'hardlink'}: {tgt} → {lnk}")
        except Exception as e: self._err(f"ln: {e}")

    def _c_find(self, args):
        "find <path> [pattern] [-type f|d]"
        if not args: self._err("find: missing path"); return
        base=self._resolve(args[0],must_exist=True)
        if not base: return
        pattern="*"; type_filter=None
        i=1
        while i<len(args):
            if args[i]=="-type" and i+1<len(args):
                type_filter=args[i+1]; i+=2
            elif not args[i].startswith("-"):
                pattern=args[i]; i+=1
            else: i+=1
        for root,dirs,files in os.walk(base):
            entries=(dirs+files) if not type_filter else (dirs if type_filter=="d" else files)
            for n in entries:
                if fnmatch.fnmatch(n,pattern):
                    print(os.path.join(root,n))

    def _c_locate(self, args):
        "locate <pattern> — search sandbox"
        if not args: self._err("locate: pattern required"); return
        pat=args[0]
        for root,dirs,files in os.walk(BASE_DIR):
            for n in dirs+files:
                if fnmatch.fnmatch(n,f"*{pat}*"): print(os.path.join(root,n))

    def _c_stat(self, args):
        "stat <path>…"
        if not args: self._err("stat: missing operand"); return
        for raw in args:
            p=self._resolve(raw,must_exist=True)
            if not p: continue
            s=os.stat(p)
            print(f"\n  File:  {p}")
            print(f"  Size:  {s.st_size} B   Mode: {oct(s.st_mode)}")
            print(f"  Mtime: {datetime.fromtimestamp(s.st_mtime).isoformat()}")
            print(f"  Inode: {s.st_ino}  Links: {s.st_nlink}\n")

    def _c_file(self, args):
        "file <path>…"
        if not args: self._err("file: missing operand"); return
        for raw in args:
            p=self._resolve(raw,must_exist=True)
            if not p: continue
            if os.path.isdir(p): print(f"  {p}: directory")
            elif os.path.islink(p): print(f"  {p}: symbolic link")
            else:
                try:
                    with open(p,"rb") as fh: magic=fh.read(8)
                    if magic.startswith(b"\x89PNG"): kind="PNG image"
                    elif magic.startswith(b"\xff\xd8"): kind="JPEG image"
                    elif magic[:4]==b"PK\x03\x04": kind="ZIP archive (.vysico?)"
                    elif magic.startswith(b"#!"): kind="script"
                    else:
                        try: open(p,encoding="utf-8").read(64); kind="ASCII text"
                        except Exception: kind="binary data"
                    print(f"  {p}: {kind}")
                except Exception as e: self._err(str(e))

    def _c_chmod(self, args):
        "chmod <octal_mode> <path>  (su)"
        if not self._check_su("chmod"): return
        if len(args)<2: self._err("chmod: usage: chmod <mode> <path>"); return
        try: mode=int(args[0],8)
        except ValueError: self._err(f"chmod: invalid mode {args[0]!r}"); return
        p=self._resolve(args[1],must_exist=True)
        if not p: return
        try: os.chmod(p,mode); self._ok(f"chmod: {p} → {oct(mode)}")
        except Exception as e: self._err(f"chmod: {e}")

    def _c_chown(self, args):
        "chown <user> <path>  (su, sandbox only)"
        if not self._check_su("chown"): return
        if len(args)<2: self._err("chown: usage: chown <user> <path>"); return
        u=self.um.get_user(args[0])
        if not u: self._err(f"chown: unknown sandbox user {args[0]!r}"); return
        p=self._resolve(args[1],must_exist=True)
        if not p: return
        self._ok(f"chown: {p} → uid {u['uid']} (sandbox record updated)")

    def _c_quota(self, args):
        "quota [-v] — show sandbox disk quota"
        used_mb = self.rc.disk_used_mb()
        quota_mb = float(self.rc.get("sandbox.disk_quota_gb","10")) * 1024
        pct = used_mb/quota_mb*100 if quota_mb > 0 else 0
        print(f"\n  Sandbox disk quota")
        print(f"  Used  : {used_mb:>10.1f} MB  ({pct:.1f}%)")
        print(f"  Quota : {quota_mb:>10.1f} MB  ({float(self.rc.get('sandbox.disk_quota_gb','10')):.0f} GB)")
        print(f"  Free  : {quota_mb-used_mb:>10.1f} MB")
        print(f"  Limit : {_SANDBOX_DISK_MAX_GB:.0f} GB  (system hard cap)\n")

    def _c_fsck(self, args):
        "fsck — check sandbox filesystem integrity"
        self._info("Running filesystem integrity check…")
        issues = check_integrity(self.k)
        if not issues:
            self._ok("fsck: filesystem OK — no issues found")
        else:
            for sev, msg in issues:
                color = "31" if sev in ("critical","error") else "33"
                print(f"  {self._c(color, f'[{sev.upper()}]')} {msg}")
            self._warn(f"fsck: {len(issues)} issue(s) found")

    # ─────────────────────────────────────────────────────────────────────────
    # TEXT TOOLS
    # ─────────────────────────────────────────────────────────────────────────

    def _c_echo(self, args):
        "echo [-n] [-e] <text>…"
        no_nl = "-n" in args
        args  = [a for a in args if a not in ("-n","-e")]
        out   = " ".join(args)
        print(out, end="" if no_nl else "\n")

    def _c_printf(self, args):
        "printf <format> [args…]"
        if not args: return
        try: print(args[0] % tuple(args[1:]), end="")
        except Exception: print(" ".join(args), end="")

    def _grep_impl(self, args, regex: bool):
        pat_flags = [a for a in args if a.startswith("-")]
        others    = [a for a in args if not a.startswith("-")]
        if not others: self._err("grep: pattern required"); return
        pattern=others[0]; files=others[1:]
        ignore="-i" in pat_flags; count="-c" in pat_flags; line_num="-n" in pat_flags
        invert="-v" in pat_flags
        flags=re.IGNORECASE if ignore else 0
        try: rx=re.compile(pattern if regex else re.escape(pattern),flags)
        except re.error as e: self._err(f"grep: {e}"); return
        def _process(text, fname=""):
            matched=0
            for i,line in enumerate(text.splitlines(),1):
                m=bool(rx.search(line))
                if invert: m=not m
                if m:
                    matched+=1
                    if not count:
                        prefix=""
                        if fname: prefix+=f"{fname}:"
                        if line_num: prefix+=f"{i}:"
                        print(prefix+line)
            if count: print(f"{fname+':' if fname else ''}{matched}")
        if not files:
            _process("\n".join(sys.stdin.read().splitlines()))
        else:
            for f in files:
                p=self._resolve(f,must_exist=True)
                if not p: continue
                with open(p,encoding="utf-8",errors="replace") as fh:
                    _process(fh.read(),f)

    def _c_grep(self, args): "grep [-i|-c|-n|-v] <pattern> [file…]"; self._grep_impl(args,False)
    def _c_egrep(self, args): "egrep — grep with regex"; self._grep_impl(args,True)

    def _c_wc(self, args):
        "wc [-l|-w|-c] <file>…"
        files=[a for a in args if not a.startswith("-")]
        if not files: self._err("wc: missing file"); return
        for f in files:
            p=self._resolve(f,must_exist=True)
            if not p: continue
            with open(p,encoding="utf-8",errors="replace") as fh: text=fh.read()
            l=len(text.splitlines()); w=len(text.split()); c=len(text.encode())
            print(f"  {l:8} {w:8} {c:8}  {f}")

    def _c_sort(self, args):
        "sort [-r|-n|-u] <file>"
        rev="-r" in args; num="-n" in args; uniq_="-u" in args
        files=[a for a in args if not a.startswith("-")]
        if not files: self._err("sort: missing file"); return
        p=self._resolve(files[0],must_exist=True)
        if not p: return
        with open(p,encoding="utf-8",errors="replace") as fh: lines=fh.readlines()
        key=float if num else str
        try: lines.sort(key=lambda x: (key(x.strip()) if num else x), reverse=rev)
        except Exception: lines.sort(reverse=rev)
        if uniq_:
            seen=set(); lines=[l for l in lines if l not in seen and not seen.add(l)]
        print("".join(lines),end="")

    def _c_uniq(self, args):
        "uniq [-c|-d] <file>"
        count="-c" in args; dup="-d" in args
        files=[a for a in args if not a.startswith("-")]
        if not files: self._err("uniq: missing file"); return
        p=self._resolve(files[0],must_exist=True)
        if not p: return
        with open(p,encoding="utf-8",errors="replace") as fh: lines=fh.readlines()
        prev=None; cnt=0
        for line in lines:
            if line==prev: cnt+=1
            else:
                if prev is not None:
                    if dup and cnt==0: pass
                    elif not dup or cnt>0:
                        print((f"  {cnt+1:4}  " if count else "")+prev,end="")
                prev=line; cnt=0
        if prev is not None: print((f"  {cnt+1:4}  " if count else "")+prev,end="")

    def _c_cut(self, args):
        "cut -d<delim> -f<fields> <file>"
        delim="\t"; fields_str="1"
        for a in args:
            if a.startswith("-d"): delim=a[2:] or "\t"
            elif a.startswith("-f"): fields_str=a[2:]
        try: fields=[int(x)-1 for x in fields_str.split(",")]
        except Exception: self._err("cut: invalid -f"); return
        files=[a for a in args if not a.startswith("-")]
        if not files: self._err("cut: missing file"); return
        p=self._resolve(files[0],must_exist=True)
        if not p: return
        with open(p,encoding="utf-8",errors="replace") as fh:
            for line in fh:
                parts=line.rstrip("\n").split(delim)
                print(delim.join(parts[f] for f in fields if f<len(parts)))

    def _c_paste(self, args):
        "paste <file1> <file2>…"
        files=[a for a in args if not a.startswith("-")]
        if len(files)<2: self._err("paste: need at least 2 files"); return
        handles=[]; data=[]
        for f in files:
            p=self._resolve(f,must_exist=True)
            if not p: return
            with open(p,encoding="utf-8",errors="replace") as fh:
                data.append(fh.readlines())
        for row in zip(*data):
            print("\t".join(l.rstrip("\n") for l in row))

    def _c_tr(self, args):
        "tr <set1> <set2>  (reads from string args)"
        if len(args)<3: self._err("tr: usage: tr <set1> <set2> <text>"); return
        s1,s2,text=args[0],args[1]," ".join(args[2:])
        table=str.maketrans(s1,s2)
        print(text.translate(table))

    def _c_sed(self, args):
        "sed 's/old/new/[g]' <file>"
        if len(args)<2: self._err("sed: usage: sed 's/old/new/' <file>"); return
        expr=args[0]; files=[a for a in args[1:] if not a.startswith("-")]
        m=re.match(r's/(.+?)/(.*)/(g?)',expr)
        if not m: self._err(f"sed: unsupported expression {expr!r}"); return
        pat,repl,flags=m.groups(); count=0 if flags=="g" else 1
        for f in files:
            p=self._resolve(f,must_exist=True)
            if not p: continue
            with open(p,encoding="utf-8",errors="replace") as fh: text=fh.read()
            print(re.sub(pat,repl,text,count=count),end="")

    def _c_awk(self, args):
        "awk '{print $N}' <file> — field printer"
        if len(args)<2: self._err("awk: usage: awk 'prog' file"); return
        prog=args[0]; files=[a for a in args[1:] if not a.startswith("-")]
        m=re.search(r'\$(\d+)',prog); col=int(m.group(1))-1 if m else 0
        sep=re.search(r'-F\s*(\S+)',prog)
        delim=sep.group(1) if sep else None
        for f in files:
            p=self._resolve(f,must_exist=True)
            if not p: continue
            with open(p,encoding="utf-8",errors="replace") as fh:
                for line in fh:
                    parts=line.split(delim) if delim else line.split()
                    if col<len(parts): print(parts[col])

    def _c_diff(self, args):
        "diff <file1> <file2>"
        files=[a for a in args if not a.startswith("-")]
        if len(files)<2: self._err("diff: need 2 files"); return
        p1=self._resolve(files[0],must_exist=True)
        p2=self._resolve(files[1],must_exist=True)
        if not p1 or not p2: return
        with open(p1,encoding="utf-8",errors="replace") as fh: l1=fh.readlines()
        with open(p2,encoding="utf-8",errors="replace") as fh: l2=fh.readlines()
        for line in difflib.unified_diff(l1,l2,fromfile=files[0],tofile=files[1]):
            if line.startswith("+"): print(self._c("32",line),end="")
            elif line.startswith("-"): print(self._c("31",line),end="")
            else: print(line,end="")

    def _c_strings(self, args):
        "strings <file> [-n min_len]"
        n=4
        if "-n" in args:
            try: n=int(args[args.index("-n")+1])
            except Exception: pass
        files=[a for a in args if not a.startswith("-")]
        if not files: self._err("strings: missing file"); return
        p=self._resolve(files[0],must_exist=True)
        if not p: return
        with open(p,"rb") as fh: data=fh.read()
        for m in re.finditer(rb'[ -~]{'+str(n).encode()+rb',}',data):
            print(m.group().decode("ascii","replace"))

    def _c_xxd(self, args):
        "xxd <file> [-l bytes]"
        limit=None
        if "-l" in args:
            try: limit=int(args[args.index("-l")+1])
            except Exception: pass
        files=[a for a in args if not a.startswith("-")]
        if not files: self._err("xxd: missing file"); return
        p=self._resolve(files[0],must_exist=True)
        if not p: return
        with open(p,"rb") as fh: data=fh.read(limit or 256)
        for i in range(0,len(data),16):
            chunk=data[i:i+16]
            hex_=(" ".join(f"{b:02x}" for b in chunk)).ljust(47)
            asc ="".join(chr(b) if 32<=b<127 else "." for b in chunk)
            print(f"  {i:08x}:  {hex_}  {asc}")

    def _c_base64(self, args):
        "base64 [-d] <file|string>"
        dec="-d" in args; items=[a for a in args if not a.startswith("-")]
        if not items: self._err("base64: missing input"); return
        val=items[0]
        p=self._resolve(val)
        if p and os.path.isfile(p):
            with open(p,"rb") as fh: data=fh.read()
        else:
            data=val.encode()
        if dec:
            try: print(base64.b64decode(data).decode("utf-8","replace"))
            except Exception as e: self._err(str(e))
        else:
            print(base64.b64encode(data).decode())

    def _c_md5(self, args):
        "md5 <file>…"
        if not args: self._err("md5: missing file"); return
        for f in args:
            p=self._resolve(f,must_exist=True)
            if not p: continue
            with open(p,"rb") as fh: d=hashlib.md5(fh.read()).hexdigest()
            print(f"  MD5 ({f}) = {d}")

    def _c_sha256(self, args):
        "sha256 <file>…"
        if not args: self._err("sha256: missing file"); return
        for f in args:
            p=self._resolve(f,must_exist=True)
            if not p: continue
            with open(p,"rb") as fh: d=hashlib.sha256(fh.read()).hexdigest()
            print(f"  SHA256 ({f}) = {d}")

    def _c_tee(self, args):
        "tee [-a] <file> — write stdin to file and stdout"
        app="-a" in args; files=[a for a in args if not a.startswith("-")]
        if not files: self._err("tee: missing file"); return
        p=self._resolve(files[0])
        if not p: return
        mode="a" if app else "w"
        try:
            text=input()
            with open(p,mode,encoding="utf-8") as fh: fh.write(text+"\n")
            print(text)
        except Exception as e: self._err(str(e))

    def _c_split(self, args):
        "split [-l N] <file> [prefix]"
        n=1000; prefix="x"
        if "-l" in args:
            try: n=int(args[args.index("-l")+1])
            except Exception: pass
        files=[a for a in args if not a.startswith("-")]
        if not files: self._err("split: missing file"); return
        if len(files)>=2: prefix=files[1]
        p=self._resolve(files[0],must_exist=True)
        if not p: return
        with open(p,encoding="utf-8",errors="replace") as fh: lines=fh.readlines()
        for i,start in enumerate(range(0,len(lines),n)):
            out_path=self._resolve(f"{prefix}{i:04d}")
            if not out_path: continue
            with open(out_path,"w",encoding="utf-8") as fh:
                fh.writelines(lines[start:start+n])
            self._ok(f"split: {out_path}")

    # ─────────────────────────────────────────────────────────────────────────
    # NETWORK commands
    # ─────────────────────────────────────────────────────────────────────────

    def _c_ifconfig(self, args):
        "ifconfig [iface]"
        if self.rc.get("sandbox.net_access","1") != "1":
            self._warn("Network access disabled (sandbox.net_access=0)"); return
        try:
            import psutil
            stats=psutil.net_if_stats(); addrs=psutil.net_if_addrs()
            ifaces=[args[0]] if args else sorted(addrs.keys())
            for iface in ifaces:
                st=stats.get(iface)
                print(f"\n  {iface}:")
                if st: print(f"    flags: {'UP' if st.isup else 'DOWN'}  mtu: {st.mtu}")
                for addr in addrs.get(iface,[]):
                    fam=str(addr.family).replace("AddressFamily.","")
                    print(f"    {fam:12s} {addr.address}")
            print()
        except ImportError: self._warn("psutil required")

    def _c_netstat(self, args):
        "netstat [-a|-n]"
        if self.rc.get("sandbox.net_access","1") != "1":
            self._warn("Network access disabled"); return
        try:
            import psutil
            conns=psutil.net_connections(kind="inet")
            print(f"\n  {'Proto':6}  {'Local':24}  {'Remote':24}  Status")
            for c in conns[:30]:
                la=f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "-"
                ra=f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "-"
                proto="tcp" if c.type.name=="SOCK_STREAM" else "udp"
                print(f"  {proto:6}  {la:24}  {ra:24}  {c.status or '-'}")
            print()
        except ImportError: self._warn("psutil required")

    def _c_ping(self, args):
        "ping [-c N] <host>"
        if self.rc.get("sandbox.net_access","1") != "1":
            self._warn("Network access disabled"); return
        count=3
        if "-c" in args:
            try: count=int(args[args.index("-c")+1])
            except Exception: pass
        hosts=[a for a in args if not a.startswith("-")]
        if not hosts: self._err("ping: missing host"); return
        host=hosts[0]; received=0
        for i in range(count):
            t0=time.time()
            try:
                socket.setdefaulttimeout(2)
                socket.create_connection((host,80),timeout=2).close()
                ms=(time.time()-t0)*1000; received+=1
                print(f"  64 bytes from {host}: seq={i} time={ms:.2f} ms")
            except Exception:
                print(f"  Request timeout for seq {i}")
            if i<count-1: time.sleep(0.5)
        lost=count-received
        print(f"\n  --- {host} ping statistics ---")
        print(f"  {count} packets transmitted, {received} received, "
              f"{lost/count*100:.0f}% packet loss\n")

    def _c_nslookup(self, args):
        "nslookup <hostname>"
        if not args: self._err("nslookup: missing host"); return
        try:
            ip=socket.gethostbyname(args[0])
            print(f"  Server:   (system resolver)")
            print(f"  Name:     {args[0]}")
            print(f"  Address:  {ip}")
        except Exception as e: self._err(f"nslookup: {e}")

    def _c_dig(self, args):
        "dig <hostname> — basic DNS lookup"
        if not args: self._err("dig: missing host"); return
        try:
            info=socket.getaddrinfo(args[0],None)
            print(f"\n  ;; ANSWER SECTION:")
            for item in info:
                print(f"  {args[0]:<30} IN  {item[0].name:<8} {item[4][0]}")
            print()
        except Exception as e: self._err(f"dig: {e}")

    def _c_curl(self, args):
        "curl <url> [-o file] [-s]"
        if self.rc.get("sandbox.net_access","1") != "1":
            self._warn("Network access disabled"); return
        silent="-s" in args; out_file=None
        if "-o" in args:
            try: out_file=args[args.index("-o")+1]
            except Exception: pass
        urls=[a for a in args if not a.startswith("-") and a!=out_file and "://" in a]
        if not urls: self._err("curl: missing URL"); return
        try:
            import requests
            r=requests.get(urls[0],timeout=10)
            if out_file:
                p=self._resolve(out_file)
                if p:
                    with open(p,"wb") as fh: fh.write(r.content)
                    self._ok(f"  → saved {len(r.content)} bytes to {out_file}")
            elif not silent:
                print(r.text[:4000])
        except ImportError: self._warn("requests package required")
        except Exception as e: self._err(f"curl: {e}")

    def _c_fetch(self, args): "fetch — alias for curl"; self._c_curl(args)

    # ─────────────────────────────────────────────────────────────────────────
    # CONFIG management
    # ─────────────────────────────────────────────────────────────────────────

    def _c_cfg(self, args):
        "cfg get|set|list|reload|save  [file] [key] [value]"
        cfg_files = {
            "global": _GLOBAL_CFG_PATH,
            "local":  _LOCAL_CFG_PATH,
            "sysctl": get_path("etc","sysctl.conf"),
        }
        if not args: self._err("cfg: subcommand required: get|set|list|reload|save"); return
        sub=args[0].lower()

        if sub=="list":
            target=args[1].lower() if len(args)>1 else "global"
            p=cfg_files.get(target)
            if not p: self._err(f"cfg list: unknown file {target!r}"); return
            data=_load_cfg(p)
            print(f"\n  [{target}]  {p}")
            for k,v in sorted(data.items()): print(f"    {k:40s} = {v}")
            print()

        elif sub=="get":
            target=args[1] if len(args)>1 else "global"
            key=args[2] if len(args)>2 else None
            p=cfg_files.get(target,_GLOBAL_CFG_PATH)
            data=_load_cfg(p)
            if key:
                v=data.get(key)
                if v: print(f"  {key} = {v}")
                else: self._err(f"cfg get: {key!r}: not found in {target}")
            else:
                for k,v in sorted(data.items()): print(f"  {k} = {v}")

        elif sub=="set":
            if not self._check_su("cfg set"): return
            target=args[1] if len(args)>1 else "global"
            if len(args)<4: self._err("cfg set: usage: cfg set <file> <key> <value>"); return
            key=args[2]; val=args[3]
            p=cfg_files.get(target)
            if not p: self._err(f"cfg set: unknown file {target!r}"); return
            data=_load_cfg(p); data[key]=val; _save_cfg(p,data)
            self.k.reload_cfg()
            self._ok(f"cfg: [{target}] {key} = {val}")

        elif sub=="reload":
            self.k.reload_cfg(); self._ok("config reloaded")

        elif sub=="save":
            target=args[1] if len(args)>1 else "global"
            self._info(f"cfg: {target} is saved on every 'cfg set' — nothing to do")

        else:
            self._err(f"cfg: unknown subcommand {sub!r}")

    # ─────────────────────────────────────────────────────────────────────────
    # PACKAGE management
    # ─────────────────────────────────────────────────────────────────────────

    def _c_pkg(self, args):
        "pkg list|info|run|kill|remove"
        if not args: self._err("pkg: list|info|run|kill|remove"); return
        sub=args[0].lower()
        apps_dir=get_path("apps","user_apps")

        if sub=="list":
            print(f"\n  {'Name':30s}  {'Size':>8}  Path")
            found=False
            for f in sorted(os.listdir(apps_dir) if os.path.isdir(apps_dir) else []):
                if not f.endswith(".vysico"): continue
                fp=os.path.join(apps_dir,f)
                meta=self.k._read_pkg_meta(fp)
                name=meta.get("name",f[:-7])
                size=os.path.getsize(fp)
                print(f"  {name:30s}  {size:>8}  {fp}"); found=True
            if not found: self._info("  (no packages)"); print()

        elif sub=="info":
            if len(args)<2: self._err("pkg info: <name>"); return
            for f in (os.listdir(apps_dir) if os.path.isdir(apps_dir) else []):
                if not f.endswith(".vysico"): continue
                fp=os.path.join(apps_dir,f)
                meta=self.k._read_pkg_meta(fp)
                if meta.get("name")==args[1] or f[:-7]==args[1]:
                    print(f"\n  Name    : {meta.get('name','?')}")
                    print(f"  Version : {meta.get('version','?')}")
                    try:
                        with zipfile.ZipFile(fp) as z:
                            print(f"  Files   : {', '.join(z.namelist())}")
                    except Exception: pass
                    print(f"  Path    : {fp}\n"); return
            self._err(f"pkg info: {args[1]!r}: not found")

        elif sub=="run":
            if len(args)<2: self._err("pkg run: <name> [-headless]"); return
            target=args[1]; headless="--headless" in args or "-headless" in args
            fp=None
            if os.path.isfile(target): fp=target
            else:
                for f in (os.listdir(apps_dir) if os.path.isdir(apps_dir) else []):
                    if not f.endswith(".vysico"): continue
                    full=os.path.join(apps_dir,f)
                    meta=self.k._read_pkg_meta(full)
                    if meta.get("name")==target or f[:-7]==target: fp=full; break
            if not fp: self._err(f"pkg run: {target!r}: not found"); return
            aid=self.k.launch_pkg(fp,headless=headless)
            if aid: self._ok(f"pkg run: {target!r} [{aid}] {'headless' if headless else 'GUI'}")
            else: self._err(f"pkg run: failed")

        elif sub=="kill":
            if len(args)<2: self._err("pkg kill: <app_id>"); return
            if self.k.kill_pkg(args[1]): self._ok(f"pkg kill: SIGTERM → {args[1]!r}")
            else: self._err(f"pkg kill: {args[1]!r}: not running")

        elif sub=="remove":
            if not self._check_su("pkg remove"): return
            if len(args)<2: self._err("pkg remove: <name>"); return
            for f in (os.listdir(apps_dir) if os.path.isdir(apps_dir) else []):
                if not f.endswith(".vysico"): continue
                fp=os.path.join(apps_dir,f)
                meta=self.k._read_pkg_meta(fp)
                if meta.get("name")==args[1] or f[:-7]==args[1]:
                    os.remove(fp); self._ok(f"pkg remove: {f} deleted"); return
            self._err(f"pkg remove: {args[1]!r}: not found")

        else:
            self._err(f"pkg: unknown subcommand {sub!r}")

    # ─────────────────────────────────────────────────────────────────────────
    # USER management
    # ─────────────────────────────────────────────────────────────────────────

    def _c_adduser(self, args):
        "adduser <name>  (su)"
        if not self._check_su("adduser"): return
        if not args: self._err("adduser: missing username"); return
        name=args[0]
        try:
            pwd1=getpass.getpass(f"  New password for {name!r}: ")
            pwd2=getpass.getpass(f"  Repeat password: ")
        except (EOFError,KeyboardInterrupt): print(); return
        if pwd1!=pwd2: self._err("adduser: passwords do not match"); return
        groups=["-G",args[args.index("-G")+1]] if "-G" in args else []
        ok=self.um.add_user(name,pwd1,groups)
        if ok: self._ok(f"adduser: user {name!r} created")
        else: self._err(f"adduser: {name!r} already exists")

    def _c_rmuser(self, args):
        "rmuser [-r] <name>  (su)"
        if not self._check_su("rmuser"): return
        remove_home="-r" in args
        names=[a for a in args if not a.startswith("-")]
        if not names: self._err("rmuser: missing username"); return
        try:
            self.um.remove_user(names[0],remove_home)
            self._ok(f"rmuser: {names[0]!r} removed")
        except PermissionError as e: self._err(str(e))
        except Exception as e: self._err(f"rmuser: {e}")

    def _c_passwd(self, args):
        "passwd [username]  (su to change others)"
        target=args[0] if args else self.k.get_cfg("profile_1_name","user")
        if args and not self._check_su("passwd"): return
        try:
            p1=getpass.getpass(f"  New password for {target!r}: ")
            p2=getpass.getpass("  Repeat: ")
        except (EOFError,KeyboardInterrupt): print(); return
        if p1!=p2: self._err("passwd: passwords do not match"); return
        # Update in users DB
        ok=self.um.change_password(target,p1)
        # Also update global.cfg if it's the main user
        main_user=self.k.get_cfg("profile_1_name","")
        if target==main_user and self._su:
            data=_load_cfg(_GLOBAL_CFG_PATH)
            data["profile_1_pass"]=p1
            _save_cfg(_GLOBAL_CFG_PATH,data)
            self.k.reload_cfg()
        if ok: self._ok(f"passwd: password updated for {target!r}")
        else: self._err(f"passwd: {target!r}: not found")

    def _c_usermod(self, args):
        "usermod -G <group> <user>  or  -d <home> <user>  (su)"
        if not self._check_su("usermod"): return
        if len(args)<3: self._err("usermod: -G <group> <user> or -d <home> <user>"); return
        flag,val,user=args[0],args[1],args[2]
        if flag=="-G":
            ok=self.um.add_to_group(user,val)
            if ok: self._ok(f"usermod: {user!r} added to group {val!r}")
            else: self._err(f"usermod: {user!r}: not found")
        elif flag=="-d":
            u=self.um.get_user(user)
            if u:
                u["home"]=val; self.um._save()
                self._ok(f"usermod: {user!r} home → {val!r}")
            else: self._err(f"usermod: {user!r}: not found")
        else: self._err(f"usermod: unknown flag {flag!r}")

    def _c_id(self, args):
        "id [user]"
        name=args[0] if args else self.k.get_cfg("profile_1_name","user")
        u=self.um.get_user(name)
        if u:
            g=",".join(u.get("groups",[]))
            print(f"  uid={u['uid']}({name}) gid={u['gid']}  groups={g}")
        else:
            print(f"  uid=1000({name}) gid=1000")

    def _c_groups(self, args):
        "groups [user]"
        name=args[0] if args else self.k.get_cfg("profile_1_name","user")
        u=self.um.get_user(name)
        if u: print("  "+(" ".join(u.get("groups",[]) or ["(none)"])))
        else: print("  users")

    def _c_who(self, _):
        "who — show logged-in users"
        user=self.k.get_cfg("profile_1_name","user")
        boot=datetime.fromtimestamp(_BOOT_TIME).strftime("%b %d %H:%M")
        print(f"  {user:12s}  console  {boot}")

    def _c_w(self, _):
        "w — who is doing what"
        self._c_who([]); self._c_uptime([])

    def _c_last(self, _):
        "last — recent logins"
        hist=get_path("var","log","shell_history")
        if os.path.isfile(hist):
            with open(hist,encoding="utf-8") as fh: lines=fh.readlines()
            for l in lines[-10:]: print(" ",l.rstrip())
        else: print("  (no history)")

    def _c_users(self, _):
        "users — list all sandbox users"
        print(f"\n  {'Name':20s}  {'UID':6}  {'Groups':30s}  Home")
        for u in self.um.list_users():
            g=",".join(u["groups"]) if u["groups"] else "-"
            print(f"  {u['name']:20s}  {u['uid']:6}  {g:30s}  {u['home']}")
        print()

    # ─────────────────────────────────────────────────────────────────────────
    # SERVICES
    # ─────────────────────────────────────────────────────────────────────────

    def _c_service(self, args):
        "service <name> start|stop|status|restart"
        services={"sheila":"Update checker","warden":"Memory warden"}
        if not args:
            for n,d in services.items(): print(f"  {n:20s}  {d}"); return
        name=args[0]; verb=args[1].lower() if len(args)>1 else "status"
        if name=="sheila":
            if verb in ("start","restart"):
                self._info("sheila: checking for updates…")
                self.k.check_updates(silent=False); self._ok("sheila: done")
            elif verb=="status": self._info("sheila: on-demand service")
            elif verb=="stop": self._info("sheila: nothing to stop")
            else: self._err(f"service: {verb!r}: unknown action")
        elif name=="warden":
            if verb in ("start","restart"):
                snap=self.warden.tick()
                self._ok(f"warden: running  CPU:{snap['cpu_pct']:.1f}%  RAM:{snap['ram_used_mb']:.0f}MB")
            elif verb=="status":
                print(self.warden.report())
            elif verb=="stop": self._info("warden: cannot be stopped")
            else: self._err(f"service: {verb!r}: unknown action")
        else:
            self._err(f"service: {name!r}: unknown service")

    def _c_rcctl(self, args):
        "rcctl — alias for service (OpenBSD style)"
        self._c_service(args)

    # ─────────────────────────────────────────────────────────────────────────
    # SANDBOX / WARDEN
    # ─────────────────────────────────────────────────────────────────────────

    def _c_warden(self, args):
        "warden status|report|tick|log  — sandbox resource warden"
        sub=args[0].lower() if args else "status"
        if sub=="status":
            snap=self.warden.tick()
            print(f"\n  Warden status — {datetime.now():%H:%M:%S}")
            print(f"  CPU         : {snap['cpu_pct']:>6.1f}%  "
                  f"(warn >{self.rc.get('sandbox.cpu_warn_pct')}%)")
            print(f"  RAM used    : {snap['ram_used_mb']:>8.1f} MB  "
                  f"/ {snap['ram_total_mb']:.0f} MB  ({snap['ram_pct']:.1f}%)")
            print(f"  RAM watch   : {self.rc.get('sandbox.ram_watch_mb')} MB threshold")
            print(f"  Disk used   : {snap['disk_used_mb']:>8.1f} MB  "
                  f"/ {snap['disk_quota_mb']:.0f} MB quota")
            print(f"  Swap used   : {snap['swap_used_mb']:>8.1f} MB  ({snap['swap_pct']:.1f}%)\n")
        elif sub=="report": print(self.warden.report())
        elif sub=="tick": self.warden.tick(); self._ok("warden: tick done")
        elif sub=="log":
            lp=get_path("var","log","warden.log")
            if os.path.isfile(lp):
                with open(lp,encoding="utf-8") as fh:
                    print("".join(fh.readlines()[-20:]),end="")
            else: self._info("(no warden log yet)")
        else: self._err(f"warden: unknown subcommand {sub!r}")

    def _c_sandbox(self, args):
        "sandbox status|clean|quota|limits  — sandbox management"
        sub=args[0].lower() if args else "status"
        if sub=="status":
            print(f"\n  Sandbox status")
            print(f"  BASE_DIR   : {BASE_DIR}")
            print(f"  Hostname   : {self.rc.get('kern.hostname')}")
            print(f"  Quota      : {self.rc.get('sandbox.disk_quota_gb')} GB  (max {_SANDBOX_DISK_MAX_GB:.0f} GB)")
            print(f"  Net access : {'yes' if self.rc.get('sandbox.net_access')=='1' else 'NO'}")
            print(f"  Exec       : {'yes' if self.rc.get('sandbox.allow_exec')=='1' else 'NO'}")
            print(f"  SecLevel   : {self.rc.get('kern.securelevel')}\n")
        elif sub=="clean":
            if not self._check_su("sandbox clean"): return
            tmp=get_path("apps","temp")
            removed=0
            for d in (os.listdir(tmp) if os.path.isdir(tmp) else []):
                fp=os.path.join(tmp,d)
                if os.path.isdir(fp):
                    shutil.rmtree(fp,ignore_errors=True); removed+=1
            self._ok(f"sandbox clean: {removed} temp dir(s) removed")
        elif sub=="quota": self._c_quota([])
        elif sub=="limits":
            print(f"\n  Sandbox limits")
            print(f"  Max disk    : {_SANDBOX_DISK_MAX_GB:.0f} GB  (hard system cap)")
            print(f"  Set quota   : {self.rc.get('sandbox.disk_quota_gb')} GB")
            print(f"  Max procs   : {self.rc.get('kern.maxproc')}")
            print(f"  Max files   : {self.rc.get('kern.maxfiles')}\n")
        else: self._err(f"sandbox: unknown subcommand {sub!r}")

    # ─────────────────────────────────────────────────────────────────────────
    # SESSION commands
    # ─────────────────────────────────────────────────────────────────────────

    def _c_whoami(self,_): print("root" if self._su else self.k.get_cfg("profile_1_name","user"))

    def _c_su(self, args):
        "su | su -l"
        if "-l" in args or "--lock" in args:
            if self._su: self._su=False; self._ok("Superuser mode deactivated.")
            else: self._warn("Not in superuser mode.")
            return
        if self._su: self._warn("Already root. Use 'su -l' to lock."); return
        try: pwd=getpass.getpass("Password: ")
        except (EOFError,KeyboardInterrupt): print(); return
        correct=self.k.get_cfg("profile_1_pass","")
        if pwd==correct:
            self._su=True; self._ok("Superuser mode activated.")
            self.k._dmesg("su: root session started"); log.info("TUI: su granted")
        else:
            self._err("su: Authentication failure"); log.warning("TUI: su failed")

    def _c_history(self, args):
        "history [-n N|-c]"
        if "-c" in args: self._hist.clear(); self._ok("history cleared"); return
        n=20
        if "-n" in args:
            try: n=int(args[args.index("-n")+1])
            except Exception: pass
        for i,l in enumerate(self._hist[-n:],start=max(1,len(self._hist)-n+1)):
            print(f"  {i:5}  {l}")

    def _c_alias(self, args):
        "alias [name=value]"
        if not args:
            for k,v in self._aliases.items(): print(f"  alias {k}={v!r}")
            return
        for a in args:
            if "=" in a:
                k,v=a.split("=",1); self._aliases[k]=v
            else:
                v=self._aliases.get(a)
                if v: print(f"  alias {a}={v!r}")
                else: self._err(f"alias: {a!r}: not found")

    def _c_unalias(self, args):
        "unalias <name>|-a"
        if "-a" in args: self._aliases.clear(); return
        for a in args:
            if a in self._aliases: del self._aliases[a]
            else: self._err(f"unalias: {a!r}: not found")

    def _c_set(self, args):
        "set [VAR=val]"
        if not args:
            for k,v in sorted(self._env_vars.items()): print(f"  {k}={v}")
            return
        for a in args:
            if "=" in a: k,v=a.split("=",1); self._env_vars[k]=v
            else: self._err(f"set: invalid syntax: {a!r}")

    def _c_export(self, args):
        "export VAR=val"
        for a in args:
            if "=" in a:
                k,v=a.split("=",1)
                self._env_vars[k]=v; os.environ[k]=v
            elif a in self._env_vars:
                os.environ[a]=self._env_vars[a]
            else: self._err(f"export: {a!r}: not set")

    def _c_unset(self, args):
        "unset VAR"
        for a in args:
            self._env_vars.pop(a,None)
            os.environ.pop(a,None)

    def _c_printenv(self, args):
        "printenv [VAR]"
        if args:
            v=self._env_vars.get(args[0]) or os.environ.get(args[0],"")
            print(v)
        else:
            for k,v in sorted({**os.environ,**self._env_vars}.items()):
                print(f"  {k}={v}")

    def _c_env(self, args): "env — print environment"; self._c_printenv([])

    def _c_which(self, args):
        "which <cmd>"
        if not args: self._err("which: missing cmd"); return
        for cmd in args:
            if cmd in self._cmds: print(f"  {cmd}: built-in")
            elif cmd in self._aliases: print(f"  {cmd}: aliased to {self._aliases[cmd]!r}")
            else: self._err(f"  {cmd}: not found")

    def _c_type(self, args): "type — same as which"; self._c_which(args)

    def _c_sleep(self, args):
        "sleep <seconds>"
        if not args: self._err("sleep: missing operand"); return
        try: time.sleep(float(args[0]))
        except Exception as e: self._err(f"sleep: {e}")

    def _c_watch(self, args):
        "watch [-n interval] <cmd> — repeat command every N seconds"
        interval=2.0
        if "-n" in args:
            try: interval=float(args[args.index("-n")+1]); args=args[2:]
            except Exception: pass
        if not args: self._err("watch: missing command"); return
        cmd=args[0]; handler=self._cmds.get(cmd.lower())
        if not handler: self._err(f"watch: {cmd!r}: not found"); return
        cmd_args=args[1:]
        self._info(f"watch: every {interval}s — Ctrl-C to stop")
        try:
            while True:
                os.system("clear")
                print(f"  watch — {datetime.now():%H:%M:%S}  every {interval}s\n")
                handler(cmd_args)
                time.sleep(interval)
        except KeyboardInterrupt: print()

    def _c_bc(self, args):
        "bc <expression> — basic calculator"
        if not args: self._err("bc: missing expression"); return
        expr=" ".join(args)
        try:
            # Safe eval with math
            allowed={"__builtins__":{}}
            allowed.update(vars(math))
            result=eval(expr,allowed)
            print(f"  {result}")
        except Exception as e: self._err(f"bc: {e}")

    def _c_yes(self, args):
        "yes [string] — output string repeatedly (Ctrl-C to stop)"
        s=" ".join(args) if args else "y"
        try:
            while True: print(s)
        except KeyboardInterrupt: pass

    def _c_true(self, _):
        "true — exit 0"
        pass

    def _c_false(self, _):
        "false — exit 1"
        pass

    def _c_banner(self, args):
        "banner <text> — large ASCII text"
        text=" ".join(args) if args else "vLaunch"
        # Simple block letters
        BLOCK = {c:" ".join(["█"*5 for _ in range(5)]) for c in text}
        print(f"\n  {'  '.join(['█'+' '+c+' '+'█' for c in text.upper()])}\n")

    def _c_clear(self, _):
        "clear — clear the screen"
        os.system("clear")

    def _c_poweroff(self, args):
        "poweroff [-t N] [-r] [-f] [-h]"
        delay=0; reboot="-r" in args; force="-f" in args; dry="-h" in args
        if "-t" in args:
            try: delay=int(args[args.index("-t")+1])
            except Exception: self._err("poweroff: -t requires integer"); return
        action="reboot" if reboot else "halt"
        self._warn(f"System going {'down for reboot' if reboot else 'offline'} in {delay}s …")
        if dry: self._info(f"poweroff dry-run: action={action} delay={delay}s force={force}"); return
        if delay>0:
            for r in range(delay,0,-1):
                print(f"\r  Shutdown in {r:3d}s …",end="",flush=True); time.sleep(1)
            print()
        if not force:
            for aid,info in list(self.k._running_apps.items()):
                try: info["proc"].terminate(); self._info(f"  terminated {info['name']!r}")
                except Exception: pass
        _revoke_token()
        self.k._dmesg(f"kernel: {action} by user")
        log.info(f"poweroff: {action}")
        print("KERNEL_HALT" if not reboot else "KERNEL_REBOOT")
        raise SystemExit(0)

    def _c_reboot(self, args): "reboot [-t N] [-f]"; self._c_poweroff(["-r"]+args)

    def _c_shutdown(self, args):
        "shutdown [-r|-h] [+minutes|now] [message]"
        reboot="-r" in args; halt="-h" in args
        delay=0
        for a in args:
            if a.startswith("+"):
                try: delay=int(a[1:])*60
                except Exception: pass
            elif a.lower()!="now" and not a.startswith("-"):
                self._info(f"shutdown: broadcast: {a}")
        if reboot: self._c_poweroff(["-r","-t",str(delay)])
        else: self._c_poweroff(["-t",str(delay)])

    # ─────────────────────────────────────────────────────────────────────────
    # HELP / MAN
    # ─────────────────────────────────────────────────────────────────────────

    def _c_help(self, _):
        "help — command reference"
        W=16
        sections=[
            ("System info",  ["uname","hostname","date","cal","uptime","dmesg",
                               "sysctl","systat","vmstat","memstat","swapinfo","iostat","cpuinfo"]),
            ("Processes",    ["ps","top","kill","pkill","pgrep","nice","renice",
                               "jobs","bg","fg","wait"]),
            ("Disk/FS",      ["df","du","ls","ll","la","cd","pwd","cat","more","less",
                               "head","tail","touch","mkdir","rm","cp","mv","ln",
                               "find","locate","stat","file","chmod","chown","quota","fsck"]),
            ("Text tools",   ["echo","printf","grep","egrep","wc","sort","uniq","cut",
                               "paste","tr","sed","awk","diff","strings","xxd",
                               "base64","md5","sha256","tee","split"]),
            ("Network",      ["ifconfig","netstat","ping","nslookup","dig","curl","fetch"]),
            ("Config",       ["cfg"]),
            ("Packages",     ["pkg"]),
            ("Users",        ["adduser","rmuser","passwd","usermod","id","groups",
                               "who","w","last","users"]),
            ("Services",     ["service","rcctl"]),
            ("Sandbox",      ["warden","sandbox"]),
            ("Session",      ["whoami","su","history","alias","unalias","set","export",
                               "unset","printenv","env","which","type","sleep","watch",
                               "bc","yes","banner","clear","poweroff","reboot","shutdown",
                               "help","man"]),
        ]
        print()
        for title, cmds in sections:
            self._bold(f"  {title}")
            for i in range(0,len(cmds),5):
                print("    "+"  ".join(f"{c:{W}s}" for c in cmds[i:i+5]))
        print()
        self._info("  man <cmd> for details   |   100+ commands available")
        print()

    def _c_man(self, args):
        "man <command>"
        if not args: self._err("man: missing command"); return
        h=self._cmds.get(args[0].lower())
        if not h: self._err(f"man: {args[0]!r}: no entry"); return
        doc=h.__doc__ or "(no description)"
        print(f"\n  NAME\n      {args[0]}\n\n  DESCRIPTION")
        for line in textwrap.dedent(doc).strip().splitlines():
            print(f"      {line}")
        print()


# ─────────────────────────────────────────────────────────────────────────────
# GUI launcher
# ─────────────────────────────────────────────────────────────────────────────

def _start_gui(kernel: Kernel):
    """
    Spawn gui.py as a child subprocess of the kernel process.

    Dependency chain:
        kernel.py  (parent process, PID = _VLAUNCH_KERNEL_PID)
            └── gui.py  (child subprocess)
                    └── .vysico apps  (grandchild subprocesses)

    If the kernel exits for any reason, the OS delivers SIGHUP to the gui
    child, and gui.py's own heartbeat timer also quits the Qt event loop.

    The kernel blocks here (proc.wait()) until the GUI subprocess exits,
    so the kernel is always "open" as long as the desktop is running.
    """
    print("KERNEL_READY", flush=True)

    gui_py = os.path.join(_HERE, "gui.py")
    if not os.path.isfile(gui_py):
        kernel_panic(f"gui.py not found at {gui_py!r}", fatal=True)
        return

    env = os.environ.copy()
    env.update({
        "_VLAUNCH_STARTED":    "1",
        "_VLAUNCH_GUI":        "1",
        "_VLAUNCH_TOKEN":      SESSION_TOKEN,
        "_VLAUNCH_KERNEL_PID": str(os.getpid()),
        "VLAUNCH_HOME":        BASE_DIR,
    })

    python = kernel._venv_python()
    log.info(f"Starting GUI subprocess: {python!r} {gui_py!r}")

    try:
        gui_proc = subprocess.Popen([python, gui_py], env=env)
        log.info(f"GUI child PID: {gui_proc.pid}")
        kernel._dmesg(f"gui.py spawned pid={gui_proc.pid}")

        # ── Kernel stays alive, monitoring the GUI child ──────────────────
        # Also keep the kernel's warden ticking while GUI is running.
        while True:
            try:
                rc = gui_proc.wait(timeout=5)
                log.info(f"GUI child exited rc={rc}")
                kernel._dmesg(f"gui.py exited rc={rc}")
                break
            except subprocess.TimeoutExpired:
                # GUI still running — tick the warden
                kernel.warden_tick()
                kernel.poll_apps()

    except KeyboardInterrupt:
        log.info("Kernel interrupted — terminating GUI child")
        try:
            gui_proc.terminate()
            gui_proc.wait(timeout=3)
        except Exception:
            pass
    except Exception as exc:
        log.error(f"_start_gui error: {exc}")
        kernel_panic(f"GUI process error: {exc}", fatal=False)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def _parse() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="kernel.py", description="vLaunch Kernel")
    p.add_argument("--gui",  type=int, choices=[0, 1], default=None, metavar="{0|1}")
    p.add_argument("--tty",  action="store_true")
    p.add_argument("_legacy", nargs="?", help=argparse.SUPPRESS)
    return p.parse_args()


def _use_gui(args, kernel: Kernel) -> bool:
    if args.tty:                    return False
    if args.gui is not None:        return args.gui == 1
    if args._legacy == "-auth8354": return True
    if args._legacy == "-auth8355": return False
    return kernel.get_local("gui", "1") == "1"


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    args   = _parse()
    kernel = Kernel()

    if not kernel.boot():
        log.critical("Boot failed")
        print("KERNEL_PANIC: boot failed", flush=True)
        _revoke_token()
        sys.exit(1)

    if _use_gui(args, kernel):
        _start_gui(kernel)
    else:
        print("KERNEL_READY", flush=True)
        TUI(kernel).run()

    _revoke_token()
