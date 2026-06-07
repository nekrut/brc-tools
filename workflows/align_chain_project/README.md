# WF-C `align_chain_project` (Phase C: chains + Liftoff + TOGA2 C.4)

Pairwise alignment -> UCSC chain pipeline (cleaned + reciprocal-best chains)
-> annotation projection (Liftoff + TOGA2 v2.0.8).

This is the most complex workflow in the port. Two internal blocks share an
intra-workflow data dependency (the C.4 TOGA2 branch consumes the C.1–3 cleaned
chains), which is why they live in one workflow.

## C.4 model (TOGA2 v2.0.8 modernization)

The old v3 pipeline used TOGA1 with `--filter_bed needs_cesar2.bed`, so
phase_c2_triage routed only the hard-tail genes to TOGA/CESAR2. **TOGA2 v2.0.8
(`toga2.py run`) has no `--filter_bed`**: it projects and classifies the FULL
reference annotation itself (`--ref_annotation` = the whole anchor BED12) through
the cleaned chain and emits its own orthology + loss outputs. The triage-subset
handoff therefore no longer applies. The current C.4 dataflow is:

1. **Liftoff** projects the anchor annotation onto the query; **phase_c2_triage**
   splits it into `liftoff_clean.gff3` (the clean majority, kept as-is) plus an
   **informational** `triage.tsv` / `needs_cesar2.bed` / `summary.json`. The BED
   is no longer consumed downstream — it is diagnostic only.
2. **TOGA2** (`toga2` step) runs `toga2.py run` over the FULL anchor annotation
   (anchor_prep `bed12` + `isoforms`) through the cleaned chain + ref/query 2bit,
   producing `query_annotation.bed`, `query_genes.bed`,
   `orthology_classification.tsv`, `loss_summary.tsv`.
3. **phase_c4_merge** (`use_toga: yes`) folds Liftoff-clean genes together with
   TOGA2's calls, tagging the rescued set with TOGA2 intactness (from
   `loss_summary.tsv`) and orthology class (from `orthology_classification.tsv`).

### TOGA2 output -> phase_c4_merge mapping (verified against `toga2:local` source)

All four final files land directly in the run's `--output toga_out/` dir
(`toga_main.py`):

| TOGA2 file | format (verified) | merge use |
|------------|-------------------|-----------|
| `loss_summary.tsv` | `level<TAB>entry<TAB>status`; level ∈ {PROJECTION,TRANSCRIPT,GENE}; PROJECTION `entry` = `<transcript>#<chain>`; status ∈ {FI,I,PI,UL,M,L,PG,PP,N} | intactness per rescued gene (matched by `<t_transcript>#` prefix) |
| `orthology_classification.tsv` | `t_gene<TAB>t_transcript<TAB>q_gene<TAB>q_transcript<TAB>orthology_class`; class ∈ {one2one,one2many,many2one,many2many,one2zero} | reference↔query gene linkage + orthology class |
| `query_annotation.bed` | BED12; col4 = projection id `<transcript>#<chain>` | transcript-level query coords (optional) |
| `query_genes.bed` | BED (≥4 col); col4 = final query gene id (== `q_gene`) | gene-level query coords -> CESAR2 GFF lines |

These column layouts match the TOGA1-era loaders in `phase_c4_merge.py`
unchanged (level/entry/status; t_gene/.../orthology_class; `#` projection
separator), so the TOGA1->TOGA2 modernization needed no field renames in the
merge — only re-verification against the real image, plus a TOGA2-format test.

### TOGA2 is GPU-independent but heavy (container-only)

`toga2:local` is the only place TOGA2 runs: a ~20 GB image
(`FROM continuumio/anaconda3` + tensorflow, rust, Nextflow, CESAR2). TOGA2 is
**GPU-independent** (CPU classifier + CESAR2), but it is **Nextflow-driven and
CPU/IO heavy** and re-aligns exons over REAL genome alignments — it does not run
on toy inputs. The image has **no published Docker tag** (local-only; rebuild
from the upstream apptainer.def / Dockerfile or pin a digest once published).
A real C.4 TOGA2 run needs: a genuine anchor/query genome pair (soft-masked
FASTA -> 2bit), a cleaned anchor->query chain, the anchor BED12 + isoforms, and
enough disk for the Nextflow work dir (well beyond the synthetic-test footprint).

