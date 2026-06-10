#!/usr/bin/env python3
"""group_cds_by_og.py — group per-strain CDS by orthogroup (WF-F helper).

Extracts ONLY the CDS-grouping core of the Pv4 pipeline's build_msa.py
(impl/scripts/build_msa.py). The downstream alignment (mafft / pal2nal /
trimal) is intentionally NOT included here — those are separate IUC steps.

For each orthogroup in ortholog_table.tsv that has >= --min-intact intact
QUERY members (the reference is not counted toward this threshold, matching
v3 build_msa.py's `len(seqs_cds) - 1 < min_intact`), this writes TWO per-OG
multifastas into --out-dir:

  {og}.cds.fa  — nucleotide CDS, one record per member strain. The CDS is
                 extracted from the (softmasked) genome FASTA via pyfaidx using
                 the GFF CDS segments (parse_gff_cds + extract_cds), with
                 internal stop codons replaced by NNN and the sequence
                 codon-truncated so len(seq) % 3 == 0.
  {og}.pep.fa  — protein, one record per member strain (translate + rstrip('*')).
                 Genes whose REFERENCE CDS carries an internal stop are dropped
                 entirely (build_msa.py logic ~lines 271-293).

The reference strain is keyed on its own fixed GFF; each query strain on its
merged ({REF}-as-ref/{query}.annotation.gff3) GFF. Gene IDs are matched on the
normalized gene id (parse_gff_cds normalize logic).

Galaxy <discover_datasets> then turns the two file sets into two parallel
'list' collections keyed by the orthogroup id (element_identifier = {og}).
"""

from __future__ import annotations

__version__ = "1.0.0"

import argparse
import csv
import logging
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    from pyfaidx import Fasta
except ImportError:  # pragma: no cover
    sys.exit("pyfaidx required — install pyfaidx (bioconda)")

COMPLEMENT = str.maketrans("ACGTacgtNn", "TGCAtgcaNn")
CODON_TABLE = {
    'TTT': 'F', 'TTC': 'F', 'TTA': 'L', 'TTG': 'L',
    'CTT': 'L', 'CTC': 'L', 'CTA': 'L', 'CTG': 'L',
    'ATT': 'I', 'ATC': 'I', 'ATA': 'I', 'ATG': 'M',
    'GTT': 'V', 'GTC': 'V', 'GTA': 'V', 'GTG': 'V',
    'TCT': 'S', 'TCC': 'S', 'TCA': 'S', 'TCG': 'S',
    'CCT': 'P', 'CCC': 'P', 'CCA': 'P', 'CCG': 'P',
    'ACT': 'T', 'ACC': 'T', 'ACA': 'T', 'ACG': 'T',
    'GCT': 'A', 'GCC': 'A', 'GCA': 'A', 'GCG': 'A',
    'TAT': 'Y', 'TAC': 'Y', 'TAA': '*', 'TAG': '*',
    'CAT': 'H', 'CAC': 'H', 'CAA': 'Q', 'CAG': 'Q',
    'AAT': 'N', 'AAC': 'N', 'AAA': 'K', 'AAG': 'K',
    'GAT': 'D', 'GAC': 'D', 'GAA': 'E', 'GAG': 'E',
    'TGT': 'C', 'TGC': 'C', 'TGA': '*', 'TGG': 'W',
    'CGT': 'R', 'CGC': 'R', 'CGA': 'R', 'CGG': 'R',
    'AGT': 'S', 'AGC': 'S', 'AGA': 'R', 'AGG': 'R',
    'GGT': 'G', 'GGC': 'G', 'GGA': 'G', 'GGG': 'G',
}
STOP_CODONS = {'TAA', 'TAG', 'TGA'}


def revcomp(seq: str) -> str:
    return seq.translate(COMPLEMENT)[::-1]


def translate(cds: str) -> str:
    aa = []
    for i in range(0, len(cds) - 2, 3):
        codon = cds[i:i + 3].upper()
        aa.append(CODON_TABLE.get(codon, 'X'))
    return ''.join(aa)


def strip_internal_stops(cds: str) -> str:
    """Replace in-frame internal stop codons (not the final codon) with NNN."""
    if len(cds) < 3:
        return cds
    codons = [cds[i:i + 3] for i in range(0, len(cds), 3)]
    n_full = len(cds) // 3
    fixed = []
    for codon in codons[:n_full - 1]:  # all but last full codon
        fixed.append('NNN' if codon.upper() in STOP_CODONS else codon)
    fixed.extend(codons[n_full - 1:])  # last codon + any remainder
    return ''.join(fixed)


def normalize_gene_id(gene_id: str) -> str:
    """Normalize a Liftoff extra-copy suffix (e.g. PKNH_1234500_1 -> PKNH_1234500)."""
    m = re.match(r'^(.+)_(\d+)$', gene_id)
    if m and len(m.group(2)) <= 2 and not m.group(1).endswith('_'):
        return m.group(1)
    return gene_id


