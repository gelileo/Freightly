"""Set (or reset) the password for an email-login user (agent operator). Admin/CLI task —
there is no self-serve signup.

    python3 scripts/set_agent_password.py <email> <password>          # DB: ./hs.db (or $HS_DB)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db, auth
from app.config import load_env


def main():
    if len(sys.argv) != 3:
        print("usage: python3 scripts/set_agent_password.py <email> <password>")
        sys.exit(2)
    email, password = sys.argv[1], sys.argv[2]
    load_env()
    conn = db.connect(os.environ.get("HS_DB", "hs.db"))
    db.init_db(conn)
    row = conn.execute("SELECT id FROM users WHERE auth_kind='email' AND auth_id=?",
                       (email,)).fetchone()
    if not row:
        print(f"no email-login user with email {email!r} (onboard/seed one first)")
        sys.exit(1)
    auth.set_password(conn, row["id"], password)
    print(f"password set for {email} (user id {row['id']})")


if __name__ == "__main__":
    main()
