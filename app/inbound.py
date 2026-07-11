"""IMAP inbound poller for Alibaba Enterprise Mail. Reads only messages with UID above a
persisted high-water mark, READ-ONLY (BODY.PEEK[]) so the human mailbox's flags are never
touched, and feeds each new broker email to router.ingest_broker_email. `imap` is injectable
(a real ImapClient in production, a fake in tests)."""
from __future__ import annotations

import os
import time

from scripts.parse_eml import parse_eml_bytes
from app import router


def _thread_root(parsed):
    if parsed.references:
        return parsed.references.split()[0]
    return parsed.in_reply_to or None


def poll_once(conn, imap, *, mailbox_addr, llm) -> list:
    uidvalidity = imap.uidvalidity()
    row = conn.execute("SELECT last_uid, uidvalidity FROM imap_state WHERE mailbox=?",
                       (mailbox_addr,)).fetchone()
    if row is None or row["uidvalidity"] != uidvalidity:
        # first run for this mailbox, or the UID epoch rolled: seed to current max, skip backlog
        conn.execute(
            "INSERT INTO imap_state (mailbox, last_uid, uidvalidity) VALUES (?, ?, ?) "
            "ON CONFLICT(mailbox) DO UPDATE SET last_uid=excluded.last_uid, "
            "uidvalidity=excluded.uidvalidity",
            (mailbox_addr, imap.max_uid(), uidvalidity))
        conn.commit()
        return []

    results = []
    for uid in imap.search_uids_after(row["last_uid"]):
        raw = imap.fetch_raw(uid)                      # PEEK: no flag change
        parsed = parse_eml_bytes(raw)
        if parsed.message_id and conn.execute(
                "SELECT 1 FROM messages WHERE mail_message_id=?", (parsed.message_id,)).fetchone():
            conn.execute("UPDATE imap_state SET last_uid=? WHERE mailbox=?", (uid, mailbox_addr))
            conn.commit()
            continue
        try:
            case = router.ingest_broker_email(conn, eml=raw, to_mailbox=mailbox_addr,
                                              thread_id=_thread_root(parsed), llm=llm)
        except Exception:
            # transient failure: leave the watermark so this uid retries next poll
            break
        results.append(case.id if case else None)
        conn.execute("UPDATE imap_state SET last_uid=? WHERE mailbox=?", (uid, mailbox_addr))
        conn.commit()
    return results


class ImapClient:
    """Real IMAP client over imaplib.IMAP4_SSL, opened READ-ONLY. Deferred import so the module
    loads without a live server."""
    def __init__(self, host, port, address, password):
        import imaplib
        self._m = imaplib.IMAP4_SSL(host, port)
        self._m.login(address, password)
        self._m.select("INBOX", readonly=True)

    def uidvalidity(self) -> str:
        import re
        typ, data = self._m.status("INBOX", "(UIDVALIDITY)")
        m = re.search(rb"UIDVALIDITY (\d+)", (data[0] if data else b"") or b"")
        return m.group(1).decode() if m else ""

    def max_uid(self) -> int:
        typ, data = self._m.uid("SEARCH", None, "ALL")
        uids = (data[0].split() if data and data[0] else [])
        return int(uids[-1]) if uids else 0

    def search_uids_after(self, last: int) -> list:
        typ, data = self._m.uid("SEARCH", None, f"UID {last + 1}:*")
        uids = [int(x) for x in (data[0].split() if data and data[0] else [])]
        return [u for u in uids if u > last]          # `n:*` can echo the last msg even if <= last

    def fetch_raw(self, uid: int) -> bytes:
        typ, data = self._m.uid("FETCH", str(uid), "(BODY.PEEK[])")
        for part in (data or []):
            if isinstance(part, tuple):
                return part[1]
        return b""

    def logout(self):
        try:
            self._m.logout()
        except Exception:
            pass


def run_poller(conn_factory, cfg, *, llm, interval=60, once=False):
    while True:
        conn = conn_factory()
        try:
            imap = ImapClient(cfg["host"], cfg["port"], cfg["address"], cfg["password"])
            try:
                poll_once(conn, imap, mailbox_addr=cfg["address"], llm=llm)
            finally:
                imap.logout()
        except Exception as e:  # keep the loop alive across transient IMAP errors
            print("inbound poll error:", type(e).__name__, str(e)[:200])
        finally:
            conn.close()
        if once:
            break
        time.sleep(interval)


if __name__ == "__main__":  # `python -m app.inbound`
    from app import config, db
    cfg = config.make_imap_config()
    if not cfg["password"]:
        raise SystemExit("SMTP_PASSWORD not set")
    db_file = os.environ.get("HS_DB", "hs.db")
    run_poller(lambda: db.connect(db_file), cfg, llm=config.make_llm())
