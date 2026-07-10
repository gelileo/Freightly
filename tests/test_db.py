from app.db import connect, init_db


def test_init_db_creates_tables():
    conn = connect(":memory:")
    init_db(conn)
    names = {r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"users", "orgs", "memberships", "engagements", "brokers",
            "broker_accounts"} <= names


def test_foreign_keys_enforced():
    conn = connect(":memory:")
    init_db(conn)
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
