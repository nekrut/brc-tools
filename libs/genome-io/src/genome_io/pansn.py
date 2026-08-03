"""Helpers for PanSN path names and PGGB graph outputs."""

from collections import defaultdict
from pathlib import Path
from typing import TextIO


def parse_pansn(name: str) -> tuple[str, str]:
    """Return (sample, contig) from a PanSN-style name like ``S#H#CONTIG``."""

    parts = name.split("#")
    if len(parts) >= 3:
        return parts[0], parts[2]
    return name, name


def load_graph_paths(paths_tsv: str | Path) -> dict[str, set[str]]:
    """Parse ``odgi paths --haplotypes`` output into contig -> set(strain)."""

    contig_members: dict[str, set[str]] = defaultdict(set)
    path = Path(paths_tsv)
    if not path.exists():
        return contig_members
    with open(path) as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("\t")
            if not parts:
                continue
            strain, contig = parse_pansn(parts[0])
            contig_members[contig].add(strain)
    return contig_members


def rename_headers(in_fh: TextIO, out_fh: TextIO, sample: str, haplotype: int = 1, delimiter: str = "#") -> int:
    """Prefix FASTA headers with PanSN SAMPLE/HAP/CONTIG fields."""

    prefix = f"{sample}{delimiter}{haplotype}{delimiter}"
    n = 0
    for line in in_fh:
        if line.startswith(">"):
            n += 1
            contig = line[1:].split(None, 1)[0]
            rest = line[1 + len(contig) :]
            out_fh.write(f">{prefix}{contig}{rest}")
        else:
            out_fh.write(line)
    return n
