#!/usr/bin/env python3
r"""Cross-product two list collections into a list:list collection.

Reads two manifests of (element_identifier, path) lines -- one for the
ANCHOR (outer) collection and one for the QUERY (inner) collection -- and,
for every (anchor, query) combination, links the QUERY file into a flat
output directory named:

    {anchor}__{query}.dat   (copy/symlink of the query's file)

Galaxy's <discover_datasets> with a two-group pattern
`(?P<identifier_0>...)__(?P<identifier_1>...)\.dat` then nests these into a
list:list collection: outer element identifier = {anchor}, inner element
identifier = {query}. (Element identifiers must not themselves contain the
`__` separator -- pipeline strain/assembly ids do not.)

Self-pairs (anchor == query, matched on element identifier) are EXCLUDED by
default so an anchor is never crossed with itself -- this is the WF-C C.4
(anchor x query) and WF-K per-assembly fanout shape, where the reference
should not be projected onto itself.

Options:
  include_self     - if true, KEEP anchor==query combinations.

NEW helper authored for this pipeline (not a Galaxy built-in); stdlib only.
"""

from __future__ import annotations

__version__ = "1.0.0"

import argparse
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


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--anchors", required=True, type=Path,
                   help="TSV of <element_identifier>\\t<path> for the OUTER (anchor) list.")
    p.add_argument("--queries", required=True, type=Path,
                   help="TSV of <element_identifier>\\t<path> for the INNER (query) list.")
    p.add_argument("--outdir", required=True, type=Path,
                   help="Directory to populate with {anchor}__{query}.dat files.")
    p.add_argument("--ext", default="dat",
                   help="Extension for emitted files (default dat).")
    p.add_argument("--include-self", action="store_true",
                   help="Keep anchor==query combinations (default: exclude).")
    args = p.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    anchors = read_manifest(args.anchors)
    queries = read_manifest(args.queries)
    if not anchors:
        logging.error("Empty anchor collection")
        return 1
    if not queries:
        logging.error("Empty query collection")
        return 1

    a_ids = [e[0] for e in anchors]
    if len(set(a_ids)) != len(a_ids):
        logging.error("Duplicate anchor element identifiers: %s", a_ids)
        return 2
    q_ids = [e[0] for e in queries]
    if len(set(q_ids)) != len(q_ids):
        logging.error("Duplicate query element identifiers: %s", q_ids)
        return 2

    # The flat discover_datasets layout joins anchor/query with `__`; an
    # identifier containing `__` would make the two-group regex ambiguous.
    bad = [i for i in a_ids + q_ids if "__" in i]
    if bad:
        logging.error(
            "Element identifiers must not contain '__' (the cross separator): %s",
            bad,
        )
        return 3

    # Stable order by element identifier so the output is deterministic.
    anchors = sorted(anchors, key=lambda e: e[0])
    queries = sorted(queries, key=lambda e: e[0])

    args.outdir.mkdir(parents=True, exist_ok=True)

    n = 0
    skipped = 0
    for a_id, _a_src in anchors:
        emitted_inner = 0
        for q_id, q_src in queries:
            if a_id == q_id and not args.include_self:
                skipped += 1
                continue
            dest = args.outdir / f"{a_id}__{q_id}.{args.ext}"
            link(q_src, dest)
            n += 1
            emitted_inner += 1
            logging.info("cross %s / %s", a_id, q_id)
        if emitted_inner == 0:
            logging.warning(
                "Anchor %s produced no inner elements (all queries excluded as self).",
                a_id,
            )

    if n == 0:
        logging.error(
            "No cross-product elements produced "
            "(anchors=%d, queries=%d, include_self=%s).",
            len(anchors), len(queries), args.include_self,
        )
        return 1

    logging.info(
        "Emitted %d (anchor,query) elements (%d self-pairs excluded) "
        "from %d anchors x %d queries",
        n, skipped, len(anchors), len(queries),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
