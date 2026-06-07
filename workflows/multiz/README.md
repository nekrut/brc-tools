# WF-I `multiz` (Phase I)

Progressive multiz fold: per hinge strain, fold all of its pairwise alignments
into one multi-way MAF, ordered closest-first by DESCENDING sourmash similarity.

File: `multiz.gxwf.yml` (gxformat2, `class: GalaxyWorkflow`).

## Inputs

| input | type | doc |
|-------|------|-----|
| `pairwise_axts` | `list:list` (outer=hinge, inner=query) | Directed per-(hinge,query) AXTs from Phase C.1, oriented so the hinge is the AXT target. |
| `target_sizes` | `list:list` (outer=hinge, inner=query) | Per-pair target (hinge) chrom `.sizes` (Phase B). |
| `query_sizes` | `list:list` (outer=hinge, inner=query) | Per-pair query chrom `.sizes` (Phase B). |
| `compare_csv` | data | Phase A sourmash `compare.csv` N×N similarity matrix (whole-collection, non-mapped). |
| `hinge_names` | `list` | One text dataset per hinge whose `element_identifier == hinge strain`, parallel to the outer dim. Feeds the `multiz_fold --hinge` scalar per map-over job. |

## Steps — our wrappers vs IUC

| step | tool_id | source | notes |
|------|---------|--------|-------|
| `axt_to_maf` | `ucsc_axtomaf` | **IUC (pending install)** | axtToMaf per (hinge,query); hinge oriented as MAF target/reference. |
| `multiz_fold` | `multiz_fold` | **OUR wrapper** | maps over the OUTER hinge dim; folds closest-first by DESC sourmash similarity. |

**IUC dependency to install before running:** `ucsc_axtomaf`.

## RUNNABILITY

- GPU-down / toga2-blocked caveats do not affect WF-I (it depends only on
  A `compare.csv`, B `.sizes`, C AXTs — not on E/F or KegAlign).
- `ucsc_axtomaf` must be installed before this workflow runs.
- Output: per-hinge `{hinge}.multiz.maf` with **strain-named** s-lines, which
  WF-K renames to GenBank accessions.

## gxformat2 flags (honest notes)

1. **Hinge scalar via map-over.** `multiz_fold` needs ALL of a hinge's per-query
   MAFs in one job (the pairwise input is mapped on the OUTER hinge dimension)
   **plus** a scalar `--hinge` string equal to that hinge's name. gxformat2 has
   no clean way to derive a per-job scalar from the outer collection's
   `element_identifier` inside a pure map-over, so the hinge name is supplied as
   a **parallel `hinge_names` text collection** keyed by the same identifier.
   This is the best-effort encoding; in the Galaxy UI an equivalent result is
   achievable by entering the hinge per map-over element, but that cannot be
   expressed declaratively here.

2. **axtToMaf kept as a separate step.** The plan allows folding axtToMaf inside
   `multiz_fold`, but our `multiz_fold` wrapper consumes `format=maf` directly,
   so axtToMaf is a separate map-over step. When separate it must map over the
   **N(N-1) DIRECTED** per-(hinge,query) AXTs (each unordered AXT producing the
   H-as-ref orientation), supplied as the `list:list` outer=hinge / inner=query.
   The exact `-tPrefix`/`-qPrefix` + `.sizes` orientation per pair (so H is
   always target) is an `ucsc_axtomaf` runtime concern; this WF wires the two
   `.sizes` collections (`target_sizes`, `query_sizes`) and the AXT collection
   but cannot encode the per-pair prefix swap declaratively.

3. **Step `label:` omitted.** `planemo workflow_lint` mis-resolves step↔output
   connections when a step `label:` contains parentheses in this YAML form;
   step keys serve as labels and per-step `doc:` carries the description.

## Lint

`planemo workflow_lint multiz.gxwf.yml` → no ERRORs. Only the standard advisory
warnings (no creator / no license / no test cases), identical to the gxformat2
reference examples.
