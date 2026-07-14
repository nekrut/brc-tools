"""MAF-format helpers for Galaxy tool wrappers."""


def species_of(seq_name: str) -> str:
    """Extract the species/accession prefix from an MAF s-line sequence name.

    MAF s-lines have the format ``s <seq_name> ...``. The sequence name is
    conventionally ``species.chrom`` (UCSC) or ``GCA_123456789.1.chrom`` (GenBank
    accession with embedded dots).

    If the leading token starts with ``GCA_`` or ``GCF_`` and a second dot-
    separated part exists, the first two parts are treated as the accession.
    Otherwise the species is the leading token (everything before the first dot).
    """
    parts = seq_name.split(".")
    if len(parts) >= 2 and parts[0].startswith(("GCA_", "GCF_")):
        return parts[0] + "." + parts[1]
    return parts[0]
