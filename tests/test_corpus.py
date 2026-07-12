from pathlib import Path
from scripts.corpus import list_corpus, merged_best
from corpus_util import needs_corpus

pytestmark = needs_corpus


def test_list_corpus_spans_both_dirs():
    paths = list_corpus()
    assert len(paths) == 922
    # both directories represented
    parents = {p.parent.name for p in paths}
    assert parents == {"LTL-mail", "LTL-mail-2"}


def test_merged_best_dedupes_by_bol_across_dirs():
    best = merged_best()
    assert len(best) == 141
    # overlap BOL present in both dirs -> the largest snapshot wins (an LTL-mail file)
    assert best["60113656921"].name == "Re_ Shipment status ---60113656921(1).eml"