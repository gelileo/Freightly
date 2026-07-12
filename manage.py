#!/usr/bin/env python3
"""Interactive manager for the HS app — the single entry point to run everything locally.

    python3 manage.py

Two local processes are managed (started detached, tracked by PID files under .run/):
  • web     — scripts/serve_local.py : agent console (/) + customer app (/customer) + JSON API
  • poller  — python -m app.inbound  : IMAP inbound (broker replies → cases); needs real mailbox

Plus: start/stop each or all, a status view (process state + DB counts), seed/reset demo data,
and a web-services mode toggle (fake = no external calls; real = Gemini + Alibaba from .env).
"""
import os
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN = ROOT / ".run"
RUN.mkdir(exist_ok=True)
DB_PATH = os.environ.get("HS_DB", str(ROOT / "hs.db"))
PORT = int(os.environ.get("PORT", "8000"))
VENV_PY = ROOT / ".venv" / "bin" / "python"
SYS_PY = sys.executable

MODE = "fake"          # web services: "fake" (offline) | "real" (Gemini + Alibaba from .env)

SERVICES = {
    "web": "Web app (agent + customer + API)",
    "poller": "Inbound mail poller",
}


# --- process tracking -----------------------------------------------------------

def _pidfile(name):
    return RUN / f"{name}.pid"


def _logfile(name):
    return RUN / f"{name}.log"


def _read_pid(name):
    f = _pidfile(name)
    if not f.exists():
        return None
    try:
        return int(f.read_text().strip())
    except ValueError:
        return None


