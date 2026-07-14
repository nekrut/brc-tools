"""Interval helpers for gene overlap calculations."""

from bisect import bisect_right
from collections import defaultdict


def index_by_chrom(gene_list):
    """Build a per-chromosome index for ``(chrom, start, end, gene_id)`` entries."""

    by = defaultdict(list)
    for chrom, start, end, gene_id in gene_list:
        by[chrom].append((start, end, gene_id))
    idx = {}
    for chrom, entries in by.items():
        entries.sort()
        idx[chrom] = ([e[0] for e in entries], entries)
    return idx


def best_query_gene(qmin, qmax, chrom_index):
    """Return the query gene with the highest fractional overlap in ``[qmin,qmax)``."""

    if chrom_index is None or qmin is None:
        return None
    starts, entries = chrom_index
    best = None
    hi = bisect_right(starts, qmax)
    for i in range(hi):
        start, end, gene_id = entries[i]
        if end <= qmin:
            continue
        overlap = min(qmax, end) - max(qmin, start)
        if overlap <= 0:
            continue
        frac = overlap / max(1, end - start)
        if best is None or frac > best[1]:
            best = (gene_id, frac)
    return best
