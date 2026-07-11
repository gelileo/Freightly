"""Load template skeletons from templates/<slug>.md. Thin for this slice — the versioned
per-agent Knowledge service comes in a later plan."""
from __future__ import annotations

import re
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# Fixed signoff injected deterministically (never left to the LLM). Single-agent default for
# now; becomes a per-agent Knowledge-service override in the multi-tenant build.
SHIPPER_SIGNOFF = """Best Regards

Hughson Huang
President

Justnano INC
Add: 14425 Yorba Ave, Chino CA 91710
Mobile: +1 (626)-688-8030
Office: +1 (626)-600-4211
hs@justnanoinc.com | www.justnanoinc.com"""


def load_template(slug: str) -> str:
    text = (TEMPLATES_DIR / f"{slug}.md").read_text(encoding="utf-8")
    m = re.search(r"^## Skeleton\s*\n(.*?)(?:\n## )", text, re.S | re.M)
    return m.group(1).strip() if m else ""
