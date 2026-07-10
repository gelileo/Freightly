import pytest

from app.db import connect, init_db
from app import repo, cases


def _c():
    c = connect(":memory:"); init_db(c)
    repo.create_org(c, "Agent", "agent", id="a1")
    repo.create_org(c, "Cust", "customer", id="c1")
    return c


def _new_case(c, status="NEW"):
    return cases.create_case(c, agent_org_id="a1", customer_org_id="c1", origin="customer",
                             bol="60114821897", issue_type="pickup", status=status, id="case1")


def test_legal_transition_path_with_audit():
    c = _c(); _new_case(c)
    cases.transition(c, "case1", "DRAFTING", "system")
    cases.transition(c, "case1", "PENDING_APPROVAL", "system")
    cases.transition(c, "case1", "SENT_TO_BROKER", "u_agent")
    cases.transition(c, "case1", "AWAITING_BROKER", "system")
    assert cases.get_case(c, "case1").status == "AWAITING_BROKER"
    trail = cases.audit_trail(c, "case1")
    assert [a.to_status for a in trail] == \
        ["DRAFTING", "PENDING_APPROVAL", "SENT_TO_BROKER", "AWAITING_BROKER"]


def test_illegal_transition_raises_and_writes_no_audit():
    c = _c(); _new_case(c)
    with pytest.raises(ValueError):
        cases.transition(c, "case1", "SENT_TO_BROKER", "system")  # NEW -> SENT is illegal
    assert cases.audit_trail(c, "case1") == []
    assert cases.get_case(c, "case1").status == "NEW"


def test_approve_email_message_sends_and_advances_case():
    c = _c(); _new_case(c)
    cases.transition(c, "case1", "DRAFTING", "system")
    cases.transition(c, "case1", "PENDING_APPROVAL", "system")
    m = cases.add_message(c, case_id="case1", party="agent", channel="email", lang="en",
                          body="Hi Will, ...", status="pending_approval", id="m1")
    cases.approve_message(c, "m1", "u_agent")
    assert cases.get_message(c, "m1").status == "sent"
    assert cases.get_case(c, "case1").status == "SENT_TO_BROKER"
    assert any(a.action.startswith("approve_message") for a in cases.audit_trail(c, "case1"))


def test_approve_nonpending_raises():
    c = _c(); _new_case(c)
    cases.add_message(c, case_id="case1", party="agent", channel="email", body="x",
                      status="draft", id="m1")
    with pytest.raises(ValueError):
        cases.approve_message(c, "m1", "u_agent")


def test_edit_and_reject():
    c = _c(); _new_case(c)
    cases.transition(c, "case1", "DRAFTING", "system")
    cases.transition(c, "case1", "PENDING_APPROVAL", "system")
    cases.add_message(c, case_id="case1", party="agent", channel="email", body="draft body",
                      status="pending_approval", id="m1")
    cases.edit_message(c, "m1", "edited body", "u_agent")
    assert cases.get_message(c, "m1").body == "edited body"
    assert any(a.action == "edit_message" for a in cases.audit_trail(c, "case1"))
    cases.reject_message(c, "m1", "u_agent")
    assert cases.get_message(c, "m1").status == "draft"
    assert cases.get_case(c, "case1").status == "DRAFTING"


def test_failed_approve_is_atomic():
    # Regression: a failed approval must NOT flip the message to 'sent' or write audit.
    c = _c()
    # case already past PENDING_APPROVAL, but a stray pending message exists
    cases.create_case(c, agent_org_id="a1", customer_org_id="c1", origin="customer",
                       status="SENT_TO_BROKER", id="case1")
    cases.add_message(c, case_id="case1", party="agent", channel="email", body="x",
                      status="pending_approval", id="m1")
    with pytest.raises(ValueError):
        cases.approve_message(c, "m1", "u_agent")  # SENT_TO_BROKER -> SENT_TO_BROKER illegal
    assert cases.get_message(c, "m1").status == "pending_approval"  # unchanged
    assert not any(a.action.startswith("approve_message")
                   for a in cases.audit_trail(c, "case1"))


def test_edit_records_prior_body():
    c = _c(); _new_case(c)
    cases.transition(c, "case1", "DRAFTING", "system")
    cases.transition(c, "case1", "PENDING_APPROVAL", "system")
    cases.add_message(c, case_id="case1", party="agent", channel="email", body="original",
                      status="pending_approval", id="m1")
    cases.edit_message(c, "m1", "revised", "u_agent")
    edit = [a for a in cases.audit_trail(c, "case1") if a.action == "edit_message"][0]
    assert "original" in (edit.detail or "")


def test_full_lifecycle_to_closed():
    c = _c(); _new_case(c)
    for to in ("DRAFTING", "PENDING_APPROVAL", "POSTED_TO_CUSTOMER", "RESOLVED", "CLOSED"):
        cases.transition(c, "case1", to, "system")
    assert cases.get_case(c, "case1").status == "CLOSED"
