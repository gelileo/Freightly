"""Deterministic .eml parsing for the broker-email drafting assistant.

See knowledge/concepts/drafting/eml-parsing.md for the governing article.
"""
from __future__ import annotations

import email
from email import policy
from email.message import Message
import re
from dataclasses import dataclass
from pathlib import Path


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


@dataclass
class ParsedEmail:
    path: str
    subject: str
    sender: str
    date: str
    body: str
    bol: list[str]
    pro: list[str]
    turns: list[Turn]


def parse_eml(path: "str | Path") -> ParsedEmail:
    path = Path(path)
    with open(path, "rb") as f:
        msg = email.message_from_binary_file(f, policy=policy.default)
    body = decode_body(msg)
    ids = extract_ids(body + " " + (msg.get("subject") or ""))
    return ParsedEmail(
        path=str(path),
        subject=(msg.get("subject") or "").strip(),
        sender=(msg.get("from") or "").strip(),
        date=(msg.get("date") or "").strip(),
        body=body,
        bol=ids["bol"],
        pro=ids["pro"],
        turns=split_turns(body),
    )


def dedupe_snapshots(paths: list[Path]) -> dict[str, Path]:
    """Group by BOL (from filename), keep the largest file per BOL.

    CAVEAT: this keys on BOL alone and returns ONE Path per BOL. For most BOLs the
    multiple files are snapshots of one growing thread, so "largest" == "most complete".
    But ~24/141 BOLs in the merged corpus carry TWO distinct threads under one BOL —
    a shipment thread AND a separate billing/FFBA thread (e.g. 60114592263, 60112135944).
    For those, this silently keeps only the larger-topic file and hides the other. Callers
    that need a specific topic must parse the specific .eml the customer/broker referenced
    rather than trusting this. See knowledge/concepts/drafting/eml-parsing.md (v2 caveat).
    """
    best: dict[str, Path] = {}
    for p in paths:
        for bol in re.findall(r"\b60\d{9}\b", p.name):
            cur = best.get(bol)
            if cur is None or p.stat().st_size > cur.stat().st_size:
                best[bol] = p
    return best


import sys


def render_thread_md(parsed: ParsedEmail) -> str:
    primary = parsed.bol[0] if parsed.bol else "UNKNOWN"
    lines = [
        f"# Case {primary}",
        "",
        f"- **Subject:** {parsed.subject}",
        f"- **From:** {parsed.sender}",
        f"- **Date:** {parsed.date}",
        f"- **BOL:** {', '.join(parsed.bol) or '(none)'}",
        f"- **PRO#:** {', '.join(parsed.pro) or '(none)'}",
        f"- **Source:** {parsed.path}",
        "",
    ]
    for i, t in enumerate(parsed.turns):
        header = "newest / unquoted" if t.marker == "" else t.marker
        lines.append(f"## Turn {i} — {header}")
        lines.append("")
        lines.append(t.body or "(empty)")
        lines.append("")
    return "\n".join(lines)


def write_case(parsed: ParsedEmail, out_root: Path) -> Path:
    primary = parsed.bol[0] if parsed.bol else "UNKNOWN"
    case_dir = Path(out_root) / primary
    case_dir.mkdir(parents=True, exist_ok=True)
    out = case_dir / "thread.md"
    out.write_text(render_thread_md(parsed), encoding="utf-8")
    return out


def main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Parse a raw .eml into cases/<BOL>/thread.md")
    ap.add_argument("eml", help="path to a .eml file")
    ap.add_argument("--out", default="cases", help="output root (default: cases)")
    ns = ap.parse_args(argv)
    parsed = parse_eml(ns.eml)
    out = write_case(parsed, Path(ns.out))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
