"""Load template skeletons from templates/<slug>.md. Thin for this slice — the versioned
per-agent Knowledge service comes in a later plan."""
from __future__ import annotations

import re
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def load_template(slug: str) -> str:
    text = (TEMPLATES_DIR / f"{slug}.md").read_text(encoding="utf-8")
    m = re.search(r"^## Skeleton\s*\n(.*?)(?:\n## )", text, re.S | re.M)
    return m.group(1).strip() if m else ""
