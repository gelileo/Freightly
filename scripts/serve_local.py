"""Run the app locally: serves the agent console (/) and customer app (/customer) plus the JSON
API against a PERSISTENT sqlite file, so data survives restarts. Frontends call /api/* (same as
on Vercel); the server strips the prefix.

    python3 scripts/serve_local.py                 # http://127.0.0.1:8000  (DB: ./hs.db)
    HS_DB=/tmp/hs.db PORT=8000 python3 scripts/serve_local.py

By default it uses the deterministic FAKE llm/transport/wechat so nothing external is called and
approving a draft does NOT send real email. Set USE_REAL_SERVICES=1 to wire real
Gemini/Alibaba/WeChat from .env (approving an email THEN sends for real)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db, server
from app.config import load_env


def main():
    load_env()
    db_path = os.environ.get("HS_DB", "hs.db")
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    web_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")

    # ensure the schema exists (CREATE TABLE IF NOT EXISTS — idempotent)
    db.init_db(db.connect(db_path))

    if os.environ.get("USE_REAL_SERVICES"):
        from app import config
        llm, transport, wechat = config.make_llm(), config.make_transport(), config.make_wechat()
        print("services: REAL (Gemini/Alibaba/WeChat from .env) — approving email SENDS for real")
    else:
        from engine.llm import FakeLlmClient
        from app.transport import FakeTransport
        from app.wechat import FakeWeChatClient
        llm, transport, wechat = FakeLlmClient(), FakeTransport(), FakeWeChatClient()
        print("services: FAKE (no external calls; approving email does NOT send). "
              "Set USE_REAL_SERVICES=1 for real.")

    print(f"DB: {db_path}   →  http://{host}:{port}/  (agent)   http://{host}:{port}/customer")
    print("Seed demo users first:  python3 scripts/seed_demo.py")
    # local dev trusts X-User-Id for curl/manual testing; production (Vercel) does NOT — set
    # TRUST_X_USER_ID=0 here to exercise the production lock-down locally.
    trust = os.environ.get("TRUST_X_USER_ID", "1") not in ("0", "false", "False", "")
    server.serve(lambda: db.connect(db_path), llm=llm, transport=transport, wechat=wechat,
                 host=host, port=port, webhook_secret=os.environ.get("WEBHOOK_SECRET", "localdev"),
                 web_root=web_root, trust_user_header=trust)


if __name__ == "__main__":
    main()
