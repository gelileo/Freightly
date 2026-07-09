def test_corpus_present(corpus_dir):
    emls = list(corpus_dir.glob("*.eml"))
    assert len(emls) == 71
