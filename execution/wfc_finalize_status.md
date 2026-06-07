# WF-C `align_chain_project` finalize + anchor_prep F3 fix

**Date:** 2026-06-07
**Galaxy:** 26.1.rc1 @ http://localhost:8080
**Scope:** finalize WF-C (F1 KegAlign-GPU aligner, F2 liftoff default `gene`, corrected
IUC param names) + fix anchor_prep F3 (BED name = GENE id) + reconcile iqtree3 version.
**No git commit performed.** ucsc_hub / toga2 untouched.

## Verdict

All three tasks done and verified:
1. WF-C aligner switched to **KegAlign-GPU** (two-stage `kegalign` -> `batched_lastz`,
   axt-native), all chain + liftoff param names corrected and **verified against the
   installed wrappers' `io_details`**. `planemo workflow_lint` = 0 ERROR. Imported via
   `POST /api/workflows from_path` (StoredWorkflow `417e33144b294c21`). Every step
   resolves EXCEPT `kegalign`/`batched_lastz` (404 — GPU path not installed, EXPECTED per F1).
2. **F3 fixed:** anchor_prep now writes the GENE id (not transcript id) into BED12 col 4.
   `planemo test --biocontainers tools/anchor_prep/` = **green (1/1 passed)**; test updated to
   assert gene-id naming (`gene1`/`gene2` in col 4, no `mrna*`).
3. **iqtree3 reconciled to 3.0.1** (the version that actually resolves to a biocontainer
   here; 3.1.2 docs were wrong). `planemo lint tools/iqtree3/` clean.

## Files changed

| file | change |
|------|--------|
| `workflows/align_chain_project/align_chain_project.gxwf.yml` | aligner lastz -> `kegalign` + `batched_lastz` (F1); corrected axtChain/chain/chainNet/netChainSubset/liftoff param + output names; chainNet `targetNet`; liftoff default `gene` (F2, `liftoff_features` unwired); conditional index-source via `state:` + flat-pipe `in:` key |
| `workflows/align_chain_project/README.md` | F1/F2 decisions, KegAlign two-stage explanation, corrected param provenance, tool-resolution note |
| `tools/anchor_prep/build_anchor_inputs.py` | `filter_bed12` rewrites BED col 4 to the gene id (F3) |
| `tools/anchor_prep/anchor_prep.xml` | test asserts gene-id in BED name col, not transcript id |
| `tools/iqtree3/macros.xml` | already 3.0.1 (kept); docs reconciled to it |
| `workflows/trees/trees.gxwf.yml` | iqtree3 version 3.1.2 -> 3.0.1 (2 spots) |
| `workflows/trees/README.md` | iqtree3 version 3.1.2 -> 3.0.1 |

(`workflows/ucsc_hub/ucsc_hub.gxwf.yml` shows modified in git but is from another effort
— NOT touched by this work.)

## Task 1 — WF-C finalize

### F1: KegAlign-GPU is the only viable C.1 aligner
IUC lastz emits no axt/psl -> cannot feed axtChain. KegAlign emits axt natively via a
**two-stage GPU pipeline** (published wrapper = richard-burhans/galaxytools):
- `kegalign` (GPU): target+query FASTA, `output_options|format|format_selector=axt` +
  `axt_type=axt` -> `kegalign_output` = `data_package.tgz` of LASTZ segments.
- `batched_lastz`: consumes that tgz -> final **axt** (`output`, format auto).

Impl flags mapped onto the wrapper sections:
`sequence_options|strand_selector=both`, `ungapped_extension_options|hspthresh=5000`,
`gapped_extension_options|gappedthresh=6000`, `gapped_extension_options|ydrop=15000`,
`interpolation_options|inner=2000`.

NOTE re: tool id — the task/plan name is `kegalign_gpu`; the **published wrapper tool id is
`kegalign`** (+ `batched_lastz`). The workflow step is labelled `kegalign_gpu` but
`tool_id: kegalign`. Neither tool is installed here (both 404); they need a `docker_gpu`
destination. This step is the production/GPU path and was NOT import-validated or run.

### F2: liftoff default `gene`
IUC `-f feature_types` is buggy (literal string templated as a file path). The feature
filter is dropped; Liftoff's default `gene` mode is used. `liftoff_features` input kept but
intentionally unwired. Corrected liftoff keys (all confirmed via `io_details`):
`target_fasta` / `reference_fasta` / `annotation` +
`chromosome_mapping|copy_detection|find_copies=true` + `...|copy_min_identity=0.95`;
output `liftoff_gff`.

### Corrected IUC param/output names — VERIFIED against installed wrappers
Probed `/api/tools/{id}?io_details=true`; all present:
- axtChain: `in_aln`, `in_target`, `in_query`, `linear_gap_options|linear_gap`, out `out`.
- chainSort/chainSwap/chainPreNet/netChainSubset: `in_chain` (+ `in_net`), out `out`.
- chainNet: out `targetNet` (+ `queryNet`); index source `...|in_tar_ref_index` /
  `...|in_que_ref_index`. The conditional **selector** (`history`) lives in `state:`; the
  data connection uses the flat-pipe `in:` key (`target_reference_index_source|in_tar_ref_index: sizes`)
  — the nested-dict form failed strict schema validation; the flat-pipe form lints clean.

