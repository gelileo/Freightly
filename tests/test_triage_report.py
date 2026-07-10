from scripts.triage_report import triage_report


def test_triage_report_covers_corpus():
    r = triage_report()
    # every file lands in exactly one triage bucket
    assert sum(r["counts"].values()) == 922
    for k in ("skip", "billing-dispute", "shipment"):
        assert k in r["counts"]
    # billing must be non-trivial (FFBA + statements-with-charges exist)
    assert r["counts"]["billing-dispute"] >= 20
    # report surfaces shipment mail the subject-classifier still can't sub-route
    assert isinstance(r["unknown_shipment"], list)
