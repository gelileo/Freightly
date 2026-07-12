"""Seed a demo org/user graph into the local DB so you have accounts to log in as. Idempotent:
re-running is a no-op if the demo users already exist.

    python3 scripts/seed_demo.py            # DB: ./hs.db (or $HS_DB)

Then log in on the running site (python3 scripts/serve_local.py):
  • Agent console  http://127.0.0.1:8000/          → email op@justnanoinc.com / password agent-demo
  • Customer app   http://127.0.0.1:8000/customer   → email uc@acme.com       / password customer-demo
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db, repo, auth
from app.config import load_env

DEMO_AGENT_PW = "agent-demo"
DEMO_CUSTOMER_PW = "customer-demo"


def main():
    load_env()
    db_path = os.environ.get("HS_DB", "hs.db")
    conn = db.connect(db_path)
    db.init_db(conn)

    if conn.execute("SELECT 1 FROM users WHERE id='op'").fetchone():
        print(f"demo data already present in {db_path}. Agent: op@justnanoinc.com / '{DEMO_AGENT_PW}'"
              f"; Customer: uc@acme.com / '{DEMO_CUSTOMER_PW}' (reset via scripts/set_agent_password.py).")
        return

    # agent org + operator
    repo.create_org(conn, "Justnano", "agent", id="agent")
    repo.create_user(conn, "Hughson (agent)", "email", "op@justnanoinc.com", id="op")
    repo.add_member(conn, "op", "agent", "admin")   # founding admin (can add operators)
    auth.set_password(conn, "op", DEMO_AGENT_PW)     # agent logs in with email + password

    # customer org + member
    repo.create_org(conn, "Acme Shipping", "customer", id="cust")
    repo.create_user(conn, "Acme Customer", "email", "uc@acme.com", id="uc")
    repo.add_member(conn, "uc", "cust", "member")
    auth.set_password(conn, "uc", DEMO_CUSTOMER_PW)   # customer logs in with email + password too

    # active engagement between them
    repo.create_engagement(conn, "cust", "agent", id="eng")
    repo.approve_engagement(conn, "eng")

    # a broker + the agent's connected mailbox (uses the real Alibaba mailbox if configured)
    repo.create_broker(conn, "Priority-1", id="p1")
    mailbox = os.environ.get("SMTP_ADDRESS", "hs@justnanoinc.com")
    broker_email = os.environ.get("TESTING_BROKER_EMAIL", "broker@example.com")
    repo.connect_broker_account(conn, "agent", "p1", mailbox=mailbox,
                                broker_email=broker_email, id="ba")

    print(f"seeded {db_path}:")
    print("  agent org 'Justnano' (id=agent), operator user id='op'")
    print("  customer org 'Acme Shipping' (id=cust), member user id='uc'")
    print("  active engagement 'eng'; broker 'Priority-1' via mailbox", mailbox)
    print("\nLog in (both use email + password now) —")
    print(f"  Agent console (/):        email 'op@justnanoinc.com'  password '{DEMO_AGENT_PW}'")
    print(f"  Customer app (/customer): email 'uc@acme.com'          password '{DEMO_CUSTOMER_PW}'")
    print("  (reset any password: python3 scripts/set_agent_password.py <email> <pw>)")


if __name__ == "__main__":
    main()