def parse_gff_cds(gff_path, target_genes=None):
    """Return dict gene_id -> [(chrom, start, end, strand, phase, parent)]."""
    out: dict = defaultdict(list)
    if not Path(gff_path).exists():
        return out
    tx_to_gene: dict = {}
    TX_TYPES = {'mRNA', 'transcript', 'pseudogenic_transcript'}
    with open(gff_path) as fh:
        for ln in fh:
            if ln.startswith('#') or not ln.strip():
                continue
            f = ln.rstrip('\n').split('\t')
            if len(f) < 9:
                continue
            if f[2] in TX_TYPES:
                attrs = {kv.split('=', 1)[0]: kv.split('=', 1)[1]
                         for kv in f[8].split(';') if '=' in kv}
                tx_id = attrs.get('ID')
                parent = attrs.get('Parent')
                if tx_id and parent:
                    tx_to_gene[tx_id] = parent
    with open(gff_path) as fh:
        for ln in fh:
            if ln.startswith('#') or not ln.strip():
                continue
            f = ln.rstrip('\n').split('\t')
            if len(f) < 9 or f[2] != 'CDS':
                continue
            attrs = {kv.split('=', 1)[0]: kv.split('=', 1)[1]
                     for kv in f[8].split(';') if '=' in kv}
            parent = attrs.get('Parent', '')
            gene_id = tx_to_gene.get(parent, parent.rsplit('.', 1)[0])
            gene_id = normalize_gene_id(gene_id)
            if target_genes is not None and gene_id not in target_genes:
                continue
            out[gene_id].append((f[0], int(f[3]), int(f[4]), f[6],
                                 int(f[7]) if f[7] != '.' else 0, parent))
    return out


def extract_cds(fasta, segments) -> str:
    if not segments:
        return ''
    strand = segments[0][3]
    parent = segments[0][5]
    same_tx = [s for s in segments if s[5] == parent] or segments
    same_tx.sort(key=lambda x: x[1], reverse=(strand == '-'))
    parts = []
    for chrom, start, end, strd, _phase, _p in same_tx:
        try:
            seq = str(fasta[chrom][start - 1:end]).upper()
        except (KeyError, IndexError):
            continue
        if strd == '-':
            seq = revcomp(seq)
        parts.append(seq)
    return ''.join(parts)


def read_manifest(path: Path) -> list[tuple[str, str]]:
    """Read tab-separated (element_identifier, path) lines; skip blanks."""
    entries: list[tuple[str, str]] = []
    with open(path) as fh:
        for line in fh:
            line = line.rstrip('\n')
            if not line:
                continue
            ident, src = line.split('\t', 1)
            entries.append((ident, src))
    return entries


def load_ortho_table(ortho_path, all_strains, min_intact, ref_strain,
                     ref_genes=None):
    """Return list of (og_id, gene_id) for OGs with >= min_intact present strains.

    og_id is the orthogroup_id column (used as collection element identifier).
    gene_id is the normalized reference gene id used to look up CDS segments.

    The reference column value can be a composite like
    ``PVPAM_140051100|PVW1_140049400,PVP01_1443100`` where the actual
    reference-strain gene is NOT the first token but an alias (the merged
    annotations and ref GFF are keyed by the reference gene id). When
    ``ref_genes`` (the set of gene ids present in the reference GFF) is given,
    we pick the candidate that is an actual reference gene; otherwise we fall
    back to the first candidate.
    """
    ogs: list[tuple[str, str]] = []
    with open(ortho_path) as fh:
        r = csv.DictReader(fh, delimiter='\t')
        for i, row in enumerate(r):
            ref_val = row.get(ref_strain, '-')
            if ref_val in ('-', '', None):
                continue
            n_present = sum(1 for s in all_strains
                            if row.get(s, '-') not in ('-', '', None))
            if n_present < min_intact:
                continue
            og_id = (row.get('orthogroup_id')
                     or row.get('og')
                     or row.get('OG')
                     or f'OG{i + 1:06d}')
            # ref_val may list several gene ids separated by ',' and '|'
            # (primary|alias,alias). Gather all candidates, then prefer the one
            # that is an actual reference-GFF gene.
            cands = [normalize_gene_id(t.strip())
                     for t in re.split(r'[,|]', ref_val) if t.strip()]
            cands = [c for c in cands if c]
            gene_id = ''
            if ref_genes is not None:
                gene_id = next((c for c in cands if c in ref_genes), '')
            if not gene_id and cands:
                gene_id = cands[0]
            if gene_id:
                ogs.append((og_id, gene_id))
    return ogs


