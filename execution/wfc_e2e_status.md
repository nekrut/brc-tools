# WF-C `align_chain_project` pass-1 — end-to-end TOOL CHAIN proof

**Date:** 2026-06-07
**Galaxy:** 26.1.rc1 @ http://localhost:8080
**Mode:** lastz-CPU (no GPU/KegAlign), Liftoff-only (no TOGA2)
**Driver:** bioblend 1.9.0, tool-by-tool via `tools.run_tool` (NOT the gxformat2 map-over)
**History:** `WFC_e2e_proof` (id `1e8ab44153008be8`)

## Verdict

The WF-C pass-1 tool chain **composes end-to-end on real data, all 18 jobs OK**, with
**one real blocker found** (the IUC lastz wrapper cannot emit AXT/PSL — see Finding F1) that
required a bridge, and **one IUC wrapper bug** (liftoff `-f` — Finding F2). cleaned.chain and
rbest.chain are both valid chain files; the merged annotation + classification.tsv are non-empty
and carry a LIFTOFF_CLEAN-tagged gene.

## Test data (tiny, real)

P. vivax mitochondrion (~6 kb, highly conserved across strains → real homology):
- **A / target / anchor** = MHC087 MIT `CM078886.1` (5988 bp), renamed `chrMIT_A`
- **B / query**          = PAM MIT `CASCJQ010000016.1` (5991 bp), renamed `chrMIT_B`

Extracted with python from `data/raw/*.fa.gz` (host has no samtools). `.sizes` derived by hand.
Anchor GFF3 synthesized: 3 protein-coding genes placed on **real ORFs** found in chrMIT_A
(ATG-start, in-frame, terminal stop, no internal stop), top-level type `gene` (see F2).

## A. Alignment + chains (one pair A,B) — ALL OK

| step | tool_id (installed) | job | state |
|------|--------------------|-----|-------|
| lastz (wrapper, MAF) | `…/lastz/lastz_wrapper_2/1.04.52+galaxy0` | c0103d8755305f16 | ok |
| lastz (CPU, AXT bridge — see F1) | `lastz` binary, run on host | — | ok (2 axt blocks) |
| axtChain | `…/ucsc_axtchain/482+galaxy2` | ceefdfd6cf7aa5ad | ok |
| chainSort (clean) | `…/ucsc_chainsort/482+galaxy0` | e25cb9ff171a4ef6 | ok |
| chainPreNet | `…/ucsc_chainprenet/482+galaxy0` | 4eb81b04b33684fd | ok |
| chainNet | `…/ucsc_chainnet/482+galaxy0` | 5761546ab79a71f2 | ok |
| netChainSubset | `…/ucsc_netchainsubset/482+galaxy0` | 68013dab1c13fb37 | ok |
| chainStitchId (cleaned.chain) | `chainStitchId` | 60e680a037f41974 | ok |
| chainSwap r1 | `…/ucsc_chainswap/482+galaxy0` | 6d9affd96770ffb9 | ok |
| chainSort r1 | `…/ucsc_chainsort` | 55504e7a2466a2e3 | ok |
| chainNet r (B,A sizes) | `…/ucsc_chainnet` | e38f593eae81d119 | ok |
| netChainSubset r | `…/ucsc_netchainsubset` | c333314861e68c5c | ok |
| chainStitchId r | `chainStitchId` | ba1915f3923e3bf1 | ok |
| chainSwap r2 | `…/ucsc_chainswap` | bd0beca16aa307c6 | ok |
| chainSort (rbest.chain) | `…/ucsc_chainsort` | dfd15528ee538abe | ok |

**Chain-file validity:**
- `cleaned.chain`: 2 chains, 13-field `chain` headers, 4 block lines.
  `chain 474352 chrMIT_A 5988 + 0 5066 chrMIT_B 5991 + 922 5991 1` (+ a 2nd chain, score 86089).
- `rbest.chain`:    2 chains, 13-field headers, 4 block lines; target=chrMIT_A query=chrMIT_B
  after swap-back (correct orientation for Phase E).
