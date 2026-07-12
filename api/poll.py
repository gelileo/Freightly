"""Vercel Cron target: one inbound IMAP poll per invocation (see vercel.json `crons`). Pulls new
broker replies from the Alibaba mailbox into cases (read-only, UID-watermarked). Optionally
protected by CRON_SECRET (Bearer)."""
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db, config, inbound  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        secret = os.environ.get("CRON_SECRET")
        if secret and self.headers.get("Authorization") != f"Bearer {secret}":
            return self._write(401, "unauthorized")
        cfg = config.make_imap_config()
        if not cfg["password"]:
            return self._write(200, "no SMTP_PASSWORD configured; skipped")
        conn = db.connect()
        try:
            imap = inbound.ImapClient(cfg["host"], cfg["port"], cfg["address"], cfg["password"])
            try:
                out = inbound.poll_once(conn, imap, mailbox_addr=cfg["address"],
                                        llm=config.make_llm())
            finally:
                imap.logout()
            self._write(200, f"polled: {out}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._write(500, f"poll error: {type(e).__name__}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _write(self, status: int, msg: str):
        b = msg.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *args):
        pass
