#!/usr/bin/env python3
"""Select and rename the WF-C chains that WF-C2's TOGA2 pass needs.

WF-C emits one cleaned chain per ordered strain pair, keyed `{target}.{query}`
(56 cells for 8 strains). WF-C2's projection grid is anchors x strains with the
anchor self-cells dropped, keyed `{anchor}_{query}` (21 cells for 3 anchors x 8
strains). TOGA2's `--chain_file` is the reference-to-query chain and its
reference is the anchor, so the chain we want for cell `{anchor}_{query}` is the
one whose TARGET is the anchor: `{anchor}.{query}`.

Bridging the two therefore needs a selection list and a rename map:

  keep.txt     `{anchor}.{query}`                       -> __FILTER_FROM_FILE__
  relabel.tsv  `{anchor}.{query}<TAB>{anchor}_{query}`  -> __RELABEL_FROM_FILE__
  order.txt    `{anchor}_{query}`                       -> __SORTLIST__ (sort_type: file)

The third one is not optional. Galaxy pairs collections in a map-over by
POSITION, not by element identifier. The other grids come out of
__CROSS_PRODUCT_FLAT__ and are therefore in anchor-collection order, while a
chain collection filtered out of WF-C's 56 keeps WF-C's own (alphabetical)
order. Without re-sorting, every cell is handed another cell's chain, TOGA2
reports "Processed 0 chains" and exits -- and because the identifiers are
correct it all looks right. order.txt is the cross-product order, so sorting
the chains by it puts the two sides back in step.

All three are pure functions of the two collections' element identifiers, so
nothing has to be hand-authored per panel.
"""
import argparse


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--anchors", required=True,
                   help="Space-separated anchor element identifiers.")
    p.add_argument("--strains", required=True,
                   help="Space-separated strain (query) element identifiers.")
    p.add_argument("--keep", required=True, help="Output: ids to keep, one per line.")
    p.add_argument("--relabel", required=True, help="Output: 2-column rename map.")
    p.add_argument("--order", required=True,
                   help="Output: cross-product order, one {anchor}_{query} per line.")
    return p.parse_args(argv)


def grid(anchors, strains):
    """Ordered (anchor, query) pairs, anchor self-cells dropped."""
    return [(a, q) for a in anchors for q in strains if q != a]


def main(argv=None):
    args = parse_args(argv)
    anchors = [x for x in args.anchors.split() if x]
    strains = [x for x in args.strains.split() if x]
    if not anchors:
        raise SystemExit("no anchor element identifiers")
    if not strains:
        raise SystemExit("no strain element identifiers")
    missing = [a for a in anchors if a not in strains]
    if missing:
        # Anchors are a subset of the panel; if one is absent the chain it needs
        # was never produced by WF-C, and TOGA2 would fail on a missing element.
        raise SystemExit(f"anchors absent from the strain collection: {missing}")

    pairs = grid(anchors, strains)
    with open(args.keep, "w") as kf, open(args.relabel, "w") as rf, open(args.order, "w") as of:
        for a, q in pairs:
            kf.write(f"{a}.{q}\n")
            rf.write(f"{a}.{q}\t{a}_{q}\n")
            of.write(f"{a}_{q}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
