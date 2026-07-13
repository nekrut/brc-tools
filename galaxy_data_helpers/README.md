# galaxy-data-helpers

A small Python helper library shared by the Galaxy tool wrappers in the
`brc-tools` repository for handling common data formats (BED, GFF3).

## Scope

Version 0.1.0 is intentionally minimal. It extracts only the two functions
confirmed to be duplicated across tool wrappers:

- `galaxy_data_helpers.bed.load_bed_genes_by_source` — shared by the reciprocal-best-chain
  overlap tool and the PGGB graph-path edge tool.
- `galaxy_data_helpers.gff.parse_gff_attributes_to_dict` — shared by the Liftoff triage
  tool and the TOGA2/CESAR2 merge tool.

## Install

```bash
pip install -e ".[test]"
```

## Run tests

```bash
pytest
```
