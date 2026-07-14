"""Sequence helpers for Galaxy tool wrappers."""

from pathlib import Path


COMPLEMENT = str.maketrans("ACGTacgtNn", "TGCAtgcaNn")


def load_fasta_as_dict(path: str | Path) -> dict[str, str]:
    """Load a FASTA file into a dictionary keyed by sequence name.

    Sequence identifiers are taken from the first whitespace-delimited token
    after each ``>`` header. Sequence characters are uppercased.
    """
    seq = {}
    name = None
    buf = []
    with open(path) as fh:
        for line in fh:
            if line.startswith(">"):
                if name is not None:
                    seq[name] = "".join(buf).upper()
                name = line[1:].split()[0]
                buf = []
            else:
                buf.append(line.strip())
    if name is not None:
        seq[name] = "".join(buf).upper()
    return seq


def classify_repeat_signature(seq: str) -> tuple[str, int]:
    """Classify a sequence by its most likely periodic repeat signature.

    Returns a tuple of ``(signature, score)`` where ``score`` is the purity
    of the best periodic consensus multiplied by 1000 and clamped to the
    range ``0..1000``.

    The smallest period (1..6) that explains the sequence well is preferred.
    Signatures are:

    - ``polyX`` for period-1 mono-nucleotide repeats (e.g. ``polyA``).
    - ``(XY)n`` for short tandem repeats (period 2..6).
    - ``lc`` for sequences that do not match any period with >= 60% purity.
    """
    L = len(seq)
    if L == 0:
        return "lc", 0
    best_frac = 0.0
    best_unit = ""
    for p in range(1, 7):
        if p > L:
            break
        cols = [{} for _ in range(p)]
        for i, ch in enumerate(seq):
            cols[i % p][ch] = cols[i % p].get(ch, 0) + 1
        match = 0
        unit = ""
        for j in range(p):
            best_base = max(cols[j], key=cols[j].get)
            unit += best_base
            match += cols[j][best_base]
        frac = match / L
        if frac > best_frac + 1e-9:
            best_frac, best_unit = frac, unit
        if frac >= 0.85:  # smallest period that explains it well -> stop
            best_frac, best_unit = frac, unit
            break
    score = int(round(best_frac * 1000))
    if best_frac < 0.60:
        return "lc", score
    if len(best_unit) == 1:
        return "poly" + best_unit, score
    return "(" + best_unit + ")n", score


def classify_bed_interval(
    fasta: dict[str, str], chrom: str, start: int, end: int
) -> tuple[str, int]:
    """Classify the sequence underlying a BED3 interval.

    ``start`` and ``end`` are 0-based, half-open coordinates, matching the
    BED convention. The sequence slice is taken from ``fasta[chrom]`` and
    passed to :func:`classify_repeat_signature`.
    """
    seq = fasta.get(chrom, "")[start:end]
    return classify_repeat_signature(seq)
