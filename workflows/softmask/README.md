# WF-B `softmask` (Phase B)

Soft-mask each assembly at the **union** of longdust + sdust low-complexity
intervals, then index. Outputs feed Phases C, D, I.

## Inputs

| Input | Type | Notes |
|---|---|---|
| `assemblies` | `collection` (list) | Per-strain assembly FASTAs. Element identifier = strain name. Every step maps over this. |

## Steps — wrappers vs IUC

| Step | tool_id | Source | Action |
|---|---|---|---|
| `longdust` | `longdust` | **OUR wrapper** | Low-complexity intervals. **Output already trimmed to 3 cols (chrom,start,end) inside the tool** (awk in the command) — no separate awk-trim step needed. |
| `sdust` | `sdust` | **OUR wrapper** | Symmetric-DUST low-complexity intervals (already 3-col BED). |
| `union_cat` | `cat1` | Galaxy distro | Concatenate longdust + sdust BEDs per strain (zipped by element identifier). |
| `sort_bed` | `bedtools_sortbed` | **IUC** | Sort intervals (required before merge). |
| `merge_bed` | `bedtools_merge` | **IUC** | Merge/union overlapping intervals. |
| `maskfasta` | `bedtools_maskfastabed` | **IUC** | `-soft` mask the assembly at merged intervals. |
| `faidx` | `samtools_faidx` | **IUC** | `.fai` index of the soft-masked FASTA. |

### Map-over / collection wiring

- `longdust` and `sdust` both map over `assemblies` → two parallel BED
  collections keyed by strain.
- `union_cat` (`cat1`) takes `input1 = longdust/output` and
  `queries_0|input2 = sdust/out_bed`; Galaxy zips the two collections by
  element identifier (strain), concatenating each strain's two BEDs.
- `maskfasta` takes `fasta = assemblies` and `bed = merge_bed/output` — two
  collections zipped by strain.

### Plan deviation (intentional)

PIPELINE_PORT_PLAN lists a standalone "trim longdust to 3 cols via awk" step.
The shipped `longdust` wrapper **already** emits 3-col BED (it pipes through
`awk '{print $1,$2,$3}'` internally). So the explicit awk step is dropped —
the union is just `cat → bedtools sort → bedtools merge`. Flagged here so the
deviation from the plan text is visible.

## Outputs

- `softmasked_fasta` — per-strain soft-masked FASTAs (low-complexity lower-cased).
- `fasta_index` — per-strain `.fai`.

> The `.sizes` file (`cut -f1,2` of `.fai`) is **not** emitted here; it is
> produced downstream where consumed (C/D/I), per the plan.

## RUNNABILITY

- **OUR wrappers loaded**: `longdust` (1.4+galaxy0) and `sdust` (0.1+galaxy0)
  are installed in this Galaxy.
- **IUC deps pending install** — `bedtools_sortbed`, `bedtools_merge`,
  `bedtools_maskfastabed`, `samtools_faidx` must be installed before the
  workflow runs. (`cat1` is a built-in distro tool, already present.)
- **GPU / toga2**: not relevant to Phase B (no alignment/annotation here).
- **Param caveat**: the IUC `state:` blocks are minimal (`soft_mask: true` on
  maskfasta; sort/merge/faidx run on defaults). Reconcile against the installed
  IUC tools' parameter names on first run.

## Lint

```
planemo workflow_lint workflows/softmask/softmask.gxwf.yml
# WARNING: Workflow missing test cases.
# CHECK: All tool ids appear to be valid.
```

(Only the standard "missing test cases" warning; no creator/license/annotation/
schema warnings; all tool ids valid.)
