from pathlib import Path
from scripts.corpus_report import corpus_report

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"


def test_every_issue_slug_has_template():
    slugs = set(corpus_report(ROOT / "LTL-mail")["by_issue"].keys())
    for slug in slugs:
        f = TEMPLATES / f"{slug}.md"
        assert f.exists(), f"missing template for {slug}"
        text = f.read_text(encoding="utf-8")
        for section in ("## Skeleton", "## Slots", "## Tone", "## Examples"):
            assert section in text, f"{slug}.md missing {section}"
