"""Collection relabeling helpers for Galaxy wrapper workflows."""

from __future__ import annotations

from itertools import product
from typing import Iterable, Tuple


def relabel_pairs(ids: Iterable[str]) -> list[tuple[str, str]]:
    """Return (underscore_id, dotted_id) pairs for every ordered combination."""

    pairs: list[tuple[str, str]] = []
    clean_ids = [item for item in ids if item]
    for a, b in product(clean_ids, clean_ids):
        pairs.append((f"{a}_{b}", f"{a}.{b}"))
    return pairs


def self_pairs(ids: Iterable[str]) -> list[tuple[str, str]]:
    """Return (X_X, X.X) pairs for the diagonal self-products."""

    return [(f"{item}_{item}", f"{item}.{item}") for item in ids if item]
