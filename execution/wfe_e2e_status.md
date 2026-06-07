# WF-E `consensus_orthology` — end-to-end proof on minimal synthetic data

Date: 2026-06-07
Galaxy: 26.1.rc1 @ http://localhost:8080 (user anton@nekrut.org)
bioblend: 1.9.0
Execution: tool-by-tool via bioblend (matches the gxwf step graph), all OUR wrappers, GPU-independent.

## VERDICT

WF-E composes end-to-end in the running Galaxy. **All 6 steps green (`ok`).** The
three critical staging contracts (`.dat` -> `{strain}.bed` / `{a}.{b}.rbest.chain`, and
the nested `list:list` -> `{anchor}-as-ref/{query}.classification.tsv` reconstruction)
all executed correctly in the real Galaxy `<command>` blocks. The phase_e_graph_edges
contig-keying FIX produces NON-EMPTY graph edges at the workflow level. No gxwf wiring
fixes were required.

## Synthetic inputs (mutually consistent, 3 strains A/B/C, shared contig chr1)

Written to `execution/wfe_synth/`:

- `A.gff3` (geneA1 chr1:101-400, geneA2 chr1:801-1200), `B.gff3` (geneB1 chr1:121-420),
  `C.gff3` (geneC1 chr1:111-410). Native per-strain GFF3 -> gene_bed -> BED4.
- `abc.gfa` — tiny GFA1, 3 nodes, three PanSN paths `A#1#chr1`, `B#1#chr1`, `C#1#chr1`
  all traversing the shared nodes (so odgi paths emits the 3 co-membership path names).
- `A.B.rbest.chain`, `A.C.rbest.chain` — single-block chains projecting A:geneA1 onto
  B:geneB1 and C:geneC1 at perfect 1:1 reciprocal overlap.
- `A-as-ref`: `B.classification.tsv`, `C.classification.tsv` — LIFTOFF_CLEAN rows
  (source=liftoff, intactness=I) mapping geneA1->geneB1 / geneA1->geneC1.

(The tools' own scattered test-data were NOT mutually consistent across the three
sources — rbest used chrA/chrB, graph used chr1, consensus used geneA/geneX — so a fresh
consistent A/B/C set on chr1 was synthesized.)

## Per-step job state (real Galaxy)

