"""JSON HTTP API over the app backend, as a pure dispatch() function (unit-testable, no
sockets). app/server.py is a thin http.server shell around this.

Auth boundary: user routes trust an upstream-authenticated `X-User-Id` header (real
WeChat/OAuth login is a gateway concern); every user route enforces app.access. `POST /inbound`
authenticates with a shared `X-Webhook-Secret`. Approval remains the only send/post path —
these handlers just call cases.approve_message etc."""
from __future__ import annotations

import hmac
import re
import sqlite3
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


def _messages(conn, case_id, agent_view=True) -> list[dict]:
    """agent_view=True → all messages (agent console). Customer view (False) → ONLY
    agent-approved Chinese posts (channel=app, lang=zh, status=posted); internal English
    drafts and raw received broker mail are withheld server-side, not just hidden by the UI."""
    out = []
    for r in conn.execute("SELECT * FROM messages WHERE case_id=? ORDER BY rowid", (case_id,)):
        if not agent_view and not (r["channel"] == "app" and r["lang"] == "zh"
                                   and r["status"] == "posted"):
            continue
        out.append({"id": r["id"], "party": r["party"], "channel": r["channel"],
                    "lang": r["lang"], "body": r["body"], "status": r["status"],
                    "classification": r["classification"]})
    return out


def _member_of(conn, user_id, org_id) -> bool:
    return bool(org_id) and repo.is_member(conn, user_id, org_id)


def _header(headers, name, default=""):
    """Case-insensitive header lookup: HTTP/2 (Vercel) lowercases header names, so a plain-dict
    `.get("Authorization")` would miss. Works for the test's plain dicts too."""
    if name in headers:
        return headers[name]
    lname = name.lower()
    for k, v in headers.items():
        if k.lower() == lname:
            return v
    return default


# --- handlers -------------------------------------------------------------------

def _create_case(req, conn, llm, transport, wechat, m, _secret) -> Response:
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
            wechat_text=b.get("wechat_text", ""), llm=llm,
            fields=b.get("fields") if isinstance(b.get("fields"), dict) else None)
    except (ValueError, KeyError) as e:
        return Response(400, {"error": str(e)})
    agent_view = repo.is_member(conn, req.user_id, case.agent_org_id)
    return Response(201, {"case": asdict(case),
                          "messages": _messages(conn, case.id, agent_view)})


def _get_case(req, conn, llm, transport, wechat, m, _secret) -> Response:
    cid = m.group("cid")
    case = cases.get_case(conn, cid)
    if case is None:
        return Response(404, {"error": "not found"})
    if not user_may_access_case(conn, req.user_id, cid):
        return Response(403, {"error": "forbidden"})
    # agent-org members see everything; customer-side callers see only approved ZH posts
    agent_view = repo.is_member(conn, req.user_id, case.agent_org_id)
    return Response(200, {"case": asdict(case),
                          "messages": _messages(conn, cid, agent_view)})


def _list_cases(req, conn, llm, transport, wechat, m, _secret) -> Response:
    out = []
    for r in conn.execute("SELECT id FROM cases ORDER BY rowid"):
        if user_may_access_case(conn, req.user_id, r["id"]):
            out.append(asdict(cases.get_case(conn, r["id"])))
    return Response(200, {"cases": out})


def _issue_types(req, conn, llm, transport, wechat, m, _secret) -> Response:
    from app import forms
    return Response(200, {"issue_types": forms.issue_types()})


def _engagements(req, conn, llm, transport, wechat, m, _secret) -> Response:
    """The caller's ACTIVE engagements (as a customer-org member), each with the agent name and
    that agent's broker accounts — so a customer can pick agent + broker when starting a case."""
    rows = conn.execute(
        "SELECT e.id, e.agent_org_id, o.name AS agent_name FROM engagements e "
        "JOIN memberships mem ON mem.org_id = e.customer_org_id "
        "JOIN orgs o ON o.id = e.agent_org_id "
        "WHERE mem.user_id = ? AND e.status = 'active'", (req.user_id,)).fetchall()
    out = []
    for r in rows:
        accts = []
        for a in repo.broker_accounts_for_agent(conn, r["agent_org_id"]):
            bn = conn.execute("SELECT name FROM brokers WHERE id=?", (a.broker_id,)).fetchone()
            accts.append({"id": a.id, "broker_name": bn["name"] if bn else a.broker_id})
        out.append({"id": r["id"], "agent_org_id": r["agent_org_id"],
                    "agent_name": r["agent_name"], "broker_accounts": accts})
    return Response(200, {"engagements": out})


