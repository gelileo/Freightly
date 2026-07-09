"""Merged read-only corpus across LTL-mail/ and LTL-mail-2/.

See knowledge/concepts/drafting/eml-parsing.md and platform-architecture.md (v2).
"""
from __future__ import annotations

from pathlib import Path

from scripts.parse_eml import dedupe_snapshots

CORPUS_DIRS = ("LTL-mail", "LTL-mail-2")


def list_corpus(dirs: tuple[str, ...] = CORPUS_DIRS) -> list[Path]:
    paths: list[Path] = []
    for d in dirs:
        paths.extend(sorted(Path(d).glob("*.eml")))
    return paths


def merged_best(dirs: tuple[str, ...] = CORPUS_DIRS) -> dict[str, Path]:
    return dedupe_snapshots(list_corpus(dirs))
