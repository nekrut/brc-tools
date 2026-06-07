# Pv4 pipeline → Galaxy: full-port plan

Port the validated `Pv4-pangenome/v3/pipeline` (phases A–K) to Galaxy as **11 per-phase
workflows** + the tool wrappers each needs. Phase D (PGGB graph) is **already done** in this
repo. Local-validate-first: wrap → `planemo test` → run on `pipeline/test_data` on local
Galaxy. No tools-iuc / IWC PRs this round.

Source of truth: `Pv4-pangenome/v3/pipeline/{PIPELINE_EXPLANATION,LOCAL,GALAXY}.md` + `impl/*.sh`
+ `impl/scripts/*.py`, **plus** `v3/ucsc_hub/` (Phase K driver + helpers + committed manifests/
autoSql) and `v3/tools/` (e.g. `chain_to_bigChain.py`). **`impl/*.sh` covers only phases A–J**
(it stops at `11_project_vcf.sh` = Phase J); there is **no Phase K impl script under impl/** — the
Phase K reference is `v3/ucsc_hub/run_phase_k.sh` + its helpers. Container images + exact flags are
pinned in `LOCAL.md` / `impl`. **Caveat: Phase K is the least-validated stage** — `verify_essentials.sh`
checks none of its outputs, so K's I/O contracts must be authored/validated fresh rather than relied on
as "validated impl."

## Decisions (interview 2026-06-06)

| # | Decision |
|---|---|
| 1 | **One workflow per phase** — A,B,C,E,F,G,H,I,J,K each its own `.ga` (D reused). **11 standalone first, validated independently; author the master orchestrator after.** |
| 2 | **Full scope** — TOGA2/CESAR2 rescue, Phase K UCSC hub, KegAlign GPU all IN. README "NOT in pipeline" adds (GARD, BUSTED-MH, outgroup, MACSE) deferred. |
| 3 | **KegAlign GPU is the Phase C default AND the validation aligner** — add a `docker_gpu` destination + tool routing to `galaxy_config_job_conf.xml` and validate WF-C on GPU. `lastz` is the swappable CPU alt (flags NOT parameter-transparent). KegAlign wrapper lives in an external repo → 🔎 verify installed + GPU dest before WF-C. |
| 4 | **Local validate first** — same gate the PGGB port used; upstream PRs deferred. |
| 5 | **Phase A similarity = `sourmash`** — `sourmash sketch dna -p k=31,scaled=1000` + `sourmash compare` → `compare.csv` (**similarity**, 1.0=identical). Uses **IUC `sourmash_sketch` + `sourmash_compare`** (GALAXY.md:35/38 give the toolshed paths — no wrap); restores the BRC `.sig` reuse story; matches every doc. WF-I fold-order sorts **descending** (closest = highest similarity). Diverges from the byte-exact mash v3 run but is functionally equivalent for fold-order + QC. |
| 6 | **Phase J ports only Path A2** (CrossMap on cleaned chain — production path); Path B graph-native VCF projection **cut** per GALAXY.md:268. |
| 7 | **Repo layout:** new tools under `tools/<tool>/`, new workflows under `workflows/<phase>/`, matching existing convention. |
| 8 | **Target panel + tests:** validate on the **5-strain test_data** panel (`min_intact` 4/3 from species.conf); document **Pv4 8-strain** (7/5) as the production preset; smoke = 3-strain/1-chr (2/2). **All tests use `pipeline/test_data`** and **replicate the local pipeline's own checks** (`impl/smoke_test.sh` + `lib/verify_essentials.sh`), diffing against validated local artifacts (**Phase K AND Phase A excepted**: K has no impl artifact; WF-A emits sourmash `compare.csv`, not mash `dist.tsv`, so it is validated by **structural assertion** — N labels in header, similarities ∈ [0,1], descending fold-order sanity — not byte-diff; `verify_essentials.sh`'s "Mash distance matrix" check is N/A for the sourmash port). |
| 9 | **Param policy:** surface species knobs as workflow-form params (`ref_strain`, `anchor_strains`, `busco_lineage`, `min_intact`, rbest/graph overlap thresholds, `hsp_threshold`, pggb `-p`/`-s`, family regex `VAR_ANTIGEN_RE`); **hardcode validated v3 tool-internal flags** (sourmash k/scaled, mafft LINSI, `axtChain -linearGap`, busted flags, …). **Note:** `VAR_ANTIGEN_RE` feeds **only** WF-K `build_hub_bb` (`--family_re`); it does NOT feed triage. phase_c2_triage rule R8 (force-CESAR2 for variant-antigen families) reads a `--family-list` **TSV file**, not a regex, and is **OFF in the validated run** (impl/04 passes no `--family-list`); it stays dormant unless a `family_list` TSV input + producer is added. |
| 10 | **Collection model:** carry strain/anchor/gene identity via Galaxy **nested collections (list:list)** keyed by `element_identifier`; each wrapper **symlinks `element_identifier` → the filename the script expects** inside the `<command>` block (the PGGB-port `.dat` lesson). |
| 11 | **WF-F = subworkflow:** a `group_cds_by_og` helper emits **PAIRED per-orthogroup collections** — `{og}.cds.fa` (nucleotide, stops→NNN, codon-truncated) **and** `{og}.pep.fa` (protein: translate + `rstrip('*')`, drop ref-internal-stop genes per build_msa.py:271-277,290-293) — applying `min_intact`. **Grouping is by coordinate lookup** (fold build_msa.py `parse_gff_cds` keyed on `normalize_gene_id`-d gene_id + `extract_cds` from softmasked FASTA) **directly into the helper**, NOT gffread `-x` keyed on the strain-column token — the ortholog_table strain columns hold `gene|alias,gene2` forms that gffread transcript/mRNA headers don't match. Then IUC `mafft`(LINSI) maps over the **protein** collection → `pal2nal` (two inputs: mafft protein aln + `{og}.cds.fa`, paired by OG element_identifier) → `trimal`. Dodges the build_msa container-in-container bug. Query gene coords from the **REF-anchor projection**. |
| 12 | **TOGA2 sequencing:** ship **Liftoff-only C.4 first** (`phase_c4_merge --toga-dir` **required**; pass an empty/staged dir for pass 1 — loaders short-circuit on missing files → same downstream contract), add the TOGA2/CESAR2 rescue branch as a fast-follow. **Pin TOGA by image digest** (`ghcr.io/hillerlab/toga@sha256:…` in a `<container>` requirement) — not `:latest`. |
| 13 | **IQ-TREE = bump-wrap `iqtree3`**, pinned to one version (`3.1.2`; reconcile the apptainer-lib `3.0.0`). The **<4-unique-sequence bootstrap fallback lives inside the wrapper** (count uniques, drop `-B`). |
| 14 | **Profile = 26.x:** new wrappers declare `@PROFILE@`=26.x to match the **Galaxy 26.1** validation instance; **re-touch the 9 existing wrappers** (currently 25.0) to match. |
| 15 | **Phase K:** **consolidate** `build_selection_bb` + `build_orthogroup_bb` into one `build_hub_bb` tool (they overlap); wrap the kentUtils as **one `ucsc_kent` suite** (shared container/macros); **validation gate = `hubCheck` clean + a one-time manual UCSC-browser load** (no impl artifact to diff). |

## Status legend

- ✅ **here** — wrapped in this repo already (Phase D work).
- ✅ **iuc** — exists in tools-iuc / usegalaxy; use as-is (version check noted where relevant).
- ⚠️ **wrap** — new wrapper needed this round (XML around existing/new container).
- ✍️ **author** — no reference implementation; must be written from spec (LOCAL.md / GALAXY.md prose), then validated.
- 🔎 **verify** — believed to exist; confirm version/flags/presence before relying on it.

---

## Master tool inventory

| Tool | Phase | Status | Note |
|---|---|---|---|
| sourmash_sketch | A | ✅ iuc | `sketch dna -p k=31,scaled=1000`; one `.sig` per assembly (BRC-ingestible). GALAXY.md:35 toolshed path. (Decision 5) |
| sourmash_compare | A | ✅ iuc | N×N **similarity** matrix → `compare.csv` (GALAXY.md:38). WF-I fold sorts descending. |
| busco | A | ✅ iuc | `-m prot` on **input protein FASTA collection**, lineage configurable |
| longdust | B | ⚠️ wrap | new wrapper per GALAXY.md:51 (single static binary); BED output, trim to 3 cols before union. 🔎 if an IUC `longdust` has since appeared, prefer it. |
| sdust | B | ⚠️ wrap | standalone `quay.io/biocontainers/sdust:0.1--h077b44d_2` (bare `sdust`); no IUC tool exists |
| bedtools (sort/merge/maskfasta) | B | ✅ iuc | `maskfasta -soft` |
| samtools (faidx) | B, D | ✅ iuc | `.sizes` = `cut -f1,2` of `.fai` |
| `__pair_strains__` | C | ⚠️ wrap / ✍️ author | ~5-line helper (NOT a Galaxy built-in, per GALAXY.md): NxN pair-collection builder from strain list; params `include_self`, `both_directions`. Feeds the C.1–3 pair map-over |
| kegalign_gpu | C | 🔎 verify | GPU default + validation aligner. Confirm installed + `docker_gpu` dest on target. Biocontainer `kegalign-gpu:1.0.0--hdfd78af_0`. |
| lastz | C | ✅ iuc | CPU alt — **NOT parameter-transparent** with KegAlign |
| axtChain | C | ✅ iuc | `ucsc_axtchain` (container `ucsc-axtchain:482--…`; verify on target) |
| chainSort, chainPreNet, chainNet, netChainSubset, chainSwap | C | ✅ iuc | `ucsc_chainsort`/`…prenet`/`…net`/`…netchainsubset`/`…chainswap` (v482; verify on target) |
| chainStitchId | C | ⚠️ wrap | the **one** chain tool not in IUC; container `ucsc-chainstitchid:482--…` — XML only |
| liftoff | C.4 | ✅ iuc | `-copies -sc 0.95 -f features.txt` (hardcoded feature-types: protein_coding_gene/ncRNA_gene/pseudogene; without `-f` Liftoff defaults to `gene` only) |
| anchor_prep | C.4 | ⚠️ wrap | one helper → `{A}.bed12` (gffread `--bed` + protein-coding filter) + `{A}.isoforms.tsv` (mRNA ID/Parent); from `setup/build_anchor_inputs.sh` |
| phase_c2_triage.py | C.4 | ⚠️ wrap | 8-rule triage; pyfaidx |
| phase_c4_merge.py | C.4 | ⚠️ wrap | provenance merge; `--toga-dir` **required** — pass an empty/staged dir for Liftoff-only pass 1 (loaders short-circuit on missing files, so output contract is unchanged) |
| toga2 / cesar2 | C.4 | ⚠️ wrap *(pass 2)* | hardest; `ghcr.io/hillerlab/toga@sha256:…` (~3 GB, **digest-pinned**) |
| odgi `paths` | E | ⚠️ wrap | **add subcommand** to existing odgi (build/stats/viz here); pin to pggb container's odgi version |
| gene-BED extractor | E | ⚠️ wrap | per-strain gene BED **from NATIVE annotations** (4-col) |
| phase_e_rbest_overlap.py | E | ⚠️ wrap | rbest-chain → gene edges (`--min_overlap`, exposed default 0.90) |
| phase_e_graph_edges.py | E | ⚠️ wrap | graph-path → gene edges (`--min-overlap`, exposed default 0.90) |
| phase_e_consensus.py | E | ⚠️ wrap | union-find → ortholog_table.tsv |
| group_cds_by_og | F | ⚠️ wrap | helper: ortholog_table + per-strain merged GFFs + softmasked FASTAs → **by coordinate lookup** (folds build_msa.py `parse_gff_cds`/`extract_cds`) → **PAIRED** per-OG collections `{og}.cds.fa` (nuc, stops→NNN) + `{og}.pep.fa` (protein, translate+`rstrip('*')`); strip stops, `min_intact` |
| gffread | F | ✅ iuc | `-x` / `-y` CDS+protein extraction |
| mafft | F | ✅ rnateam | tool id `rbc_mafft` (LINSI), on usegalaxy; no wrap |
| pal2nal | F | ✅ iuc | codon back-translate |
| trimal | F | ✅ iuc | `-automated1` |
| iqtree3 | G | ⚠️ wrap | bump-wrap, pin `3.1.2`; binary `iqtree3`; `<4`-unique fallback in-wrapper |
| hyphy busted | H | ✅ iuc | `--srv No --branches All`; gene id rides `element_identifier` |
| axtToMaf | I, K | ✅ iuc | `ucsc_axttomaf` (XML id `ucsc_axtomaf`; v482) |
| multiz_fold | I | ⚠️ wrap | one tool: order closest-first from `compare.csv` (DESC) + progressive fold (ports `impl/10_multiz.sh`) |
| bcftools (annotate/sort/concat/index) | J | ✅ iuc | rename-chrs, sort-before-index |
| CrossMap (vcf) | J | ✅ iuc | cleaned chain |
| ucsc_kent suite (mafIndex, hubCheck, + any missing bedToBigBed/gff3ToGenePred/genePredToBed/faToTwoBit) | K | ⚠️ wrap | one suite dir, shared `ucsc-kent-tools` container + macros. **`mafIndex` has NO validated reference invocation** (`v3/tools/mafIndex` is a 0-byte placeholder; the reference run failed Permission denied, impl tolerates via `\|\| true`) → source from the `ucsc-kent-tools` container and validate independently (confirm it produces a usable `.bai`). `mafToBigMaf` deliberately NOT in suite — bypassed by `maf_to_bigmaf_bed.py` (rejects overlapping multiz blocks). |
| process_maf.py | K | ⚠️ wrap | EXISTS `v3/ucsc_hub/process_maf.py`; per-MAF reorder/filter/sort by ref accession; **assumes s-lines ALREADY accession-named** (the strain→accession rename is a separate WF-I→WF-K step) |
| maf_to_bigmaf_bed.py | K | ⚠️ wrap | EXISTS `v3/ucsc_hub/`; emits bigMaf BED from MAF — **bypasses `mafToBigMaf`'s overlap rejection** (multiz blocks overlap in ref coords) |
| chain_to_bigChain.py | K | ⚠️ wrap | EXISTS `v3/tools/chain_to_bigChain.py` (74 lines); chain → bigChain.bed(6+6)+bigLink.bed(4+1) |
| build_hub_bb.py | K | ⚠️ wrap | **consolidated** from `build_selection_bb.py` + `build_orthogroup_bb.py` (EXIST in `v3/ucsc_hub/`, **no argparse** — Pv4 paths/REF_ACC/gene-prefix hardcoded → parameterization rewrite). Emits selection BED12+5 **and** orthogroup BED12 from ortholog_table (+ BUSTED jsons). |
| build_trackdb.py | K | ✍️ author | does not exist; per-assembly trackDb.txt from LOCAL.md K.5 spec |
| build_genomes_txt.py | K | ✍️ author | does not exist (`genomes.txt`/`hub.txt` are static committed files); author global 9-field genomes manifest |

**Already-wrapped here (reused as-is):** pansn_rename, fasta_concat, gfaffix, pggb, wfmash,
seqwish, smoothxg, odgi(build/stats/viz), vg(view/convert/deconstruct). *(All re-touched to profile 26.x — Decision 14.)*

**Phase K autoSql schema assets to bundle** (committed; required by every `bedToBigBed -as=`):
`bigMaf.as`, `bigSelectionPlus5.as` (`v3/ucsc_hub/`), `bigChain.as`, `bigLink.as` (`v3/tools/`).
The gff3-derived BigBed12 annotation track needs no `.as` file.

### New wrappers this round (count ≈ 23)

1. **longdust** (B) — new wrapper per GALAXY.md:51
2. **sdust** (B) — no IUC tool found
3. **`__pair_strains__`** (C) — ~5-line NxN pair-collection helper (per GALAXY.md; NOT a built-in)
4. **chainStitchId** (C) — XML only; the other 6 chain tools + axtToMaf are ✅ iuc
5. **anchor_prep** (C.4) — `{A}.bed12` + `{A}.isoforms.tsv`
6. **phase_c2_triage** (C.4)
7. **phase_c4_merge** (C.4) — `--toga-dir` required (pass empty/staged dir for pass 1)
8. **toga2/cesar2** (C.4) — *pass 2*, digest-pinned, hardest
9. **odgi `paths`** subcommand (E)
10. **gene-BED extractor** (E) — from native annotations
11. **phase_e_rbest_overlap** (E)
12. **phase_e_graph_edges** (E)
13. **phase_e_consensus** (E)
14. **group_cds_by_og** (F) — the WF-F orchestration helper (mafft/pal2nal/trimal are IUC)
15. **iqtree3** bump (G) — pinned 3.1.2
16. **multiz_fold** (I) — order + progressive fold in one tool
17. **ucsc_kent** suite (K) — mafIndex, hubCheck (+ verify bedToBigBed/gff3ToGenePred/genePredToBed/faToTwoBit)
18. **maf_to_bigmaf_bed.py** (K) — port from `v3/ucsc_hub/`; bypasses mafToBigMaf overlap rejection
19. **process_maf** (K) — port from `v3/ucsc_hub/`
20. **chain_to_bigChain** (K) — port from `v3/tools/`
21. **build_hub_bb** (K) — consolidated parameterization rewrite
22. **build_trackdb** (K) — ✍️ author from spec
23. **build_genomes_txt** (K) — ✍️ author from spec

(`sourmash_sketch`/`sourmash_compare` are **not** new — ✅ iuc per GALAXY.md:35/38, see inventory.)

Plus 🔎 verifications: sdust biocontainer, any IUC `longdust`, kegalign GPU + dest, bedToBigBed/gff3ToGenePred/genePredToBed/faToTwoBit on target.

---

## The 11 workflows

Inputs follow `GALAXY.md`: `assemblies` (list, keyed by strain), `annotations` (parallel list),
`proteomes` (parallel list, for BUSCO), `cohort_vcfs` (per-chr list), `ref_strain`,
`anchor_strains`, `chrom_rename`, a `strain→accession` map (for K), plus the Decision-9 form
params. Collection element identifier = strain name is the binding key throughout (Phase K shifts to
accession space — see WF-K).

### WF-A `inventory` (Phase A)
- **In:** assemblies; **proteomes** (per-strain protein FASTA collection — **either a real test_data
  pipeline input OR derived** via a gffread `-y` step over (annotations, assemblies); commit one and
  add `proteomes` to GALAXY.md Inputs accordingly); `busco_lineage`.
- **Steps:** sourmash_sketch ✅iuc (map-over assemblies, `sketch dna -p k=31,scaled=1000`) → sourmash_compare ✅iuc
  (N×N **similarity** → `compare.csv`) · busco (map-over **proteomes**, `-m prot -l <lineage>`) ✅iuc —
  BUSCO runs `-m prot` on proteins, so it MUST map over `proteomes`, not `assemblies`.
- **Out:** `compare.csv` (similarity; feeds WF-I fold order, sorted **descending**), per-strain `.sig`
  signatures (BRC reuse), per-strain BUSCO summaries.
- **New wrappers:** none (sourmash_sketch/compare are ✅ iuc, GALAXY.md:35/38). **Map-over:** per strain.

### WF-B `softmask` (Phase B)
- **In:** assemblies.
- **Steps (map-over strain):** longdust ⚠️ + sdust ⚠️ → **trim longdust to 3 cols (chrom,start,end)
  via awk** (sdust already 3-col) → bedtools sort|merge of concatenated longdust3col+sdust (union)
  ✅ → bedtools maskfasta `-soft` ✅ → samtools faidx ✅ → `.sizes` = `cut -f1,2` of `.fai`.
- **Out:** softmasked FASTAs + `.fai` + `.sizes` (feed C, D, I).
- **New wrappers:** longdust, sdust.

### WF-C `align_chain_project` (Phase C)
Largest workflow; two internal blocks **with an intra-WF data dependency** (C.4 consumes C.1–3
output), which is why they are fused into one workflow.
- **C.1–3 chains** (map-over N(N−1)/2 pairs): `__pair_strains__` helper → KegAlign GPU 🔎 →
  axtChain✅→chainSort✅→chainPreNet✅→chainNet✅→netChainSubset✅→chainStitchId⚠️ (**cleaned chain**);
  swap✅→sort✅→net✅→subset✅→chainStitchId⚠️→swap✅→sort✅ (**rbest chain** — matches validated impl
  `chainSwap→chainSort→chainNet→netChainSubset→chainStitchId→chainSwap→chainSort`).
  - **rbest chain collection element_identifier MUST be `{a}.{b}`** so the source/target pair
    survives into Phase E (phase_e_rbest_overlap keys strains off the filename stem).
- **anchor_prep** (one helper, map-over anchors): from the chrom-reconciled `{A}.fixed.gff3` produce
  `{A}.bed12` (gffread `--bed` + protein-coding-gene filter) and `{A}.isoforms.tsv` (mRNA
  ID/Parent). Wire `{A}.bed12` → phase_c2_triage(`--reference-bed`), phase_c4_merge(`--ref-bed`),
  toga (positional ref bed12), WF-K selection/orthogroup; `{A}.isoforms.tsv` → toga `--cb`.
  Chrom reconciliation uses the **`chrom_rename` TSV input only** (need only cover ref/anchors).
- **C.4 projection — pass 1 Liftoff-only** (subworkflow, map-over anchor×query): liftoff ✅ →
  phase_c2_triage ⚠️ → phase_c4_merge ⚠️ (`--toga-dir` **required**; pass an **empty/staged dir** for
  pass 1 → loaders short-circuit on missing files, tags all LIFTOFF_CLEAN/flagged, **same output
  contract**). **Pass 2 adds** toga2/cesar2 ⚠️ (filtered to `needs_cesar2.bed`;
  **consumes the C.1–3 `{A}.{Q}.cleaned.chain`** — intra-WF edge: C.1–3 MUST precede C.4 TOGA2).
- **Aligner flags are NOT parameter-transparent** (kegalign↔lastz): KegAlign `--strand both
  --hsp_threshold 5000 --gapped_threshold 6000 --inner 2000 --ydrop 15000 --output_format axt`;
  lastz `--masking=50 --hspthresh=4500 --gappedthresh=6000 --inner=2000 --ydrop=15000 --format=axt`.
  Both emit AXT. Chain build `axtChain -linearGap=loose -faT -faQ`, target=A query=B, softmasked
  FASTAs(+.sizes) from WF-B.
- **Out:** **pairwise AXTs (C.1)** (→I; **flat list of N(N−1)/2 unordered pairs**, element_identifier
  `{A}__vs__{B}` with A<B, matching `impl/03_align_chain.sh:30`), `*.cleaned.chain` (→J,K),
  `*.rbest.chain` (→E), per-(anchor,query) merged GFF3 +
  classification.tsv (→E, as a **list:list** outer=anchor / inner=query). cleaned.chain consumed at
  different cardinalities: J uses N−1 (ref→target), K uses full N(N−1) directed, C.4 uses anchors×queries.
- **New wrappers (pass 1):** `__pair_strains__`, chainStitchId, anchor_prep, phase_c2_triage,
  phase_c4_merge. **(pass 2):** toga2.
- **Scaling:** 28 pairs ×2 dirs; anchors×others projections (Pv4: 35; test panel: smaller).

### WF-D `pggb_graph` (Phase D) — **DONE, reuse**
- `workflows/pggb-pangenome-build/pggb-pangenome-build.ga` already produces `.og`/`.gfa`.
- **One change:** add `odgi paths --haplotypes` subcommand to the odgi wrapper (output → WF-E).
- **Prerequisite gate (shared with WF-E):** see odgi-datatype prerequisite below.

### WF-E `consensus_orthology` (Phase E)
- **In (two distinct GFF sources):** (1) **native per-strain GFF3 annotations** → per-strain gene
  BEDs (the orthogroup **nodes**); (2) **C.4 merged GFF3 + per-(anchor,query) classification.tsv**
  (list:list) → consensus only (**projection edges**). Also: rbest chains (C, element_identifier
  `{a}.{b}`), pggb `odgi` graph (D).
- **Steps:** native GFF→gene BED (helper) → feeds **both** phase_e_rbest_overlap ⚠️ AND
  phase_e_graph_edges ⚠️ · odgi paths ⚠️ → phase_e_graph_edges · phase_e_consensus ⚠️ (union-find)
  consumes the C.4 classifications + both edge TSVs.
- **Out:** `ortholog_table.tsv` (→F, K).
- **New wrappers:** gene-BED extractor, phase_e_rbest_overlap, phase_e_graph_edges, phase_e_consensus
  (+ odgi paths). **Overlap thresholds exposed as params, default 0.90** (Decision 9).
- **Divergence note:** standalone `odgi paths` (not bundled in consensus per GALAXY.md:143). Pin odgi
  version (match pggb container); `assert_contents` test that the path/haplotype name appears in
  **column 0** of `odgi paths --haplotypes` (phase_e_graph_edges reads `parts[0]`).
- **Staging note (critical — `.dat` break):** all three phase_e_* scripts derive strain/pair identity
  from input **filenames**, but Galaxy stores datasets as `.dat`. Each wrapper's `<command>` MUST
  stage collection elements before globbing — a Cheetah `#for $el in $collection#` loop symlinking
  `$el` to `$el.element_identifier` with the required extension (`${strain}.bed`;
  `${a}.${b}.rbest.chain`), then pass `stagingdir/*.bed` / `*.rbest.chain`. rbest/graph_edges consume
  **flat** collections.
- **Nested-collection note (consensus):** phase_e_consensus walks `{anchor}-as-ref/{query}.classification.tsv`.
  WF-C.4 emits a **list:list** (outer=anchor, inner=query); the consensus wrapper reconstructs the
  `${anchor}-as-ref/${query}.classification.tsv` tree (symlinks) and passes the staged root as `--liftoff_dir`.

### WF-F `msa` (Phase F) — **subworkflow**, runs twice (strict `core_v3` + relaxed `core_relaxed`)
- **In:** ortholog_table; gene-coord source = ref's own fixed GFF + ref softmasked FASTA, and the
  **REF-anchor subset** of C.4 merged GFF3s (one `{query}.annotation.gff3` per non-ref query from
  `{REF}-as-ref/` — do NOT wire all anchors) + per-strain softmasked FASTAs (B); `min_intact`
  (required form param; test 4/3, Pv4 7/5).
- **Steps:** **group_cds_by_og** ⚠️ (ortholog_table + per-strain merged GFFs + per-strain softmasked
  FASTAs + `min_intact` → **by coordinate lookup**, folding build_msa.py `parse_gff_cds`/`extract_cds`;
  emits **PAIRED** per-OG collections: `{og}.cds.fa` nucleotide [**internal stops→NNN**, codon-truncated]
  **and** `{og}.pep.fa` protein [translate + `rstrip('*')`, drop ref-internal-stop genes]) → **mafft**
  LINSI (`--localpair --maxiterate 1000`, map-over OG, on the **protein** `{og}.pep.fa` collection →
  protein alignment) → **pal2nal** (`-output fasta`; **two inputs paired by OG element_identifier**:
  mafft protein alignment + `{og}.cds.fa` nucleotide → `{og}.codon.aln.fa`) → **trimal** (`-automated1`).
  All IUC except group_cds_by_og. (No separate `translate` step — translate is folded into the helper.)
- **Out:** TWO labeled collections — strict `core_v3` (~1.6k) + relaxed `core_relaxed` (~4.2k) — of
  per-OG codon + protein (+ cleaned) alignments.
- **New wrappers:** group_cds_by_og.
- **Why subworkflow:** build_msa.py calls `run_in_container.sh` (absent in Galaxy) — a
  container-in-container path that breaks; decomposing runs each aligner as its own Galaxy job.
- **Identity:** sort each input collection on the shared **strain element_identifier** before pulling
  per-member CDS, so gene models pair correctly per orthogroup. **test_data assertions:** every
  non-dash ortholog_table token resolves to exactly one CDS record (no silent drops); pal2nal's two
  inputs carry identical strain record sets/order per OG.

### WF-G `trees` (Phase G) — runs twice
- **In:** codon-alignment collections (F) — maps over **both** `core_v3` and `core_relaxed`.
- **Steps (map-over gene):** iqtree3 `-m MFP -B 1000 -T 2`; **<4 unique seqs → drop `-B` inside the
  wrapper** (count uniques; bootstrap hangs silently below 4).
- **Out:** TWO `.treefile` collections; **collapse the rest into `{set}_trees.tar`** (Decision 8/15).
- **New wrappers:** iqtree3 (pinned 3.1.2).

### WF-H `selection` (Phase H) — runs twice
- **In:** codon alignments (F) + treefiles (G), paired by gene — **both** sets.
- **Steps (map-over gene):** hyphy busted `--srv No --branches All` ✅.
- **Out:** TWO `busted.json` collections; **collapse into `{set}_busted.tar`** past threshold.
  **Gene id rides `element_identifier`** (BUSTED writes a fixed-named `busted.json`); WF-K derives
  gene id from element_identifier, NOT a `parts[-2]` dir scheme. **Tar layout (pin):** the collapse
  step **renames each element's `busted.json` → `{element_identifier}.json`** and tars them flat — one
  `<gene_id>.json` per element at the tar **root** (gene_id = the BUSTED element_identifier). build_hub_bb
  `extract_busted_jsons` MUST key gene_id off the member **BASENAME** (strip `.json`), NOT `parts[-2]`
  (a Galaxy element-id tar has no per-gene dir, so the old `parts[-2]` logic misparses/drops every gene).
  H output is a **subset** of G input (genes lacking a treefile / invalid JSON dropped) — WF-K must
  tolerate missing entries.
- **New wrappers:** none.

### WF-I `multiz` (Phase I)
- **In:** pairwise AXTs (C.1, **the full unordered N(N−1)/2 set**), `.sizes` (B), **`compare.csv` (A,
  sourmash similarity)**.
- **Collection structure (pin):** multiz_fold needs ALL pair-MAFs involving a hinge plus `compare.csv`,
  so the **AXT/pair-MAF set is a whole-collection (non-mapped) input**; hinge identity is the mapped
  scalar. Restructure as **list:list (outer = hinge, inner = Q)** so a map-over on the **outer hinge**
  dimension hands one hinge's full set of Q pair-MAFs to one multiz_fold job. A plain Galaxy map (one
  element per job) cannot serve the AXT collection as the mapped input.
- **Steps (map-over hinge):** **axtToMaf folded INSIDE multiz_fold** (orientation is hinge-aware): per
  hinge H, run axtToMaf once over the whole AXT set, selecting whichever **unordered** AXT exists
  (`H__vs__Q` or `Q__vs__H`) per pair and orienting `-tPrefix`/`-qPrefix` **together with the two
  `.sizes` args** so H is always the MAF target/reference — when the stored AXT has Q as target, use
  `-tPrefix=Q. -qPrefix=H.` with sizes Q then H (mirroring `impl/10_multiz.sh:32-50`; NOT a fixed
  `-tPrefix=H. -qPrefix=Q.`). Then **multiz_fold** ⚠️ orders strains **closest-first = descending
  similarity** from `compare.csv` and runs the whole progressive multiz fold internally (ports the
  `impl/10_multiz.sh` loop; sequential reduce is awkward in a pure `.ga`, and RAM is managed in one
  place). No `multiz_progressive.py` exists. *(If axtToMaf is instead kept as a separate step, it must
  map over the **N(N−1) DIRECTED** pairs — each unordered AXT producing both H-as-ref and Q-as-ref
  MAFs — not the N(N−1)/2 unordered pairs.)*
- **Out:** per-hinge `.multiz.maf` with **strain-named** s-lines (→K, which renames to accessions).
- **New wrappers:** multiz_fold.
- **Scaling:** RAM-bound; one multi-GB MAF per hinge in flight.

### WF-J `vcf_projection` (Phase J — Path A2 only) — **NO new wrappers**
- **In:** cohort_vcfs, chrom_rename (small `_v1`→GenBank TSV), **the N−1 subset of cleaned chains
  where source = REF_STRAIN** (one per non-ref target, element_identifier = target strain — distinct
  from WF-E rbest and WF-K full N(N−1)), target FASTAs (B).
- **Steps:** bcftools annotate `--rename-chrs` ✅ → (map-over target) CrossMap vcf ✅ → bcftools
  sort→index ✅ → bcftools concat `-a` ✅.
- **Out:** `cohort_on_{target}.vcf.gz` (Pv4: 7).

### WF-K `ucsc_hub` (Phase K) — operates in **accession space**
**Re-derived from `v3/ucsc_hub/run_phase_k.sh`.** Least-validated stage; I/O contracts authored fresh.
- **Namespace shift:** Phase K works in **GenBank accession** space (e.g. `GCA_900093555.2`).
  Requires a hand-maintained **strain→accession map** as an explicit WF-K input. Hub dirs per-accession
  (`ucsc_hub/GCA_*`); sizes `{ACC}.fa.fai`; key `REF_ACC` off `ref_strain` via the map. **Add a
  strain→accession s-line rename between WF-I and WF-K** (process_maf requires accession-named s-lines
  + accession sizes).
- **In:** strain→accession map, multiz MAFs (I, strain-named), **full N(N−1) directed** cleaned chains
  (C; map-over key = directed pair), merged GFFs (C.4), BUSTED jsons (H — **both** sets), ortholog_table
  (E), assemblies (B), ref `{A}.bed12` (WF-C anchor_prep). Plus the four autoSql `.as` assets.
- **Steps:**
  - bigMaf: gunzip → **process_maf.py `<ref_acc> <in.maf> <out.maf>`** ⚠️ (drop blocks missing ref
    acc, reorder s-lines ref-first, sort by (ref_chrom, ref_start)) → **`maf_to_bigmaf_bed.py <ref_acc>
    <fixed.maf> <out.bed>`** ⚠️ (**bypasses `mafToBigMaf`'s overlap rejection** — multiz blocks overlap
    in ref coords) | `sort -k1,1 -k2,2n` | `bedToBigBed -type=bed3+1 -as=bigMaf.as -tab`🔎; plus a
    separate `mafIndex`⚠️ step.
  - bigChain: chain_to_bigChain⚠️ → bedToBigBed `-type=bed6+6 -as=bigChain.as`🔎 +
    `-type=bed4+1 -as=bigLink.as`🔎.
  - annotation: gff3ToGenePred🔎→genePredToBed🔎→bedToBigBed🔎 (BigBed12, no `.as`). **TWO sources**
    (per `build_annot_bb`, run_phase_k.sh:94-145): (1) **native self-annotation** per anchor
    (`PvP01.genbank.gff3` / `{anchor}.fixed.gff3`) AND (2) **cross-strain** `{anchor}-as-ref/{strain}.annotation.gff3`
    (C.4 merged). **Fanned out over 4 anchors × all strains** as `annot_from_{anchor}.bb` per accession.
  - selection + orthogroup: **build_hub_bb**⚠️ (consolidated) → bedToBigBed `-type=bed12+5
    -as=bigSelectionPlus5.as`🔎. Selection runs once per set → `selection_core_v3.bb` +
    `selection_core_relaxed.bb` (strict JSONs under `core_v3_hyphy/bulk/`, relaxed `core_relaxed_hyphy/`).
  - faToTwoBit🔎 (per accession).
  - manifests: build_trackdb✍️ (per-assembly trackDb.txt) + build_genomes_txt✍️ (global; 9-field;
    `defaultPos` real `chrN:start-end`; valid `twoBitPath`) + hub.txt → hubCheck⚠️.
- **Out:** `ucsc_hub/` collection (list:list, outer=accession, inner=track type).
- **New wrappers:** ucsc_kent suite (mafIndex, hubCheck, +verify others), maf_to_bigmaf_bed.py,
  process_maf, chain_to_bigChain, build_hub_bb (rewrite), build_trackdb, build_genomes_txt
  (author-from-spec).
- **Validation:** outside the A→J impl gate → **gate on hubCheck clean + one manual UCSC-browser load**
  on test_data (Decision 15). `genomes.txt` failure mode: hub won't load without real `defaultPos` +
  resolvable `twoBitPath`.

### WF-master (after the 11 are green)
Top-level `.ga` importing WF-A…K as subworkflows in dependency order
(`A→B→{C,D}; C→{E,I,J}; A→I; E→F→{G→H}; {H,I,J,C.4,E,B}→K`; `cohort_vcfs` is an external WF-J input).
**WF-I and WF-J do NOT sit downstream of F/E:** WF-I depends on A(compare.csv), B(sizes), C(AXT) only;
WF-J depends on C(cleaned chains), B(target FASTAs), cohort_vcfs only.

---

## Custom-script wrappers — I/O contracts (for wrapping)

All are stdlib/pyfaidx Python (no heavy deps); each becomes a thin `<command>` wrapper.
Aggregators take **globs** → Galaxy versions take **collections** and build the glob in the command
block (staging each element to `element_identifier`, see WF-E).

**Port targets vs author-from-spec / rewrite:**
- **Port (exist, thin):** phase_c2_triage, phase_c4_merge, phase_e_* (3), process_maf
  + maf_to_bigmaf_bed.py (`v3/ucsc_hub/`), chain_to_bigChain (`v3/tools/`, 74 lines).
- **Rewrite (exist, no argparse — hardcoded Pv4 constants):** build_hub_bb (consolidates
  `build_selection_bb.py` + `build_orthogroup_bb.py`). Extract TOOLS/HUB/WORK/INPUTS/STAGING paths,
  STRICT/RELAXED archive paths, ORTHOLOG_TABLE, ref BED12, SIZES_FILE, REF_ACC, gene prefix into CLI
  args.
- **Author from spec (do NOT exist):** build_trackdb, build_genomes_txt — write from LOCAL.md K.5
  (LOCAL.md:1078–1094 is a spec, not a file).
- **Decomposed (NOT ported as one tool):** build_msa.py → WF-F subworkflow via `group_cds_by_og`
  helper + IUC mafft/pal2nal/trimal (Decision 11).

| Script | WF | Args (key) | In | Out | Map/global |
|---|---|---|---|---|---|
| phase_c2_triage.py | C.4 | --liftoff-gff --query-fasta --reference-bed --output-dir --query-name **--family-list** (TSV; R8, OFF in validated run) **--subtelomere-bp** + thresholds | liftoff GFF, query FA, ref BED12, (optional family-list TSV) | needs_cesar2.bed, liftoff_clean.gff3, triage.tsv, summary.json | per query |
| phase_c4_merge.py | C.4 | --query --triage-dir **--toga-dir (required; pass empty/staged dir for pass 1, loaders short-circuit on missing files)** --out-dir --ref-bed | `--triage-dir`→`liftoff_clean.gff3`; `--toga-dir`→`loss_summary.tsv`,`orthology_classification.tsv`,`query_annotation.bed`,`query_genes.bed` | {q}.annotation.gff3, {q}.classification.tsv | per query |
| toga (toga2/cesar2) | C.4 | positional: ref.bed12, cleaned.chain, ref-softmasked.fa, query-softmasked.fa; --pn (out); --cb (isoforms.tsv); --u12 ""; --kt; --filter_bed needs_cesar2.bed; --nc cores | ref.bed12, `{A}.{Q}.cleaned.chain`, softmasked FASTAs, isoforms.tsv, needs_cesar2.bed | query_annotation/orthology/loss | per anchor×query; **skipped if cleaned chain missing OR needs_cesar2.bed empty** |
| phase_e_rbest_overlap.py | E | --chains --annotations --strains --min_overlap (exposed) --output | rbest chains (`{a}.{b}.rbest.chain`), gene BEDs (`{strain}.bed`) | rbest_edges.tsv | global (flat) |
| phase_e_graph_edges.py | E | --paths --annotations --strains --min-overlap (exposed, default 0.90) --output | odgi paths tsv (col 0 = path), gene BEDs | graph_edges.tsv | global (flat) |
| phase_e_consensus.py | E | --liftoff_dir --rbest --graph --anchors --strains --ref --output | classifications tree `{anchor}-as-ref/{query}.classification.tsv`, both edge tsvs | ortholog_table.tsv (4 fixed cols + 1/strain) | global (nested list:list) |
| group_cds_by_og *(new helper)* | F | --ortho --gffs (per-strain merged GFFs) --fastas (per-strain softmasked) --strains --min-intact --out-dir | ortho table, per-strain merged GFFs, softmasked FASTAs | **PAIRED** collections `{og}.cds.fa` (nuc, stops→NNN) + `{og}.pep.fa` (protein) | global → emits per-OG collections |
| process_maf.py | K | positional: ref_acc, in.maf, out.maf | accession-named MAF + ref_acc | ref-first, ref-filtered, sorted MAF | per MAF |
| maf_to_bigmaf_bed.py | K | positional: ref_acc, in.maf, out.bed | accession-named (processed) MAF + ref_acc | bigMaf BED (bypasses mafToBigMaf overlap rejection) | per MAF |
| chain_to_bigChain.py | K | chain.gz → bigChain.bed bigLink.bed | chain | 2 BED | per chain |
| build_hub_bb.py | K | **(rewrite)** CLI args: ortho table, BUSTED archives (strict+relaxed), ref bed12, sizes, ref_acc, gene prefix, `--family_re` (VAR_ANTIGEN_RE), outputs | ortho table, BUSTED jsons (`{set}_busted.tar`: one `<gene_id>.json` per element at tar root) | selection BED12+5 (per set) + orthogroup BED12 | global (selection per set). **`extract_busted_jsons` keys gene_id off member BASENAME (strip `.json`), NOT `parts[-2]`** |
| build_trackdb.py | K | **(author)** --assembly --strain --hub_dir --strains --anchors --output (LOCAL.md:1078–1094) | hub layout | trackDb.txt | per assembly |
| build_genomes_txt.py | K | **(author)** global; 9-field; defaultPos real chrN:start-end; valid twoBitPath | per-assembly metadata | genomes.txt | global |
| pansn_rename.py | D | (done) | | | |

`fix_gff_chroms.sh` → the workflow takes `chrom_rename` as input instead (covers the anchor
`{A}.fixed.gff3`). Length-matching fallback not ported this round.

---

## Test data & validation

`Pv4-pangenome/v3/pipeline/test_data/` (`species.conf`, `samples.txt`, `contig_map.tsv`; 5-strain
panel, with a 3-strain/1-chr smoke subset). **All testing uses this** (Decision 8):
- per-tool `planemo test` `<assert_contents>` fixtures (tiny inputs already exist for D),
- per-workflow `*-tests.yml` (IWC layout),
- a local-Galaxy e2e run that **replicates `impl/smoke_test.sh` + `lib/verify_essentials.sh`** and
  diffs outputs against the validated local artifacts (**Phase A and Phase K excepted**, see below).

**Phase A is not byte-diffable** (WF-A emits sourmash `compare.csv`; the validated local run produced
only mash `dist.tsv` — no `compare.csv` artifact exists) → validate WF-A by **structural assertion** on
`compare.csv` (N labels in header, similarities ∈ [0,1], descending fold-order sanity), NOT byte-diff.
`verify_essentials.sh`'s "Mash distance matrix" check (`lib/verify_essentials.sh:38-40`) is **N/A** for
the sourmash port; when adapting `verify_essentials.sh`, substitute a `compare.csv` structural check.

Gate per workflow: `planemo lint` clean · `planemo test --biocontainers` green (profile **26.x**) ·
imports + runs on the **Galaxy 26.1** instance against test_data · key output matches the local-run
artifact. **Phase K has no validated-impl artifact** → gate on `hubCheck` clean + a one-time manual
UCSC-browser load.

---

## Build sequence

Wrappers are independent (parallel-ish); workflows gate on their wrappers. (Re-touch the 9 existing
wrappers to profile 26.x as a first chore — Decision 14.)

1. **Low-risk wrappers first:** longdust, sdust, chainStitchId, odgi paths,
   ucsc_kent suite (mafIndex/hubCheck), maf_to_bigmaf_bed, process_maf, chain_to_bigChain. (+ verify
   kegalign GPU + dest, bedToBigBed/gff3ToGenePred/genePredToBed/faToTwoBit.)
2. **Script ports/rewrites:** anchor_prep, phase_c2_triage, phase_c4_merge, gene-BED extractor,
   phase_e_* (3), group_cds_by_og, build_hub_bb (rewrite), build_trackdb / build_genomes_txt
   (author-from-spec), iqtree3.
3. **Hardest:** toga2/cesar2 (3 GB digest-pinned image, GPU/IO heavy), multiz_fold.
4. **Workflows** A,B,(D reuse),E,G,H,J first (fewest new deps) → C (pass 1 Liftoff-only),F,I →
   C (pass 2 TOGA2) → K (designed-from-docs, own validation).
5. **Master** workflow + full test_data e2e.
6. (Deferred) tools-iuc + IWC PRs.

---

## Prerequisite gates

- **odgi datatype (WF-D + WF-E):** binary graph datatype `odgi` (file_ext `odgi`; class `Odgi`),
  exposed via a local **un-upstreamed monkey-patch** to `lib/galaxy/datatypes/binary.py`. Before
  WF-D/WF-E: (1) re-run `scripts/patch_og_datatype.sh` against **Galaxy 26.1** (written for
  release_25.0 — verify it appends cleanly); (2) **manually add** the `odgi` `<datatype>` to
  `datatypes_conf.xml` (the script only warns); (3) build the `odgi paths` subcommand (deferred at P7)
  + smoke test it reads the patched `.og` and emits the haplotype-paths TSV. Re-apply after any Galaxy
  upgrade until the core PR lands.
- **KegAlign GPU (WF-C):** the only documented job_conf here has a single `local`/`docker_heavy` (CPU)
  destination — no GPU. Required before WF-C: a `docker_gpu` destination in
  `galaxy_config_job_conf.xml` passing `--gpus all` (docker) or `gres`/`--gpus` (cluster), a
  `<tool id="kegalign…" destination="docker_gpu"/>` routing entry, and a preflight that the
  destination resolves to a GPU node (nvidia-smi reachable in-container). Until committed, KegAlign
  would silently land on CPU.

---

## Open questions (remaining genuinely-open ops items)

1. **kegalign wrapper provenance.** Confirm the exact external repo / tool_id + version of the
   already-deployed KegAlign wrapper on the target, and that the `docker_gpu` destination + tool
   routing are in place (Decision 3 / prerequisite gate). Until confirmed, GPU deployment is open.
2. **bedToBigBed / gff3ToGenePred / genePredToBed / faToTwoBit on target.** Not found in
   tools-iuc/ucsc_tools — confirm present on the 26.1 instance; if absent, fold into the `ucsc_kent`
   suite (cheap — same container).
3. **TOGA digest.** Resolve the concrete `ghcr.io/hillerlab/toga@sha256:…` digest to pin (Decision 12);
   mirror it if registry availability is a concern.
4. **strain→accession map provenance (WF-K).** Confirm the canonical source of the per-strain GenBank
   accession map (origin: `ACC[]` in run_phase_k.sh; no script produces it) — supply as a committed
   input for test_data.
