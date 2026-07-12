"""Standalone validation of the libSQL/Turso backend adapter (app.db._LibsqlConnection) against
a local `file:` DB, driving it through the real repo/cases code. Run with a Python that has
libsql-client installed:  LIBSQL_URL=file:/tmp/hs_verify.db .venv/bin/python scripts/verify_libsql.py
Not part of the pytest suite (libsql-client's sync-over-async client can stall pytest teardown);
this hard-exits when done. The stdlib-sqlite suite remains the correctness baseline."""
import os, sqlite3, sys, tempfile

os.environ.setdefault("LIBSQL_URL", "file:" + tempfile.mkdtemp() + "/hs_verify.db")
os.environ.pop("LIBSQL_AUTH_TOKEN", None)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import db, repo, cases

fails = []
def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        fails.append(name)

c = db.connect(); db.init_db(c)
check("backend is libSQL adapter", type(c).__name__ == "_LibsqlConnection")

repo.create_org(c, "Cust", "customer", id="cust")
repo.create_org(c, "Agent", "agent", id="agent")
u = repo.create_user(c, "wx:a", "wechat", "openid-a", union_id="uni")
repo.add_member(c, u.id, "cust", "member")
check("is_member", repo.is_member(c, u.id, "cust"))
found = repo.user_by_auth_id(c, "wechat", "openid-a")
check("row['col'] dict access + union_id", found is not None and found.union_id == "uni")

repo.create_engagement(c, "cust", "agent", id="eng"); repo.approve_engagement(c, "eng")
case = cases.create_case(c, agent_org_id="agent", customer_org_id="cust", origin="customer",
                         bol="60114338678", issue_type="pickup")
cases.transition(c, case.id, "DRAFTING", actor="t", action="x")
m = cases.add_message(c, case_id=case.id, party="agent", channel="email", lang="en",
                      body="hi", status="pending_approval")
check("add_message + get_message", cases.get_message(c, m.id).body == "hi")

# explicit rollback undoes only the manual insert (create_org above was committed)
c.execute("INSERT INTO orgs (id, name, type) VALUES ('x','X','customer')")
c.rollback()
check("rollback undoes uncommitted write",
      c.execute("SELECT COUNT(*) n FROM orgs WHERE id='x'").fetchone()["n"] == 0)

# UNIQUE violation surfaces as sqlite3.IntegrityError (so app code catches it uniformly)
try:
    repo.add_member(c, u.id, "cust", "member")
    check("duplicate membership raises IntegrityError", False)
except sqlite3.IntegrityError:
    check("duplicate membership raises IntegrityError", True)
except Exception as e:
    check(f"duplicate membership raises IntegrityError (got {type(e).__name__})", False)

print("\n" + ("ALL PASS" if not fails else f"FAILURES: {fails}"))
sys.stdout.flush()
os._exit(0 if not fails else 1)   # hard-exit: libsql-client leaves a bg thread that stalls a normal exit
