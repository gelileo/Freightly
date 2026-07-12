from corpus_util import needs_corpus

pytestmark = needs_corpus
def test_corpus_present(corpus_dir):
    emls = list(corpus_dir.glob("*.eml"))
    assert len(emls) == 71