def safe_name(s: str) -> str:
    """Make an OG id safe as a filename / collection element identifier."""
    return re.sub(r'[^A-Za-z0-9_.\-]', '_', s)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ortho', required=True, help='ortholog_table.tsv')
    ap.add_argument('--ref', required=True, help='Reference strain name (table column).')
    ap.add_argument('--ref-gff', required=True, help="Reference fixed gff3.")
    ap.add_argument('--ref-fasta', required=True, help='Reference softmasked FASTA.')
    ap.add_argument('--query-gff-manifest', required=True,
                    help='TSV <strain>\\t<gff_path>, one per query strain.')
    ap.add_argument('--query-fasta-manifest', required=True,
                    help='TSV <strain>\\t<fasta_path>, one per query strain.')
    ap.add_argument('--min-intact', type=int, default=2)
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--log-level', default='INFO')
    args = ap.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format='%(levelname)s %(message)s',
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    gff_entries = dict(read_manifest(Path(args.query_gff_manifest)))
    fa_entries = dict(read_manifest(Path(args.query_fasta_manifest)))
    queries = sorted(gff_entries)
    if set(gff_entries) != set(fa_entries):
        logging.error('Query GFF and FASTA collections have mismatched strains: '
                      'gff=%s fasta=%s', sorted(gff_entries), sorted(fa_entries))
        return 2
    if args.ref in queries:
        logging.error('Reference strain %s also present in query collections', args.ref)
        return 2

    all_strains = [args.ref] + queries
    outdir = Path(args.out_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    # 0) Reference GFF CDS map (parsed once, unfiltered): its keys are used to
    #    disambiguate composite ref-column values where the reference gene is an
    #    alias, not the first token, and the map itself serves as ref_cds_map.
    ref_cds_map = parse_gff_cds(args.ref_gff)
    ref_all_genes = set(ref_cds_map)

    # 1) Orthogroups passing the min-intact filter -> (og_id, ref_gene_id)
    ogs = load_ortho_table(args.ortho, all_strains, args.min_intact, args.ref,
                           ref_genes=ref_all_genes)
    target_genes = {g for _, g in ogs}
    logging.info('%d orthogroups intact in >= %d strains (%d distinct ref genes)',
                 len(ogs), args.min_intact, len(target_genes))

    # 2) Reference FASTA
    ref_fa = Fasta(args.ref_fasta)

    # 3) Per-query GFF + FASTA
    query_cds_maps: dict = {}
    query_fastas: dict = {}
    for q in queries:
        query_cds_maps[q] = parse_gff_cds(gff_entries[q], target_genes)
        query_fastas[q] = Fasta(fa_entries[q])
        logging.info('  %-12s %d target genes found in GFF',
                     q, len(query_cds_maps[q]))

    n_ok = n_skip = 0
    for og_id, gene_id in ogs:
        ref_segs = ref_cds_map.get(gene_id, [])
        ref_cds = extract_cds(ref_fa, ref_segs) if ref_segs else ''
        if not ref_cds or len(ref_cds) % 3 != 0:
            n_skip += 1
            continue
        ref_prot = translate(ref_cds).rstrip('*')
        if '*' in ref_prot:  # internal stop in reference -> drop gene
            n_skip += 1
            continue

        seqs_cds = {args.ref: ref_cds}
        seqs_prot = {args.ref: ref_prot}

        for q in queries:
            q_segs = query_cds_maps[q].get(gene_id, [])
            q_cds = extract_cds(query_fastas[q], q_segs) if q_segs else ''
            if not q_cds:
                continue
            q_cds = q_cds[:(len(q_cds) // 3) * 3]       # codon-truncate
            q_cds = strip_internal_stops(q_cds)          # internal stops -> NNN
            q_prot = translate(q_cds).rstrip('*')
            seqs_cds[q] = q_cds
            seqs_prot[q] = q_prot

        # member count = intact QUERIES with a real CDS (reference excluded),
        # matching v3 build_msa.py: `len(seqs_cds) - 1 < min_intact`.
        if len(seqs_cds) - 1 < args.min_intact:
            n_skip += 1
            continue

        base = safe_name(og_id)
        cds_path = outdir / f'{base}.cds.fa'
        pep_path = outdir / f'{base}.pep.fa'
        with open(cds_path, 'w') as fh:
            for k, v in seqs_cds.items():
                fh.write(f'>{k}\n{v}\n')
        with open(pep_path, 'w') as fh:
            for k, v in seqs_prot.items():
                fh.write(f'>{k}\n{v}\n')
        n_ok += 1
        logging.info('OG %s gene=%s members=%d', og_id, gene_id, len(seqs_cds))

    logging.info('Done: %d orthogroups written, %d skipped', n_ok, n_skip)
    if n_ok == 0:
        logging.error('No orthogroups passed the filters; no output produced.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
