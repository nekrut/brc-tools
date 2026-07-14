"""GFF3 helpers for Galaxy tool wrappers."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re


GENE_FEATURE_TYPES = {"gene"}
TRANSCRIPT_FEATURE_TYPES = {"mRNA", "transcript", "pseudogenic_transcript"}
EXTRA_COPY_RE = re.compile(r"^(.+?)_(\d+)$")


def parse_gff_attributes_to_dict(attr_str: str) -> dict:
    """Parse a GFF3 attribute string (column 9) into a dictionary.

    GFF3 attributes are semicolon-separated ``key=value`` pairs. The trailing
    semicolon, if present, is ignored. Empty values are preserved.

    Parameters
    ----------
    attr_str : str
        Raw ninth column of a GFF3 record.

    Returns
    -------
    dict
        Mapping of attribute key to value.

    Notes
    -----
    This is a minimal, strict parser used by the Liftoff triage and TOGA2
    merge tool wrappers. It does not unescape URL-encoded values; if that
    becomes required it should be added explicitly.
    """
    d = {}
    for kv in attr_str.strip().rstrip(";").split(";"):
        kv = kv.strip()
        if "=" in kv:
            key, value = kv.split("=", 1)
            d[key.strip()] = value.strip()
    return d


def normalize_gene_id(gid: str) -> str:
    """Strip common transcript / extra-copy suffixes from a gene id."""

    if not gid or gid == "None":
        return gid
    for pattern in (r"^(.+)_t\d+$", r"^(.+)\.\d+$"):
        match = re.match(pattern, gid)
        if match:
            return match.group(1)
    match = EXTRA_COPY_RE.match(gid)
    if match:
        core, suffix = match.group(1), match.group(2)
        if len(suffix) <= 2 and not core.endswith("_"):
            return core
    return gid


def parse_gff_cds(
    gff_path, target_genes: set[str] | None = None, transcript_types=None
):
    """Build a ``gene_id -> [segments]`` map from a GFF3 file.

    Each segment tuple is ``(chrom, start, end, strand, phase, parent)`` where
    ``parent`` is the transcript ID owning the CDS fragment.
    """

    path = Path(gff_path)
    out: dict[str, list[tuple]] = defaultdict(list)
    if not path.exists():
        return out
    tx_to_gene: dict[str, str] = {}
    tx_types = set(transcript_types or TRANSCRIPT_FEATURE_TYPES)
    with open(path) as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 9:
                continue
            ftype = fields[2]
            attrs = parse_gff_attributes_to_dict(fields[8])
            if ftype in tx_types:
                tx_id = attrs.get("ID")
                parent = attrs.get("Parent")
                if tx_id and parent:
                    tx_to_gene[tx_id] = parent

    with open(path) as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) < 9 or fields[2] != "CDS":
                continue
            attrs = parse_gff_attributes_to_dict(fields[8])
            parent = attrs.get("Parent", "")
            gene_id = tx_to_gene.get(parent, parent.rsplit(".", 1)[0])
            gene_id = normalize_gene_id(gene_id)
            if target_genes is not None and gene_id not in target_genes:
                continue
            chrom = fields[0]
            start = int(fields[3])
            end = int(fields[4])
            strand = fields[6]
            phase = int(fields[7]) if fields[7] != "." else 0
            out[gene_id].append((chrom, start, end, strand, phase, parent))
    return out
