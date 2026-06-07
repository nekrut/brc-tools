# WF-F `msa` — Pv4 Phase F (codon/protein MSA)

Per-orthogroup codon (and protein) multiple-sequence alignments. Decomposes
`build_msa.py` into Galaxy jobs to dodge its `run_in_container.sh`
container-in-container path.

File: `msa.gxwf.yml` (gxformat2, `class: GalaxyWorkflow`).

## Inputs

| input | type | notes |
|---|---|---|
| `ortholog_table` | data (tabular) | `ortholog_table.tsv` from WF-E; `orthogroup_id` col + one col/strain |
| `ref_name` | string (default `REF`) | must match reference column header |
| `ref_gff` | data (gff3) | reference's own fixed GFF3 |
| `ref_fasta` | data (fasta) | reference softmasked genome |
| `query_gff` | list collection | REF-anchor subset of C.4 merged GFF3s, key = strain |
| `query_fasta` | list collection | per-strain softmasked FASTAs (Phase B), key = strain |
| `min_intact` | int (default 4) | orthogroup member threshold; sets which set you build |

## Steps — our wrappers vs IUC

| step | tool_id | source |
|---|---|---|
| `group_cds_by_og` | `group_cds_by_og` | **OUR wrapper** |
| `mafft_linsi` | `rbc_mafft` | IUC (rnateam) |
| `pal2nal_codon` | `pal2nal` | IUC |
| `trimal_clean` | `trimal` | IUC |

`group_cds_by_og` emits two parallel list collections (`cds`, `pep`) keyed by
orthogroup, applying `min_intact` (folds `parse_gff_cds`/`extract_cds`:
internal stops -> NNN, codon-truncated; protein = translate + `rstrip('*')`,
ref-internal-stop OGs dropped). MAFFT LINSI (`--localpair --maxiterate 1000`)
maps over the **protein** collection; pal2nal back-translates each protein
alignment against the matching `{og}.cds.fa` (`-output fasta -codontable 1`),
the two collections paired by orthogroup `element_identifier`; trimal
`-automated1` cleans the codon alignment.

## Two sets (`core_v3` / `core_relaxed`)

A single run produces one set. Run the workflow **twice** with different
`min_intact`:

| set | test panel | Pv4 8-strain |
|---|---|---|
| strict `core_v3` (~1.6k OGs) | `min_intact = 4` | `7` |
| relaxed `core_relaxed` (~4.2k OGs) | `min_intact = 3` | `5` |

Outputs: `protein_alignments`, `codon_alignments` (`{og}.codon.aln.fa`),
`codon_alignments_clean` (-> `core_v3_clean` / `core_relaxed_clean`). The
codon alignments feed WF-G (trees) and WF-H (selection).

## Scaling / collapse note

`core_relaxed` is ~4.2k orthogroups -> ~4.2k alignment datasets per run.
Per Decision 8/15 the bulk of downstream per-gene artifacts is collapsed to a
single archive past the scaling threshold; the alignment collections here stay
as collections because WF-G / WF-H map over them directly.

## RUNNABILITY

- **IUC deps pending install:** `rbc_mafft`, `pal2nal`, `trimal` are not yet
  installed on the validation Galaxy (only our wrappers are loaded). Install
  before running. `planemo workflow_lint` still reports "All tool ids appear to
  be valid".
- **IUC input/state keys are best-effort:** `mafft_linsi` / `pal2nal_codon` /
  `trimal_clean` use the conventional IUC wrapper input names
  (`inputs`/`outputAlignment`, `input_protein`/`input_dna`/`output`,
  `in`/`trimmed_output`) and minimal `state:` for the validated flags. These
  must be reconciled against the actual installed wrapper versions; the `state:`
  blocks encode LINSI / `-output fasta -codontable 1` / `-automated1` intent and
  may need key renames once the tools are installed.
- The pal2nal map-over pairing (protein aln + cds, by OG element_identifier) is
  the load-bearing wiring; verify both collections carry identical OG element
  sets/order after install.

## Lint

`planemo workflow_lint msa.gxwf.yml` -> clean except the standard
"Workflow missing test cases" warning.
