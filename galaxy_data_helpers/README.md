# galaxy-data-helpers

Utility functions shared by the Galaxy tool wrappers in the `brc-tools`
repository. The goal is to keep frequently copied parsing logic (BED/GFF/FASTA)
and small algorithms (repeat classifiers, MAF helpers) in one importable place.

## What it provides today

| Module | What it covers | Typical use cases |
| --- | --- | --- |
| `galaxy_data_helpers.bed` | Load per-sample BED files keyed by filename stem. | Phase E reciprocal-best overlap + graph-edges tools. |
| `galaxy_data_helpers.gff` | Parse column 9 `key=value` pairs into a dict. | Liftoff triage, TOGA merge, anchor-prep filters. |
| `galaxy_data_helpers.sequence` | FASTA-to-dict loader plus mono/tandem repeat classifier and BED interval helper. | Dustmasker, tantan, Windowmasker `lc_classify` scripts. |
| `galaxy_data_helpers.maf` | Extract species/accession prefix from an MAF `s`-line sequence name. | `process_maf.py`, `maf_to_bigmaf_bed.py`. |

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
