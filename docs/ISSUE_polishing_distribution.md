# Polishing → release: validate, rerun, and upstream the Pv4 pangenome tools & workflows

The full 8-strain *P. vivax* (Pv4) pangenome pipeline now runs end-to-end (Phases A→K)
on the cluster-backed Galaxy. Provenance for that run lives in
`RUN_PV4_FULL_ON_GALAXY.md` and the per-phase status log. This issue tracks the work to
turn that working-but-bespoke pipeline into **released, reproducible artifacts**: validated
tools in the ToolShed and workflows in IWC, reconciled with the upstream pangenome effort.

## Work streams

0. **Clean rerun of the whole Pv4 pipeline on this cluster** — from staged inputs, every
   phase from a fresh history, capturing per-phase outputs as the regression baseline.
1. **Manual validation of each newly-wrapped tool** — params, `help`, citations, tests,
   `@TOOL_VERSION@`/`profile`, outputs/labels, sane defaults. Many of our tools are still
   `version="1.0"` ad-hoc wrappers (see table) and need to be brought to IUC standard.
2. **Manual rerun of each workflow** — independently of the driver scripts, via the GUI /
   `planemo run`, confirming each produces the expected outputs.
3. **ToolShed commits** — push each validated tool to the ToolShed (own repo per tool).
4. **IWC commits** — submit each validated workflow to [iwc](https://github.com/galaxyproject/iwc).
5. **Reconcile with the pangenome IUC effort**
   ([galaxyproject/tools-iuc#7364](https://github.com/galaxyproject/tools-iuc/issues/7364))
   — our graph-stack wrappers (pggb, wfmash, seqwish, smoothxg, odgi, gfaffix, vg) overlap
   with that umbrella. Decide per tool: adopt the IUC wrapper, contribute ours, or merge.
   **Do not ToolShed/IWC a graph-stack tool until its reconciliation decision is made.**

The model: each owner takes a **vertical slice** (a set of tools + the workflows that use
them) and carries it through streams 1→4. Streams 0 and 5 are cross-cutting and have a
single lead each. ToolShed/IWC for a given artifact is done by whoever validated it.

---

## Ownership

### @nekrut (Anton) — lead: stream 0 (full rerun) + IWC coordination; slice A/B
- **Stream 0 — full Pv4 rerun (baseline):** re-run A→K from staged inputs, one history per
  phase, archive outputs as the regression reference everyone validates against. Publish
  the expected per-phase counts (sourmash matrix, OG counts, BUSTED counts, projected-var
  counts, bigMaf record count).
- **Stream 4 lead:** own the IWC submission process/PR conventions; unblock 3/4 for others.
- **Slice A/B tools:** `sourmash_sketch`, `sourmash_compare`, `sdust`, `longdust`,
  `fasta_concat`, `pansn_rename`.
- **UCSC hub tools** (pairs with the K/J work from the Pv4 run): `build_hub_bb`,
  `build_trackdb`, `build_genomes_txt`, `ucsc_kent`.
- **Slice workflows:** `inventory`, `softmask`, `ucsc_hub` (K), `vcf_projection` (J).

### @d-callan (Danielle) — lead: stream 5 (pangenome reconciliation); slice D/E
- **Stream 5 lead — reconcile with tools-iuc#7364:** for each graph-stack tool decide
  adopt-IUC / contribute-ours / merge, and record the decision in this issue.
  Tools in scope: `pggb`, `wfmash`, `seqwish`, `smoothxg`, `odgi`, `gfaffix`, `vg`.
- **Slice D/E tools (non-graph):** `phase_e_consensus`, `phase_e_graph_edges`,
  `phase_e_rbest_overlap`, `group_cds_by_og`.
- **Slice D/E workflows:** `pggb_graph`, `pggb-pangenome-build`, `consensus`.

### @as042 (Andrew) — slice C/F-G-H/I (alignment, MAF, selection)
- **Alignment / chain / MAF tools:** `anchor_prep`, `gene_bed`, `chainStitchId`,
  `chain_to_bigChain`, `process_maf`, `multiz_fold`, `maf_to_bigmaf_bed`,
  `phase_c2_triage`, `phase_c4_merge`.
- **Selection / tree tools:** `iqtree3`, `toga2`.
- **Slice workflows:** `align_chain_project`, `msa`, `trees`, `selection`, `multiz`.

> Note: the Phase C aligner (KegAlign) and `vcf_projection`'s CrossMap step are
> IUC/upstream tools we depend on but don't wrap — validate the wiring, not the wrapper.

---

## Per-tool checklist (stream 1 → 3)

For each tool: [ ] params/help/citation reviewed · [ ] tests pass (`planemo test`) ·
[ ] `@TOOL_VERSION@`/profile/version-suffix proper · [ ] ToolShed repo pushed.

| Tool | Current version | Owner | Reconcile w/ #7364? |
|---|---|---|---|
| sourmash_sketch | 1.0 | @nekrut | |
| sourmash_compare | 1.0 | @nekrut | |
| sdust | 1.0 | @nekrut | |
| longdust | @TOOL_VERSION@ | @nekrut | |
| fasta_concat | @TOOL_VERSION@ | @nekrut | |
| pansn_rename | 1.0 | @nekrut | |
| pggb | 1.0 | @d-callan | **yes** |
| wfmash | 1.0 | @d-callan | **yes** |
| seqwish | 1.0 | @d-callan | **yes** |
| smoothxg | 1.0 | @d-callan | **yes** |
| odgi (odgi_build) | @TOOL_VERSION@ | @d-callan | **yes** |
| gfaffix | @TOOL_VERSION@ | @d-callan | **yes** |
| vg (vg_convert) | @TOOL_VERSION@ | @d-callan | **yes** |
| phase_e_consensus | 1.0 | @d-callan | |
| phase_e_graph_edges | 1.0 | @d-callan | |
| phase_e_rbest_overlap | 1.0 | @d-callan | |
| group_cds_by_og | @TOOL_VERSION@ | @d-callan | |
| anchor_prep | @TOOL_VERSION@ | @as042 | |
| gene_bed | @TOOL_VERSION@ | @as042 | |
| chainStitchId | @TOOL_VERSION@ | @as042 | |
| chain_to_bigChain | @TOOL_VERSION@ | @as042 | |
| process_maf | 1.0 | @as042 | |
| multiz_fold | 1.0 | @as042 | |
| maf_to_bigmaf_bed | 1.0 | @as042 | |
| build_hub_bb | @TOOL_VERSION@ | @nekrut | |
| build_trackdb | @TOOL_VERSION@ | @nekrut | |
| build_genomes_txt | @TOOL_VERSION@ | @nekrut | |
| ucsc_kent (bedToBigBed) | @BEDTOBIGBED_VERSION@ | @nekrut | |
| phase_c2_triage | 1.0 | @as042 | |
| phase_c4_merge | 1.0 | @as042 | |
| iqtree3 | @TOOL_VERSION@ | @as042 | |
| toga2 | 1.0 | @as042 | |

## Per-workflow checklist (stream 2 → 4)

For each workflow: [ ] reruns clean (GUI / `planemo run`) · [ ] outputs match the stream-0
baseline · [ ] tests + `.dockstore.yml` · [ ] IWC PR opened.

| Workflow | Phase | Owner |
|---|---|---|
| inventory | A | @nekrut |
| softmask | B | @nekrut |
| align_chain_project | C | @as042 |
| pggb_graph | D | @d-callan |
| pggb-pangenome-build | D | @d-callan |
| consensus | E | @d-callan |
| msa | F | @as042 |
| trees | G | @as042 |
| selection | H | @as042 |
| multiz | I | @as042 |
| vcf_projection | J | @nekrut |
| ucsc_hub | K | @nekrut |

## Sequencing / dependencies
1. **@nekrut** lands the stream-0 baseline first — everything else validates against it.
2. **@d-callan** posts per-tool reconciliation decisions (stream 5) **before** any
   graph-stack tool is pushed to ToolShed (stream 3) or its workflow to IWC.
3. Tool → ToolShed (stream 3) precedes the workflow that uses it → IWC (stream 4).

## Known sharp edges to fold into validation (from the Pv4 run)
- `group_cds_by_og` needs the **ref-as-ref projected GFF** (C.4), not native annotation;
  the cds/pep inputs are distinguished by sequence content, not tool label.
- `iqtree3` / `multiz_fold` / hyphy hit conda-build races and AVX/CPU-heterogeneity
  (libmamba fails here — `conda create --solver classic`). Pin AVX-requiring tools.
- `multiz_fold` hinge must be passed as literal text; list:list inner elements aren't
  addressable — use standalone per-hinge collections.
- The UCSC `hubCheck` binary segfaults on this host; `ucsc_hub` validation currently
  leans on `bigMafToMaf` round-trip + structural checks (`configs/validate_hub.py`).
