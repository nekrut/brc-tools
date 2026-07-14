# galaxy-data-helpers

Utility functions shared by the Galaxy tool wrappers in the `brc-tools`
repository. The goal is to keep frequently copied parsing logic (BED/GFF/FASTA)
and small algorithms (repeat classifiers, MAF helpers) in one importable place.

## What it provides today

| Module | What it covers | Typical use cases |
| --- | --- | --- |
| `galaxy_data_helpers.bed` | Load per-sample BED files keyed by filename stem. | Phase E reciprocal-best overlap + graph-edges tools. |
| `galaxy_data_helpers.gff` | Attribute parsing, `normalize_gene_id`, `parse_gff_cds`, plus protein-coding filters and BED/isoform emitters. | Liftoff triage, TOGA merge, anchor-prep filters, orthogroup CDS grouping. |
| `galaxy_data_helpers.sequence` | FASTA loader, repeat classifier, reverse complement, translation, CDS extractors, stop-codon utilities. | Dustmasker/tantan/Windowmasker helpers, `phase_c2_triage`, `group_cds_by_og`. |
| `galaxy_data_helpers.maf` | Species parsing plus block iterators, reference indexing, and BED3 emitters. | `process_maf.py`, `maf_to_bigmaf_bed.py`. |
| `galaxy_data_helpers.orthology` | Edge weights, union-find, reciprocal overlap, positional collapsing. | `phase_e_consensus.py` orthogroup builder. |
| `galaxy_data_helpers.chains` | UCSC chain parsing, block iterator, gene projection. | `phase_e_rbest_overlap.py` reciprocal-best block projection. |
| `galaxy_data_helpers.intervals` | Per-chromosome interval index + best-overlap lookup. | rbest projection overlap filtering. |
| `galaxy_data_helpers.pansn` | PanSN path parsing, PGGB path grouping, and FASTA header renaming. | `phase_e_graph_edges.py`, `pansn_rename.py`. |
| `galaxy_data_helpers.multiz` | Sourmash compare.csv loader, hinge similarities, and ordering. | `multiz_fold/multiz_order.py`. |
| `galaxy_data_helpers.io` | Manifest readers and “maybe gzip” file handles. | `group_cds_by_og.py`, `pansn_rename.py`. |
| `galaxy_data_helpers.collections` | Relabel/self pairs for collection cross-products. | WF-C relabel/self-pairs helpers. |

Each helper is intentionally small (“do one thing”) so tool wrappers can compose
them without inheriting pipeline-specific behavior.

## Install

```bash
pip install -e ".[test]"
```

## Run tests

```bash
pytest
```
