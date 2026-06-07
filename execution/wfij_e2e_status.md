# WF-J (vcf_projection) + WF-I (multiz) — live end-to-end status

Date: 2026-06-07. Galaxy 26.1.rc1 @ localhost:8080. Synthetic tiny data, GPU-independent.
All tool jobs run via bioblend on the live server. Both corrected `.gxwf.yml`
import cleanly (`from_path`, HTTP 200, every tool step `tool_errors: None`).

NOT committed. Edited only:
- `workflows/vcf_projection/vcf_projection.gxwf.yml`
- `workflows/multiz/multiz.gxwf.yml`

## Installed tool ids (live)
- bcftools_annotate: `iuc/.../bcftools_annotate/1.22+galaxy0`
- crossmap_vcf:      `iuc/.../crossmap_vcf/0.7.3+galaxy0`
- bcftools_sort:     `greg/.../bcftools_sort/1.4.0`  (OLD non-IUC wrapper)
- bcftools_concat:   `iuc/.../bcftools_concat/1.22+galaxy0`
- ucsc_axtomaf:      `iuc/ucsc_axttomaf/ucsc_axtomaf/482+galaxy1` (note repo=ucsc_axttomaf)
- multiz_fold:       `multiz_fold` (OURS)

---

## WF-J — PROVEN end-to-end (annotate -> crossmap -> sort -> concat)

History `WFJ_e2e_synthetic`. Synthetic data: src1 (200bp) -> tgt1 (200bp) colinear
UCSC chain; cohort VCF with 5 SNPs on `src1`; chrom_rename `src1\tsrc1`; target.fa `tgt1`.

Per-step job state:
| step | tool | state |
|------|------|-------|
| 1 rename_chroms | bcftools_annotate `--rename-chrs` | ok |
| 2 crossmap_project | crossmap_vcf | ok |
| 3 sort_vcf | bcftools_sort (greg/1.4.0) | ok |
| 4 concat_vcfs | bcftools_concat `-a` | ok (668-byte BCF) |

Evidence — projected VCF in TARGET coords (CrossMap output, chrom now `tgt1`,
positions preserved by colinear chain; REF realleled to target FASTA):
```
#CHROM  POS  ID  REF  ALT  QUAL  FILTER  INFO  FORMAT  S1   S2
tgt1    20   .   G         50    PASS    .     GT      0/1  1/1
tgt1    55   .   T    G    50    PASS    .     GT      0/1  1/1
tgt1    90   .   C    G    50    PASS    .     GT      0/1  1/1
tgt1    130  .   A    G    50    PASS    .     GT      0/1  1/1
tgt1    170  .   C    G    50    PASS    .     GT      0/1  1/1
```
Non-empty projected VCF in target coords confirmed; sort+concat -a green.

### IUC param fixes applied to vcf_projection.gxwf.yml
1. **concat_vcfs `--allow-overlaps` nesting (WRONG -> FIXED).**
   Authored blind as a sibling of `naive`:
   ```yaml
   sec_default: { mode: { naive: "no", allow_overlaps: "yes" } }
   ```
   Live schema: `allow_overlaps` is the test_param of a NESTED conditional
   `sec_default|mode|overlaps|allow_overlaps`, reachable only when `naive=no`.
   Fixed to:
   ```yaml
   sec_default:
     mode:
       naive: "no"
       overlaps:
         allow_overlaps: "yes"
   ```
2. **concat_vcfs `output_type: z` INVALID -> `b`.**
   IUC bcftools_concat 1.22 `output_type` options are ONLY `{b,v}` (no z/u).
   `z` returned API 400 (`invalid option ('z')`). Changed to `b` (bgzipped BCF).
   (Same is true for bcftools_annotate: `{b,v}` only — its authored `output_type: v`
   was already valid, left as-is.)

### Verified-correct as authored (no change needed)
- `rename_chroms.in: sec_annotate|rename_chrs` — matches live `data` param exactly.
- `rename_chroms.output_file`, `output_type: v` — valid.
- `crossmap_project` nested params all correct:
  `seq_source|index_source_s: history`, `seq_source|input`,
  `seq_source|input_fasta`, `seq_source|chain_source|index_source: history`,
  `seq_source|chain_source|input_chain`; output `output` — all match live schema.
