"""Mail transport port + a deterministic fake for tests + a guarded real Gmail adapter.

Mirrors the engine.llm port pattern: the app depends only on the MailTransport Protocol, so
tests run without network/credentials. Real Gmail requires google-api-python-client + OAuth
and is exercised only behind a credentials guard."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class SentRef:
    message_id: str
    thread_id: str


class MailTransport(Protocol):
    def send(self, *, from_addr: str, to: str, subject: str, body: str,
             thread_id: str | None = None, in_reply_to: str | None = None) -> SentRef: ...


@dataclass
class FakeTransport:
    """Records sends; returns deterministic refs. Preserves a passed thread_id (so a reply
    keeps the same thread), otherwise mints one."""
    sent: list[dict] = field(default_factory=list)

    def send(self, *, from_addr, to, subject, body, thread_id=None, in_reply_to=None) -> SentRef:
        self.sent.append({"from_addr": from_addr, "to": to, "subject": subject, "body": body,
                          "thread_id": thread_id, "in_reply_to": in_reply_to})
        n = len(self.sent)
        return SentRef(message_id=f"fakemsg-{n}", thread_id=thread_id or f"fakethread-{n}")


@dataclass
class AlibabaSmtpTransport:
    """Real adapter for Alibaba Enterprise Mail over SMTP-SSL. Auth = mailbox address + the
    16-digit third-party client password. `smtp_factory(host, port)` is injectable (defaults to
    smtplib.SMTP_SSL) so tests run without network. From is locked to the authenticated mailbox."""
    address: str
    password: str
    host: str = "smtp.qiye.aliyun.com"
    port: int = 465
    smtp_factory: object = None

    def send(self, *, from_addr, to, subject, body, thread_id=None, in_reply_to=None) -> SentRef:
        if from_addr != self.address:
            raise ValueError(
                f"from_addr {from_addr!r} must be the authenticated mailbox {self.address!r}")
        from email.message import EmailMessage
        from email.utils import make_msgid

        msgid = make_msgid(domain=self.address.split("@")[-1])
        mime = EmailMessage()
        mime["Message-ID"] = msgid
        mime["From"] = from_addr
        mime["To"] = to
        mime["Subject"] = subject
        ref = in_reply_to or thread_id
        if ref:
            mime["In-Reply-To"] = ref
            mime["References"] = ref
        mime.set_content(body)

        client = self._connect()
        try:
            client.login(self.address, self.password)
            client.send_message(mime)
        finally:
            try:
                client.quit()
            except Exception:
                pass
        return SentRef(message_id=msgid, thread_id=(ref or msgid))

    def _connect(self):
        if self.smtp_factory is not None:
            return self.smtp_factory(self.host, self.port)
        import smtplib
        return smtplib.SMTP_SSL(self.host, self.port, timeout=25)


class GmailTransport:
    """Real adapter. Requires `google-api-python-client` + an OAuth token, and a
    `google.oauth2.credentials.Credentials`. Sends RFC-822 mail from the agent's connected
    mailbox; sets In-Reply-To/References for threading; returns the Gmail message + thread ids.
    Imports are deferred so `import app.transport` works without the library installed."""

    def __init__(self, credentials=None, user_id: str = "me"):
        self._creds = credentials
        self._user = user_id

    def _service(self):
        from googleapiclient.discovery import build  # deferred
        return build("gmail", "v1", credentials=self._creds)

    def send(self, *, from_addr, to, subject, body, thread_id=None, in_reply_to=None) -> SentRef:
        import base64
        from email.message import EmailMessage

        mime = EmailMessage()
        mime["From"] = from_addr
        mime["To"] = to
        mime["Subject"] = subject
        if in_reply_to:
            mime["In-Reply-To"] = in_reply_to
            mime["References"] = in_reply_to
        mime.set_content(body)
        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
        payload = {"raw": raw}
        if thread_id:
            payload["threadId"] = thread_id
        sent = self._service().users().messages().send(userId=self._user, body=payload).execute()
        return SentRef(message_id=sent["id"], thread_id=sent.get("threadId", thread_id or sent["id"]))
