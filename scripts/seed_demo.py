"""Seed a demo org/user graph into the local DB so you have accounts to log in as. Idempotent:
re-running is a no-op if the demo users already exist.

    python3 scripts/seed_demo.py            # DB: ./hs.db (or $HS_DB)

Then log in on the running site (python3 scripts/serve_local.py):
  • Agent console  http://127.0.0.1:8000/          → X-User-Id:  op   (Justnano operator)
  • Customer app   http://127.0.0.1:8000/customer   → X-User-Id:  uc   (Acme customer)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db, repo
from app.config import load_env


def main():
    load_env()
    db_path = os.environ.get("HS_DB", "hs.db")
    conn = db.connect(db_path)
    db.init_db(conn)

    if conn.execute("SELECT 1 FROM users WHERE id='op'").fetchone():
        print(f"demo data already present in {db_path}. Log in as 'op' (agent) / 'uc' (customer).")
        return

    # agent org + operator
    repo.create_org(conn, "Justnano", "agent", id="agent")
    repo.create_user(conn, "Hughson (agent)", "email", "op@justnanoinc.com", id="op")
    repo.add_member(conn, "op", "agent", "operator")

    # customer org + member
    repo.create_org(conn, "Acme Shipping", "customer", id="cust")
    repo.create_user(conn, "Acme Customer", "email", "uc@acme.com", id="uc")
    repo.add_member(conn, "uc", "cust", "member")

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
    print("\nLog in — Agent console: X-User-Id 'op'   |   Customer app: X-User-Id 'uc'")


if __name__ == "__main__":
    main()
