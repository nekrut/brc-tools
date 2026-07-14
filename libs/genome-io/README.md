# genome-io

Lightweight, reusable Python library for parsing and processing genomic data formats (BED, GFF3, FASTA, MAF, etc.). Designed to be used by genomics workflow wrappers and other tools that need to manipulate sequence annotations and alignments without heavy dependencies.

Part of the `brc-tools` repository (`libs/genome-io/`), but published independently on PyPI and Bioconda.

## What it provides today

| Module | What it covers | Typical use cases |
| --- | --- | --- |
| `genome_io.bed` | Load per-sample BED files keyed by filename stem. | Phase E reciprocal-best overlap + graph-edges tools. |
| `genome_io.gff` | Attribute parsing, `normalize_gene_id`, `parse_gff_cds`, plus protein-coding filters and BED/isoform emitters. | Liftoff triage, TOGA merge, anchor-prep filters, orthogroup CDS grouping. |
| `genome_io.sequence` | FASTA loader, repeat classifier, reverse complement, translation, CDS extractors, stop-codon utilities. | Dustmasker/tantan/Windowmasker helpers, `phase_c2_triage`, `group_cds_by_og`. |
| `genome_io.maf` | Species parsing plus block iterators, reference indexing, and BED3 emitters. | `process_maf.py`, `maf_to_bigmaf_bed.py`. |
| `genome_io.orthology` | Edge weights, union-find, reciprocal overlap, positional collapsing. | `phase_e_consensus.py` orthogroup builder. |
| `genome_io.chains` | UCSC chain parsing, block iterator, gene projection. | `phase_e_rbest_overlap.py` reciprocal-best block projection. |
| `genome_io.intervals` | Per-chromosome interval index + best-overlap lookup. | rbest projection overlap filtering. |
| `genome_io.pansn` | PanSN path parsing, PGGB path grouping, and FASTA header renaming. | `phase_e_graph_edges.py`, `pansn_rename.py`. |
| `genome_io.multiz` | Sourmash compare.csv loader, hinge similarities, and ordering. | `multiz_fold/multiz_order.py`. |
| `genome_io.io` | Manifest readers and “maybe gzip” file handles. | `group_cds_by_og.py`, `pansn_rename.py`. |
| `genome_io.collections` | Relabel/self pairs for collection cross-products. | WF-C relabel/self-pairs helpers. |

Each helper is intentionally small (“do one thing”) so tool wrappers can compose
them without inheriting pipeline-specific behavior.

## Install

From PyPI:
```bash
pip install genome-io
```

From source (development):
```bash
cd libs/genome-io
pip install -e ".[test]"
```

## Run tests

```bash
cd libs/genome-io
pytest
```
