import pytest

from app.db import connect, init_db
from app import repo


def _setup():
    c = connect(":memory:"); init_db(c)
    repo.create_org(c, "Cust", "customer", id="c1")
    repo.create_org(c, "Agent", "agent", id="a1")
    return c


def test_engagement_lifecycle():
    c = _setup()
    e = repo.create_engagement(c, "c1", "a1", id="e1")
    assert e.status == "pending"
    assert repo.active_agents_for_customer(c, "c1") == set()  # not active yet
    repo.approve_engagement(c, "e1")
    assert repo.active_agents_for_customer(c, "c1") == {"a1"}
    assert repo.active_customers_for_agent(c, "a1") == {"c1"}
    repo.revoke_engagement(c, "e1")
    assert repo.active_agents_for_customer(c, "c1") == set()


def test_engagement_type_validation():
    c = _setup()
    with pytest.raises(ValueError):
        repo.create_engagement(c, "a1", "c1", id="bad")  # roles swapped


def test_approve_is_transition_guarded():
    c = _setup()
    repo.create_engagement(c, "c1", "a1", id="e1")
    repo.approve_engagement(c, "e1")
    repo.revoke_engagement(c, "e1")
    # a revoked engagement cannot be silently reactivated by re-approving
    with pytest.raises(ValueError):
        repo.approve_engagement(c, "e1")
    # a fresh re-invite for the same pair is also blocked by UNIQUE (no re-engagement path yet)
    with pytest.raises(Exception):
        repo.create_engagement(c, "c1", "a1", id="e2")


def test_approve_revoke_missing_raises():
    c = _setup()
    with pytest.raises(ValueError):
        repo.approve_engagement(c, "nope")
    with pytest.raises(ValueError):
        repo.revoke_engagement(c, "nope")
