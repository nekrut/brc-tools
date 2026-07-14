"""Sequence helpers for Galaxy tool wrappers."""

from pathlib import Path


COMPLEMENT = str.maketrans("ACGTacgtNn", "TGCAtgcaNn")
CODON_TABLE = {
    "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
    "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
    "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
    "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
    "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
    "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
    "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
    "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
    "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
    "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
    "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
    "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
    "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
    "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
    "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
    "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
}
STOP_CODONS = {"TAA", "TAG", "TGA"}


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


def revcomp(seq: str) -> str:
    """Return the reverse complement of ``seq`` (accepts mixed case)."""
    return seq.translate(COMPLEMENT)[::-1]


def translate(cds: str) -> str:
    """Translate a nucleotide CDS into amino acids using the standard table."""
    aa = []
    upper = cds.upper()
    for i in range(0, len(upper) - 2, 3):
        codon = upper[i : i + 3]
        aa.append(CODON_TABLE.get(codon, "X"))
    return "".join(aa)


def strip_internal_stops(cds: str) -> str:
    """Replace in-frame internal stop codons (all but the terminal codon)."""
    if len(cds) < 3:
        return cds
    codons = [cds[i : i + 3] for i in range(0, len(cds), 3)]
    n_full = len(cds) // 3
    fixed: list[str] = []
    for codon in codons[: max(n_full - 1, 0)]:
        fixed.append("NNN" if codon.upper() in STOP_CODONS else codon)
    fixed.extend(codons[max(n_full - 1, 0) :])
    return "".join(fixed)


def has_internal_stop(cds_nt: str) -> bool:
    """Return True when ``cds_nt`` contains an in-frame stop before the end."""
    if len(cds_nt) < 6 or len(cds_nt) % 3 != 0:
        return False
    n_codons = len(cds_nt) // 3
    for i in range(n_codons - 1):
        codon = cds_nt[i * 3 : (i + 1) * 3].upper()
        if codon in STOP_CODONS:
            return True
    return False


def extract_sequence(fasta, chrom: str, start: int, end: int, strand: str) -> str:
    """Extract a region (1-based, inclusive) from ``fasta`` and strand-correct it."""
    seq = str(fasta[chrom][start - 1 : end]).upper()
    return revcomp(seq) if strand == "-" else seq


def extract_cds(segments, fasta, transcript: str | None = None) -> str:
    """Assemble CDS sequence from parsed segments.

    ``segments`` should be a list of ``(chrom, start, end, strand, phase, parent)``
    tuples such as those returned by :func:`galaxy_data_helpers.gff.parse_gff_cds`.
    When ``transcript`` is given only segments for that Parent are used; otherwise
    segments belonging to the first entry's parent are preferred.
    """

    if not segments:
        return ""
    parent = transcript or segments[0][5]
    parent_segments = [s for s in segments if s[5] == parent] or segments
    strand = parent_segments[0][3]
    ordered = sorted(parent_segments, key=lambda s: s[1], reverse=(strand == "-"))
    parts: list[str] = []
    for chrom, start, end, strd, _phase, _parent in ordered:
        try:
            seq = str(fasta[chrom][start - 1 : end]).upper()
        except (KeyError, IndexError):
            continue
        if strd == "-":
            seq = revcomp(seq)
        parts.append(seq)
    return "".join(parts)
