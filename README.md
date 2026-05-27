# brc-tools

Galaxy tool wrappers for the [BRC (Bioinformatics Research Center)](https://veupathdb.org)
pangenome pipelines, focused on the [PGGB](https://github.com/pangenome/pggb)
stack.

This is a "staging" repository: tools land here first, get exercised
against real pangenome builds (currently *Plasmodium vivax*), then
migrate to [galaxyproject/tools-iuc](https://github.com/galaxyproject/tools-iuc)
once stable. Installation onto Galaxy servers is via the Galaxy Tool Shed
(`owner: nekrut`).

## Tools

All wrappers target Galaxy `profile="25.0"` (Galaxy 26.x compatible) and
use the `@TOOL_VERSION@+galaxy@VERSION_SUFFIX@` macro pattern.

| Tool        | Version  | Subcommands wrapped                | Status | Tests |
| ----------- | -------- | ---------------------------------- | ------ | ----: |
| [`pansn_rename`](tools/pansn_rename)   | 1.0.0  | (custom Python wrapper)       | NEW    | 3 |
| [`fasta_concat`](tools/fasta_concat)   | 1.0.0  | (custom Python wrapper)       | NEW    | 3 |
| [`gfaffix`](tools/gfaffix)         | 0.2.2  | (single binary)                   | NEW    | 2 |
| [`pggb`](tools/pggb)               | 0.7.4  | (thin orchestrator)               | NEW    | 1 |
| [`wfmash`](tools/wfmash)           | 0.24.2 | (single binary)                   | bumped from 0.14 | 2 |
| [`seqwish`](tools/seqwish)         | 0.7.11 | (single binary)                   | refreshed | 2 |
| [`smoothxg`](tools/smoothxg)       | 0.8.2  | (single binary)                   | NEW    | 2 |
| [`odgi`](tools/odgi)               | 0.9.4  | `build`, `stats`, `viz`           | bumped from 0.3 + new subs | 4 |
| [`vg`](tools/vg)                   | 1.73.0 | `view`, `convert`, `deconstruct`  | bumped from 1.23 + new sub | 6 |

**Total: 9 tools, 25 planemo tests, all passing via biocontainers.**

## Architecture

These tools chain into the canonical PGGB pangenome construction pipeline:

```
per-strain FASTAs (list collection)
        │
        ▼
   ┌──────────────────┐       Per-strain PanSN-rename — adds SAMPLE#HAP# prefix
   │  pansn_rename    │       to every contig name so downstream tools can
   └────────┬─────────┘       disambiguate identically-named contigs.
            │
            ▼
   ┌──────────────────┐       Collapse the renamed collection into one
   │  fasta_concat    │       multifasta. Handles plain/gzipped inputs
   └────────┬─────────┘       transparently.
            │
            ▼
   ┌──────────────────┐       PanGenome Graph Builder — orchestrates the
   │      pggb        │       sub-tools below internally. Outputs the
   └────────┬─────────┘       canonical .smooth.final.gfa + .og.
            │
            │  (pggb's internal pipeline; the sub-tools below are also
            │   wrapped standalone for users who want step-level control)
            │
            │   wfmash    ──► PAF alignments (whole-genome aligner;
            │                 MashMap mapping + WFA base alignment)
            │      │
            │      ▼
            │   seqwish   ──► induced GFA1 (transitive closure of PAF
            │      │          into a graph)
            │      ▼
            │   smoothxg  ──► POA-smoothed GFA1 (block-wise POA cleans
            │      │          up alignment artifacts)
            │      ▼
            │   gfaffix   ──► fixed GFA1 (collapse walk-preserving
            │      │          shared affixes — final tidy)
            │      ▼
            │   odgi build ─► binary .og (succinct graph for fast queries)
            │
            ▼
   ┌──────────────────┐       Downstream consumers operating on the final
   │  odgi stats /viz │       .og: graph metrics, 1D path-coloured viz.
   │                  │
   │  vg deconstruct  │       VCF projection: graph → per-strain VCF
   │                  │       relative to a chosen reference path.
   └──────────────────┘
```

## Installation

### Via Galaxy Tool Shed (preferred, once tools are uploaded)

In Galaxy admin UI, install repositories from `nekrut` owner. Each
`tools/<tool>/.shed.yml` configures the suite.

### Local Galaxy (development)

Symlink `tools/` into a Galaxy `local_tool_conf.xml`:

```xml
<?xml version="1.0"?>
<toolbox tool_path="/path/to/brc-tools/tools" monitor="true">
  <section id="pangenome_input" name="Pangenome :: Input prep">
    <tool file="pansn_rename/pansn_rename.xml"/>
    <tool file="fasta_concat/fasta_concat.xml"/>
  </section>
  <section id="pangenome_build" name="Pangenome :: Graph build">
    <tool file="pggb/pggb.xml"/>
    <tool file="wfmash/wfmash.xml"/>
    <tool file="seqwish/seqwish.xml"/>
    <tool file="smoothxg/smoothxg.xml"/>
    <tool file="gfaffix/gfaffix.xml"/>
  </section>
  <section id="pangenome_odgi" name="Pangenome :: odgi">
    <tool file="odgi/build.xml"/>
    <tool file="odgi/stats.xml"/>
    <tool file="odgi/viz.xml"/>
  </section>
  <section id="pangenome_vg" name="Pangenome :: vg">
    <tool file="vg/convert.xml"/>
    <tool file="vg/deconstruct.xml"/>
    <tool file="vg/view.xml"/>
  </section>
</toolbox>
```

Add `local_tool_conf.xml` to `tool_config_file` in `galaxy.yml`, point
your job destination at docker-enabled biocontainers, and restart.

### Direct planemo test (no Galaxy install)

```bash
# from this repo root
planemo lint tools/pansn_rename/
planemo test --biocontainers tools/pggb/
```

The biocontainer images all live under `quay.io/biocontainers/`.

## Dependencies

All tool deps are pulled from `bioconda` via biocontainers. No additional
system dependencies. Container resolution config (Galaxy `galaxy.yml`):

```yaml
container_resolvers:
  - type: explicit
  - type: cached_mulled
  - type: mulled
  - type: build_mulled
default_container_resolver_type: mulled
```

## Per-tool notes

### pansn_rename (NEW — custom Python wrapper)

Rewrites FASTA headers to follow the
[PanSN spec](https://github.com/pangenome/PanSN-spec):

    >chr1                       ──►  >SAMPLE#HAP#chr1
    >chr2 length=14000          ──►  >SAMPLE#HAP#chr2 length=14000

- `Sample name` param is **optional**; when blank, auto-derives from the
  input dataset's element identifier. This lets the tool map over a
  Galaxy `list` collection in a workflow with no per-element parameter
  threading.
- Delimiter is a `select` (`hash`/`pipe`/`underscore`/`dot`) instead of a
  text input — Galaxy aggressively sanitizes literal `#` and `|` chars
  in test params, so the select pattern dodges that.
- Gzip detection in the underlying script is magic-byte based (Galaxy
  stores all datasets as `.dat`, so extension-based gzip detection
  silently breaks).

### fasta_concat (NEW — custom Python wrapper)

Collapses a `multiple="true"` FASTA collection into a single multifasta.
Decompresses gzipped inputs and optionally gzips output. Wrote this
rather than chain `flatten + cat1` because cat1 only operates on a
single dataset; the `__FLATTEN__` + `cat1` combination ran cat on the
collection's first element only.

### gfaffix 0.2.2 (NEW)

Single Rust binary. Wrapper exposes:
- `--output_refined` (required, GFA out)
- `--output_affixes` (optional TSV of collapsed shared prefixes/suffixes)
- `--output_transformation` (optional node-transformation map)
- `--check_transformation` (paranoid sequence-preservation check)
- `--dont_collapse` (regex over P/W lines)

### pggb 0.7.4 (NEW — thin orchestrator)

Wraps the upstream `pggb` shell pipeline as a single Galaxy tool.
Surfaces the commonly-tuned knobs: `-s` segment-length, `-p` map-pct-id,
`-n` n-haplotypes, `-k` min-match-len, `-c` n-mappings, `-Y`
exclude-delim, `-G` poa-length-targets, `-P` poa-params, `-O`
poa-padding, `-V` vcf-spec, plus skip-viz/skip-normalization/abpoa
flags.

Key wrapper-side details (these are non-obvious but documented inline):

- Input is pre-staged via `bgzip -c | samtools faidx` — pggb requires a
  bgzipped + `.fai` + `.gzi`-indexed input.
- Output collection uses `;`-chained shell with explicit `if [ -n "$f" ]`
  guards rather than `&&` chains. Rationale: pggb internally calls
  `vg deconstruct` when `--vcf-spec` is set; if the spec doesn't match
  graph path names, vg deconstruct fails and pggb propagates exit 1
  *after* the canonical GFA + .og are already written. The wrapper still
  ships the graph when present and only hard-errors when the critical
  GFA or .og is genuinely missing.
- `samtools` + `htslib` are declared as additional requirements (used
  during stage-in).
- OOM stdio regex catches `Failed to allocate` / `std::bad_alloc` /
  `Cannot allocate memory` for Galaxy's `fatal_oom` level (enables
  auto-resubmit to a larger runner).

### wfmash 0.24.2 (bumped from 0.14)

CLI surface largely rewritten in 0.24:
- `-s` is no longer "segment-length"; segment length is now controlled
  via internal heuristics. Wrapper exposes `--kmer-size`, `--sketch-size`,
  `--mappings`, `--block-length`, `--group-prefix` instead.
- Conditional for self-map vs query-vs-target modes.
- `samtools 1.21` added to requirements for the `faidx` pre-step.

### seqwish 0.7.11 (refreshed)

- All flags switched from short-form (`-r/-k/-B/-m`) to long-form
  (`--repeat-max`/`--min-match-len`/`--transclose-batch`/`--match-list`)
  per IUC convention.
- `--seqs` accepts `fastqsanger`/`fastqsanger.gz` (not generic `fastq`).
- Output: single GFA1.

### smoothxg 0.8.2 (NEW)

POA-aware graph smoother. Symlinks input to working dir before invoking
(smoothxg writes prep temp files next to its input; Galaxy mounts inputs
read-only). OOM stdio regex declared via the shared `stdio` macro.

### odgi 0.9.4 (bumped from 0.3, subset)

Three subcommands wrapped: `build`, `stats`, `viz`. The remaining
subcommands (`paths`, `pav`, `position`, `layout`, `sort`) are deferred
to a follow-up PR — they're needed for downstream PAV and graph-native
VCF projection workflows, not for the build pipeline itself.

- `odgi build`: GFA → succinct binary `.og` graph.
- `odgi stats`: graph metrics (length, nodes, edges, paths, steps). The
  wrapper auto-enables `--summarize` if no stat option is selected.
- `odgi viz`: 1D path-coloured PNG render. Tests assert image-width
  dimensions (with delta tolerance for odgi's auto-padding).

### vg 1.73.0 (bumped from 1.23, plus new `deconstruct`)

Three subcommands:
- `vg view`: format conversions (vg ↔ GFA ↔ JSON ↔ dot).
- `vg convert`: GFA → PackedGraph/HashGraph/XG (the `vg convert -g -p`
  pre-step needed for `vg deconstruct` on GFA input).
- `vg deconstruct`: VCF projection. Two modes via conditional:
  `-p` (explicit path names) vs `-P` (PanSN-style prefix). The GFA→vg
  pre-conversion happens inside the wrapper since vg deconstruct can't
  read GFA directly.

## What's deliberately not here

- **Workflows**: see [the IWC repo](https://github.com/galaxyproject/iwc)
  once the PGGB workflow is upstreamed. The workflow lives separately
  because IWC has its own contribution lifecycle.
- **odgi subcommands beyond build/stats/viz** (paths, pav, position,
  layout, sort): deferred until the downstream PAV / graph-native VCF
  workflows are wrapped.
- **pggb 0.6.x compatibility**: the wrapper targets 0.7.x. v2-style
  builds (which used 0.6.x defaults like `poa-length-target=4001,4507`,
  `poa-padding=0.03`, `n-mappings=8`) can be reproduced by passing those
  values to the 0.7.x wrapper explicitly.

## Validation history

Wrappers have been exercised end-to-end on the 8-strain *Plasmodium
vivax* pangenome panel (the v3 reference workflow documented in
[Pv4-pangenome PANGENOME.md](https://github.com/nekrut/Pv4-pangenome/blob/main/v3/writeup/PANGENOME.md)).

Two e2e runs confirmed the stack:

1. **Default-params run** on fresh NCBI fetches (~25 min wall on 16
   cores) — graph length within −2.7 % of the v2 native reference.
2. **v2-replicate run** with v2's exact inputs + v2's pggb params
   (~41 min wall) — path counts match v2 within +0.76 % (perfect modulo
   PvP01 NCBI re-annotation drift). Node/edge counts diverge ~50 %
   because pggb 0.7's smoothxg collapses more aggressively than 0.6's;
   that's algorithm drift, not the workflow.

## Layout

```
brc-tools/
├── README.md                 (this file)
└── tools/
    ├── pansn_rename/
    │   ├── pansn_rename.xml
    │   ├── pansn_rename.py
    │   ├── macros.xml
    │   ├── .shed.yml
    │   └── test-data/
    ├── fasta_concat/         (same structure)
    ├── gfaffix/
    ├── pggb/
    ├── wfmash/
    ├── seqwish/
    ├── smoothxg/
    ├── odgi/
    │   ├── build.xml
    │   ├── stats.xml
    │   ├── viz.xml
    │   ├── macros.xml
    │   ├── .shed.yml
    │   └── test-data/
    └── vg/                   (similar; view/convert/deconstruct)
```

Each tool has its own `macros.xml` (version tokens, requirements,
citations), `.shed.yml` (Tool Shed metadata), and `test-data/` (small
fixtures, all under 1 MB per IUC convention).

## Contributing

For non-trivial changes:

1. Open an issue describing the change.
2. Run `planemo format && planemo lint && planemo test --biocontainers
   tools/<tool>/` before committing.
3. Submit a PR.

For trivial fixes (typos, version bumps, etc.), a direct PR is fine.

## License

MIT (matches Galaxy core + tools-iuc). Per-tool licenses are inherited
from upstream:
- `pggb`/`wfmash`/`seqwish`/`smoothxg`/`odgi` — MIT
- `vg` — MIT
- `gfaffix` — MIT

## Citations

When using these wrappers in published work, cite the underlying tools
(DOIs are embedded in each tool's `<citations>` block):

- PGGB / smoothxg: Garrison et al., *Nat. Biotechnol.* 2024 ([10.1038/s41587-023-01793-w](https://doi.org/10.1038/s41587-023-01793-w))
- wfmash: Guarracino et al., *Bioinformatics* 2024 ([10.1093/bioinformatics/btae155](https://doi.org/10.1093/bioinformatics/btae155))
- seqwish: Garrison & Guarracino, *Bioinformatics* 2023 ([10.1093/bioinformatics/btac743](https://doi.org/10.1093/bioinformatics/btac743))
- odgi: Guarracino et al., *Bioinformatics* 2022 ([10.1093/bioinformatics/btac308](https://doi.org/10.1093/bioinformatics/btac308))
- vg: Garrison et al., *Nat. Biotechnol.* 2018 ([10.1038/nbt.4227](https://doi.org/10.1038/nbt.4227))
- gfaffix: Steiner et al., *Bioinformatics* 2023 ([10.1093/bioinformatics/btac788](https://doi.org/10.1093/bioinformatics/btac788))
- PanSN-spec: <https://github.com/pangenome/PanSN-spec>

## Authors

- Anton Nekrutenko ([@nekrut](https://github.com/nekrut),
  [ORCID 0000-0002-5987-8032](https://orcid.org/0000-0002-5987-8032))
- Claude Opus 4.7 (Anthropic) — autonomous wrapper development +
  per-tool review pass.
