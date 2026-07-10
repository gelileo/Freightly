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
