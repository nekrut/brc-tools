#!/usr/bin/env python3
"""Assemble per-strain % genome masked into a clean MultiQC custom-content table.

bedtools genomecov (hist, -max 1) already did the coverage; this tool only reads
each masker's per-strain genomecov output, picks the genome-wide depth>=1 row
(``genome <TAB> 1 <TAB> covered_bp <TAB> genome_bp <TAB> fraction``), and pivots
the five maskers into one matrix:

    Sample <TAB> dustmasker <TAB> windowmasker <TAB> tantan <TAB> fastan <TAB> union
    PvP01  <TAB> 13.63 ...

The header is plain (no leading ``#``) so MultiQC custom-content reads it as a
table rather than mis-parsing it as embedded YAML config. Inputs are passed as
space-separated ``identifier=path`` tokens per collection (the element-identifier
reading pattern used by collection_relabel_map).
"""
import argparse


def parse_pairs(tokens):
    out = {}
    for t in tokens:
        if not t:
            continue
        ident, _, path = t.partition("=")
        out[ident] = path
    return out


def genome_masked_pct(genomecov_path):
    """Return 100 * fraction from the 'genome' depth>=1 row of a genomecov hist."""
    with open(genomecov_path) as fh:
        for line in fh:
            cols = line.rstrip("\n").split("\t")
            # chrom, depth, covered_bp, chrom_bp, fraction
            if len(cols) >= 5 and cols[0] == "genome" and cols[1] == "1":
                return round(100.0 * float(cols[4]), 2)
    # No depth>=1 genome row => nothing masked
    return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dustmasker", nargs="*", default=[])
    ap.add_argument("--windowmasker", nargs="*", default=[])
    ap.add_argument("--tantan", nargs="*", default=[])
    ap.add_argument("--fastan", nargs="*", default=[])
    ap.add_argument("--union", nargs="*", default=[])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    maskers = [
        ("dustmasker", parse_pairs(a.dustmasker)),
        ("windowmasker", parse_pairs(a.windowmasker)),
        ("tantan", parse_pairs(a.tantan)),
        ("fastan", parse_pairs(a.fastan)),
        ("union", parse_pairs(a.union)),
    ]
    cols = [name for name, _ in maskers]

    # Strain order follows the first non-empty masker collection.
    strains = []
    for _, mp in maskers:
        if mp:
            strains = list(mp.keys())
            break

    with open(a.out, "w") as out:
        out.write("Sample\t" + "\t".join(cols) + "\n")
        for strain in strains:
            vals = []
            for _, mp in maskers:
                p = mp.get(strain)
                vals.append(genome_masked_pct(p) if p else 0.0)
            out.write(strain + "\t" + "\t".join(f"{v:.2f}" for v in vals) + "\n")


if __name__ == "__main__":
    main()
