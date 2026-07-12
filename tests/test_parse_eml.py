import email
from email import policy
from scripts.parse_eml import decode_body
from corpus_util import needs_corpus


def _msg(path):
    with open(path, "rb") as f:
        return email.message_from_binary_file(f, policy=policy.default)


def test_decode_body_returns_plaintext(sample_pickup):
    body = decode_body(_msg(sample_pickup))
    assert "reaching out to carrier!" in body
    # base64 payload must be decoded, not raw
    assert "Content-Transfer-Encoding" not in body
    # the Front quoting marker survives
    assert "wrote:" in body


def test_extract_ids_finds_bol(sample_pickup, sample_status):
    from scripts.parse_eml import extract_ids
    b1 = extract_ids(decode_body(_msg(sample_pickup)))
    assert b1["bol"] == ["60114338678"]
    b2 = extract_ids(decode_body(_msg(sample_status)))
    assert b2["bol"] == ["60114476384"]


def test_extract_ids_pro_pattern():
    from scripts.parse_eml import extract_ids
    ids = extract_ids("Please see PRO# 72406971 for BOL 60114821897")
    assert ids["bol"] == ["60114821897"]
    assert ids["pro"] == ["72406971"]


def test_split_turns_front_style(sample_pickup):
    from scripts.parse_eml import split_turns, Turn
    turns = split_turns(decode_body(_msg(sample_pickup)))
    # broker reply on top, one quoted shipper message below -> 2 turns
    assert len(turns) == 2
    assert turns[0].marker == ""  # newest, unquoted
    assert turns[0].body.strip().startswith("reaching out to carrier")
    assert turns[1].marker.startswith("On ")
    assert "still not pickup" in turns[1].body


def test_split_turns_outlook_style():
    from scripts.parse_eml import split_turns, Turn
    text = (
        "Latest reply body.\n"
        "From: hs@justnanoinc.com\n"
        "Sent: Wednesday, July 8, 2026 1:23 PM\n"
        "To: William Jerry\n"
        "Subject: Re: BOL 123\n"
        "Older quoted body.\n"
    )
    turns = split_turns(text)
    assert len(turns) == 2
    assert turns[0].body.strip() == "Latest reply body."
    assert turns[1].marker.startswith("From:")
    assert "Older quoted body." in turns[1].body


def test_parse_eml_aggregates(sample_pickup):
    from pathlib import Path
    from scripts.parse_eml import parse_eml

    p = parse_eml(sample_pickup)
    assert p.subject == "Re: pickup --- 60114338678"
    assert "ltlwest@priority1.com" in p.sender
    assert p.bol == ["60114338678"]
    assert len(p.turns) == 2


@needs_corpus
def test_dedupe_snapshots_keeps_largest(corpus_dir):
    from pathlib import Path
    from scripts.parse_eml import dedupe_snapshots

    # BOL 60114662390 has 9 Front-style snapshots of one growing thread.
    group = sorted(corpus_dir.glob("*60114662390*.eml"))
    assert len(group) >= 9
    best = dedupe_snapshots(group)
    assert "60114662390" in best
    largest = max(group, key=lambda p: p.stat().st_size)
    assert best["60114662390"] == largest


from scripts.parse_eml import render_thread_md, write_case, parse_eml


def test_render_thread_md_lists_turns(sample_pickup):
    md = render_thread_md(parse_eml(sample_pickup))
    assert "# Case 60114338678" in md
    assert "Re: pickup --- 60114338678" in md
    assert md.count("## Turn") == 2


def test_write_case_creates_thread_file(tmp_path, sample_pickup):
    out = write_case(parse_eml(sample_pickup), tmp_path)
    assert out == tmp_path / "60114338678" / "thread.md"
    assert out.exists()
    assert "60114338678" in out.read_text()


from scripts.parse_eml import parse_eml_bytes


def test_parse_from_bytes_matches_path(sample_pickup):
    raw = sample_pickup.read_bytes()
    a, b = parse_eml(sample_pickup), parse_eml_bytes(raw)
    assert a.body == b.body and a.bol == b.bol and a.subject == b.subject


def test_parse_bytes_reads_threading_headers():
    raw = (b"Message-ID: <abc@justnanoinc.com>\r\n"
           b"In-Reply-To: <root@justnanoinc.com>\r\n"
           b"References: <root@justnanoinc.com>\r\n"
           b"Subject: Re: BOL 60114821897\r\nFrom: broker@example.com\r\n\r\n"
           b"Hello, per your BOL 60114821897.\r\n")
    pe = parse_eml_bytes(raw)
    assert pe.message_id == "<abc@justnanoinc.com>"
    assert pe.in_reply_to == "<root@justnanoinc.com>"
    assert pe.references == "<root@justnanoinc.com>"