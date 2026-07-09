"""Deterministic .eml parsing for the broker-email drafting assistant.

See knowledge/concepts/drafting/eml-parsing.md for the governing article.
"""
from __future__ import annotations

import email
from email import policy
from email.message import Message
import re
from dataclasses import dataclass


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


# Front/Apple-style:  "On May 21, 2026 at 9:21 AM GMT-5 someone@x.com wrote:"
_FRONT_MARKER = re.compile(r"(?m)^On .+ wrote:\s*$")
# Outlook/Foxmail-style block start:  "From: ...."
_OUTLOOK_MARKER = re.compile(r"(?m)^From:\s.+$")


@dataclass
class Turn:
    marker: str  # the quoting marker line above this turn ("" for the newest/top turn)
    body: str


def split_turns(text: str) -> list[Turn]:
    """Split quoted history into turns, newest first. Handles both quoting formats."""
    # Collect all marker positions from both formats.
    marks = [(m.start(), m.group().strip()) for m in _FRONT_MARKER.finditer(text)]
    marks += [(m.start(), m.group().strip()) for m in _OUTLOOK_MARKER.finditer(text)]
    marks.sort()

    if not marks:
        return [Turn(marker="", body=text.strip())]

    turns: list[Turn] = []
    # Newest turn: text before the first marker, no quoting marker of its own.
    first_start = marks[0][0]
    turns.append(Turn(marker="", body=text[:first_start].strip()))
    # Each subsequent turn spans from its marker to the next marker.
    for i, (start, marker) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        # body is everything after the marker line up to the next marker
        line_end = text.find("\n", start)
        body_start = line_end + 1 if line_end != -1 else end
        turns.append(Turn(marker=marker, body=text[body_start:end].strip()))
    return turns