File: `align_chain_project.gxwf.yml` (gxformat2, `class: GalaxyWorkflow`).

## Inputs

| input | type | feeds |
|-------|------|-------|
| `masked_fastas` | list (per strain) | `pair_strains` (C.1); per-pair target/query FASTAs for the chain block |
| `sizes` | list (per strain `.sizes`) | axtChain / chainPreNet / chainNet |
| `anchor_gff3s` | list (per anchor `{A}.fixed.gff3`) | `anchor_prep` |
| `assemblies` | list (per strain, unmasked) | Liftoff (full map-over run) |
| `anchor_assembly` | data | Liftoff gene-source FASTA (template) |
| `anchor_fixed_gff3` | data | Liftoff `-g` (template) |
| `anchor_bed12` | data | triage `--reference-bed`, merge `--ref-bed` (template) |
| `query_assembly` | data | Liftoff target (template) |
| `query_masked` | data | triage `--query-fasta` (template) |
| `query_name` | string | triage label / merge output naming |
| `liftoff_features` | data | Liftoff `-f` (protein_coding_gene / ncRNA_gene / pseudogene) |
| `core_identity_min` / `core_coverage_min` / `family_identity_min` / `subtelomere_bp` | params | phase_c2_triage thresholds (Decision 9, exposed) |

Anchor chrom reconciliation is assumed done upstream — anchors enter as already
reconciled `{A}.fixed.gff3` (per the plan, reconciliation uses the `chrom_rename`
TSV and need only cover ref/anchors).

## Steps: our wrappers vs IUC

OUR loaded wrappers (exact tool_ids):
- `pair_strains` — C.1 NxN unordered pair builder -> `list:paired` (`{A}__vs__{B}`, forward=A, reverse=B).
- `chainStitchId` — the one chain tool not in IUC (used twice: cleaned + rbest).
- `anchor_prep` — `{A}.bed12` (gffread `--bed` + protein-coding filter) + `{A}.isoforms.tsv`.
- `phase_c2_triage` — 8-rule triage -> `liftoff_clean.gff3` + `needs_cesar2.bed` + `triage.tsv` + `summary.json`.
- `toga2` — TOGA2 v2.0.8 (`toga2.py run`) projection over the FULL anchor BED12 (container-only `toga2:local`; see "C.4 model").
- `phase_c4_merge` — provenance merge; **`use_toga: yes`**, folding Liftoff-clean + TOGA2 intactness/orthology (output contract unchanged; loaders short-circuit if TOGA2 outputs are absent).

IUC / external tools used (all resolve in the running Galaxy EXCEPT the GPU aligner):
- `ucsc_axtchain` (482+galaxy2), `ucsc_chainsort`, `ucsc_chainprenet`, `ucsc_chainnet`,
  `ucsc_netchainsubset`, `ucsc_chainswap` (all 482+galaxy0) — **installed, resolve cleanly**.
- `liftoff` (1.6.3+galaxy0) — **installed, resolves cleanly**.
- `kegalign` + `batched_lastz` (richard-burhans/galaxytools) — the C.1 GPU aligner.
  **NOT installed on this CPU instance; require a GPU job destination (`docker_gpu`).**
  This step CANNOT be import-validated or run here — it is the production/GPU path
  (Decision F1). See below.

### Aligner decision (F1): KegAlign-GPU is the only viable C.1 aligner

The IUC `lastz` wrapper exposes only bam/maf/blastn/paf/general/differences output —
**no axt and no psl** — so its output cannot feed `axtChain` (`in_aln` accepts only
axt/psl). KegAlign emits axt natively, via its two-stage GPU pipeline:

