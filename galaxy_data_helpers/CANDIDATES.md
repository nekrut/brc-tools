# Future candidates for `galaxy_data_helpers`

This file tracks duplicated helper logic and other reusable primitives across the `tools/` Python scripts. The list is ordered by priority and grouped by confidence. The first release (0.1.0) contains only the two confirmed duplicate functions that were already extracted into `galaxy_data_helpers.bed` and `galaxy_data_helpers.gff`.

## 0.1.0 — already done

| Function | Module | Donor scripts |
|---|---|---|
| `load_bed_genes_by_source` | `galaxy_data_helpers.bed` | `tools/phase_e_rbest_overlap/phase_e_rbest_overlap.py`, `tools/phase_e_graph_edges/phase_e_graph_edges.py` |
| `parse_gff_attributes_to_dict` | `galaxy_data_helpers.gff` | `tools/phase_c2_triage/phase_c2_triage.py`, `tools/phase_c4_merge/phase_c4_merge.py` |

The remaining work for these two is on the **tool-wrapper side**, not in the library. Once `galaxy-data-helpers` is available on bioconda, the donor scripts should be updated to import from `galaxy_data_helpers` and declare `<requirement type="package" version="0.1.0">galaxy-data-helpers</requirement>` in their XML wrappers. This is intentionally deferred until the conda package lands.

## 0.2.0 — already done

| Function | Module | Donor scripts |
|---|---|---|
| `load_fasta_as_dict`, `classify_repeat_signature`, `classify_bed_interval` | `galaxy_data_helpers.sequence` | `tools/dustmasker/lc_classify.py`, `tools/tantan/lc_classify.py`, `tools/windowmasker/lc_classify.py` |
| `species_of` | `galaxy_data_helpers.maf` | `tools/process_maf/process_maf.py`, `tools/maf_to_bigmaf_bed/maf_to_bigmaf_bed.py` |

## 0.3.0 — already done

| Function | Module | Donor scripts |
|---|---|---|
| `normalize_gene_id`, `parse_gff_cds` | `galaxy_data_helpers.gff` | `tools/phase_e_consensus/phase_e_consensus.py`, `tools/group_cds_by_og/group_cds_by_og.py`, `tools/phase_c2_triage/phase_c2_triage.py`, `tools/phase_c4_merge/phase_c4_merge.py` |
| `revcomp`, `translate`, `strip_internal_stops`, `has_internal_stop`, `extract_cds`, `extract_sequence` | `galaxy_data_helpers.sequence` | `tools/group_cds_by_og/group_cds_by_og.py`, `tools/phase_c2_triage/phase_c2_triage.py` |

## 0.4.0 — already done

| Function | Module | Donor scripts |
|---|---|---|
| `UnionFind`, `edge_weight`, `reciprocal_overlap`, `collapse_positions` | `galaxy_data_helpers.orthology` | `tools/phase_e_consensus/phase_e_consensus.py` |
| `parse_chain_header`, `iter_chains`, `project_gene` | `galaxy_data_helpers.chains` | `tools/phase_e_rbest_overlap/phase_e_rbest_overlap.py` |
| `index_by_chrom`, `best_query_gene` | `galaxy_data_helpers.intervals` | `tools/phase_e_rbest_overlap/phase_e_rbest_overlap.py` |
| `parse_pansn`, `load_graph_paths` | `galaxy_data_helpers.pansn` | `tools/phase_e_graph_edges/phase_e_graph_edges.py` |

## 0.5.0 — already done

| Function | Module | Donor scripts |
|---|---|---|
| `parse_blocks`, `iter_maf_blocks`, `find_ref_index`, `reorder_block`, `emit_bed_record` | `galaxy_data_helpers.maf` | `tools/process_maf/process_maf.py`, `tools/maf_to_bigmaf_bed/maf_to_bigmaf_bed.py` |
| `load_matrix`, `similarities_to_hinge`, `order_queries` | `galaxy_data_helpers.multiz` | `tools/multiz_fold/multiz_order.py` |

## 0.6.0 — already done

Single-instance helpers (anchor prep, gene BED, manifests, PanSN renaming, collection relabel/self pairs) now live across `galaxy_data_helpers.gff`, `.io`, `.pansn`, `.orthology`, and `.collections` modules.

## Deferred / probably not for the library

- `fasta_concat.py` — trivial; overlaps `cat1`/`fasta-merge` in IUC.
- `build_genomes_txt.py` — static manifest logic with no reusable science.
- `masking_table.py` — standalone masking table summary; no known duplication.

## How to add a candidate

1. Extract the function into `src/galaxy_data_helpers/<module>.py`.
2. Add a unit test in `tests/test_<module>.py` that reproduces the donor tool's `planemo` test coverage.
3. Update the donor tool's `<command>` block to import from `galaxy_data_helpers` once the new version is on bioconda.
4. Bump `version` in `pyproject.toml` and update this file to mark the item as done.
