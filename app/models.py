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
