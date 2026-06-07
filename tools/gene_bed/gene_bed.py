#!/usr/bin/env python3
"""Emit a 4-column gene BED (chrom, start-1, end, gene_id) from a native GFF3.

Selects gene-type feature rows (gene / protein_coding_gene / ncRNA_gene /
pseudogene), parses the ID attribute, strips a leading "gene-" prefix, and
writes BED4 with a 0-based start.

Logic ported verbatim from the GFF->BED awk step in
Pv4-pangenome/v3/pipeline/impl/06_consensus.sh (Phase E / WF-E), where it
produces the per-strain orthogroup node set consumed by the rbest-overlap
and graph-edge sources of the Phase E consensus.

stdlib only.
"""
import argparse
import sys

# Feature types treated as "gene" rows, matching 06_consensus.sh:
#   $3=="gene"||$3=="protein_coding_gene"||$3=="ncRNA_gene"||$3=="pseudogene"
GENE_TYPES = {"gene", "protein_coding_gene", "ncRNA_gene", "pseudogene"}


def parse_id(attributes):
    """Replicate: id=$9; sub(/.*ID=/,"",id); sub(/;.*/,"",id); sub(/^gene-/,"",id).

    Take everything after the last 'ID=' (awk's greedy .* is rightmost), then
    cut at the first ';', then strip a leading 'gene-' prefix.
    """
    idx = attributes.rfind("ID=")
    if idx == -1:
        return ""
    val = attributes[idx + len("ID="):]
    semi = val.find(";")
    if semi != -1:
        val = val[:semi]
    if val.startswith("gene-"):
        val = val[len("gene-"):]
    return val


def gff_to_bed(infile, outfile):
    n = 0
    for line in infile:
        if not line or line[0] == "#":
            continue
        line = line.rstrip("\n")
        if not line:
            continue
        cols = line.split("\t")
        if len(cols) < 9:
            continue
        if cols[2] not in GENE_TYPES:
            continue
        gene_id = parse_id(cols[8])
        if gene_id == "":
            continue
        try:
            start0 = int(cols[3]) - 1
            end = int(cols[4])
        except ValueError:
            continue
        outfile.write("%s\t%d\t%s\t%s\n" % (cols[0], start0, str(end), gene_id))
        n += 1
    return n


def main():
    ap = argparse.ArgumentParser(
        description="Emit a 4-column gene BED from a native GFF3 annotation."
    )
    ap.add_argument("--input", required=True, help="Input GFF3 annotation")
    ap.add_argument("--output", required=True, help="Output BED4 file")
    args = ap.parse_args()

    with open(args.input) as fh, open(args.output, "w") as out:
        n = gff_to_bed(fh, out)
    sys.stderr.write("gene_bed: wrote %d gene rows\n" % n)


if __name__ == "__main__":
    main()
