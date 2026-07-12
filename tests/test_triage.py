from scripts.parse_eml import parse_eml
from scripts.triage import triage


def _bt(path):
    p = parse_eml(path)
    return triage(p.body, p.sender)


def test_triage_billing_dispute():
    # FFBA "Free Freight Bill Audit ... pricing variance ... additional charge"
    assert _bt("tests/fixtures/FFBA BOL# 60112079078.eml") == "billing-dispute"
    # out-of-route charge from Warp
    assert _bt("tests/fixtures/BOL 60114409180 _ P-118701-2621.eml") == "billing-dispute"


def test_triage_skip():
    # statement: sender NoReply@Priority1, empty body
    assert _bt("tests/fixtures/JUSTNANO INC Statement from Priority1 is attached.eml") == "skip"
    # promo
    assert _bt("tests/fixtures/10% Off Freight Promo LTL, Truckload And Expedited.eml") == "skip"
    # drayage / containers-from-port sales
    assert _bt("tests/fixtures/Drayage.eml") == "skip"
    # "any shipments going out this week" sales check-in
    assert _bt("tests/fixtures/Any Shipments Going Out This Week_.eml") == "skip"


def test_triage_shipment():
    # PO# needed to schedule a delivery = a real shipment issue
    assert _bt("tests/fixtures/60112049235.eml") == "shipment"


def test_triage_unit_rules():
    assert triage("", "Priority1 Statement <NoReply@Priority1.com>") == "skip"
    assert triage("Please see the out of route charge", "William Jerry <x@priority1.com>") == "billing-dispute"
    assert triage("This shipment still not pickup, please push carrier", "LTL West <ltlwest@priority1.com>") == "shipment"
