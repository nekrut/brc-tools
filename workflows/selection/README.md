# WF-H `selection` — Pv4 Phase H (episodic selection, BUSTED)

Per-gene HyPhy BUSTED test for episodic positive selection.

File: `selection.gxwf.yml` (gxformat2, `class: GalaxyWorkflow`).

## Inputs

| input | type | notes |
|---|---|---|
| `codon_alignments` | list collection | per-OG codon alignments from WF-F; key = gene/OG id |
| `treefiles` | list collection | per-gene treefiles from WF-G; paired to alignments by gene id |

Run once per set (`core_v3`, then `core_relaxed`); the two input collections of
a run must be the same set.

## Steps — our wrappers vs IUC

| step | tool_id | source |
|---|---|---|
| `hyphy_busted` | `hyphy_busted` | IUC |

`hyphy_busted` maps over the alignment + tree collections **paired by gene
`element_identifier`**. Flags: `--srv No --branches All`. BUSTED writes a
fixed-named `busted.json`; the gene id rides `element_identifier` (WF-K derives
gene id from `element_identifier`, **not** a `parts[-2]` dir scheme).

Output: `busted_json` — per-gene `busted.json` list collection.

## Two sets + collapse note

Run twice, producing two `busted.json` collections (`core_v3`, `core_relaxed`).
Past the scaling threshold each set is collapsed into `{set}_busted.tar`
(Decision 8/15). The collapse step (outside this workflow) **renames each
element's `busted.json` -> `{element_identifier}.json` and tars them flat** — one
`<gene_id>.json` per element at the tar **root**. WF-K `build_hub_bb`
`extract_busted_jsons` keys gene_id off the member **basename** (strip `.json`),
not `parts[-2]`.

H output is a **subset** of the G input: genes lacking a treefile or producing
invalid JSON are dropped, so WF-K must tolerate missing entries.

## RUNNABILITY

- **IUC dep pending install:** `hyphy_busted` is not yet installed on the
  validation Galaxy. Install before running.
- **IUC input/state keys are best-effort:** the step uses conventional
  `hyphy_busted` wrapper input names (`input_file` for the alignment, `tree_file`
  for the tree, output `busted_output`) and `state:` `srv: "No"` /
  `branches: All` for the validated flags. Reconcile against the installed
  wrapper version; key renames may be needed. The alignment+tree map-over
  pairing by `element_identifier` is the load-bearing wiring.
- `planemo workflow_lint selection.gxwf.yml` -> clean except the standard
  "Workflow missing test cases" warning; "All tool ids appear to be valid".
