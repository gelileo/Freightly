import email
from email import policy
from scripts.parse_eml import decode_body


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
