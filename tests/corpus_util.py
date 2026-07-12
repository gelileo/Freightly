"""Test helpers for the email corpus.

The bulk raw corpus (`LTL-mail/`, `LTL-mail-2/` — real customer/broker email) is NOT in git; it
lives only on a dev machine. The handful of ground-truth `.eml` that unit tests assert against are
committed under `tests/fixtures/`. Analysis/distribution tests that scan the *whole* corpus are
skipped when the folders are absent (e.g. on a fresh clone / CI)."""
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures"
CORPUS = ROOT / "LTL-mail"
CORPUS2 = ROOT / "LTL-mail-2"


def fixt(name: str) -> str:
    """Absolute path (str) to a committed fixture email."""
    return str(FIX / name)


# Marker for tests that need the FULL corpus on disk (distribution / scan asserts).
needs_corpus = pytest.mark.skipif(
    not (CORPUS.exists() and CORPUS2.exists()),
    reason="full LTL-mail corpus not present (dev-only dataset; not in git)")
