"""Helpers for ordering multiz folds from sourmash compare matrices."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, List


def load_matrix(path: str | Path) -> tuple[list[str], list[list[str]]]:
    """Return (labels, rows) from a sourmash compare CSV."""

    with open(path, newline="") as fh:
        rows = [row for row in csv.reader(fh) if row and any(c.strip() for c in row)]
    if not rows:
        raise ValueError("compare.csv is empty")
    labels = [c.strip() for c in rows[0]]
    data = rows[1:]
    return labels, data


def similarities_to_hinge(labels: list[str], data: list[list[str]], hinge: str) -> dict[str, float]:
    """Map each label to its similarity vs. the hinge strain."""

    if hinge not in labels:
        return {}
    h_col = labels.index(hinge)
    sims: dict[str, float] = {}
    for i, label in enumerate(labels):
        if i >= len(data):
            break
        row = data[i]
        if h_col < len(row):
            try:
                sims[label] = float(row[h_col])
            except ValueError:
                pass
    if h_col < len(data):
        h_row = data[h_col]
        for j, label in enumerate(labels):
            if label not in sims and j < len(h_row):
                try:
                    sims[label] = float(h_row[j])
                except ValueError:
                    pass
    return sims


def order_queries(queries: Iterable[str], sims: dict[str, float]) -> list[str]:
    """Sort queries by descending similarity to the hinge; missing ones go last."""

    present = [q for q in queries if q in sims]
    missing = [q for q in queries if q not in sims]
    present.sort(key=lambda q: (-sims[q], q))
    return present + missing