| Step | tool_id | job state | output |
|---|---|---|---|
| gene_bed (map-over native_annotations list, 3 elements) | `gene_bed` | ok, ok, ok | auto list collection `13cea0e6...` (A/B/C BEDs) |
| odgi build | `odgi_build` | ok | `.og` |
| odgi paths --haplotypes | `odgi_paths` | ok | paths.tsv (A#1#chr1, B#1#chr1, C#1#chr1) |
| rbest overlap | `phase_e_rbest_overlap` | ok | rbest_edges.tsv |
| graph edges | `phase_e_graph_edges` | ok | graph_edges.tsv |
| consensus | `phase_e_consensus` | ok | ortholog_table.tsv |

## Output verification

**rbest_edges.tsv — NON-EMPTY (2 edges):**
```
strain_a  gene_a   strain_b  gene_b   overlap_a  overlap_b
A         geneA1   C         geneC1   1.000      1.000
A         geneA1   B         geneB1   1.000      1.000
```

**graph_edges.tsv — NON-EMPTY (5 edges), keyed by contig `chr1` (THE FIX WORKS):**
```
strain_a  gene_a   strain_b  gene_b   path_id  overlap
C         geneC1   A         geneA1   chr1     1.000
C         geneC1   A         geneA2   chr1     1.000
C         geneC1   B         geneB1   chr1     1.000
A         geneA1   B         geneB1   chr1     1.000
A         geneA2   B         geneB1   chr1     1.000
```
Pre-fix (keying by full path name) this file would be header-only: odgi emits one unique
path per haplotype, so every key mapped to a single strain -> `len(strain_list) < 2`
-> zero edges. (Confirmed: re-running the unfixed v3 impl script on the same paths.tsv
gives 0 edges; the FIXED bundled copy gives 5.)

**ortholog_table.tsv — 1 orthogroup spanning all 3 strains:**
```
orthogroup_id  label     n_strains  max_copies  A              B        C
OG000001       CORE-VAR  3          2           geneA1,geneA2  geneB1   geneC1
```
>=1 orthogroup grouping genes across strains: YES (3 strains in one orthogroup).
Label is CORE-VAR (max_copies=2) because the coarse path-level graph edge pulls A:geneA2
into the group (geneA2 shares contig chr1, so it co-members at path level). This is the
documented behaviour of the graph source ("coarse approximation... subsequently filtered";
here rbest+classification anchor geneA1 1:1 while graph adds geneA2). Expected, not a bug.

## CRITICAL: `.dat` staging confirmed in REAL Galaxy command blocks

Real `command_line` from the executed jobs (abbreviated):

- **rbest** — `.dat` symlinked to element_identifier filenames:
  `ln -s .../dataset_*.dat 'chains_dir/A.B.rbest.chain'` ;
  `ln -s ... 'chains_dir/A.C.rbest.chain'` ; `'annotations_dir/{A,B,C}.bed'`
  then `--chains 'chains_dir/*.rbest.chain' --annotations 'annotations_dir/*.bed'`.
- **graph** — `ln -s ... 'stage/{A,B,C}.bed'` and
  `--strains 'A B C'` derived from the `#echo` over element_identifiers (matches staged BEDs).
- **consensus** — nested list:list reconstructed:
  `mkdir -p 'stage/A-as-ref'` ;
  `ln -s ... 'stage/A-as-ref/B.classification.tsv'` ;
  `ln -s ... 'stage/A-as-ref/C.classification.tsv'` ; then `--liftoff_dir stage`.

All three staging contracts work exactly as the README "Decision 10 / .dat lesson" claims.

## gxwf wiring review (consensus.gxwf.yml)

No fixes needed. Verified against live tool definitions:

- Output ports all match: `odgi_paths/paths_tsv`, `gene_bed/output`,
  `rbest_overlap/rbest_edges`, `graph_edges/output`, `consensus/ortholog_table`. OK.
- Tool param names match: both edge tools expose Galaxy param `min_overlap`
  (graph's `argument="--min-overlap"` maps to name `min_overlap`); gxwf passes
  `rbest_min_overlap` / `graph_min_overlap` into `min_overlap`. OK.
- `planemo workflow_lint workflows/consensus/consensus.gxwf.yml` -> "All tool ids appear
  to be valid"; only the benign "Workflow missing test cases" warning.

## Map-over / collection notes (honest gaps)

- gene_bed auto-map-over the `native_annotations` list works and produces a `list`
  collection whose element_identifiers (A/B/C) propagate to the staged BED filenames
  consumed (flat) by both edge tools. This collection appears in the history as a
  tool-named auto-collection (not in `run_tool`'s `output_collections` field; found via
  history contents) — a bioblend reporting quirk, not a workflow issue.
- `c4_classifications` is a real `list:list`; the outer element (anchor `A`) with two
  inner elements (`B`, `C`) reconstructs cleanly to `A-as-ref/{B,C}.classification.tsv`.
  Tested with a single anchor; multi-anchor (`A`,`B`-as-ref both present) was not
  exercised but the wrapper loop `#for $a in $classifications#` handles N outer elements
  by construction.
- `graph_edges` step intentionally has NO `strains` workflow input — the wrapper derives
  `--strains` from BED element_identifiers. Correct by design; README's gxformat2 honesty
  notes already flag this. (rbest_overlap and consensus DO take `strains` as text.)
- The gxwf nested-tree reconstruction cannot be expressed in gxformat2 itself; it lives
  in the wrapper `<command>` (as the README states). The list:list is passed whole. Proven
  to work in the real engine here.

## Files

- Synthetic inputs: `/home/anton/git/pangenome_tools_wfs/execution/wfe_synth/`
- This report: `/home/anton/git/pangenome_tools_wfs/execution/wfe_e2e_status.md`
- Galaxy history: `WF-E_e2e_synth` (id `d413a19dec13d11e`)
- No git commit performed.