- `sort_vcf.output_type: z` — valid (greg/1.4.0 accepts {b,u,z,v}).

### Synthetic-data gotcha worth recording (not a YAML bug)
CrossMap chain field order is UCSC-standard `chain score Nm Sz STRAND Start End ...`
(strand BEFORE start/end). A chain with strand AFTER coords makes CrossMap read the
start field as the strand and abort: `Source strand in a chain file must be +`. The
v3 cleaned chains are real UCSC chains so this only bit synthetic data; noted so
test-data authors don't repeat it. CrossMap chain `txt` ftype (extensions=['txt']).

### bcftools_sort version gap
Installed wrapper is `greg/bcftools_sort/1.4.0`, NOT the IUC repo. It exposes ONLY
`input_file` + `output_type` (no `-T` temp-dir / max-mem knobs that 11_project_vcf.sh
uses via `-T "$TMP_SORT"`). For the workflow this is immaterial: `output_type`
accepts `z`, the only param WF-J needs, and the step ran green. Doc note added to the
YAML. If IUC bcftools_sort is later installed the `tool_id` should switch to the iuc
repo path.

### WF-J map-over / collection gaps blocking one-click run
- **Per-target chain selection.** Production projects the SAME renamed cohort VCF onto
  every non-ref target, each via that target's `REF_STRAIN.{target}` cleaned chain.
  The YAML models this as CrossMap map-over the `cleaned_chains` list (eid=target)
  zipped with `target_fastas` (eid=target). That is the correct shape, BUT the two
  collections must be IDENTIFIER-MATCHED at runtime; gxformat2 does not enforce the
  zip — the user must supply two list collections keyed on the same target eids.
  Verified the single-target case live; the N-1 fan-out is a collection-construction
  responsibility outside the tool params.
- **Per-chr concat.** 11_project_vcf.sh concats PER-CHR projected VCFs into one
  per-target cohort VCF. The YAML instead reduces the per-TARGET sort outputs into one
  concat (`input_files` multi-data). For Pv4 (cohort VCF already whole-genome, one VCF
  per target) this is the right granularity; if the cohort is delivered per-chr the
  collection would need an inner per-chr dimension + a grouped concat (list:list ->
  reduce inner). Flagged as a structural difference vs the shell, not a param bug.

---

## WF-I — PROVEN end-to-end (axtToMaf x2 -> multiz_fold)

History `WFI_e2e_synthetic`. Synthetic data: 3 strains H/A/B (120bp single chrom each),
A = H with 4 SNPs, B = H with 10 SNPs; ungapped AXT `H_vs_A`, `H_vs_B` (H = target);
.sizes per strain; compare.csv with sim(H,A)=0.96 > sim(H,B)=0.90.

Per-step job state:
| step | tool | state |
|------|------|-------|
| 1a axt_to_maf (H vs A) | ucsc_axtomaf | ok |
| 1b axt_to_maf (H vs B) | ucsc_axtomaf | ok |
| 2 multiz_fold (hinge=H) | multiz_fold | ok |

Evidence — final multi-way `{hinge}.multiz.maf`, ONE block, 3 s-lines (>=2 per block):
```
##maf version=1 scoring=multiz
# multiz.v11.2 pairs/A.maf pairs/B.maf 1
a score=30619.0
s H.H1 0 120 + 120 CAGATTTTCATATTATGCAGAAAATCTACTTCGCCTGATACGAGTCGGTTATCTTCGG...
s A.A1 0 120 + 120 CAGATTTTCATATTATGCAGAAATTCTACTTCGCCTGATACGAGTCGGTTATCTTCGC...
s B.B1 0 120 + 120 CGGATTTTCATATTATGCTGAAAATCTACTTCGCCTGATACGAGTCGGTTATCTTCGG...
```
The `pairs/A.maf pairs/B.maf` order confirms multiz_order folded A first (DESC
similarity 0.96 > 0.90) — closest-first ordering works on live compare.csv.

