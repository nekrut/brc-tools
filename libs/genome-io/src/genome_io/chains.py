"""Helpers for UCSC chain files (phase_e_rbest_overlap)."""

from __future__ import annotations

from pathlib import Path
from typing import Generator, Union


# Not `dict[str, int | str]`: a type alias is a plain assignment, so it is
# evaluated at import time and PEP 604 unions need 3.10 (the module's
# `from __future__ import annotations` only defers real annotations).
ChainHeader = dict[str, Union[int, str]]
ChainBlock = tuple[int, int, int, int, str]


def parse_chain_header(line: str) -> ChainHeader | None:
    """Parse a ``chain`` header line into a dict of fields."""

    parts = line.strip().split()
    if len(parts) < 13 or parts[0] != "chain":
        return None
    return {
        "tName": parts[2],
        "tSize": int(parts[3]),
        "tStart": int(parts[5]),
        "tEnd": int(parts[6]),
        "qName": parts[7],
        "qSize": int(parts[8]),
        "qStrand": parts[9],
        "qStart": int(parts[10]),
        "qEnd": int(parts[11]),
    }


def iter_chains(path: str | Path) -> Generator[tuple[ChainHeader, list[ChainBlock]], None, None]:
    """Yield ``(header, blocks)`` records from a UCSC chain file."""

    header = None
    blocks: list[ChainBlock] = []
    t = q = 0
    with open(path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("chain"):
                if header:
                    yield header, blocks
                header = parse_chain_header(line)
                blocks = []
                if not header:
                    continue
                t = header["tStart"]
                q = header["qStart"]
            elif header and line.strip():
                cols = line.split()
                size = int(cols[0])
                if header["qStrand"] == "+":
                    qf0, qf1 = q, q + size
                else:
                    qf1 = header["qSize"] - q
                    qf0 = header["qSize"] - (q + size)
                blocks.append((t, t + size, qf0, qf1, header["qStrand"]))
                if len(cols) >= 3:
                    t += size + int(cols[1])
                    q += size + int(cols[2])
        if header:
            yield header, blocks


def project_gene(start: int, end: int, blocks: list[ChainBlock]) -> tuple[int, int | None, int | None]:
    """Project a target gene interval through chain blocks into query coords."""

    aligned = 0
    qmin = qmax = None
    for t0, t1, qf0, qf1, strand in blocks:
        lo, hi = max(start, t0), min(end, t1)
        if hi <= lo:
            continue
        aligned += hi - lo
        if strand == "+":
            a, b = qf0 + (lo - t0), qf0 + (hi - t0)
        else:
            a, b = qf1 - (hi - t0), qf1 - (lo - t0)
        lo_q, hi_q = (a, b) if a <= b else (b, a)
        qmin = lo_q if qmin is None else min(qmin, lo_q)
        qmax = hi_q if qmax is None else max(qmax, hi_q)
    return aligned, qmin, qmax
