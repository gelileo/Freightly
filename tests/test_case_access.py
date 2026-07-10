from app.db import connect, init_db
from app import repo, cases
from app.access import user_may_access_case


def _net():
    c = connect(":memory:"); init_db(c)
    repo.create_org(c, "Cust", "customer", id="c1")
    repo.create_org(c, "Agent", "agent", id="a1")
    repo.create_org(c, "Other", "agent", id="a2")
    repo.create_user(c, "uc1", "email", "uc1@x", id="uc1"); repo.add_member(c, "uc1", "c1", "member")
    repo.create_user(c, "ua1", "email", "ua1@x", id="ua1"); repo.add_member(c, "ua1", "a1", "operator")
    repo.create_user(c, "ua2", "email", "ua2@x", id="ua2"); repo.add_member(c, "ua2", "a2", "operator")
    repo.create_engagement(c, "c1", "a1", id="e1"); repo.approve_engagement(c, "e1")
    cases.create_case(c, agent_org_id="a1", customer_org_id="c1", origin="customer",
                      bol="60114821897", status="NEW", id="case1")
    return c


def test_case_access_scoping():
    c = _net()
    assert user_may_access_case(c, "ua1", "case1") is True   # agent-org member
    assert user_may_access_case(c, "uc1", "case1") is True   # customer w/ active engagement
    assert user_may_access_case(c, "ua2", "case1") is False  # unrelated agent org
    assert user_may_access_case(c, "nobody", "case1") is False


def test_customer_access_requires_active_engagement():
    c = _net()
    repo.revoke_engagement(c, "e1")  # engagement no longer active
    assert user_may_access_case(c, "uc1", "case1") is False  # customer loses access
    assert user_may_access_case(c, "ua1", "case1") is True   # agent still owns the case
