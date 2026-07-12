"""Load template skeletons from templates/<slug>.md. Thin for this slice — the versioned
per-agent Knowledge service comes in a later plan."""
from __future__ import annotations

import os
import re
from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# The signoff is PII (real name / address / phones / email), so it is NOT hardcoded here — it
# comes from the SHIPPER_SIGNOFF env var (kept in .env, out of git; newlines as \n). A neutral
# placeholder is used when unset (tests/CI). Becomes a per-agent Knowledge-service override in the
# multi-tenant build.
_DEFAULT_SIGNOFF = ("Best Regards\n\n[Shipper Name]\n[Title]\n\n[Company]\n[Address]\n"
                    "[Phone]\n[shipper email] | [website]")


def shipper_signoff() -> str:
    """Fixed signoff block injected deterministically (never left to the LLM)."""
    raw = os.environ.get("SHIPPER_SIGNOFF")
    return raw.replace("\\n", "\n") if raw else _DEFAULT_SIGNOFF


# Back-compat constant = the neutral default; runtime callers should use shipper_signoff().
SHIPPER_SIGNOFF = _DEFAULT_SIGNOFF


def load_template(slug: str) -> str:
    text = (TEMPLATES_DIR / f"{slug}.md").read_text(encoding="utf-8")
    m = re.search(r"^## Skeleton\s*\n(.*?)(?:\n## )", text, re.S | re.M)
    return m.group(1).strip() if m else ""
