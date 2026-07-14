"""Orthology helpers shared by genomics workflow wrappers."""

from __future__ import annotations

from collections import defaultdict
import csv
import re
from pathlib import Path
from typing import Iterable


WEIGHTS: dict[tuple[str, str], float] = {
    ("cesar2", "I"): 1.00,
    ("cesar2", "PI"): 0.70,
    ("cesar2", "UL"): 0.40,
    ("cesar2", "PG"): 0.40,
    ("cesar2", "L"): 0.00,
    ("cesar2", "M"): 0.00,
    ("cesar2", "FI"): 0.20,
    ("liftoff", "I"): 0.95,
}


def edge_weight(source: str, intactness: str) -> float:
    """Return the numeric weight for an evidence edge."""

    if source == "liftoff":
        return 0.95
    if source == "none":
        return 0.0
    return WEIGHTS.get((source, intactness), 0.10)


class UnionFind:
    """Minimal union-find with path compression."""

    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        parent = self.parent
        path = []
        while parent.get(x, x) != x:
            path.append(x)
            x = parent.get(x, x)
        for node in path:
            parent[node] = x
        parent.setdefault(x, x)
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[ra] = rb


def reciprocal_overlap(a, b) -> float:
    """Return the minimum reciprocal overlap of two intervals.

    ``a`` and ``b`` can be ``(start, end)`` or ``(start, end, payload)`` tuples.
    """

    s1, e1 = a[0], a[1]
    s2, e2 = b[0], b[1]
    ov = max(0, min(e1, e2) - max(s1, s2))
    if ov <= 0:
        return 0.0
    return min(ov / max(1, e1 - s1), ov / max(1, e2 - s2))


def collapse_positions(gene_ids, strain: str, node_positions: dict[str, tuple[str, int, int]]):
    """Group gene IDs by overlapping genomic position for one strain."""

    recs = [(gid, node_positions.get(f"{strain}#{gid}")) for gid in gene_ids]
    positioned = [(pos, gid) for gid, pos in recs if pos is not None]
    no_pos = [gid for gid, pos in recs if pos is None]
    if not positioned:
        return [[g] for g in dict.fromkeys(no_pos)]

    clusters: list[list[str]] = []
    by_chrom: dict[str, list[tuple[int, int, str]]] = defaultdict(list)
    for (chrom, start, end), gid in positioned:
        by_chrom[chrom].append((start, end, gid))

    for chrom, entries in by_chrom.items():
        entries.sort()
        used = [False] * len(entries)
        for i, (s_i, e_i, gid_i) in enumerate(entries):
            if used[i]:
                continue
            group = [gid_i]
            used[i] = True
            for j in range(i + 1, len(entries)):
                if used[j]:
                    continue
                s_j, e_j, gid_j = entries[j]
                if s_j > e_i:
                    break
                ov = max(0, min(e_i, e_j) - max(s_i, s_j))
                if ov and min(
                    ov / max(1, e_i - s_i), ov / max(1, e_j - s_j)
                ) >= 0.2:
                    group.append(gid_j)
                    used[j] = True
            clusters.append(group)

    for gid in dict.fromkeys(no_pos):
        clusters.append([gid])
    return clusters


def safe_name(value: str) -> str:
    """Make an orthogroup identifier filesystem and collection safe."""

    return re.sub(r"[^A-Za-z0-9_.\-]", "_", value)


def load_ortho_table(
    ortho_path: str | Path,
    strains: Iterable[str],
    min_intact: int,
    ref_strain: str,
    normalize_fn=None,
) -> list[tuple[str, str]]:
    """Parse ortholog_table.tsv rows into (orthogroup_id, reference_gene_id)."""

    norm = normalize_fn or (lambda x: x)
    results: list[tuple[str, str]] = []
    strains = list(strains)
    with open(ortho_path) as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for idx, row in enumerate(reader, start=1):
            ref_val = row.get(ref_strain, "-")
            if not ref_val or ref_val in {"-", ""}:
                continue
            n_present = sum(1 for strain in strains if row.get(strain, "-") not in {"-", "", None})
            if n_present < min_intact:
                continue
            og_id = row.get("orthogroup_id") or row.get("og") or row.get("OG") or f"OG{idx:06d}"
            candidates = [norm(part.strip()) for part in re.split(r"[,|]", ref_val) if part.strip()]
            candidates = [cand for cand in candidates if cand]
            if not candidates:
                continue
            results.append((og_id, candidates[0]))
    return results