Both pass `head -1 | awk '$1=="chain" && NF==13'` (the impl validator).

## B. Annotation projection (anchor→query, Liftoff-only) — ALL OK

| step | tool_id | job | state |
|------|---------|-----|-------|
| anchor_prep | `anchor_prep` | 1efe9eb0bff40152 | ok |
| liftoff | `…/liftoff/1.6.3+galaxy0` | a3ff968b01c9046c | ok |
| phase_c2_triage | `phase_c2_triage` | a5e7909db9879e3a | ok |
| phase_c4_merge (use_toga=no) | `phase_c4_merge` | 44def14be693a1c2 | ok |

- **anchor_prep** → `chrMIT_A.bed12` (3 genes) + isoforms.tsv (gene→gene.t1).
- **liftoff** (`-copies -sc 0.95`, find_copies=true) → all 3 genes lifted onto chrMIT_B;
  gene3 `valid_ORFs=1 coverage=1.0 sequence_ID=1.0`, gene1/gene2 frame-broken on query.
- **phase_c2_triage** (subtelomere_bp=0, see note) → triage.tsv: gene3=**LIFTOFF_OK**,
  gene1/gene2=CESAR2_FALLBACK; summary `liftoff_clean=1, needs_cesar2=2`;
  liftoff_clean.gff3 contains gene3 (non-empty).
- **phase_c4_merge** (toga=no, empty toga dir) →
  - `B.annotation.gff3` **non-empty**: gene3 with `source=liftoff;intactness=I`.
  - `B.classification.tsv` **non-empty**, header + 4 rows; the LIFTOFF_CLEAN row:
    `gene3  gene3  liftoff  I  chrMIT_B  2920  3711  -  liftoff_clean`.

## FINDINGS / BLOCKERS

### F1 (BLOCKER, lastz→axtChain): IUC LASTZ wrapper cannot emit AXT or PSL
`devteam/lastz/lastz_wrapper_2/1.04.52` exposes output formats:
`bam, general_def, general_full, maf, blastn, paf, differences` — **no axt, no psl**.
But `ucsc_axtchain.in_aln` accepts only `['axt','psl']`. So the workflow's
`lastz/output -> axtchain/axt` edge **does not type-check with this wrapper**.
The wrapper *runs* fine (MAF job ok, score 474147, real homology) but its output cannot feed
axtChain. The impl script (`03_align_chain.sh`) uses the **raw `lastz` binary** with
`--format=axt`, which the Galaxy wrapper does not surface.
**Bridge used for this proof:** generated the AXT with the same lastz binary
(`…/_conda/pkgs/lastz-1.04.52-h7b50bb2_1/bin/lastz`, the binary the wrapper itself uses) with the
exact impl flags `--masking=50 --hspthresh=4500 --gappedthresh=6000 --inner=2000 --ydrop=15000
--format=axt`, then uploaded as an `axt` dataset → axtChain consumed it cleanly.
**Fix options for the .ga:** (a) request/patch an IUC lastz wrapper that exposes `--format=axt`
(or `psl`); (b) keep KegAlign (its `--output_format axt` is native) as the real C.1 and treat the
IUC lastz wrapper as not-viable for this chain; (c) add a tiny maf→axt (or paf→psl) converter
step. As-is, **C.1→C.2 cannot run one-click with the installed IUC lastz wrapper.**

