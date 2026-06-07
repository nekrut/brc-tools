#!/usr/bin/env python3
"""Order query strains closest-first for a multiz progressive fold.

Reads a sourmash ``compare.csv`` similarity matrix (Decision 5: similarity,
1.0 = identical) and emits the query strains, one per line, sorted by
*descending* similarity to the hinge strain (closest first).

This is the opposite of the mash distance convention (ascending distance) the
original ``10_multiz.sh`` used: sourmash reports similarity, so the fold order
sorts DESC.

The candidate set is restricted to the query strains actually available as
pairwise MAFs (passed via ``--queries``); any query missing from the matrix
is appended last (stable) so it is still folded, just not prioritised.
"""
import argparse
import csv
import sys


def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description="Order query strains closest-first (descending sourmash "
                    "similarity) for a multiz progressive fold."
    )
    p.add_argument("--compare-csv", required=True,
                   help="sourmash compare.csv similarity matrix.")
    p.add_argument("--hinge", required=True,
                   help="Hinge (reference) strain name.")
    p.add_argument("--queries", required=True, nargs="+",
                   help="Query strain names available as pairwise MAFs.")
    return p.parse_args(argv)


def load_matrix(path):
    """Return (labels, rows) from a sourmash compare CSV.

    sourmash writes a header row of N comma-separated strain labels followed by
    N rows of similarities (no row-label column).
    """
    with open(path, newline="") as fh:
        rows = [r for r in csv.reader(fh) if r and any(c.strip() for c in r)]
    if not rows:
        raise ValueError("compare.csv is empty")
    labels = [c.strip() for c in rows[0]]
    data = rows[1:]
    return labels, data


def similarities_to_hinge(labels, data, hinge):
    """Map each label -> similarity to the hinge.

    The hinge's similarities are the column under the hinge label. Each data row
    i corresponds to labels[i]; the value at the hinge column is sim(labels[i],
    hinge). Falls back to the hinge *row* if the matrix is asymmetric/ragged.
    """
    if hinge not in labels:
        return {}
    h_col = labels.index(hinge)
    sims = {}
    for i, label in enumerate(labels):
        if i >= len(data):
            break
        row = data[i]
        if h_col < len(row):
            try:
                sims[label] = float(row[h_col])
            except ValueError:
                pass
    # Asymmetric / ragged fallback: read the hinge row directly.
    if h_col < len(data):
        h_row = data[h_col]
        for j, label in enumerate(labels):
            if label not in sims and j < len(h_row):
                try:
                    sims[label] = float(h_row[j])
                except ValueError:
                    pass
    return sims


def order_queries(queries, sims):
    """Sort queries by DESCENDING similarity to the hinge (closest first).

    Queries absent from the matrix sort last, preserving their input order.
    Ties broken by name for determinism.
    """
    present = [q for q in queries if q in sims]
    missing = [q for q in queries if q not in sims]
    present.sort(key=lambda q: (-sims[q], q))
    return present + missing


def main(argv=None):
    args = parse_args(argv)
    labels, data = load_matrix(args.compare_csv)
    sims = similarities_to_hinge(labels, data, args.hinge)
    ordered = order_queries(args.queries, sims)
    if not ordered:
        sys.stderr.write("ERROR: no query strains to order\n")
        return 1
    for q in ordered:
        sys.stdout.write(q + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