### planemo workflow_lint
`workflows/align_chain_project/align_chain_project.gxwf.yml` -> **0 ERROR**,
`CHECK: All tool ids appear to be valid`. Remaining WARNINGs are cosmetic (per-step
annotations, missing test cases, the standard top-level `name` strict-schema note, and the
expected "disconnected" index-source inputs that need the per-pair sizes helper / editor relink).

### WF-C import resolution table
`POST /api/workflows from_path` -> StoredWorkflow `417e33144b294c21` (latest_workflow_id 17),
created OK. Per-tool resolution (`GET /api/tools/{id}`):

| step | tool_id | resolves? | version |
|------|---------|-----------|---------|
| pair_strains | `pair_strains` | YES | 1.0.0+galaxy0 |
| **kegalign_gpu** | `kegalign` | **NO (404)** — EXPECTED (F1, GPU path) | — |
| **batched_lastz** | `batched_lastz` | **NO (404)** — EXPECTED (F1, GPU path) | — |
| axtchain | `ucsc_axtchain` | YES | 482+galaxy2 |
| chainsort_clean / _r1 / _rbest | `ucsc_chainsort` | YES | 482+galaxy0 |
| chainprenet | `ucsc_chainprenet` | YES | 482+galaxy0 |
| chainnet / chainnet_r | `ucsc_chainnet` | YES | 482+galaxy0 |
| netchainsubset / _r | `ucsc_netchainsubset` | YES | 482+galaxy0 |
| chainstitchid_clean / _r | `chainStitchId` | YES | 482+galaxy0 |
| chainswap_r1 / _r2 | `ucsc_chainswap` | YES | 482+galaxy0 |
| anchor_prep | `anchor_prep` | YES | 0.12.7+galaxy0 |
| liftoff | `liftoff` | YES | 1.6.3+galaxy0 |
| phase_c2_triage | `phase_c2_triage` | YES | 1.0.0+galaxy0 |
| phase_c4_merge | `phase_c4_merge` | YES | 1.0.0+galaxy0 |

**Result:** the entire chain block + projection block resolve cleanly; only the KegAlign GPU
aligner (kegalign + batched_lastz) is absent, exactly as the F1 decision requires.

## Task 2 — anchor_prep F3 fix

**Bug confirmed:** `phase_c4_merge.py:142` builds `ref_genes` from BED12 col 4 (`fields[3]`)
and reconciles it against the clean-GFF **gene** IDs (`ref_id` keys from `liftoff_clean`,
`ref_genes - seen_ref`). `gffread --bed` puts the **transcript** id in col 4, so every gene
showed up as a spurious unprojected `*.t1` row.

**Fix:** `build_anchor_inputs.py::filter_bed12` now rewrites BED col 4 to the gene id
(`out_fields[3] = gid`, gid from the trailing `geneID=` attribute, with fallback to the
existing name when absent). v3's `impl/setup/build_anchor_inputs.sh` kept `f[:12]` unchanged
(same latent transcript-id-in-name behavior) — so this is the deliberate F3 correction, and
it is the correct keying for phase_c4_merge.

**Test (real gffread biocontainer, `quay.io/biocontainers/gffread`):** the produced BED12 now
reads (verified from the test job output):
```
chr1	999	2000	gene1	100	+	999	2000	0,0,0	2	301,301,	0,700,
chr1	3999	5000	gene2	100	-	3999	5000	1,0,0	2	401,401,	0,600,
```
Test updated to assert the full tab-delimited line (gene id specifically in col 4) plus
`not_has_text mrna1/mrna2`. `planemo test --biocontainers tools/anchor_prep/` -> **All 1
test(s) executed passed.** `planemo lint tools/anchor_prep/` clean.

## Task 3 — iqtree3 version reconcile

`tools/iqtree3/macros.xml` @TOOL_VERSION@ was already **3.0.1**; the loaded tool resolved to
3.0.1. The trees workflow doc + README claimed **3.1.2** (inconsistent). Biocontainer check
(`quay.io/biocontainers/iqtree` tags) confirms **3.0.1, 3.1.1, 3.1.2 all exist**. Pinned the
version that actually resolves here — **3.0.1** — and fixed the docs to match:
- `workflows/trees/trees.gxwf.yml` (2 mentions) 3.1.2 -> 3.0.1
- `workflows/trees/README.md` 3.1.2 -> 3.0.1

`planemo lint tools/iqtree3/` -> clean, `ToolVersionValid: 3.0.1+galaxy0`.

## Honesty / deviations
- KegAlign tool id: task says `kegalign_gpu`; the real published wrapper id is `kegalign`
  (+ `batched_lastz` for the axt stage). Used the real ids; step labelled `kegalign_gpu`.
  KegAlign output is a tgz data package, NOT axt directly — the axt comes from the
  `batched_lastz` second stage. Wired both; neither installed here (GPU path, F1).
- KegAlign threshold param paths (`ungapped_extension_options|hspthresh`, etc.) were taken
  from the richard-burhans wrapper macros (fetched from GitHub), NOT from a live instance
  (tool not installed) — best-effort, correct per the published wrapper source.
- The per-pair `.sizes` join + rbest size-swap + C.4 cross-product map-over gaps from the
  e2e status remain (editor relink / helper tool needed); unchanged by this finalize.
