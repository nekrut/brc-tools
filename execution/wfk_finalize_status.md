# WF-K (ucsc_hub) finalize — latent sort bug fixed

**Verdict: FIXED + VERIFIED.** The latent bedToBigBed unsorted-input bug in
`workflows/ucsc_hub/ucsc_hub.gxwf.yml` is resolved. Three `sort1` steps added
(bigChain / bigLink / annotation branches), mirroring the existing
`sort_bigmaf_bed`. planemo lint clean (no ERRORs). Re-imported into Galaxy
26.1.rc1 — ZERO tool_errors on all 33 steps. Sorted bigChain path re-run on
synthetic 2-record input: produces valid `.bb` (bigBed magic), and the unsorted
path was reproduced to FAIL ("not sorted at line 2"), proving the fix is
load-bearing.

Date: 2026-06-07. Galaxy http://localhost:8080. NOT committed (per instruction).

## 1. Sort steps added (the fix)

The committed YAML only wired `sort_bigmaf_bed` (sort1) before `bigmaf_bb`. The
bigChain, bigLink, and annotation BEDs fed `bedToBigBed` UNSORTED. bedToBigBed
REQUIRES `sort -k1,1 -k2,2n` input. Added three sort1 steps, each with state
identical to `sort_bigmaf_bed` (column 1 alpha ASC, then column_set col 2 num ASC):

| new step          | input source                       | feeds        | -type   |
|-------------------|------------------------------------|--------------|---------|
| `sort_bigchain_bed` | `chain_to_bigchain/bigchain_bed` | `bigchain_bb`| bed6+6  |
| `sort_biglink_bed`  | `chain_to_bigchain/biglink_bed`  | `biglink_bb` | bed4+1  |
| `sort_annot_bed`    | `genepred_to_bed/output`         | `annot_bb`   | bed12   |

Rewired the three downstream bedToBigBed `in.bed` from the raw producer output to
the new `sort_*/out_file1`. All sort steps use `tool_id: sort1` (Galaxy built-in),
matching the existing `sort_bigmaf_bed` exactly.

**build_hub_bb selection/orthogroup BEDs: NO external sort needed.** Verified in
`tools/build_hub_bb/build_hub_bb.py`: it sorts its BEDs in-process
(`lines.sort(key=lambda x:(x[0],x[1]))` at lines 259 for selection and 304 for
orthogroup) BEFORE its internal bedToBigBed. So the build_hub_bb branch was never
affected by this bug and needs no sort step. No change made there.

## 2. planemo workflow_lint

```
$ planemo workflow_lint workflows/ucsc_hub/ucsc_hub.gxwf.yml
.. WARNING: Workflow does not specify a creator.
.. WARNING: Workflow does not specify a license.
.. WARNING: Workflow missing test cases.
.. CHECK: All tool ids appear to be valid.
```
No ERRORs. Only the benign creator / license / missing-test-cases advisories.
"All tool ids appear to be valid" (the new sort1 ids resolve).

## 3. Re-import — ZERO tool_errors

`POST /api/workflows {"from_path": ".../ucsc_hub.gxwf.yml"}` ->
StoredWorkflow id `1e8ab44153008be8`, latest_workflow_id 16. Downloaded the
materialized workflow and inspected `tool_errors` on every step:

- 33 total steps (16 input/param nodes + 17 tool nodes).
- **TOTAL tool_errors: 0.**
- All 17 tool steps resolved: process_maf, maf_to_bigmaf_bed,
  sort_bigmaf_bed/sort_bigchain_bed/sort_biglink_bed/sort_annot_bed (sort1),
  bigmaf_bb/bigchain_bb/biglink_bb/annot_bb (ucsc_bedtobigbed),
  chain_to_bigChain, ucsc_gff3togenepred, ucsc_genepredtobed, build_hub_bb,
  ucsc_fatotwobit, build_genomes_txt, ucsc_hubcheck.

The three newly added sort1 steps imported with no tool_errors.

## 4. Sorted bigChain path — valid .bb (optional gate, DONE)

Ran the exact now-wired path (chain_to_bigChain -> sort -k1,1 -k2,2n ->
bedToBigBed) on a synthetic 2-chain input crafted to put two chains on the SAME
target chrom with out-of-order starts (start 500 emitted before start 0), so the
sort is genuinely load-bearing. Used the macros-pinned kent biocontainer
`quay.io/biocontainers/ucsc-bedtobigbed:482--hdc0a859_0` and
`v3/tools/bigChain.as`.

- **UNSORTED -> bedToBigBed FAILS** (reproduces the latent bug):
  `same_bc.bed is not sorted at line 2. Please use the -sort option...`
  No `.bb` produced.
- **SORTED -> bedToBigBed SUCCEEDS**:
  ```
  pass1 - making usageList (1 chroms)
  pass2 - checking and writing primary data (2 records, 12 fields)
  ```
  Output `same_SORTED.bb` (13726 B), first 4 bytes `eb f2 89 87` = bigBed magic
  0x8789F2EB. VALID.

(Note: a 2-chrom / 1-record-per-chrom unsorted BED happened to pass bedToBigBed —
the strict check is within-chrom start ordering, which the same-chrom test above
exercises. Real multi-chain-per-chrom data WILL hit the failure, which is exactly
why the sort is required.)

Artifacts under `/tmp/wfk_finalize/`.

## Files changed

- `workflows/ucsc_hub/ucsc_hub.gxwf.yml` — added `sort_bigchain_bed`,
  `sort_biglink_bed`, `sort_annot_bed` (sort1) and rewired bigchain_bb /
  biglink_bb / annot_bb to consume the sorted outputs. (ONLY file changed.)

NOT git committed (per instruction). No other efforts touched
(align_chain_project, anchor_prep, iqtree3, toga2 untouched).