1. `kegalign` (GPU) — target+query FASTA, `output_options|format|format_selector=axt`
   -> a `data_package.tgz` of LASTZ segments.
2. `batched_lastz` — consumes that tgz, runs the LASTZ commands -> the final **axt**
   (`format=auto` -> axt).

Both tools need a GPU destination and are NOT installed here, so C.1 is the
unvalidated production path. Everything downstream of the axt (the chain block +
projection) IS installed and resolves. The task's `kegalign_gpu` label maps to the
published wrapper tool id **`kegalign`** (+ `batched_lastz` for the axt stage).

## Aligner / chain command provenance

Matches `impl/03_align_chain.sh`:
- KegAlign (GPU, the only viable aligner — F1): `--strand both --hsp_threshold 5000
  --gapped_threshold 6000 --inner 2000 --ydrop 15000 --format axt`, mapped onto the
  richard-burhans wrapper sections: `sequence_options|strand_selector=both`,
  `ungapped_extension_options|hspthresh=5000`, `gapped_extension_options|gappedthresh=6000`,
  `gapped_extension_options|ydrop=15000`, `interpolation_options|inner=2000`,
  `output_options|format|format_selector=axt`.
- lastz (CPU): NOT used — its wrapper has no axt output (F1).
- chain build: `axtChain -linearGap=loose` via `in_aln`/`in_target`/`in_query` +
  `linear_gap_options|linear_gap=loose` (the wrapper takes fasta directly; no -faT/-faQ).
- cleaned chain: axtChain -> chainSort -> chainPreNet -> chainNet -> netChainSubset -> chainStitchId
- rbest chain: chainSwap -> chainSort -> chainNet -> netChainSubset -> chainStitchId -> chainSwap -> chainSort

C.4 (`impl/04_annotate_project.sh`, modernized for TOGA2 v2.0.8): liftoff
`-copies -sc 0.95` -> phase_c2_triage (-> `liftoff_clean.gff3` + informational
triage) and, in parallel, `toga2.py run` over the FULL anchor BED12; both feed
phase_c4_merge (`use_toga: yes`).
Liftoff corrected param names: `target_fasta` / `reference_fasta` / `annotation` +
`chromosome_mapping|copy_detection|find_copies=true` +
`chromosome_mapping|copy_detection|copy_min_identity=0.95`; output `liftoff_gff`.
**Decision F2:** the IUC liftoff `-f feature_types` is buggy (templates the literal
string as a file path), so the feature filter is dropped and Liftoff's default `gene`
mode is used. `liftoff_features` is kept as an input but intentionally NOT wired.

## Outputs

- `cleaned_chain` — `{A}.{B}.cleaned.chain` (-> WF-J, WF-K). The B->A direction is a downstream `chainSwap` (not materialised here).
- `rbest_chain` — `{a}.{b}.rbest.chain` (-> WF-E `phase_e_rbest_overlap`).
- `pairwise_axt` — pairwise AXT (-> WF-I), `{A}__vs__{B}` with A<B.
- `anchor_bed12_out` / `anchor_isoforms_out` — `{A}.bed12` / `{A}.isoforms.tsv`.
- `merged_annotation_gff3` / `classification_tsv` — per-(anchor,query) (-> WF-E, WF-F).

## RUNNABILITY

