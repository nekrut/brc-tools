"""BED-format helpers for Galaxy tool wrappers."""

import glob
from collections import defaultdict
from pathlib import Path


def load_bed_genes_by_source(pattern: str) -> dict:
    """Load genes from BED files matching `pattern`, keyed by source.

    Parameters
    ----------
    pattern : str
        Glob pattern for BED files (e.g. ``"annotations/*.bed"``).

    Returns
    -------
    dict
        Mapping strain name -> list of ``(chrom, start, end, gene_id)`` tuples.
        The strain name is taken from each file stem.

    Notes
    -----
    This is intentionally minimal: comment/blank lines and rows with fewer than
    four columns are skipped. The function is shared by the reciprocal-best-chain
    overlap tool and the PGGB graph-path edge tool.
    """
    genes = defaultdict(list)
    for bed_path in glob.glob(pattern):
        strain = Path(bed_path).stem
        with open(bed_path) as fh:
            for line in fh:
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 4:
                    continue
                chrom = parts[0]
                start = int(parts[1])
                end = int(parts[2])
                gene_id = parts[3]
                genes[strain].append((chrom, start, end, gene_id))
    return genes
