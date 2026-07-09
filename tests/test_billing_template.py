from pathlib import Path

TPL = Path(__file__).resolve().parent.parent / "templates" / "billing-dispute.md"


def test_billing_template_exists_with_sections():
    assert TPL.exists()
    text = TPL.read_text(encoding="utf-8")
    for section in ("## Skeleton", "## Slots", "## Tone", "## Examples"):
        assert section in text, f"missing {section}"
    # skeleton must not commit to a fabricated amount
    assert "{charge_ref}" in text and "{BOL}" in text
