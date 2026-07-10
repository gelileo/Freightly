from app.db import connect, init_db
from app import repo
from app.access import user_may_access_engagement, parties_connected, visible_org_ids


def _net():
    c = connect(":memory:"); init_db(c)
    for cid in ("c1", "c2"):
        repo.create_org(c, cid, "customer", id=cid)
    for aid in ("a1", "a2"):
        repo.create_org(c, aid, "agent", id=aid)
    repo.create_user(c, "uc1", "email", "uc1@x", id="uc1"); repo.add_member(c, "uc1", "c1", "member")
    repo.create_user(c, "ua1", "email", "ua1@x", id="ua1"); repo.add_member(c, "ua1", "a1", "operator")
    repo.create_engagement(c, "c1", "a1", id="e_c1a1"); repo.approve_engagement(c, "e_c1a1")
    repo.create_engagement(c, "c2", "a2", id="e_c2a2"); repo.approve_engagement(c, "e_c2a2")
    return c


def test_isolation():
    c = _net()
    assert user_may_access_engagement(c, "uc1", "e_c1a1") is True
    assert user_may_access_engagement(c, "ua1", "e_c1a1") is True
    # cross-boundary: c1's user cannot touch c2<->a2
    assert user_may_access_engagement(c, "uc1", "e_c2a2") is False
    assert user_may_access_engagement(c, "ua1", "e_c2a2") is False
    assert parties_connected(c, "c1", "a1") is True
    assert parties_connected(c, "c1", "a2") is False
    assert visible_org_ids(c, "uc1") == {"c1"}


def test_pending_engagement_not_accessible():
    c = _net()
    repo.create_engagement(c, "c1", "a2", id="pend")  # pending, not approved
    assert user_may_access_engagement(c, "uc1", "pend") is False
