# WF-E `consensus_orthology` (Phase E)

Builds the consensus **ortholog_table.tsv** that drives Phase F (MSA) and Phase K
(UCSC hub). Three orthology-evidence sources are combined: native gene models as
graph **nodes**, plus two independent **edge** sources (reciprocal-best chains and
pggb graph-path co-membership), reconciled by a union-find consensus that also
ingests the C.4 Liftoff/TOGA classifications.

File: `consensus.gxwf.yml` (gxformat2 / `class: GalaxyWorkflow`).

## Dataflow

```
native_annotations (list, per-strain GFF3)
        │  gene_bed  (map-over: 1 BED per strain)
        ▼
   per-strain gene BED collection  ── NODES ──┐
        │                                      │
        ├──────────────► phase_e_rbest_overlap │  (+ rbest_chains, strains, min_overlap)
        │                       │ rbest_edges.tsv
        │                                      │
graph (.og, WF-D) ─ odgi_paths ─► paths.tsv    │
        │                       │              │
        └──────────────► phase_e_graph_edges ──┘  (+ min_overlap)
                                │ graph_edges.tsv
                                ▼
c4_classifications (list:list) ► phase_e_consensus ► ortholog_table.tsv
   (+ anchors, strains, ref_strain)
```

## Inputs

| Input | Type | Notes |
|---|---|---|
| `native_annotations` | `list` | Per-strain **native** GFF3. element_identifier = strain. The orthogroup NODES (distinct from C.4 merged GFFs). |
| `rbest_chains` | `list` | WF-C reciprocal-best chains, **flat**. element_identifier MUST be `{a}.{b}` — `phase_e_rbest_overlap` keys source/target strains off the filename stem. |
| `graph` | `data` (`odgi`) | pggb `.og` from WF-D. The `odgi paths` step lives here, so the **graph** is the dependency (not a pre-extracted TSV). |
| `c4_classifications` | `list:list` | C.4 per-(anchor,query) classification tables. outer = `{anchor}-as-ref`, inner = `{query}.classification.tsv`. Consumed only by consensus. |
| `strains` | `string` | All strain names (text; pins membership/order). |
| `anchors` | `string` | Anchor strains (subset of `strains`) used as C.4 projection refs. |
| `ref_strain` | `string` | Reference strain (must be one of `anchors`). |
| `rbest_min_overlap` | `float` (0.90) | `phase_e_rbest_overlap --min_overlap` (Decision 9). |
| `graph_min_overlap` | `float` (0.90) | `phase_e_graph_edges --min_overlap` (Decision 9). |

## Outputs

- `ortholog_table` — `ortholog_table.tsv` (4 fixed cols + 1 per strain) → WF-F, WF-K.
- `gene_beds` — per-strain native gene BED collection (the nodes).
- `rbest_edges`, `graph_edges` — the two intermediate edge TSVs (useful for QC/diff).

## Our wrappers vs IUC

**All five steps are OUR wrappers** — no IUC tools in this workflow:

| Step | tool_id | Source |
|---|---|---|
| gene BED extractor | `gene_bed` | OUR wrapper |
| odgi paths | `odgi_paths` | OUR wrapper (`paths` subcommand added to the odgi suite, Phase D) |
| rbest overlap edges | `phase_e_rbest_overlap` | OUR wrapper |
| graph co-membership edges | `phase_e_graph_edges` | OUR wrapper |
| union-find consensus | `phase_e_consensus` | OUR wrapper |

No IUC deps to pre-install for WF-E.

## RUNNABILITY

- **odgi datatype prerequisite (shared with WF-D).** WF-E reads the pggb `.og`
  binary, which needs the local `odgi` datatype monkey-patch on Galaxy 26.1
  (`scripts/patch_og_datatype.sh` + a manual `<datatype>` entry in
  `datatypes_conf.xml`). The `odgi paths` subcommand must be present and smoke-tested
  to read the patched `.og` and emit the haplotype-paths TSV. See `workflows/pggb_graph/README.md`.
- **`.dat` staging (critical).** All three `phase_e_*` scripts derive strain/pair
  identity from input **filenames**, but Galaxy stores datasets as `.dat`. Each
  wrapper's `<command>` stages collection elements to `element_identifier` filenames
  (`{strain}.bed`, `{a}.{b}.rbest.chain`) before globbing. `rbest_chains` and the gene
  BED collection are consumed **flat**; `c4_classifications` is the **nested list:list**
  tree the consensus wrapper reconstructs as `{anchor}-as-ref/{query}.classification.tsv`
  and passes as `--liftoff_dir`.
- **TOGA2 blocked → Liftoff-only pass 1.** `c4_classifications` comes from WF-C pass 1
  (Liftoff-only). The consensus consumes whatever classifications exist; the TOGA2/CESAR2
  rescue branch is a fast-follow and does not change the WF-E contract.
- **GPU-down note** does not apply to WF-E (no aligner step here); it is a WF-C concern.

## gxformat2 honesty notes

- The `list:list` `c4_classifications` is declared cleanly as a workflow input and
  passed whole to `phase_e_consensus` (non-mapped). The nested-tree reconstruction
  (`{anchor}-as-ref/{query}.classification.tsv`) happens **inside** the wrapper's
  `<command>` staging, not in the workflow graph — gxformat2 cannot express that
  symlink tree, so it is encoded as the wrapper contract and flagged here.
- `gene_bed` auto-maps over `native_annotations` (Galaxy collection map-over); both
  edge tools then consume the resulting BED **collection** as a single whole input.
- `strains` / `anchors` / `ref_strain` are passed as workflow-form **text** params
  (the wrappers derive real identity from `element_identifier`; the text lists pin
  membership/order), per Decision 9/10.

## Lint

`planemo workflow_lint workflows/consensus/consensus.gxwf.yml` → no errors; only the
benign `Workflow missing test cases` warning (a `*-tests.yml` is a separate deliverable).
