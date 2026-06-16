#!/usr/bin/env python3
"""Emit one `{id}_{id}` line per collection element identifier.
Used to drop the self-cross diagonal (X_X) in WF-C's __FILTER_FROM_FILE__ steps:
panel self-pairs (on the genome list) and anchor self-pairs (on the anchor list)."""
import argparse
ap = argparse.ArgumentParser()
ap.add_argument("--ids", required=True, help="space-separated element identifiers")
ap.add_argument("--out", required=True)
a = ap.parse_args()
ids = [x for x in a.ids.split() if x]
with open(a.out, "w") as f:
    for i in ids:
        f.write(f"{i}_{i}\n")
