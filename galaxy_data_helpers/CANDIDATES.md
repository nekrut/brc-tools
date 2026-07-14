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

## 0.5.0 — MAF and multiz helpers

| Candidate | Type | Donor scripts | Notes |
|---|---|---|---|
| `parse_blocks` | Function | `tools/process_maf/process_maf.py` | Parse MAF file into blocks. Suggested module: `galaxy_data_helpers.maf`. |
| `iter_maf_blocks` | Generator | `tools/process_maf/process_maf.py`, `tools/maf_to_bigmaf_bed/maf_to_bigmaf_bed.py` | Both scripts walk MAF `a` blocks. A shared generator would deduplicate the loop. |
| `emit_block` | Function | `tools/maf_to_bigmaf_bed/maf_to_bigmaf_bed.py` | Convert one MAF block to bigMaf BED3+1. Suggested module: `galaxy_data_helpers.maf`. |
| `load_matrix` + `similarities_to_hinge` + `order_queries` | Functions | `tools/multiz_fold/multiz_order.py` | Sourmash `compare.csv` → fold order. Suggested module: `galaxy_data_helpers.multiz` or `galaxy_data_helpers.matrix`. |

## 0.6.0 — single-instance helpers that are good library candidates

These are not duplicated yet, but they isolate reusable logic from large scripts and should move into the library for testability.

| Candidate | Type | Donor script | Suggested module |
|---|---|---|---|
| `collect_protein_coding_genes` + `filter_bed12` + `build_isoforms` | Functions | `tools/anchor_prep/build_anchor_inputs.py` | `galaxy_data_helpers.gff` |
| `gff_to_bed` + `parse_id` | Functions | `tools/gene_bed/gene_bed.py` | `galaxy_data_helpers.gff` |
| `load_ortho_table` | Function | `tools/group_cds_by_og/group_cds_by_og.py` | `galaxy_data_helpers.orthology` |
| `read_manifest` | Function | `tools/group_cds_by_og/group_cds_by_og.py` | `galaxy_data_helpers.io` |
| `safe_name` | Function | `tools/group_cds_by_og/group_cds_by_og.py` | `galaxy_data_helpers.ids` |
| `open_maybe_gz` | Function | `tools/pansn_rename/pansn_rename.py` | `galaxy_data_helpers.io` |
| `rename` (PanSN header) | Function | `tools/pansn_rename/pansn_rename.py` | `galaxy_data_helpers.pansn` |
| `relabel_map` | Function | `tools/collection_relabel_map/relabel_map.py` | `galaxy_data_helpers.collections` |
| `self_pairs` | Function | `tools/collection_self_pairs/self_pairs.py` | `galaxy_data_helpers.collections` |
| `is_subtelomeric` | Function | `tools/phase_c2_triage/phase_c2_triage.py` | `galaxy_data_helpers.coordinates` |
| `get_splice_sites` | Function | `tools/phase_c2_triage/phase_c2_triage.py` | `galaxy_data_helpers.sequence` |
| `triage_gene` + rule engine | Function | `tools/phase_c2_triage/phase_c2_triage.py` | `galaxy_data_helpers.triage` (with R7/R8 as pluggable rules) |
| `load_liftoff_clean` + `load_toga2_loss_summary` + `load_toga2_orthology` | Functions | `tools/phase_c4_merge/phase_c4_merge.py` | `galaxy_data_helpers.triage` |
| `build_hub_bb` track logic | Functions | `tools/build_hub_bb/build_hub_bb.py` | `galaxy_data_helpers.hub` |
| `build_trackdb` stanza builders | Functions | `tools/build_trackdb/build_trackdb.py` | `galaxy_data_helpers.hub` |
| `chain_to_bigChain` | Function | `tools/chain_to_bigChain/chain_to_bigChain.py` | `galaxy_data_helpers.hub` or `galaxy_data_helpers.chains` |

## Deferred / probably not for the library

- `fasta_concat.py` — trivial; overlaps `cat1`/`fasta-merge` in IUC.
- `build_genomes_txt.py` — static manifest logic with no reusable science.
- `masking_table.py` — standalone masking table summary; no known duplication.

## How to add a candidate

1. Extract the function into `src/galaxy_data_helpers/<module>.py`.
2. Add a unit test in `tests/test_<module>.py` that reproduces the donor tool's `planemo` test coverage.
3. Update the donor tool's `<command>` block to import from `galaxy_data_helpers` once the new version is on bioconda.
4. Bump `version` in `pyproject.toml` and update this file to mark the item as done.
