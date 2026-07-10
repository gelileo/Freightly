"""Typed dataclasses mirroring the domain-core rows (see app/db.py schema)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Org:
    id: str
    name: str
    type: str  # 'customer' | 'agent'


@dataclass
class User:
    id: str
    name: str
    auth_kind: str  # 'wechat' | 'phone' | 'email'
    auth_id: str


@dataclass
class Membership:
    user_id: str
    org_id: str
    role: str  # 'admin' | 'operator' | 'member'


@dataclass
class Engagement:
    id: str
    customer_org_id: str
    agent_org_id: str
    status: str  # 'pending' | 'active' | 'revoked'


@dataclass
class Broker:
    id: str
    name: str


@dataclass
class BrokerAccount:
    id: str
    agent_org_id: str
    broker_id: str
    mailbox: str | None


@dataclass
class Case:
    id: str
    agent_org_id: str
    customer_org_id: str | None
    broker_account_id: str | None
    shipment_bol: str | None
    shipment_pro: str | None
    origin: str  # 'customer' | 'broker'
    issue_type: str | None
    status: str
    mail_thread_id: str | None


@dataclass
class Message:
    id: str
    case_id: str
    party: str      # 'customer' | 'agent' | 'broker' | 'system'
    channel: str    # 'app' | 'email'
    lang: str | None
    body: str
    status: str     # draft|pending_approval|approved|sent|posted|received
    classification: str | None = None
    mail_message_id: str | None = None
    in_reply_to: str | None = None


@dataclass
class AuditLog:
    id: str
    case_id: str
    actor: str
    action: str
    from_status: str | None
    to_status: str | None
    detail: str | None = None
