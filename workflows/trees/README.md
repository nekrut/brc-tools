# WF-G `trees` — Pv4 Phase G (per-gene ML trees)

Per-gene maximum-likelihood trees from the WF-F codon alignments.

File: `trees.gxwf.yml` (gxformat2, `class: GalaxyWorkflow`).

## Inputs

| input | type | notes |
|---|---|---|
| `codon_alignments` | list collection | per-OG codon (or cleaned codon) alignments from WF-F; key = gene/OG id |
| `bootstrap` | boolean (default true) | UFBoot `-B 1000`; auto-dropped <4 uniques inside the wrapper |

Run once per set: feed the `core_v3` collection, then the `core_relaxed`
collection.

## Steps — our wrappers vs IUC

| step | tool_id | source |
|---|---|---|
| `iqtree` | `iqtree3` | **OUR wrapper** (pinned 3.0.1) |

`iqtree3` maps over the alignment collection (one tree per gene),
`-m MFP -B 1000 -T ${GALAXY_SLOTS:-2}`. The `<4`-unique-sequence bootstrap
fallback (count uniques, drop `-B`; UFBoot hangs silently below 4) lives
**inside the wrapper**.

Outputs: `treefiles` (per-gene `.treefile`, Newick) and `iqtree_reports`
(per-gene model + log-likelihood report).

## Two sets + collapse note

Run twice, once over each WF-F set, producing two `.treefile` collections
(`core_v3`, `core_relaxed`). Per Decision 8/15 the bulk of the per-gene trees
is collapsed into `{set}_trees.tar` past the scaling threshold. That
tar/collapse is done **outside** this workflow (the workflow emits the raw
per-gene collection so WF-H can pair trees to alignments by `element_identifier`
before any archiving).

## RUNNABILITY

- No IUC deps: the only tool is our `iqtree3` wrapper, loaded on the validation
  Galaxy.
- `planemo workflow_lint trees.gxwf.yml` -> clean except the standard
  "Workflow missing test cases" warning; "All tool ids appear to be valid".