def _get_audit(req, conn, llm, transport, wechat, m, _secret) -> Response:
    cid = m.group("cid")
    if cases.get_case(conn, cid) is None:
        return Response(404, {"error": "not found"})
    if not user_may_access_case(conn, req.user_id, cid):
        return Response(403, {"error": "forbidden"})
    return Response(200, {"audit": [asdict(a) for a in cases.audit_trail(conn, cid)]})


def _message_action(action):
    def handler(req, conn, llm, transport, wechat, m, _secret) -> Response:
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
            elif action == "reject":
                cases.reject_message(conn, mid, req.user_id)
            else:  # approve — for an email message this actually SENDS via the transport
                _approve_and_maybe_send(conn, transport, case, msg, req.user_id)
        except ValueError as e:
            return Response(409, {"error": str(e)})
        return Response(200, {"message": asdict(cases.get_message(conn, mid)),
                              "case": asdict(cases.get_case(conn, cid))})
    return handler


def _approve_and_maybe_send(conn, transport, case, msg, actor) -> None:
    """Approve a message. For an email (broker-facing) message this SENDS via the transport
    BEFORE marking sent, then stamps the message's mail id and the case's thread id (so broker
    replies thread back). A missing recipient/transport or illegal transition raises ValueError
    (→ 409) and nothing is sent. This is the only outbound send path."""
    if msg.channel != "email":
        cases.approve_message(conn, msg.id, actor)  # app post — no transport
        return
    acct = repo.broker_account(conn, case.broker_account_id) if case.broker_account_id else None
    to = acct.broker_email if acct else None
    from_addr = acct.mailbox if acct else None
    if not to:
        raise ValueError("no broker recipient configured for this case")
    if not from_addr:
        raise ValueError("no sending mailbox configured for this case")
    if transport is None:
        raise ValueError("no mail transport configured")
    if msg.status != "pending_approval":
        raise ValueError(f"cannot approve message in status {msg.status!r}")
    # GUARDRAIL: never send an unfinished draft to a broker. A draft still carrying an
    # anti-fabrication marker (`[[MISSING: …]]`) or an unfilled template slot (`{…}`) must be
    # edited/completed before it can go out. Raise → 409, nothing sent.
    from engine.validate import find_placeholders
    placeholders = find_placeholders(msg.body)
    if placeholders:
        raise ValueError(
            "draft has unfilled placeholders " + ", ".join(placeholders[:5])
            + " — edit the draft to fill or remove them before sending")
    # Validate BOTH transitions before any network call, so a legal send commits fully.
    cases._check_transition(case.status, "SENT_TO_BROKER")
    cases._check_transition("SENT_TO_BROKER", "AWAITING_BROKER")
    subject = f"{case.issue_type or 'Shipment'} --- {case.shipment_bol or ''}".strip()
    # Network send first: if it raises, nothing below runs → message stays pending_approval.
    ref = transport.send(from_addr=from_addr, to=to, subject=subject, body=msg.body,
                         thread_id=case.mail_thread_id, in_reply_to=msg.in_reply_to)
    # All post-send bookkeeping in ONE transaction (message sent + both transitions + thread
    # stamp) so a crash can't strand the case at SENT_TO_BROKER with no thread id.
    try:
        conn.execute("UPDATE messages SET status='sent', mail_message_id=? WHERE id=?",
                     (ref.message_id, msg.id))
        cases._apply_transition(conn, case.id, case.status, "SENT_TO_BROKER", actor,
                                "approve_message:sent")
        cases._apply_transition(conn, case.id, "SENT_TO_BROKER", "AWAITING_BROKER", actor,
                                "awaiting_broker_reply")
        if not case.mail_thread_id:
            conn.execute("UPDATE cases SET mail_thread_id=? WHERE id=?", (ref.thread_id, case.id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _inbound(req, conn, llm, transport, wechat, m, secret) -> Response:
    given = _header(req.headers, "X-Webhook-Secret")
    if not secret or not hmac.compare_digest(str(given), str(secret)):
        return Response(401, {"error": "bad webhook secret"})
    b = req.body
    try:
        case = router.ingest_broker_email(
            conn, eml=b.get("eml"), to_mailbox=b.get("to_mailbox"),
            thread_id=b.get("thread_id"), llm=llm)
    except (ValueError, KeyError, TypeError, OSError):
        # bad/missing eml path, unknown mailbox, unreadable file, etc. → client error.
        # Generic message: this is an external webhook; do not echo raw exception text
        # (which can leak a filesystem path / internal detail).
        return Response(400, {"error": "invalid inbound request"})
    if case is None:
        return Response(200, {"skipped": True})
    return Response(200, {"case_id": case.id})


# --- auth / invites (WeChat-login adapter) --------------------------------------

def _auth_wechat_login(req, conn, llm, transport, wechat, m, _secret) -> Response:
    from app import auth
    js_code = req.body.get("js_code")
    if not js_code:
        return Response(400, {"error": "js_code required"})
    try:
        token, user, needs_bind = auth.login_wechat(conn, wechat, js_code)
    except ValueError as e:
        return Response(400, {"error": str(e)})
    return Response(200, {"session_token": token, "user": asdict(user),
                          "needs_bind": needs_bind})


def _auth_login(req, conn, llm, transport, wechat, m, _secret) -> Response:
    from app import auth
    email, password = req.body.get("email"), req.body.get("password")
    if not email or not password:
        return Response(400, {"error": "email and password required"})
    result = auth.login_password(conn, email, password)
    if result is None:
        return Response(401, {"error": "invalid email or password"})
    token, user = result
    return Response(200, {"session_token": token, "user": asdict(user)})


def _auth_bind(req, conn, llm, transport, wechat, m, _secret) -> Response:
    from app import auth
    code = req.body.get("code")
    if not code:
        return Response(400, {"error": "code required"})
    try:
        mem = auth.bind_via_invite(conn, user_id=req.user_id, code=code)
    except ValueError as e:
        return Response(409, {"error": str(e)})
    return Response(200, {"membership": asdict(mem)})


def _auth_logout(req, conn, llm, transport, wechat, m, _secret) -> Response:
    from app import auth
    ah = _header(req.headers, "Authorization")
    if ah.startswith("Bearer "):
        auth.revoke_session(conn, ah[len("Bearer "):])
    return Response(200, {"ok": True})


def _onboard_customer(req, conn, llm, transport, wechat, m, _secret) -> Response:
    b = req.body
    name, login = b.get("customer_name"), b.get("login")
    if not name or not login:
        return Response(400, {"error": "customer_name and login required"})
    # the caller must act as one of their agent orgs
    agent_orgs = [r["id"] for r in conn.execute(
        "SELECT o.id FROM orgs o JOIN memberships mem ON mem.org_id = o.id "
        "WHERE mem.user_id = ? AND o.type = 'agent'", (req.user_id,))]
    agent_org_id = b.get("agent_org_id")
    if agent_org_id is not None:
        if agent_org_id not in agent_orgs:
            return Response(403, {"error": "not a member of that agent org"})
    elif len(agent_orgs) == 1:
        agent_org_id = agent_orgs[0]
    elif not agent_orgs:
        return Response(403, {"error": "only an agent-org member can onboard customers"})
    else:
        return Response(400, {"error": "specify agent_org_id (you belong to multiple)"})
    try:
        result = router.onboard_customer(conn, agent_org_id=agent_org_id, customer_name=name,
                                         login=login, contact_name=b.get("contact_name"))
    except sqlite3.IntegrityError:
        return Response(409, {"error": "login already taken"})
    return Response(201, result)


def _create_invite(req, conn, llm, transport, wechat, m, _secret) -> Response:
    from app import auth
    b = req.body
    cust = b.get("customer_org_id")
    role = b.get("role", "member")
    if not cust:
        return Response(400, {"error": "customer_org_id required"})
    if role not in ("admin", "operator", "member"):
        return Response(400, {"error": "bad role"})
    # caller must belong to an agent org actively engaged with this customer org
    agents = repo.active_agents_for_customer(conn, cust)
    if not any(repo.is_member(conn, req.user_id, a) for a in agents):
        return Response(403, {"error": "forbidden"})
    code = auth.create_invite(conn, customer_org_id=cust, role=role, created_by=req.user_id)
    return Response(201, {"code": code, "qr_scene": code})


# --- routing --------------------------------------------------------------------

_ROUTES = [
    ("POST", re.compile(r"^/cases$"), _create_case, True),
    ("GET", re.compile(r"^/cases$"), _list_cases, True),
    ("GET", re.compile(r"^/issue-types$"), _issue_types, True),
    ("GET", re.compile(r"^/engagements$"), _engagements, True),
    ("GET", re.compile(r"^/cases/(?P<cid>[^/]+)$"), _get_case, True),
    ("GET", re.compile(r"^/cases/(?P<cid>[^/]+)/audit$"), _get_audit, True),
    ("POST", re.compile(r"^/cases/(?P<cid>[^/]+)/messages/(?P<mid>[^/]+)/approve$"),
     _message_action("approve"), True),
    ("POST", re.compile(r"^/cases/(?P<cid>[^/]+)/messages/(?P<mid>[^/]+)/edit$"),
     _message_action("edit"), True),
    ("POST", re.compile(r"^/cases/(?P<cid>[^/]+)/messages/(?P<mid>[^/]+)/reject$"),
     _message_action("reject"), True),
    ("POST", re.compile(r"^/auth/login$"), _auth_login, False),
    ("POST", re.compile(r"^/auth/wechat/login$"), _auth_wechat_login, False),
    ("POST", re.compile(r"^/auth/bind$"), _auth_bind, True),
    ("POST", re.compile(r"^/auth/logout$"), _auth_logout, True),
    ("POST", re.compile(r"^/invites$"), _create_invite, True),
    ("POST", re.compile(r"^/onboard-customer$"), _onboard_customer, True),
    ("POST", re.compile(r"^/inbound$"), _inbound, False),  # webhook: no user auth
]


def dispatch(req: Request, *, conn, llm, transport=None, webhook_secret=None,
             wechat=None) -> Response:
    path = req.path.split("?", 1)[0]
    # Resolve a Bearer session token to a user_id (real clients). A valid token sets the identity;
    # a present-but-invalid token is a *bad* credential — never a silent fall-through to the legacy
    # X-User-Id header. We defer the 401 until after route matching, though, so a public route
    # (e.g. /auth/wechat/login) still works when a client's global interceptor attaches a stale
    # token to the very request meant to re-login. On a protected route a bad token hard-401s.
    auth_header = _header(req.headers, "Authorization")
    bearer_present = auth_header.startswith("Bearer ")
    bearer_bad = False
    if bearer_present:
        from app import auth
        uid = auth.resolve_session(conn, auth_header[len("Bearer "):])
        if uid is None:
            bearer_bad = True
        else:
            req.user_id = uid
    for method, rx, handler, needs_user in _ROUTES:
        if method != req.method:
            continue
        m = rx.match(path)
        if not m:
            continue
        if bearer_bad and needs_user:  # bad token on a protected route: reject, no fall-through
            return Response(401, {"error": "invalid or expired session"})
        if needs_user and not req.user_id:
            return Response(401, {"error": "missing X-User-Id"})
        if not isinstance(req.body, dict):
            return Response(400, {"error": "request body must be a JSON object"})
        return handler(req, conn, llm, transport, wechat, m, webhook_secret)
    return Response(404, {"error": "no such route"})