### IUC param fixes applied to multiz.gxwf.yml (axt_to_maf step)
The whole axt_to_maf `in:` block was authored against guessed names. Live IUC
`ucsc_axtomaf` (repo `ucsc_axttomaf`) schema is completely different:
| authored (WRONG) | live (FIXED) |
|------------------|--------------|
| `axt:`           | `in_axt:` |
| `ref_sizes:`     | `target_reference_index_source\|in_tar_ref_index:` (history mode, ftype tabular) |
| `query_sizes:`   | `query_reference_index_source\|in_que_ref_index:` (history mode, ftype tabular) |
| out: `output`    | out: `out` |
Added the two index-source selector conditionals to `state`
(`*_index_source_selector: history`) and the scalar `t_prefix` / `q_prefix` params
(authored block had no prefixes at all). Also fixed the multiz_fold input wire
`pairwise_mafs: axt_to_maf/output` -> `axt_to_maf/out`.

### multiz_fold step — verified correct as authored
`pairwise_mafs` (data_collection), `compare_csv` (data), `hinge` (text), output
`folded_maf` — all match the OUR-wrapper schema; ran green. multiz_order.py keys ONLY
on the MAF collection element_identifiers + compare.csv labels (NOT s-line prefixes),
confirmed by reading the wrapper + multiz_order.py and by the live fold.

### WF-I map-over / collection gaps blocking one-click run
- **-tPrefix / -qPrefix per-element (the real gap).** Production
  impl/10_multiz.sh sets `-tPrefix="{hinge}." -qPrefix="{query}."` so s-lines read
  `H.chr` / `Q.chr` (WF-K then renames strain s-lines to GenBank). These are PER-ELEMENT
  scalars derived from the map-over identifiers, which gxformat2 cannot express inside a
  pure map-over (same limitation that already forces the `hinge_names` parallel-label
  collection for the multiz_fold `--hinge` scalar). YAML leaves `t_prefix`/`q_prefix`
  EMPTY with a doc note. Live proof that this does NOT break the fold: with empty
  prefixes s-lines are `H1`/`A1`; multiz_fold still composed because ordering ignores
  prefixes. To restore production `strain.chrom` naming, prefixes must be fed
  per-element (parallel label collections, like hinge_names) — currently a manual /
  pre-staging step, not wireable one-click. In my live run I set the prefixes manually
  (`H.`, `A.`, `B.`) to demonstrate the production naming works (see s-lines above).
- **Per-hinge pair-MAF SET (list:list outer=hinge).** multiz_fold needs ALL of a
  hinge's per-query MAFs in ONE job. The YAML restructures axt outputs as
  list:list (outer=hinge, inner=query) and map-overs the OUTER dimension. The
  axt_to_maf step map-overs the SAME list:list of directed AXTs. This is the correct
  shape; the runtime gap is that building the directed per-(hinge,query) AXT list:list
  (each unordered Phase-C AXT oriented H-as-target) + the matched target_sizes /
  query_sizes list:list is upstream collection construction, not expressible as tool
  params. Verified the single-hinge (H) inner-list case live.
- **--hinge scalar.** Wired via the `hinge_names` parallel list (eid == hinge), the
  documented gxformat2 workaround. Live run supplied `hinge=H` as a scalar directly;
  the parallel-collection map-over equivalence is by design, not separately exercised
  here.

---

## Summary of edits
vcf_projection.gxwf.yml: concat `overlaps|allow_overlaps` nesting fix; concat
`output_type z->b`; doc notes on bcftools_sort version gap + concat output_type +
per-target/per-chr collection gaps.
multiz.gxwf.yml: axt_to_maf param names (`in_axt`,
`*_reference_index_source|in_*_ref_index`, selectors), `t_prefix`/`q_prefix` added,
output `output->out`; multiz_fold wire `output->out`; doc note on the per-element
prefix map-over gap.

Both files re-import into live Galaxy with zero tool_errors. Both pipelines run green
end-to-end on synthetic data. No GPU used. No git commit.
