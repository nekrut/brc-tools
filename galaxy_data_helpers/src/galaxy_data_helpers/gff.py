"""GFF3 helpers for Galaxy tool wrappers."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re


GENE_FEATURE_TYPES = {"gene"}
TRANSCRIPT_FEATURE_TYPES = {"mRNA", "transcript", "pseudogenic_transcript"}
EXTRA_COPY_RE = re.compile(r"^(.+?)_(\d+)$")
PROTEIN_CODING_TYPES = {"protein_coding_gene", "gene"}
BED_GENE_TYPES = {"gene", "protein_coding_gene", "ncRNA_gene", "pseudogene"}


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


def collect_protein_coding_genes(gff_path, feature_types=None) -> set[str]:
    """Return the set of gene IDs whose type is protein-coding (or `feature_types`)."""

    types = set(feature_types or PROTEIN_CODING_TYPES)
    genes: set[str] = set()
    with open(gff_path) as fh:
        for line in fh:
            if not line or line.startswith("#"):
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 9 or cols[2] not in types:
                continue
            attrs = parse_gff_attributes_to_dict(cols[8])
            gid = attrs.get("ID")
            if gid:
                genes.add(gid)
    return genes


def filter_bed12(raw_bed_path, out_path, allowed_genes: set[str] | None = None) -> tuple[int, int]:
    """Filter a BED12 emitted by gffread, rewriting name column to gene IDs."""

    total = kept = 0
    gene_pattern = re.compile(r"geneID=([^;]+)")
    with open(raw_bed_path) as src, open(out_path, "w") as dst:
        for line in src:
            row = line.rstrip("\n")
            if not row:
                continue
            cols = row.split("\t")
            total += 1
            if len(cols) < 12:
                continue
            gene_id = None
            if len(cols) >= 13:
                match = gene_pattern.search(cols[12])
                if match:
                    gene_id = match.group(1)
            if gene_id is None:
                gene_id = cols[3]
            if allowed_genes and gene_id not in allowed_genes:
                continue
            trimmed = cols[:12]
            trimmed[3] = gene_id
            dst.write("\t".join(trimmed) + "\n")
            kept += 1
    return total, kept


def build_isoforms(gff_path, out_path) -> int:
    """Write `gene_id<TAB>transcript_id` rows for every mRNA feature."""

    rows: list[tuple[str, str]] = []
    with open(gff_path) as fh:
        for line in fh:
            if not line or line.startswith("#"):
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 9 or cols[2] != "mRNA":
                continue
            attrs = parse_gff_attributes_to_dict(cols[8])
            tx = attrs.get("ID", "")
            gene = attrs.get("Parent", "")
            if tx and gene:
                rows.append((gene, tx))
    rows.sort(key=lambda pair: (pair[0], pair[1]))
    with open(out_path, "w") as dst:
        for gene, tx in rows:
            dst.write(f"{gene}\t{tx}\n")
    return len(rows)


def parse_gene_id(attributes: str) -> str:
    """Extract the gene ID from a GFF3 attribute column, stripping a leading gene- prefix."""

    idx = attributes.rfind("ID=")
    if idx == -1:
        return ""
    value = attributes[idx + 3 :]
    semi = value.find(";")
    if semi != -1:
        value = value[:semi]
    if value.startswith("gene-"):
        value = value[5:]
    return value


def gff_to_bed_rows(gff_path, out_path, gene_types=None) -> int:
    """Emit BED4 gene rows (chrom, start0, end, gene_id) from a GFF3."""

    types = set(gene_types or BED_GENE_TYPES)
    n = 0
    with open(gff_path) as src, open(out_path, "w") as dst:
        for line in src:
            if not line or line.startswith("#"):
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 9 or cols[2] not in types:
                continue
            gene_id = parse_gene_id(cols[8])
            if not gene_id:
                continue
            try:
                start0 = int(cols[3]) - 1
                end = int(cols[4])
            except ValueError:
                continue
            dst.write(f"{cols[0]}\t{start0}\t{end}\t{gene_id}\n")
            n += 1
    return n
