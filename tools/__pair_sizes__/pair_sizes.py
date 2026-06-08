#!/usr/bin/env python3
"""Emit the per-pair .sizes files as a list:paired keyed {A}__vs__{B}.

Reads a manifest of (element_identifier, path) lines for a per-strain
`.sizes` list collection and, for every unordered pair (A, B) with A<B,
writes two files into the output directory:

    {A}__vs__{B}_forward.sizes   (copy/symlink of A's .sizes)
    {A}__vs__{B}_reverse.sizes   (copy/symlink of B's .sizes)

This MIRRORS the `pair_strains` enumeration EXACTLY (same lexicographic
A<B ordering, same {A}__vs__{B} element identifiers), so the resulting
list:paired sizes collection is identifier-matched to the `pair_strains`
list:paired FASTA collection and the two can be map-over-zipped: the
forward slot is the target (A) sizes, the reverse slot is the query (B)
sizes -- exactly what axtChain / chainPreNet / chainNet need per pair.

Pair selection mirrors pair_strains:
  include_self     - if true, also emit (A, A).
  both_directions  - if true, emit both (A, B) and (B, A) ordered pairs.

NEW helper authored for this pipeline (not a Galaxy built-in); stdlib only.
"""

from __future__ import annotations

__version__ = "1.0.0"

import argparse
import itertools
import logging
import os
import sys
from pathlib import Path


def read_manifest(path: Path) -> list[tuple[str, str]]:
    """Read tab-separated (identifier, path) lines; skip blanks."""
    entries: list[tuple[str, str]] = []
    with open(path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line:
                continue
            ident, src = line.split("\t", 1)
            entries.append((ident, src))
    return entries


def link(src: str, dest: Path) -> None:
    """Symlink src->dest, falling back to copy across filesystems."""
    try:
        os.symlink(os.path.abspath(src), dest)
    except OSError:
        import shutil

        shutil.copyfile(src, dest)


def enumerate_pairs(
    entries: list[tuple[str, str]],
    include_self: bool,
    both_directions: bool,
) -> list[tuple[tuple[str, str], tuple[str, str]]]:
    # Stable order by element identifier so A<B is deterministic --
    # identical to pair_strains.enumerate_pairs.
    ordered = sorted(entries, key=lambda e: e[0])
    pairs: list[tuple[tuple[str, str], tuple[str, str]]] = []
    if both_directions:
        for a, b in itertools.permutations(ordered, 2):
            pairs.append((a, b))
        if include_self:
            for a in ordered:
                pairs.append((a, a))
    else:
        for a, b in itertools.combinations(ordered, 2):
            pairs.append((a, b))
        if include_self:
            for a in ordered:
                pairs.append((a, a))
    return pairs


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", required=True, type=Path,
                   help="TSV of <element_identifier>\\t<sizes_path> lines.")
    p.add_argument("--outdir", required=True, type=Path,
                   help="Directory to populate with *_forward/*_reverse .sizes files.")
    p.add_argument("--ext", default="sizes",
                   help="Extension for emitted files (default sizes).")
    p.add_argument("--include-self", action="store_true")
    p.add_argument("--both-directions", action="store_true")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    entries = read_manifest(args.manifest)
    if len(entries) < 1:
        logging.error("Empty input collection")
        return 1

    idents = [e[0] for e in entries]
    if len(set(idents)) != len(idents):
        logging.error("Duplicate element identifiers: %s", idents)
        return 2

    args.outdir.mkdir(parents=True, exist_ok=True)

    pairs = enumerate_pairs(entries, args.include_self, args.both_directions)
    if not pairs:
        logging.error(
            "No pairs produced (n=%d, include_self=%s, both_directions=%s). "
            "Need >=2 strains, or enable include_self.",
            len(entries), args.include_self, args.both_directions,
        )
        return 1

    for (a_id, a_src), (b_id, b_src) in pairs:
        base = f"{a_id}__vs__{b_id}"
        link(a_src, args.outdir / f"{base}_forward.{args.ext}")
        link(b_src, args.outdir / f"{base}_reverse.{args.ext}")
        logging.info("pair %s", base)

    logging.info("Emitted %d pair-sizes from %d strains", len(pairs), len(entries))
    return 0


if __name__ == "__main__":
    sys.exit(main())
