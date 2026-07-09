from pathlib import Path

from scripts.corpus_report import classify_issue, corpus_report

ROOT = Path(__file__).resolve().parent.parent


def test_classify_issue_known_prefixes():
    assert classify_issue("Re: pickup --- 60114338678") == "pickup"
    assert classify_issue("Re: Shipment status --- 60114476384") == "shipment-status"
    assert classify_issue("Re: POD --- 60114592263") == "pod-request"
    assert classify_issue("Re: Delivery window --- 60114839031") == "delivery-window"
    assert classify_issue("Re: Cancel shipment --- 60114304778") == "cancellation"
    assert classify_issue("Re: Request for Return Reason --- 60113820374") == "return-reason"
    assert classify_issue("Re: Urgent Delivery Request – Crate Damaged _ 60114821897") == "damage"


def test_every_corpus_file_maps_to_known_issue():
    report = corpus_report(ROOT / "LTL-mail")
    # No subject may fall through as uncategorized; if this fails, add the new
    # category to issue-taxonomy.md in THIS task (same-task rule) and extend classify_issue.
    assert report["unknown"] == [], f"uncategorized subjects: {report['unknown']}"