- **KegAlign-GPU is the only viable C.1 aligner (F1).** The IUC lastz wrapper cannot emit axt/psl, so it can't feed axtChain; KegAlign (`kegalign` -> `batched_lastz`) emits axt natively. KegAlign needs a `docker_gpu` job destination that the documented `job_conf.xml` here does not have, and neither `kegalign` nor `batched_lastz` is installed on this CPU instance. **C.1 therefore cannot be import-validated or run here — it is the production/GPU path.** All downstream steps (chains, liftoff, triage, merge) ARE installed and resolve.
- **TOGA2 C.4 wired (`use_toga: yes`).** The `toga2` step runs `toga2.py run` over the FULL anchor annotation (no `needs_cesar2.bed` filter) and its four outputs feed `phase_c4_merge`. `toga2` is container-only (`toga2:local`, ~20 GB, GPU-independent but Nextflow/CPU-heavy) and does not run on toy inputs, so the C.4 TOGA2 leg is NOT exercised in the synthetic CI here — `phase_c4_merge` itself is validated end-to-end on real TOGA2-format inputs (see its planemo test "TOGA2-merge path"). The chain/2bit plumbing into `toga2` resolves; a real projection requires a genuine genome pair + cleaned chain (see "C.4 model" above).
- **Tool resolution (verified by `POST /api/workflows from_path` + `/api/tools/{id}` probe):** all steps resolve EXCEPT `kegalign` + `batched_lastz` (404, GPU path not installed — EXPECTED per F1). `planemo workflow_lint` reports `All tool ids appear to be valid`.

## Known limitations (gxformat2 could not express these cleanly — relink in the editor)

1. **Per-pair `.sizes` lookup (chain block).** axtChain / chainPreNet / chainNet
   each need the **target** and **query** `.sizes` for *that specific pair*. The
   `pair_strains` `list:paired` element carries only the two FASTAs, not the
   sizes, and gxformat2 has no construct to join the flat `sizes` collection to
   the per-pair identity. The steps are wired to the whole `sizes` collection as
   a placeholder; this is the single biggest map-over gap and needs either a
   manual relink in the Galaxy editor or a tiny "pair sizes" helper tool that,
   like `pair_strains`, emits a `list:paired` of `.sizes` keyed `{A}__vs__{B}`.
   Same concern for axtChain's separate target/query FASTAs (wired to the paired
   collection; the editor must point target=forward, query=reverse).

2. **lastz over a `list:paired`.** Encoded as `target: pairs / query: pairs`
   (both the paired collection) on the assumption the IUC lastz wrapper exposes
   distinct target/query inputs that Galaxy fills from the forward/reverse slots.
   Verify the real wrapper's input names once installed; the conventional ids
   here are best-effort and the param keys (`masking`, `hspthresh`, …) follow
   lastz CLI naming but may differ from the wrapper's `name=` attributes.

3. **C.4 anchor x query cross-product.** The real projection is a cross-product
   (each anchor projected onto every non-anchor query) producing a `list:list`
   (outer=anchor, inner=query). gxformat2 cannot enumerate a cross-product, so
   C.4 is encoded as a **single-anchor / single-query template** (scalar
   `data`/`string` inputs). To run the full matrix, drive it map-over from a
   parent workflow (e.g. a `__CROSS_PRODUCT_NESTED__` over anchors x queries) or
   wire the map-over in the editor. `anchor_prep` *is* mapped over the
   `anchor_gff3s` list correctly.

4. **rbest element_identifier.** Phase E (`phase_e_rbest_overlap`) keys strains
   off the chain filename stem, so the rbest output element id MUST resolve to
   `{a}.{b}`. Coming off the `pair_strains` `{A}__vs__{B}` identifiers this needs
   a relabel (e.g. `__RELABEL_FROM_FILE__` or editor rename) — not expressible
   inline here.

5. **IUC chain-tool input/param names are conventional guesses** (`axt`,
   `target_fasta`, `target_sizes`, `out_chain`, `linearGap`, …). Re-verify
   against each installed wrapper's actual `<param name=...>` and adjust the
   `in:`/`state:` keys; the topology (step order + connections) is the
   load-bearing part and is correct per impl.

## Lint

`planemo workflow_lint align_chain_project.gxwf.yml` -> **0 ERROR**, `CHECK: All
tool ids appear to be valid`. Remaining WARNINGs are cosmetic: per-step
annotations, missing test cases, and one strict-schema note ("Extra inputs are
not permitted at name") for the standard gxformat2 top-level `name` key (kept so
the workflow is named).
