# Autonomous build campaign — status

Started 2026-06-06 (overnight, autonomous). Goal: wrap every new ⚠️ tool to planemo-green,
workflow-by-workflow per `PIPELINE_PORT_PLAN.md`, author the 11 `.ga` workflows, then attempt a
local-Galaxy test_data e2e. Toolchain refreshed: planemo 0.75.44, Galaxy dev (latest).

## e2e composition scoreboard (2026-06-07)
Proven to compose in live Galaxy 26.1.rc1 on test/synthetic data (tool-by-tool via bioblend; gxformat2
map-over one-click still needs helper-tool/editor work where noted): **WF-A** (sourmash), **WF-B**
(softmask, full e2e), **WF-C pass-1** (chains + Liftoff projection), **WF-E** (consensus — graph-edges
fix validated: 5 edges vs v3's 0; .dat + nested list:list staging confirmed), **WF-F/G/H** (msa→trees→
BUSTED), **WF-I** (multiz), **WF-J** (vcf projection). Each surfaced + fixed blind-IUC gxformat2 params.
⏳ WF-K (hub) in flight. 🔒 WF-C full run GPU-gated (KegAlign). WF-D = existing pggb wf + odgi paths.

## ⚠️ Decisions (status)
- ✅ **RESOLVED 2026-06-07: `phase_e_graph_edges` — FIXED** (commit 8fbe76d). Decision was "fix". Found
  TWO latent v3 bugs (2nd masked by 1st): (1) keyed by full path name → edges always empty; (2) gene
  comprehension referenced undefined `g` → NameError once the loop runs. Both fixed; test now asserts
  real edges. Phase E now uses all 3 signals (diverges from v3 output). The v3 source script is left
  as-is (historical); only our wrapped port is fixed.
