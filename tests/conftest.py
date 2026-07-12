import os
import sys
from pathlib import Path
import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # so tests can `import corpus_util`

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "LTL-mail"                 # full raw corpus (dev-only, not in git)
FIX = ROOT / "tests" / "fixtures"          # committed ground-truth emails


@pytest.fixture
def corpus_dir() -> Path:
    if not CORPUS.exists():
        pytest.skip("full LTL-mail corpus not present (dev-only dataset)")
    return CORPUS


@pytest.fixture
def sample_pickup() -> Path:
    # Front-style, single "On ... wrote:" marker, BOL 60114338678
    return FIX / "Re_ pickup --- 60114338678.eml"


@pytest.fixture
def sample_status() -> Path:
    # Front-style, single "On ... wrote:" marker, BOL 60114476384
    return FIX / "Re_ Shipment status --- 60114476384.eml"
