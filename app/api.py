"""JSON HTTP API over the app backend, as a pure dispatch() function (unit-testable, no
sockets). app/server.py is a thin http.server shell around this.

Auth boundary: user routes trust an upstream-authenticated `X-User-Id` header (real
WeChat/OAuth login is a gateway concern); every user route enforces app.access. `POST /inbound`
authenticates with a shared `X-Webhook-Secret`. Approval remains the only send/post path —
these handlers just call cases.approve_message etc."""
from __future__ import annotations

import hmac
import re
from dataclasses import asdict, dataclass, field

from app import repo, cases, router
from app.access import user_may_access_case


@dataclass
class Request:
    method: str
    path: str
    user_id: str | None = None
    headers: dict = field(default_factory=dict)
    body: dict = field(default_factory=dict)


@dataclass
class Response:
    status: int
    body: dict


def _messages(conn, case_id) -> list[dict]:
    return [{"id": r["id"], "party": r["party"], "channel": r["channel"], "lang": r["lang"],
             "body": r["body"], "status": r["status"], "classification": r["classification"]}
            for r in conn.execute(
                "SELECT * FROM messages WHERE case_id=? ORDER BY rowid", (case_id,))]


def _member_of(conn, user_id, org_id) -> bool:
    return bool(org_id) and repo.is_member(conn, user_id, org_id)


# --- handlers -------------------------------------------------------------------

def _create_case(req, conn, llm, m, _secret) -> Response:
    b = req.body
    eng = conn.execute(
        "SELECT customer_org_id, agent_org_id FROM engagements WHERE id=?",
        (b.get("engagement_id"),)).fetchone()
    if eng is None:
        return Response(400, {"error": "unknown engagement"})
    if not (_member_of(conn, req.user_id, eng["customer_org_id"])
            or _member_of(conn, req.user_id, eng["agent_org_id"])):
        return Response(403, {"error": "forbidden"})
    try:
        case = router.open_customer_case(
            conn, engagement_id=b["engagement_id"], broker_account_id=b.get("broker_account_id"),
            bol=b.get("bol"), pro=b.get("pro"), issue_type=b.get("issue_type"),
            wechat_text=b.get("wechat_text", ""), llm=llm)
    except (ValueError, KeyError) as e:
        return Response(400, {"error": str(e)})
    return Response(201, {"case": asdict(case), "messages": _messages(conn, case.id)})


def _get_case(req, conn, llm, m, _secret) -> Response:
    cid = m.group("cid")
    if cases.get_case(conn, cid) is None:
        return Response(404, {"error": "not found"})
    if not user_may_access_case(conn, req.user_id, cid):
        return Response(403, {"error": "forbidden"})
    return Response(200, {"case": asdict(cases.get_case(conn, cid)),
                          "messages": _messages(conn, cid)})


def _list_cases(req, conn, llm, m, _secret) -> Response:
    out = []
    for r in conn.execute("SELECT id FROM cases ORDER BY rowid"):
        if user_may_access_case(conn, req.user_id, r["id"]):
            out.append(asdict(cases.get_case(conn, r["id"])))
    return Response(200, {"cases": out})


def _get_audit(req, conn, llm, m, _secret) -> Response:
    cid = m.group("cid")
    if cases.get_case(conn, cid) is None:
        return Response(404, {"error": "not found"})
    if not user_may_access_case(conn, req.user_id, cid):
        return Response(403, {"error": "forbidden"})
    return Response(200, {"audit": [asdict(a) for a in cases.audit_trail(conn, cid)]})


def _message_action(action):
    def handler(req, conn, llm, m, _secret) -> Response:
        cid, mid = m.group("cid"), m.group("mid")
        case = cases.get_case(conn, cid)
        if case is None:
            return Response(404, {"error": "not found"})
        # only the case's AGENT org may approve/edit/reject
        if not _member_of(conn, req.user_id, case.agent_org_id):
            return Response(403, {"error": "forbidden"})
        msg = cases.get_message(conn, mid)
        if msg is None or msg.case_id != cid:
            return Response(404, {"error": "message not found"})
        try:
            if action == "edit":
                cases.edit_message(conn, mid, req.body.get("body", ""), req.user_id)
            elif action == "approve":
                cases.approve_message(conn, mid, req.user_id)
            else:  # reject
                cases.reject_message(conn, mid, req.user_id)
        except ValueError as e:
            return Response(409, {"error": str(e)})
        return Response(200, {"message": asdict(cases.get_message(conn, mid)),
                              "case": asdict(cases.get_case(conn, cid))})
    return handler


def _inbound(req, conn, llm, m, secret) -> Response:
    given = req.headers.get("X-Webhook-Secret", "")
    if not secret or not hmac.compare_digest(str(given), str(secret)):
        return Response(401, {"error": "bad webhook secret"})
    b = req.body
    try:
        case = router.ingest_broker_email(
            conn, eml=b.get("eml"), to_mailbox=b.get("to_mailbox"),
            thread_id=b.get("thread_id"), llm=llm)
    except (ValueError, KeyError, TypeError, OSError) as e:
        # bad/missing eml path, unknown mailbox, unreadable file, etc. → client error
        return Response(400, {"error": str(e)})
    if case is None:
        return Response(200, {"skipped": True})
    return Response(200, {"case_id": case.id})


# --- routing --------------------------------------------------------------------

_ROUTES = [
    ("POST", re.compile(r"^/cases$"), _create_case, True),
    ("GET", re.compile(r"^/cases$"), _list_cases, True),
    ("GET", re.compile(r"^/cases/(?P<cid>[^/]+)$"), _get_case, True),
    ("GET", re.compile(r"^/cases/(?P<cid>[^/]+)/audit$"), _get_audit, True),
    ("POST", re.compile(r"^/cases/(?P<cid>[^/]+)/messages/(?P<mid>[^/]+)/approve$"),
     _message_action("approve"), True),
    ("POST", re.compile(r"^/cases/(?P<cid>[^/]+)/messages/(?P<mid>[^/]+)/edit$"),
     _message_action("edit"), True),
    ("POST", re.compile(r"^/cases/(?P<cid>[^/]+)/messages/(?P<mid>[^/]+)/reject$"),
     _message_action("reject"), True),
    ("POST", re.compile(r"^/inbound$"), _inbound, False),  # webhook: no user auth
]


def dispatch(req: Request, *, conn, llm, webhook_secret=None) -> Response:
    path = req.path.split("?", 1)[0]
    for method, rx, handler, needs_user in _ROUTES:
        if method != req.method:
            continue
        m = rx.match(path)
        if not m:
            continue
        if needs_user and not req.user_id:
            return Response(401, {"error": "missing X-User-Id"})
        if not isinstance(req.body, dict):
            return Response(400, {"error": "request body must be a JSON object"})
        return handler(req, conn, llm, m, webhook_secret)
    return Response(404, {"error": "no such route"})
