"""Lightweight IO helpers (manifest parsing, gzip detection)."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Tuple
import gzip
import io


def read_manifest(path: str | Path, delimiter: str = "\t") -> List[Tuple[str, str]]:
    """Read a two-column manifest (identifier <DELIM> path), skipping blanks."""

    entries: List[Tuple[str, str]] = []
    with open(path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split(delimiter, 1)
            if len(parts) != 2:
                continue
            entries.append((parts[0], parts[1]))
    return entries


def open_maybe_gz(path: str | Path, mode: str = "rt") -> io.IOBase:
    """Open `path`, sniffing gzip magic bytes instead of trusting extensions."""

    path = Path(path)
    if "r" in mode:
        with open(path, "rb") as probe:
            is_gz = probe.read(2) == b"\x1f\x8b"
        if is_gz:
            return gzip.open(path, mode)
    if "w" in mode and mode.endswith("t"):
        return open(path, mode)
    return open(path, mode)
