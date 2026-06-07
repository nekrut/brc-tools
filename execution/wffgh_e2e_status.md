# WF-F → G → H selection backbone — end-to-end execution status

**Result: GREEN.** The science core (CDS-grouping → protein MSA → codon
back-translation → trimming → ML trees → BUSTED selection scan) composes
end-to-end in the running Galaxy 26.1.rc1 (http://localhost:8080) on minimal
synthetic data, tool-by-tool via bioblend. All 11 jobs finished `ok`. Every
required piece of evidence verified: a real protein MSA, a back-translated
codon alignment (len = 3× protein), Newick treefiles, and BUSTED
`busted.json` that parse and carry a `test results` p-value.

Date: 2026-06-07. Galaxy 26.1.rc1. API key: `e6684cd2946c56a48c1b59e7c0dc5255`
(`.env` `GALAXY_API_KEY`, admin). History: `417e33144b294c21`.
This is GPU-independent — none of these tools use the GPU.

## Synthetic inputs (no upstream run)

Built by `/tmp/wffgh/gen_data.py`. 4 strains (REF + Q1/Q2/Q3, 1:1), two
orthogroups, each gene an in-frame CDS with no internal stops; queries diverge
from REF by 6/10/14 synonymous-and-nonsynonymous SNPs so trees and BUSTED have
signal and there are 4 distinct sequences (so IQ-TREE `-B` is not auto-dropped).

| Item | Detail |
|---|---|
| ortholog_table.tsv | `orthogroup_id` + REF/Q1/Q2/Q3 columns; OG0001=geneA, OG0002=geneB |
| geneA CDS | 120 nt (40 codons) per strain |
| geneB CDS | 135 nt (45 codons) per strain |
| Genomes | one contig `<strain>_chr1` per strain; both genes plus-strand, phase 0 |
| GFF3 | gene → mRNA → CDS per gene, matching build_msa.py's parse_gff_cds |

Inputs uploaded; query GFF/FASTA built as two parallel `list` collections
(element_identifier = strain). All upload datasets `ok`.

## Per-step job states

Tool-by-tool (no gxformat2 map-over needed); each IUC step driven with
bioblend `run_tool` using the `{"batch": True, "values": [hdca]}` map-over form
so it maps over the per-OG collection.

| Step | Phase | tool_id (live version) | Jobs | State |
|---|---|---|---|---|
| group_cds_by_og | WF-F | `group_cds_by_og` (1.0.0+galaxy0, OUR) | 1 | ok |
| mafft LINSI | WF-F | `rbc_mafft/7.526+galaxy2` | 2 (per OG) | ok, ok |
| pal2nal | WF-F | `pal2nal/14.1+galaxy0` | 2 | ok, ok |
| trimal | WF-F | `trimal/1.5.1+galaxy0` | 2 | ok, ok |
| iqtree3 | WF-G | `iqtree3` (3.0.1+galaxy0, OUR) | 2 | ok, ok |
| hyphy_busted | WF-H | `hyphy_busted/2.5.96+galaxy0` | 2 | ok, ok |

**Note on installed iqtree3 version:** the live tool reports
`3.0.1+galaxy0`, while the WF-G doc text claims "pinned 3.1.2". The
installed build is 3.0.1; update the doc or repin if 3.1.2 is required.

## Output evidence (all downloaded + checked)

- **Protein MSA** (mafft, OG0001): 4 records (REF/Q1/Q2/Q3) all aligned to
  length 40. Real LINSI alignment.
- **Codon alignment** (pal2nal): OG0001 len 120 = 3×40; OG0002 len 135 = 3×45.
  Back-translation length invariant holds for every record.
- **trimal -automated1**: ran on both codon-alignment elements, FASTA output.
- **Treefiles** (iqtree3, Newick, all 4 taxa + UFBoot support values):
  - OG0001 `(REF:0.0000020228,(Q1:0.044,Q2:0.080)60:0.0075,Q3:0.127);`
  - OG0002 `(REF:0.0000010000,Q1:0.046,(Q2:0.078,Q3:0.112)32:1e-6);`
- **busted.json** (both OGs): valid JSON, `"test results"` present, p-value
  0.5, LRT 0 (expected — synthetic data has no injected positive selection;
  the point is the test runs and emits a parseable statistical result).

## CRITICAL deliverable — IUC params authored BLIND vs. live tool (the fix list)

The msa / trees / selection `.gxwf.yml` step params were written before these
IUC tools were installed. Below is the exact correct shape from each live
`/api/tools/<id>?io_details=true`, the every-fix list, and what I applied.

### rbc_mafft — `…/rnateam/mafft/rbc_mafft/7.526+galaxy2`

Live input tree (relevant bits):
- input is a conditional `input` (test `mapping`, opts `implicit`/`merge`,
  default `implicit`) → repeat `batches` → **data param `inputs`**. So the
  collection input path is `input|batches_0|inputs`.
- protein flag: conditional `datatype_selection` (test `datatype`, opts
  `''` / `--nuc` / `--amino`). Use **`--amino`**.
- mode: conditional `flavour` (test `type`); LINSI is the preset
  **`mafft-linsi`** (= `--localpair --maxiterate 1000`; no custom block needed).
- output: **`outputAlignment`** (fasta) — this one was already right.

Fixes to `msa.gxwf.yml` `mafft_linsi`:
1. tool_id `rbc_mafft` → full `…/rbc_mafft/7.526+galaxy2`.
2. input `inputs:` → `input|batches_0|inputs:` (the real param is nested in a
   conditional+repeat; a bare `inputs` does not exist).
3. drop `state.cond_flavour.flavourType: linsi` → `state.flavour.type: mafft-linsi`.
4. drop `state.datatype.datatype_serving: amino_acids` →
   `state.datatype_selection.datatype: "--amino"`.
5. add `state.input.mapping: implicit` (the conditional test param).
   APPLIED.

### pal2nal — `…/iuc/pal2nal/pal2nal/14.1+galaxy0`

Live inputs (flat, no conditionals): `protein_alignment` (data),
`nucleotide_fastas` (data), `output_format` (select: clustal/paml/**fasta**/
codon), `genetic_code` (select: 1/2/…), bool flags, output **`output_file`**
(plus `html_output_file`).

Fixes to `pal2nal_codon`:
1. tool_id `pal2nal` → full `…/pal2nal/14.1+galaxy0`.
2. `input_protein` → `protein_alignment`.
3. `input_dna` → `nucleotide_fastas`.
4. `state.codontable: "1"` → `state.genetic_code: "1"`.
5. `out: output` → `out: output_file` (and the `codon_alignments`
   `outputSource` updated to `pal2nal_codon/output_file`).
   APPLIED.

### trimal — `…/iuc/trimal/trimal/1.5.1+galaxy0`

Live: data input named **`in`**; conditional `trimming_mode` with test param
**`mode_selector`** (opts keep leading dash: `-nogaps`, …, **`-automated1`**,
`manual`, `custom`); select `out_format_selector` (`-fasta` etc.); output
**`trimmed_output`** (already right).

Fixes to `trimal_clean`:
1. tool_id `trimal` → full `…/trimal/1.5.1+galaxy0`.
2. `state.trimming_mode.mode: automated1` →
   `state.trimming_mode.mode_selector: "-automated1"` (wrong key name AND
   missing the leading dash — the value must be `-automated1`).
3. add `state.out_format_selector: "-fasta"` to keep FASTA codon output.
4. input source updated to `pal2nal_codon/output_file` (cascade of pal2nal fix).
   APPLIED.

### hyphy_busted — `…/iuc/hyphy_busted/hyphy_busted/2.5.96+galaxy0`

Live: alignment data input **`input_file`**; tree data input **`input_nhx`**
(format nhx/newick — NOT `tree_file`); conditional `branch_cond` with test
param **`branch_sel`** (opts `specify`/`All`/`Internal`/`Leaves`/
`'Unlabeled-branches'`, default `All`); `gencodeid` select (default
`Universal` = code 1); advanced `section` (syn_rates, rates, …); output
**`busted_output`** (`hyphy_results.json`) + `busted_md_report`.

Fixes to `selection.gxwf.yml` `hyphy_busted`:
1. tool_id `hyphy_busted` → full `…/hyphy_busted/2.5.96+galaxy0`.
2. tree input `tree_file` → **`input_nhx`**.
3. `state.branches: All` → `state.branch_cond.branch_sel: All` (it's the test
   param of a conditional, not a flat param).
4. **`state.srv: "No"` REMOVED — this wrapper version exposes NO `--srv`
   param.** The impl/09_hyphy.sh `--srv No` cannot be reproduced from the
   Galaxy GUI; BUSTED here runs with its default SRV model. Documented in the
   step doc. (If `--srv No` is scientifically required, a newer/patched
   hyphy_busted wrapper that exposes it would be needed — flagged below.)
5. genetic code: default `Universal` already = code 1, so no change needed;
   confirmed matches impl `-codontable 1` / pal2nal genetic_code 1.
   APPLIED.

### iqtree3 (WF-G, OUR wrapper) — no param fixes

Live `iqtree3` inputs `alignment` (data) + `bootstrap` (bool, default true),
outputs `treefile` (nhx) + `iqtree_report` (txt) — all already match
`trees.gxwf.yml`. Only doc nit: installed version is **3.0.1+galaxy0**, doc
says pinned 3.1.2 (reconcile).

## Map-over / collection-pairing gaps that block a one-click run

The chain works tool-by-tool, but a one-click gxformat2 run has these gaps to
watch:

1. **mafft map-over target is buried.** Because the real collection input is
   `input|batches_0|inputs` (inside conditional `input`=implicit + repeat
   `batches`), the workflow editor / gxformat2 must connect the upstream `pep`
   collection to that nested repeat slot and rely on implicit map-over. A naive
   `inputs:` connection (as originally authored) fails with a 400. Confirmed
   working via the bioblend batch form; the gxformat2 `in:` key must use the
   `input|batches_0|inputs` path.

2. **pal2nal & busted pair two collections by element_identifier.** pal2nal
   takes (protein_alignment, nucleotide_fastas) and busted takes (input_file,
   input_nhx). For the paired map-over to line up the correct OG, BOTH input
   collections must share identical element_identifiers in the same order.
   Here the OG ids (OG0001/OG0002) flow unchanged from group_cds_by_og →
   mafft → pal2nal → iqtree3 → busted, so pairing is automatic. Verified the
   pal2nal output and busted output collections both keyed OG0001/OG0002.
   In a real run, confirm trimal is OR is not in the BUSTED path: the impl
   pipeline (08/09) feeds BUSTED the *un-trimmed* `*.codon.aln.fa`; I followed
   that (BUSTED + iqtree3 both consume `pal2nal_codon` output, trimal output is
   a separate `codon_alignments_clean` deliverable). If WF-H is meant to
   consume the trimmed alignments instead, rewire its `codon_alignments` input.

3. **`--srv No` is unreachable** in hyphy_busted 2.5.96+galaxy0 (see fix #4
   above). This is a genuine semantic gap vs. the CLI pipeline, not just a
   param-name mismatch.

4. **iqtree3 `<4-unique` bootstrap fallback** lives inside OUR wrapper, so a
   real run with low-diversity OGs is fine, but the synthetic data was built
   with 4 distinct sequences specifically so `-B 1000` is exercised (not the
   fallback). The fallback path itself was not hit in this run.

## Files changed (NOT committed, per instructions)

- `workflows/msa/msa.gxwf.yml` — mafft / pal2nal / trimal steps + codon
  outputSource fixed; full toolshed tool_ids pinned.
- `workflows/selection/selection.gxwf.yml` — hyphy_busted step fixed; full
  tool_id pinned; `--srv` gap documented.
- `workflows/trees/trees.gxwf.yml` — unchanged (already correct); only a
  version-doc nit noted (3.0.1 installed vs 3.1.2 in doc).

All three YAMLs re-validated as parseable after edits.

Reproduce: scripts in `/tmp/wffgh/` (gen_data.py, run.py, step_*.py),
synthetic inputs in `/tmp/wffgh/data/`, state in `/tmp/wffgh/state.json`.
Stayed out of tools/toga2 and workflows/align_chain_project.
