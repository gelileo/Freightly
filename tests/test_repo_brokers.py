import pytest

from app.db import connect, init_db
from app import repo


def _setup():
    c = connect(":memory:"); init_db(c)
    repo.create_org(c, "Agent", "agent", id="a1")
    repo.create_org(c, "Cust", "customer", id="c1")
    return c


def test_broker_account_lifecycle():
    c = _setup()
    repo.create_broker(c, "Priority-1", id="b1")
    acct = repo.connect_broker_account(c, "a1", "b1", mailbox="ltlwest@priority1.com", id="ba1")
    assert acct.agent_org_id == "a1" and acct.broker_id == "b1"
    accts = repo.broker_accounts_for_agent(c, "a1")
    assert [a.id for a in accts] == ["ba1"]
    assert repo.agent_for_mailbox(c, "ltlwest@priority1.com") == "a1"
    assert repo.agent_for_mailbox(c, "unknown@x.com") is None


def test_duplicate_agent_broker_rejected():
    c = _setup()
    repo.create_broker(c, "Priority-1", id="b1")
    repo.connect_broker_account(c, "a1", "b1", id="ba1")
    with pytest.raises(Exception):
        repo.connect_broker_account(c, "a1", "b1", id="ba2")  # UNIQUE(agent,broker)


def test_customer_org_cannot_hold_broker_account():
    c = _setup()
    repo.create_broker(c, "Priority-1", id="b1")
    with pytest.raises(ValueError):
        repo.connect_broker_account(c, "c1", "b1", id="bad")  # c1 is a customer org
