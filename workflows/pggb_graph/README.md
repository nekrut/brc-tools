# WF-D `pggb_graph` (Phase D) — REUSE + one new step

Phase D (the PGGB variation graph) is **already implemented** in this repo. WF-D
does **not** introduce a new workflow file: it **reuses the existing**

```
workflows/pggb-pangenome-build/pggb-pangenome-build.ga
```

(wfmash → seqwish → smoothxg → gfaffix → odgi), which already emits the smoothed
GFA1 and the `odgi` `.og` binary graph.

## The one change for Phase E

WF-D's only addition this round is the **`odgi paths` subcommand** added to the
existing odgi wrapper suite (which already ships `odgi build` / `odgi stats` /
`odgi viz`). It runs `odgi paths --haplotypes` on the `.og` graph and emits the
haplotype-paths TSV consumed by WF-E `phase_e_graph_edges` (which reads the
path/haplotype name from **column 0**).

```
pggb-pangenome-build.ga  ──►  .og graph  ──►  odgi paths --haplotypes  ──►  paths.tsv  ──►  WF-E
```

- tool_id: `odgi_paths` (OUR wrapper; version `0.9.4+galaxy0`).
- Input: `idx` = the `.og` graph. Output: `paths_tsv` (tabular).
- Pin the odgi version to the **pggb container's** odgi version so the `.og`
  written by Phase D is readable by the `paths` subcommand.
- In WF-E the `odgi paths` step is wired **inside** `consensus.gxwf.yml` (so the
  graph datatype, not a pre-extracted TSV, is the cross-workflow dependency).

## `.dat` staging reality

Same lesson as the rest of the port (Decision 10): Galaxy stores every dataset as a
`.dat` file, so any tool that derives identity from a filename must **stage collection
elements to their `element_identifier`** inside the `<command>` before use.
`odgi paths` itself takes a single `.og` (no globbing needed), but its **downstream**
consumer `phase_e_graph_edges` keys path names off `.og` path content, and the rbest
side keys strains off `{a}.{b}.rbest.chain` filenames — those wrappers do the symlink
staging. Flagging here because WF-D's `.og` is the upstream of that chain.

## Nested `list:list` reality

Phase E's `phase_e_consensus` consumes the C.4 classifications as a **nested
`list:list`** (outer = `{anchor}-as-ref`, inner = `{query}.classification.tsv`). That
nesting is produced by WF-C.4, not WF-D, but it is the shape WF-E expects alongside
the graph paths produced here. gxformat2 declares the `list:list` as a plain typed
input; the actual `{anchor}-as-ref/{query}.classification.tsv` directory tree is
reconstructed by symlink **inside** the `phase_e_consensus` `<command>`, because
gxformat2 cannot express that staging in the workflow graph. See
`workflows/consensus/README.md`.

## odgi datatype prerequisite (shared gate: WF-D + WF-E)

The binary graph datatype `odgi` (file_ext `odgi`, class `Odgi`) is exposed via a
local **un-upstreamed monkey-patch** to `lib/galaxy/datatypes/binary.py`. Before
running WF-D or WF-E on Galaxy 26.1:

1. Re-run `scripts/patch_og_datatype.sh` against **Galaxy 26.1** (written for
   release_25.0 — verify it appends cleanly).
2. **Manually add** the `odgi` `<datatype>` entry to `datatypes_conf.xml` (the script
   only warns; it does not edit the conf).
3. Build + smoke-test the `odgi paths` subcommand: confirm it reads the patched `.og`
   and emits the haplotype-paths TSV.

Re-apply after any Galaxy upgrade until the core datatype PR lands.

## RUNNABILITY

- **GPU-down does NOT affect WF-D** (no aligner step — that is WF-C, which uses lastz
  on CPU when the GPU/KegAlign path is down).
- **TOGA2 blocked does NOT affect WF-D** (TOGA is a WF-C.4 concern).
- WF-D is gated on the **odgi datatype prerequisite** above; otherwise it is the
  already-validated PGGB build (`pggb-pangenome-build.ga`).
