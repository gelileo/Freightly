from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "LTL-mail"


@pytest.fixture
def corpus_dir() -> Path:
    return CORPUS


@pytest.fixture
def sample_pickup() -> Path:
    # Front-style, single "On ... wrote:" marker, BOL 60114338678
    return CORPUS / "Re_ pickup --- 60114338678.eml"


@pytest.fixture
def sample_status() -> Path:
    # Front-style, single "On ... wrote:" marker, BOL 60114476384
    return CORPUS / "Re_ Shipment status --- 60114476384.eml"