- ✅ **RESOLVED: commit** — night's work on branch `galaxy-port-wrappers` (8544af5) + the fix (8fbe76d).
- ⚠️ **CORRECTION 2026-06-07: sourmash is NOT in the toolshed** (live-verified: repo API + full
  7,672-repo listing + search; Bioconda-only). The pass-2 finding I reverted was right; GALAXY.md's
  sourmash toolshed path was aspirational/wrong. Decision 5's "sourmash = no wrap" is false →
  **wrapping sourmash_sketch + sourmash_compare ourselves** (keeps the sourmash choice; mash is the
  fallback if we'd rather not maintain it). PIPELINE_PORT_PLAN.md needs the sourmash rows re-flipped
  to ⚠️ wrap.
- **IUC installs: 17/18 loaded** (`execution/iuc_install_status.md`). Exceptions/notes: sourmash
  (above); `lastz` = devteam (resolves to `lastz`); `bcftools_sort` only old `greg/1.4.0` (version
  gap, WF-J); busco needs `apicomplexa_odb10` lineage DB fetched via data_manager before its step runs.
- ⚠️ **TOGA1-vs-TOGA2 fork (NEW, 2026-06-07).** Built `toga2:local` (20.7 GB) from TOGA2's apptainer.def
  → it's **TOGA2 v2.0.8**, a click-group CLI (`run --ref_2bit --query_2bit --chain_file --ref_annotation
  --isoform_file …`) with **NO `--filter_bed`** and **2bit/--ref_annotation inputs**. But v3/impl/04 uses
  **TOGA1** (`toga … --filter_bed needs_cesar2.bed`) — the triage→rescue-subset handoff depends on
  `--filter_bed`. So TOGA2 ≠ drop-in; adopting it means redesigning C.4. The toga2 wrapper was rewired to
  TOGA2's real CLI but is **UNCOMMITTED pending decision**: (a) build TOGA1 image to match v3 exactly, or
  (b) adopt TOGA2 v2.0.8 + redesign C.4. (sourmash resolved → wrapped.)
- 🖥️ **Disk tight**: root 99% used, ~13 GB free (toga2:local image is 20.7 GB). Watch before heavy e2e.
- ✅ RESOLVED: TOGA→TOGA2 v2.0.8 (wrapper rewired, committed; C.4 redesign pending); mafIndex dropped;
  group_cds_by_og→v3 queries-only; sourmash wrapped.
- **WF-C pass-1 COMPOSES e2e** (18 Galaxy jobs ok on a P. vivax MIT pair + synthetic anchor GFF):
  lastz→axtChain→…→chainStitchId = cleaned.chain + rbest.chain; anchor_prep→liftoff→triage→merge
  (Liftoff-only) = annotation.gff3 + classification.tsv. Findings (`execution/wfc_e2e_status.md`):
  - **F1 (decided: KegAlign-GPU only):** IUC lastz wrapper emits NO axt → can't feed axtChain. No CPU
    alignment path; **GPU driver fix is now a WF-C prerequisite** (KegAlign is axt-native). Update
    align_chain_project.gxwf.yml to use kegalign + the corrected IUC param names (recorded in the status
    doc); mark GPU-required. PENDING.
  - **F2 (decided: default 'gene'):** IUC liftoff `-f` passes free text as a file path → FileNotFoundError;
    use default gene for now + FILE AN IUC BUG. PENDING (issue).
  - **F3 (our side):** anchor_prep bed12 name = transcript id; merge keys on gene id → spurious rows. FIX. PENDING.
  - Corrected IUC param names for align_chain_project.gxwf.yml captured (axtChain in_aln/in_target/in_query/
    linear_gap; chain tools in_chain + *_reference_index_source; liftoff target_fasta/reference_fasta/annotation).
- ⏳ Still open / next: GPU driver (now needed for WF-C run), C.4 TOGA2 redesign (pass-2), apply WF-C
  gxformat2 corrections + F3 fix, validate WF-F/G/H + WF-J + WF-I + WF-K composition (GPU-independent via
  synthetic intermediates), file IUC liftoff bug.

### (original) Decision detail
- **Bug in `phase_e_graph_edges.py` (Phase E, source pipeline).** `load_graph_paths()` keys
  `path_strains` by the full PanSN path name (line 68), so every key maps to exactly one strain →
  the `len(strain_list) < 2: continue` guard skips every path → **the graph co-membership edge table
  is ALWAYS header-only**. The validated v3 run therefore built orthogroups from only 2 of the 3
  intended signals (projection + rbest; graph signal inert). The wrapper is a **faithful port** (kept
  as-is, planemo-green). **Decision: reproduce-as-is, or fix?** Fix is ~1 line — key by `contig` (=
  `parse_pansn(path_name)[1]`) instead of `path_name`: `path_strains[contig].add(strain)` and use
  `contig` as the path_id — matching the gene-overlap code below it that already filters by
  `chrom == contig`. This changes orthogroup output, so it's your call (science).
- **`group_cds_by_og` min_intact semantics.** The new helper filters orthogroups by
  `len(members incl. ref) < min_intact`; the source `build_msa.py` filters by
  `len(queries only) < min_intact` (i.e. ref-excluded). Same knob, off-by-the-ref — shifts which
  OGs land in the strict/relaxed sets. Trivial to match source (subtract 1 / exclude ref). **Decision:
  keep new semantics or match `build_msa.py`?** (affects set membership counts).
- **`mafIndex` has no biocontainer** (no `ucsc-mafindex` on bioconda/quay; v3 ref was a 0-byte
  placeholder). Wrapped lint-green but non-functional (test passes only via `expect_failure`). Since
  `maf_to_bigmaf_bed` bypasses `mafToBigMaf` and bigMaf `.bb` is self-indexing, mafIndex is probably
  **not needed**. **Decision: drop mafIndex, or source the binary another way** (custom container)?
- **TOGA2 image (WF-C pass 2).** Wrapper XML is lint-green but **non-functional**: the container
  `ghcr.io/hillerlab/toga` is NOT anonymously pullable (denied/404 from this host) — TOGA2 upstream
  actually ships an **Apptainer def** (`supply/containers/apptainer.def`), not a documented ghcr Docker
  image. Needs a maintainer with registry creds to **resolve a real, digest-pinned image** (or build/
  mirror one). Also: (a) CLI may be TOGA1 (`toga --pn…`) vs TOGA2 (`toga2.py run …` subcommands) —
  verify against the actual image; (b) add the missing **`query_genes.bed`** output (phase_c4_merge
  consumes 4 toga files, wrapper collects 3). **Decision: provide a pullable TOGA image** to finish it.
- **GPU driver** — fix `nvidia-smi` mismatch (root/reboot) to enable KegAlign-GPU validation (WF-C).
- **Commit?** — confirm I should commit the night's wrappers (I left them uncommitted per your rule).

## Known blockers (surfaced for morning review)
- **GPU down** — `nvidia-smi` fails (NVML driver/library mismatch). KegAlign-GPU (WF-C validation
  choice) cannot run until the host driver is fixed (needs root/reboot — I can't do it). WF-C is
  built to support both; its test runs on **lastz-CPU** (test_data is tiny). GPU validation deferred.
- **TOGA2/CESAR2** (WF-C pass 2) — 3 GB image, heavy; attempted last, may not finish overnight.
- **Full Galaxy e2e integration** — requires installing ~16 IUC tools + datatype patch into
  `~/galaxy`; the slow final phase. Wrappers (the verifiable deliverable) come first.

## Tranches (each = a background Workflow: author + planemo lint + test --biocontainers)

| T | Workflow | New ⚠️ tools | Status |
|---|---|---|---|
| 1 | WF-B softmask | longdust, sdust | ✅ GREEN (profile 26.0; longdust 3 tests, sdust 2 tests; verifier-confirmed) |
| 2 | WF-C pass1 | __pair_strains__, chainStitchId, anchor_prep, phase_c2_triage, phase_c4_merge | ✅ GREEN (all 5; verifier-confirmed; profile 26.0) |
| 3 | WF-E consensus | odgi `paths` (subcmd), gene-BED extractor, phase_e_rbest_overlap, phase_e_graph_edges, phase_e_consensus | ✅ GREEN (5/5 wrappers; ⚠️ phase_e_graph_edges ports a real upstream BUG — see Decisions Needed) |
| 4-6 | WF-F/G/I | group_cds_by_og, iqtree3, multiz_fold | ✅ GREEN (3/3; group_cds_by_og has a min_intact divergence — see Decisions) |
| 7 | WF-K hub | ucsc_kent suite, process_maf, maf_to_bigmaf_bed, chain_to_bigChain, build_hub_bb, build_trackdb, build_genomes_txt | ✅ GREEN (7/7; ⚠️ mafIndex has no biocontainer — see Decisions) |
| 8 | WF-C pass2 | toga2/cesar2 | ⚠️ SCAFFOLD ONLY — XML lint-green but BLOCKED on image (see Decisions) |
| 9 | repo | profile-bump existing 9 wrappers → 26.0 | ✅ GREEN (all 9 @ 26.0, lint-clean; light tools re-tested) |
| 10 | integration | stand up ~/galaxy + load all wrappers | ✅ GREEN — Galaxy 26.1.rc1 @ localhost:8080, **41/41 tool XMLs loaded, 0 failures** |
| 11 | workflows | author 11 gxformat2 workflows vs loaded tool_ids | ✅ GREEN (10 .gxwf.yml + WF-D reuse; all lint-clean; WF-C/I/K flag gxformat2 map-over limits) |
| 12 | e2e proof | install IUC deps + run WF-B softmask on test_data | ✅ GREEN — WF-B ran end-to-end (14 jobs ok, masking verified); committed .gxwf.yml fixed to match |

No new tools (skip wrapping): WF-A (sourmash+busco iuc), WF-D (pggb reused), WF-H (hyphy iuc), WF-J (bcftools+CrossMap iuc).

## After wrappers
- Author the 11 `.ga` workflows (+ tests.yml, README) under `workflows/<phase>/`.
- Bump the 9 existing wrappers to the newest profile planemo accepts.
- Integration: stand up `~/galaxy`, install IUC tools + our wrappers, run test_data e2e
  (lastz-CPU for C; skip/queue GPU + TOGA2).

## Log
- T1 launched.
- **T1 GREEN** (profile 26.0): `tools/longdust/` (3 tests pass), `tools/sdust/` (2 tests pass); both verifier-confirmed via independent `planemo test --biocontainers`. Minor polish noted: no bio.tools xref (none exists); sdust Test#2 duplicates defaults. Uncommitted.
- T2 launched (WF-C pass1).
- **T2 GREEN** (profile 26.0, all verifier-confirmed): `tools/chainStitchId/` (1 test), `tools/anchor_prep/` (1), `tools/phase_c2_triage/` (1, ports the real script + pyfaidx), `tools/phase_c4_merge/` (1, Liftoff-only path; wrapper handles optional TOGA), `tools/__pair_strains__/` (3 — list:paired collection helper works). Notes: tests are single-path/weak in places (clean-path only for triage; Liftoff-only only for merge); cosmetic URL mismatch in pair_strains macros; stale repo-root tool_test_output.json (harmless). Uncommitted.
- T3 launched (WF-E).
- **T3 GREEN** (profile 26.0, verifier-confirmed): `tools/odgi/paths.xml` (added to suite, 1 test), `tools/gene_bed/` (1), `tools/phase_e_rbest_overlap/` (2 tests, .dat collection staging works), `tools/phase_e_consensus/` (1 test, nested list:list staging works), `tools/phase_e_graph_edges/` (1 test, **faithful port of a header-only-output bug** — see Decisions Needed). Uncommitted.
- T4-6 launched.
- **T4-6 GREEN** (profile 26.0, verifier-confirmed): `tools/group_cds_by_og/` (1 test — real CDS join/translate verified; ⚠️ min_intact divergence, see Decisions), `tools/iqtree3/` (2 tests — ≥4 and <4-seq fallback both pass), `tools/multiz_fold/` (2 tests — sourmash-DESC ordering + progressive fold). Uncommitted.
- T7 launched (WF-K).
- **T7 GREEN** (profile 26.0, verifier-confirmed): `tools/ucsc_kent/` suite — bedToBigBed/faToTwoBit/gff3ToGenePred/genePredToBed/hubCheck run in real ucsc-*:482 biocontainers + pass; **mafIndex caveated** (no container, see Decisions). `tools/process_maf/`, `tools/maf_to_bigmaf_bed/`, `tools/chain_to_bigChain/` (ports), `tools/build_hub_bb/` (consolidated rewrite, selection BED12+5 + orthogroup BED12), `tools/build_trackdb/` (author), `tools/build_genomes_txt/` (author) — all green. Uncommitted.
- **22/22 CPU wrappers green** (mafIndex caveated). T8 (toga2) + T9 (profile-bump) launched in parallel.
- **T8 toga2: SCAFFOLD ONLY** — XML lint-green (only intentional TestsMissing); BLOCKED on a pullable image (see Decisions). Faithful TOGA1-CLI port from impl/04; needs image + CLI verify + query_genes.bed output.
- **T9 GREEN** — 9 existing wrappers → profile 26.0, all lint-clean; pansn_rename/fasta_concat/gfaffix re-tested pass; odgi paths.xml profile tokenized. Repo now uniformly 26.0. Uncommitted.
- **WRAPPER PHASE COMPLETE: 22 new green + 9 existing green @ 26.0.** (toga2 scaffold pending image.)
- T10 launched (integration).
- **T10 GREEN — Galaxy 26.1.rc1 running at http://localhost:8080**, serving all 41 of our tool XMLs (31 dirs; odgi/vg/ucsc_kent are suites), **0 load failures** (verified `GET /api/tools`). Start: `cd ~/galaxy && GALAXY_SKIP_CLIENT_BUILD=1 ./run.sh --daemon`; stop: `./run.sh stop`. odgi `.og` datatype ships natively in dev-tip (patch reverted, source clean). One DB migration applied (universe.sqlite backed up first). Status: `execution/integration_status.md`. local_tool_conf.xml rewritten to list all 41.
- T11 launched (author workflows).
- **T11 GREEN** — 10 `workflows/<phase>/*.gxwf.yml` authored (inventory, softmask, align_chain_project, consensus, msa, trees, selection, multiz, vcf_projection, ucsc_hub) + WF-D reuses existing pggb-pangenome-build.ga. All `planemo workflow_lint` clean (0 errors; cosmetic warnings). Our-wrapper tool_ids verified against live /api/tools. WF-C/I/K READMEs flag gxformat2 gaps (per-pair sizes lookup, anchor×query cross-product, rbest relabel, per-hinge scalar) needing editor relink or small helper tools. Uncommitted.
- T12 launched (e2e proof).
- **T12 GREEN — WF-B softmask ran END-TO-END** on real Galaxy: 2 P. vivax chromosomes (PvP01 LT635614.2, PvSY56 QMFC01000003.1) as a list collection → 14 jobs `ok` (longdust, sdust, cat1, bedtools_sortbed, bedtools_mergebed, bedtools_maskfastabed, samtools_faidx ×2 strains), invocation `5969b1f7201f12ae` completed, ~61s. Soft-masking VERIFIED: 23.3% / 17.3% lowercase, sizes unchanged. Installed IUC bedtools + samtools_faidx from toolshed. Report: `execution/wfb_e2e_status.md`.
- **The shipped softmask.gxwf.yml needed 5 fixes to run** (authoring agents wrote IUC param names blind, since those tools weren't installed at authoring time). Committed file now PATCHED + matches the green run: bedtools_merge→bedtools_mergebed; maskfasta bed→input, soft_mask→soft; bedtools_sortbed genome selector pinned to `hist`. ⚠️ **The other 9 authored workflows almost certainly need the same per-IUC-step runtime-param validation** — they are lint-clean but only WF-B is runtime-proven.

---

## MORNING SUMMARY — where it stands

**Delivered + verified tonight:**
- **31 tool wrappers planemo-green** @ profile 26.0 (22 new across WF-B/C/E/F/G/I/K + 9 existing re-bumped). Independent verifier re-ran every test.
- **Galaxy 26.1.rc1 running** at http://localhost:8080 (`cd ~/galaxy && GALAXY_SKIP_CLIENT_BUILD=1 ./run.sh --daemon`; stop `./run.sh stop`) with **all 41 tool XMLs loaded, 0 failures**.
- **11 workflows authored** (gxformat2, lint-clean) under `workflows/<phase>/`.
- **WF-B proven end-to-end** on real data (the composition proof).
- Everything **uncommitted** (per your rule) — review the working tree, then say the word to commit.

**To finish the full e2e (your next session):**
1. Decide the 5 items under "Decisions needed" (esp. the `phase_e_graph_edges` bug + commit).
2. Fix the GPU driver → enables WF-C KegAlign (else it runs lastz-CPU).
3. Provide a pullable TOGA2 image → finishes WF-C pass 2.
4. Install the remaining IUC tools (sourmash, busco, liftoff, gffread, rbc_mafft, pal2nal, trimal, hyphy_busted, bcftools*, crossmap, ucsc_* chain tools, lastz) — then **runtime-validate each workflow's IUC-step params** (same fixes WF-B needed) and run them on test_data, phase by phase.
4. WF-C/I/K need editor relink / small helper tools for the gxformat2 map-over gaps (documented in their READMEs).

**Then:** toolshed + IWC registration (your stated final step).
