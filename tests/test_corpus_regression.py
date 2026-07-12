from scripts.triage_report import triage_report
from scripts.parse_eml import parse_eml
from engine.drafting import DraftRequest, draft
from engine.llm import FakeLlmClient
from corpus_util import needs_corpus


@needs_corpus
def test_triage_distribution_locked():
    # Ground truth over the merged 922-file corpus (LTL-mail + LTL-mail-2).
    r = triage_report()
    assert r["counts"] == {"skip": 327, "billing-dispute": 60, "shipment": 535}
    assert len(r["unknown_shipment"]) == 203


def test_engine_replays_known_cases():
    # Representative real emails route to the expected triage bucket through the engine.
    cases = {
        "tests/fixtures/FFBA BOL# 60112079078.eml": "billing-dispute",
        "tests/fixtures/10% Off Freight Promo LTL, Truckload And Expedited.eml": "skip",
        "tests/fixtures/Re_ pickup --- 60114338678.eml": "shipment",
    }
    llm = FakeLlmClient()
    for path, expected_triage in cases.items():
        p = parse_eml(path)
        r = draft(DraftRequest(body=p.body, sender=p.sender, subject=p.subject,
                               facts={}, source_text=p.body), llm)
        assert r.triage == expected_triage, f"{path} -> {r.triage}, expected {expected_triage}"