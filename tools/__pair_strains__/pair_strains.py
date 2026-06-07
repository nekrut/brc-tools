#!/usr/bin/env python3
"""Enumerate unordered strain pairs from a list collection of FASTAs.

Reads a manifest of (element_identifier, path) lines (one per input
collection element) and, for every selected pair (A, B), writes two
files into the output directory:

    {A}__vs__{B}_forward.fa   (copy/symlink of A's FASTA)
    {A}__vs__{B}_reverse.fa   (copy/symlink of B's FASTA)

Galaxy's <discover_datasets> then groups the *_forward / *_reverse pair
under list element identifier `{A}__vs__{B}` in a list:paired collection.

Pair selection:
  include_self     - if true, also emit (A, A) pairs.
  both_directions  - if true, emit both (A, B) and (B, A); otherwise only
                     the unordered pair A<B (lexicographic on identifier).

NEW ~5-line helper authored for this pipeline (not a Galaxy built-in).
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
    # Stable order by element identifier so A<B is deterministic.
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
                   help="TSV of <element_identifier>\\t<fasta_path> lines.")
    p.add_argument("--outdir", required=True, type=Path,
                   help="Directory to populate with *_forward/*_reverse files.")
    p.add_argument("--ext", default="fa",
                   help="Extension for emitted files (default fa).")
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

    logging.info("Emitted %d pairs from %d strains", len(pairs), len(entries))
    return 0


if __name__ == "__main__":
    sys.exit(main())
