import pytest

from app.db import connect, init_db
from app import repo


def _c():
    c = connect(":memory:"); init_db(c); return c


def test_create_and_membership():
    c = _c()
    org = repo.create_org(c, "Justnano", "agent", id="ag1")
    assert org.type == "agent"
    repo.create_user(c, "Agent One", "email", "agent1@example.com", id="u1")
    repo.add_member(c, "u1", "ag1", "admin")
    assert repo.is_member(c, "u1", "ag1") is True
    assert repo.is_member(c, "u1", "nope") is False
    assert repo.member_org_ids(c, "u1") == {"ag1"}


def test_org_type_validated():
    c = _c()
    with pytest.raises(Exception):
        repo.create_org(c, "bad", "broker", id="x")  # not a valid org type