def _alive(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True      # exists but owned by another user → still alive


def _running(name):
    pid = _read_pid(name)
    if pid and _alive(pid):
        return pid
    if _pidfile(name).exists():
        _pidfile(name).unlink()      # stale pidfile
    return None


def _build(name):
    """Return (python_exe, args, env_overrides) for a service, honoring MODE."""
    env = {"HS_DB": DB_PATH}
    if name == "web":
        env["PORT"] = str(PORT)
        if MODE == "real":
            env["USE_REAL_SERVICES"] = "1"
            py = str(VENV_PY) if VENV_PY.exists() else SYS_PY
        else:
            env.pop("USE_REAL_SERVICES", None)
            py = SYS_PY
        return py, ["scripts/serve_local.py"], env
    if name == "poller":
        py = str(VENV_PY) if VENV_PY.exists() else SYS_PY   # real Gemini summarize → venv
        return py, ["-m", "app.inbound"], env
    raise KeyError(name)


def start(name):
    if _running(name):
        print(f"  {name} already running (pid {_read_pid(name)}).")
        return
    if name == "poller" and not VENV_PY.exists():
        print("  ! poller needs the .venv (google-genai) — create it first (see docs/LOCAL_E2E_GUIDE.md).")
        return
    py, args, env = _build(name)
    log = open(_logfile(name), "a")
    proc = subprocess.Popen([py, *args], cwd=str(ROOT), env={**os.environ, **env},
                            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    _pidfile(name).write_text(str(proc.pid))
    time.sleep(1.2)
    if not _alive(proc.pid):
        print(f"  ✗ {name} exited immediately — last log lines:")
        _tail(name)
        _pidfile(name).unlink(missing_ok=True)
        return
    if name == "web":
        print(f"  ✓ web started (pid {proc.pid}, {MODE} mode)  →  http://127.0.0.1:{PORT}/  "
              f"(agent)   http://127.0.0.1:{PORT}/customer")
    else:
        print(f"  ✓ poller started (pid {proc.pid})  — polling the mailbox every ~60s")


def stop(name):
    pid = _running(name)
    if not pid:
        print(f"  {name} not running.")
        return
    try:
        os.killpg(os.getpgid(pid), signal.SIGTERM)
    except ProcessLookupError:
        pass
    for _ in range(20):
        if not _alive(pid):
            break
        time.sleep(0.1)
    _pidfile(name).unlink(missing_ok=True)
    print(f"  ✓ {name} stopped.")


def _tail(name, n=8):
    f = _logfile(name)
    if f.exists():
        lines = f.read_text(errors="replace").splitlines()[-n:]
        for ln in lines:
            print("      " + ln)


# --- status ---------------------------------------------------------------------

def _db_counts():
    if not Path(DB_PATH).exists():
        return None
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row

    def one(sql):
        try:
            return c.execute(sql).fetchone()[0]
        except sqlite3.OperationalError:
            return "?"
    counts = {
        "orgs": one("SELECT COUNT(*) FROM orgs"),
        "agent_orgs": one("SELECT COUNT(*) FROM orgs WHERE type='agent'"),
        "customer_orgs": one("SELECT COUNT(*) FROM orgs WHERE type='customer'"),
        "users": one("SELECT COUNT(*) FROM users"),
        "engagements": one("SELECT COUNT(*) FROM engagements"),
        "active_engagements": one("SELECT COUNT(*) FROM engagements WHERE status='active'"),
        "brokers": one("SELECT COUNT(*) FROM brokers"),
        "cases": one("SELECT COUNT(*) FROM cases"),
        "messages": one("SELECT COUNT(*) FROM messages"),
    }
    c.close()
    return counts


def show_status():
    print("\n── Status ──────────────────────────────────────────────")
    print(f"  web mode: {MODE}   DB: {DB_PATH}   port: {PORT}")
    for name, label in SERVICES.items():
        pid = _running(name)
        state = f"running (pid {pid})" if pid else "stopped"
        print(f"  {label:<34} {state}")
        if pid and name == "web":
            print(f"      → http://127.0.0.1:{PORT}/  |  /customer")
    counts = _db_counts()
    print("  ── data ──")
    if counts is None:
        print(f"    (no DB at {DB_PATH} — use 'Seed / reset demo data')")
    else:
        print(f"    orgs: {counts['orgs']}  (agents {counts['agent_orgs']}, "
              f"customers {counts['customer_orgs']})")
        print(f"    users: {counts['users']}   brokers: {counts['brokers']}")
        print(f"    engagements: {counts['engagements']} "
              f"(active {counts['active_engagements']})")
        print(f"    cases: {counts['cases']}   messages: {counts['messages']}")
    print("─────────────────────────────────────────────────────────\n")


# --- seed / reset ---------------------------------------------------------------

def _run_seed():
    r = subprocess.run([SYS_PY, "scripts/seed_demo.py"], cwd=str(ROOT),
                       env={**os.environ, "HS_DB": DB_PATH})
    return r.returncode == 0


def seed_menu():
    while True:
        print("\n  Seed / reset demo data")
        print("    1) Seed demo data (create if absent)")
        print("    2) Reset (delete DB, then reseed)")
        print("    0) Back")
        ch = input("  seed> ").strip()
        if ch == "1":
            _run_seed()
        elif ch == "2":
            if _running("web") or _running("poller"):
                print("  ! stop web/poller first (they hold the DB).")
                continue
            if Path(DB_PATH).exists():
                Path(DB_PATH).unlink()
                print(f"  deleted {DB_PATH}")
            _run_seed()
        elif ch == "0":
            return


# --- menus ----------------------------------------------------------------------

def pick_service(verb):
    print(f"\n  {verb} which app?")
    print("    1) Web app (agent + customer + API)")
    print("    2) Inbound mail poller")
    print("    0) Back")
    ch = input(f"  {verb.lower()}> ").strip()
    return {"1": "web", "2": "poller"}.get(ch)


def main():
    global MODE
    print(__doc__.strip().splitlines()[0])
    while True:
        print("\n=== HS app manager ===")
        print("  1) Start an app…")
        print("  2) Stop an app…")
        print("  3) Start ALL")
        print("  4) Stop ALL")
        print("  5) Status")
        print("  6) Seed / reset demo data…")
        print(f"  7) Toggle web mode (currently: {MODE})")
        print("  q) Quit")
        try:
            ch = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            ch = "q"
        if ch == "1":
            s = pick_service("Start")
            if s:
                start(s)
        elif ch == "2":
            s = pick_service("Stop")
            if s:
                stop(s)
        elif ch == "3":
            for s in SERVICES:
                start(s)
        elif ch == "4":
            for s in SERVICES:
                stop(s)
        elif ch == "5":
            show_status()
        elif ch == "6":
            seed_menu()
        elif ch == "7":
            MODE = "real" if MODE == "fake" else "fake"
            print(f"  web mode → {MODE}"
                  + ("  (approving a broker email will SEND for real)" if MODE == "real" else ""))
            if _running("web"):
                print("  (restart the web app for the mode change to take effect)")
        elif ch == "q":
            print("bye — running apps keep running; use Stop ALL to shut them down.")
            return
        else:
            print("  ?")


if __name__ == "__main__":
    main()
