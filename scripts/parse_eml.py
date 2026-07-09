"""Deterministic .eml parsing for the broker-email drafting assistant.

See knowledge/concepts/drafting/eml-parsing.md for the governing article.
"""
from __future__ import annotations

import email
from email import policy
from email.message import Message
import re


def decode_body(msg: Message) -> str:
    """Return the best plain-text body: prefer text/plain, else stripped HTML."""
    plain = None
    html = None
    for part in msg.walk():
        ctype = part.get_content_type()
        if ctype == "text/plain" and plain is None:
            plain = part.get_content()
        elif ctype == "text/html" and html is None:
            html = part.get_content()
    if plain is not None:
        return plain
    if html is not None:
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"&nbsp;", " ", text)
        return re.sub(r"[ \t]+", " ", text)
    return ""


def _dedupe_ordered(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def extract_ids(text: str) -> dict[str, list[str]]:
    """Extract BOL (60#########) and PRO# numbers, deduped, in order of appearance."""
    bol = _dedupe_ordered(re.findall(r"\b60\d{9}\b", text))
    pro = _dedupe_ordered(re.findall(r"PRO#?\s*(\d{6,})", text, flags=re.IGNORECASE))
    return {"bol": bol, "pro": pro}
