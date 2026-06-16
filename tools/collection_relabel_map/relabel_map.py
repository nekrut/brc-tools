#!/usr/bin/env python3
"""Emit `{a}_{b}\t{a}.{b}` for every ordered pair of collection element identifiers.
The cross-product cells are named `A_B` (underscore join); downstream Phase E expects
`A.B`. This 2-col TSV drives WF-C's __RELABEL_FROM_FILE__ step."""
import argparse, itertools
ap = argparse.ArgumentParser()
ap.add_argument("--ids", required=True, help="space-separated element identifiers")
ap.add_argument("--out", required=True)
a = ap.parse_args()
ids = [x for x in a.ids.split() if x]
with open(a.out, "w") as f:
    for x, y in itertools.product(ids, ids):
        f.write(f"{x}_{y}\t{x}.{y}\n")
