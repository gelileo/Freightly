from app.db import connect, init_db
from app import repo, cases
from engine.llm import FakeLlmClient
from app.inbound import poll_once

LLM = FakeLlmClient()
MB = "hs@justnanoinc.com"


def _db():
    c = connect(":memory:"); init_db(c); return c


def test_imap_state_table_exists():
    c = _db()
    cols = {r["name"] for r in c.execute("PRAGMA table_info(imap_state)")}
    assert {"mailbox", "last_uid", "uidvalidity"} <= cols


class FakeImap:
    """Canned mailbox keyed by UID; read-only by construction (no flag writes exist)."""
    def __init__(self, msgs, uidvalidity="100"):
        self.msgs = dict(msgs)
        self._uv = uidvalidity

    def uidvalidity(self): return self._uv
    def max_uid(self): return max(self.msgs) if self.msgs else 0
    def search_uids_after(self, last): return sorted(u for u in self.msgs if u > last)
    def fetch_raw(self, uid): return self.msgs[uid]


def _seed_case_awaiting(conn):
    repo.create_org(conn, "Cust", "customer", id="cust")
    repo.create_org(conn, "Agent", "agent", id="agent")
    repo.create_engagement(conn, "cust", "agent", id="eng"); repo.approve_engagement(conn, "eng")
    repo.create_broker(conn, "P1", id="p1")
    repo.connect_broker_account(conn, "agent", "p1", mailbox=MB, broker_email="b@x.com", id="ba")
    c = cases.create_case(conn, agent_org_id="agent", customer_org_id="cust", origin="customer",
                          broker_account_id="ba", bol="60114338678", issue_type="pickup",
                          mail_thread_id="<root@justnanoinc.com>")
    cases.transition(conn, c.id, "DRAFTING", actor="t", action="x")
    cases.add_message(conn, case_id=c.id, party="agent", channel="email", lang="en",
                      body="draft", status="pending_approval")
    cases.transition(conn, c.id, "PENDING_APPROVAL", actor="t", action="x")
    cases.transition(conn, c.id, "SENT_TO_BROKER", actor="t", action="x")
    cases.transition(conn, c.id, "AWAITING_BROKER", actor="t", action="x")
    return c


def test_first_run_seeds_watermark_and_skips_backlog():
    c = _db()
    imap = FakeImap({1: b"x", 2: b"x", 3: b"x"})
    assert poll_once(c, imap, mailbox_addr=MB, llm=LLM) == []
    row = c.execute("SELECT last_uid FROM imap_state WHERE mailbox=?", (MB,)).fetchone()
    assert row["last_uid"] == 3


def test_new_reply_matched_to_case_becomes_zh_pending():
    c = _db()
    case = _seed_case_awaiting(c)
    c.execute("INSERT INTO imap_state (mailbox, last_uid, uidvalidity) VALUES (?,0,'100')", (MB,))
    reply = (b"Message-ID: <r1@x.com>\r\nIn-Reply-To: <root@justnanoinc.com>\r\n"
             b"References: <root@justnanoinc.com>\r\nSubject: Re: BOL 60114338678\r\n"
             b"From: b@x.com\r\n\r\nDelivered on the 6th. POD attached.\r\n")
    out = poll_once(c, FakeImap({5: reply}), mailbox_addr=MB, llm=LLM)
    assert out == [case.id]
    assert c.execute("SELECT last_uid FROM imap_state WHERE mailbox=?",
                     (MB,)).fetchone()["last_uid"] == 5
    zh = c.execute("SELECT COUNT(*) n FROM messages WHERE case_id=? AND channel='app' "
                   "AND lang='zh' AND status='pending_approval'", (case.id,)).fetchone()["n"]
    assert zh == 1


def test_duplicate_message_id_is_idempotent():
    c = _db()
    _seed_case_awaiting(c)
    c.execute("INSERT INTO imap_state (mailbox, last_uid, uidvalidity) VALUES (?,0,'100')", (MB,))
    reply = (b"Message-ID: <dup@x.com>\r\nIn-Reply-To: <root@justnanoinc.com>\r\n"
             b"Subject: Re: BOL 60114338678\r\nFrom: b@x.com\r\n\r\nfollow up\r\n")
    poll_once(c, FakeImap({5: reply}), mailbox_addr=MB, llm=LLM)
    before = c.execute("SELECT COUNT(*) n FROM messages").fetchone()["n"]
    poll_once(c, FakeImap({5: reply, 6: reply}, uidvalidity="100"), mailbox_addr=MB, llm=LLM)
    after = c.execute("SELECT COUNT(*) n FROM messages").fetchone()["n"]
    assert after == before


class FlakyLlm:
    """FakeLlmClient whose summarize raises the first time, then succeeds (transient error)."""
    def __init__(self):
        self._inner = FakeLlmClient(); self._fail = True

    def generate(self, **kw): return self._inner.generate(**kw)

    def summarize(self, **kw):
        if self._fail:
            self._fail = False
            raise RuntimeError("transient LLM error")
        return self._inner.summarize(**kw)


def test_transient_llm_failure_does_not_strand_reply():
    # C1 regression: an LLM error mid-ingest must NOT leave a half-processed reply that the
    # Message-ID dedup then skips forever. Nothing is persisted on failure; the next poll fully
    # reprocesses and produces the customer relay.
    c = _db()
    case = _seed_case_awaiting(c)
    c.execute("INSERT INTO imap_state (mailbox, last_uid, uidvalidity) VALUES (?,0,'100')", (MB,))
    reply = (b"Message-ID: <r1@x.com>\r\nIn-Reply-To: <root@justnanoinc.com>\r\n"
             b"References: <root@justnanoinc.com>\r\nSubject: Re: BOL 60114338678\r\n"
             b"From: b@x.com\r\n\r\nDelivered on the 6th.\r\n")
    flaky = FlakyLlm()
    # poll 1: summarize raises -> break, nothing persisted, watermark unchanged
    assert poll_once(c, FakeImap({5: reply}), mailbox_addr=MB, llm=flaky) == []
    assert c.execute("SELECT last_uid FROM imap_state WHERE mailbox=?",
                     (MB,)).fetchone()["last_uid"] == 0
    assert c.execute("SELECT COUNT(*) n FROM messages WHERE case_id=? AND party='broker'",
                     (case.id,)).fetchone()["n"] == 0        # no partial received-message row
    # poll 2: healthy LLM -> the same reply reprocesses and the relay is produced
    assert poll_once(c, FakeImap({5: reply}), mailbox_addr=MB, llm=flaky) == [case.id]
    zh = c.execute("SELECT COUNT(*) n FROM messages WHERE case_id=? AND channel='app' "
                   "AND lang='zh' AND status='pending_approval'", (case.id,)).fetchone()["n"]
    assert zh == 1


import os as _os
import pytest as _pytest


@_pytest.mark.skipif(not _os.environ.get("SMTP_PASSWORD"), reason="no SMTP_PASSWORD; skip live IMAP")
def test_live_imap_login_readonly():
    from app.inbound import ImapClient
    from app.config import load_env, make_imap_config
    load_env(); cfg = make_imap_config()
    c = ImapClient(cfg["host"], cfg["port"], cfg["address"], cfg["password"])
    assert int(c.uidvalidity()) >= 0
    c.logout()
