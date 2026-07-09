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