### F2 (BUG, IUC liftoff wrapper): `-f feature_types` passes the literal string as a FILE path
`liftoff/1.6.3+galaxy0` templates `-f "${feature_types}"` where `feature_types` is a free-text
param, but Liftoff's `-f` expects a **file** of feature types → `FileNotFoundError:
'protein_coding_gene'`. The workflow input `liftoff_features` (a `data` file) is therefore **not
wireable to this wrapper at all** (the wrapper has no data input for `-f`; only inline text).
**Workaround for this proof:** dropped `-f` and used top-level GFF type `gene` (Liftoff's default
liftable type). triage/merge both accept `gene` (their `GENE_TYPES` set includes
`gene, protein_coding_gene, ncRNA_gene, pseudogene`), so downstream is unaffected.
**Fix:** patch the IUC wrapper to write `feature_types` to a temp file and pass that path
(`echo "$feature_types" | tr ',' '\n' > ft.txt; -f ft.txt`), OR keep all anchor genes as
top-level `gene` and omit `-f`. The .gxwf.yml's `feature_types: liftoff_features` edge is
currently non-functional.

### F3 (minor, merge ID namespace): BED12 name=transcript vs clean-GFF ID=gene
`phase_c4_merge` keys the reference gene set off the BED name column. `anchor_prep` emits BED12
with the **transcript** id (`gene3.t1`) in the name column, while the clean GFF gene ID is
`gene3`. Result: classification.tsv lists `gene3` (from the GFF, correctly tagged
`liftoff/I/liftoff_clean`) **and** three `*.t1` "unprojected/M" rows (from the BED names that never
match a GFF gene id). The LIFTOFF_CLEAN tagging is correct; the spurious `.t1` M-rows are a
cosmetic id-mismatch. Worth aligning anchor_prep BED name ↔ merge ref-id keying.

## CORRECTED IUC PARAM NAMES (WF-B-style fix list for the .ga)

The `.gxwf.yml` `in:`/`state:`/`out:` keys were conventional guesses. Verified against
`/api/tools?io_details`; corrections:

| step | .gxwf.yml key | CORRECT key (installed wrapper) |
|------|---------------|----------------------------------|
| **lastz** | `target` | `source\|target` (with `source\|ref_source=history`) |
| lastz | `query` | `query` ✓ |
| lastz | `masking: 50` | **no such param** — wrapper has no `--masking`; masking comes from input softmask only |
| lastz | `hspthresh: 4500` | `hsp\|hsp_method\|hsp_method_selector=x` + `hsp\|hsp_method\|x\|hspthresh` |
| lastz | `gappedthresh` | `gap_ext\|gappedthresh` |
| lastz | `inner` | `interpolation\|inner` |
| lastz | `ydrop` | `gap_ext\|ydrop` |
| lastz | `format: axt` | `output_format\|out\|format` — **`axt` NOT available** (F1); opts: bam/general_def/general_full/maf/blastn/paf/differences |
| lastz | strand | `where_to_look\|strand` = `--strand=both` |
| lastz | out `output` | `output` ✓ (format tabular) |
| **axtChain** | `axt` | `in_aln` |
| axtChain | `target_fasta` | `in_target` (ext **fasta**, not 2bit) |
| axtChain | `query_fasta` | `in_query` (ext fasta) |
| axtChain | `linearGap: loose` | `linear_gap_options\|linear_gap = loose` |
| axtChain | `faT: true` / `faQ: true` | **no such params** — wrapper takes fasta directly; drop both |
| axtChain | out `out_chain` | `out` (2nd output `out_details` gated by `details_output` bool) |
| **chainSort** | `input` | `in_chain` |
| chainSort | out `output` | `out` |
| **chainPreNet** | `input` | `in_chain` |
| chainPreNet | `target_sizes` | `target_reference_index_source\|target_reference_index_source_selector=history` + `…\|in_tar_ref_index` |
| chainPreNet | `query_sizes` | `query_reference_index_source\|…_selector=history` + `…\|in_que_ref_index` |
| chainPreNet | out `output` | `out` |
| **chainNet** | `input` | `in_chain` |
| chainNet | `target_sizes`/`query_sizes` | same conditional pattern as chainPreNet (`in_tar_ref_index`/`in_que_ref_index`) |
| chainNet | out `target_net` | `targetNet` (also `queryNet`); format `ucsc.net` |
| **netChainSubset** | `net` | `in_net` (ext `ucsc.net`) |
| netChainSubset | `chain` | `in_chain` |
| netChainSubset | out `output` | `out` |
| **chainSwap** | `input` | `in_chain` |
| chainSwap | out `output` | `out` |
| **chainStitchId** | `input` / out `output` | `input` / `output` ✓ (our wrapper, correct) |
| **anchor_prep** | `input` / `bed12`/`isoforms` | ✓ correct |
| **liftoff** | `target` | `target_fasta` |
| liftoff | `reference` | `reference_fasta` |
| liftoff | `gff` | `annotation` |
| liftoff | `feature_types` | `alignment\|feature_types` (but **broken**, F2) |
| liftoff | `copies: true` | `chromosome_mapping\|copy_detection\|find_copies = true` |
| liftoff | `sc: 0.95` | `chromosome_mapping\|copy_detection\|copy_min_identity = 0.95` |
| liftoff | out `output` | `liftoff_gff` (also `unmapped`) |
| **phase_c2_triage** | all keys | ✓ correct (`liftoff_gff`,`query_fasta`,`reference_bed`,`query_name`,`core_*`,`family_identity_min`,`subtelomere_bp`; out `triage_tsv`/`needs_cesar2_bed`/`liftoff_clean_gff3`/`summary_json`). `family_list` is an extra optional data input. |
| **phase_c4_merge** | `query`/`liftoff_clean`/`ref_bed` | ✓ correct |
| phase_c4_merge | `toga: {use_toga: "no"}` | `toga\|use_toga = no` ✓ (flat key form) |
| phase_c4_merge | out | `annotation_gff3`/`classification_tsv` ✓ |

(`pair_strains` tool_id is plain `pair_strains` — the `__pair_strains__` form is not the
installed id; the .gxwf.yml already uses `pair_strains`, which is correct.)

## MAP-OVER / CROSS-PRODUCT GAPS still blocking one-click run

1. **Per-pair `.sizes` join (biggest gap).** chainPreNet/chainNet need the *specific* pair's
   target+query `.sizes` via the `history`-source conditional (`in_tar_ref_index`/
   `in_que_ref_index`). gxformat2 cannot join the flat `sizes` list to the `pair_strains`
   `list:paired` element identity. Needs a "pair sizes" helper emitting a `list:paired` of
   `.sizes` keyed `{A}__vs__{B}`, or editor relink. Same for axtChain `in_target`/`in_query`
   (must point target=forward, query=reverse of the pair). **Confirmed required** — the tools
   take two separate positional size/fasta inputs that have no per-pair source in the YAML.
2. **rbest sizes are swapped.** The rbest `chainNet` correctly needs target=B.sizes, query=A.sizes
   (opposite of the cleaned pass). A per-pair-sizes helper must expose both orientations, or the
   editor must swap the two `in_*_ref_index` inputs on the rbest chainNet.
3. **rbest element_identifier relabel.** Output came out keyed to chrMIT_A/chrMIT_B; Phase E keys
   strains off the filename stem `{a}.{b}`. From `pair_strains` `{A}__vs__{B}` ids this still needs
   a relabel — not expressible inline.
4. **C.4 anchor × query cross-product.** Encoded as single-anchor/single-query template. The real
   run is a cross-product (each anchor × every query) → `list:list`. Still needs a parent
   `__CROSS_PRODUCT_NESTED__` or editor map-over. `anchor_prep` over `anchor_gff3s` is fine.
5. **F1/F2 (above) are NEW one-click blockers** beyond the README's known limitations: the IUC
   lastz wrapper has no axt output, and the IUC liftoff `-f` is unusable. Both must be resolved
   (wrapper patch or aligner choice) before C.1→C.2 and the liftoff feature filter run one-click.

## Notes on honesty / deviations
- `subtelomere_bp=0` was used for triage so a gene could pass (the whole 6 kb MIT contig is inside
  any realistic subtelomere flank; with the default 100 kb **every** gene flags R7, which is
  correct behavior for a tiny contig, not a tool failure). With bp=0, gene3 legitimately passed all
  8 rules → LIFTOFF_OK. This is a test-data artifact of using a 6 kb contig, not a workflow defect.
- The lastz **wrapper** job was run (proves the aligner step executes) but its MAF output cannot
  feed axtChain (F1); the AXT that fed the chain came from the lastz **binary** with the impl flags.
  This is the one place the proof steps outside a Galaxy job, and it is forced by F1.
- No git commit performed. tools/toga2 untouched.
