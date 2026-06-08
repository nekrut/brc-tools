# Map-over helpers — build + wiring status

**Date:** 2026-06-07. **Galaxy:** 26.1.rc1 @ localhost:8080. No git commit.

## What was built

Two stdlib-only collection-constructor tools (modelled on
`tools/__pair_strains__`: Cheetah manifest loop → small Python symlinker →
`discover_datasets` grouping), both **planemo-green** and **live-loaded**.

### 1. `__cross_product__` (tool id `cross_product`)
- Two `list` inputs (anchors, queries) → **`list:list`** keyed
  outer=`{anchor}` / inner=`{query}`; **excludes anchor==query** by default
  (`--include-self` to keep). Carries the QUERY file in each cell.
- Nesting via flat `{anchor}__{query}.dat` files +
  `discover_datasets pattern="(?P<identifier_0>.+?)__(?P<identifier_1>.+)\.dat"`
  (the canonical Galaxy list:list pattern, confirmed against
  `galaxy/test/functional/tools/collection_creates_dynamic_nested.xml`).
- Guards: duplicate-id check on each list; rejects ids containing `__`.
- **planemo test: 2/2 passed** — (a) 2 anchors × 3 queries → nested
  `anc1:qry1 … anc2:qry3`; (b) self-exclusion (anchor `qry1` does NOT cross
  query `qry1`).

### 2. `__pair_sizes__` (tool id `pair_sizes`)
- Per-strain `.sizes` `list` → **`list:paired`** keyed `{A}__vs__{B}`
  (forward=A.sizes, reverse=B.sizes), using the **exact** `pair_strains`
  enumeration so the two paired collections are identifier-aligned and zip
  under map-over.
- Same `_forward/_reverse` discover pattern as `pair_strains`, `.sizes` ext,
  `tabular` format.
- **planemo test: 2/2 passed** — 3-strain unordered (A__vs__B/A__vs__C/B__vs__C)
  + both-directions case.

## Wiring (only where it closes a gap)

**WF-C `align_chain_project.gxwf.yml`** (re-imports with **zero tool_errors**,
41 steps; `planemo workflow_lint` = 0 ERROR, all tool ids valid):
- Added step **`pair_sizes`** (C.1b) off the `sizes` input.
- Repointed `chainprenet`, `chainnet`, **and** the rbest `chainnet_r` sizes
  inputs from the un-joinable flat `sizes` to `pair_sizes/pair_sizes`
  (cleaned: target=forward/query=reverse; rbest: target=reverse/query=forward).
- Added step **`cross_anchor_query`** (`cross_product` over `assemblies` ×
  `assemblies`, self excluded) as the C.4 anchor×query enumeration grid.
- Updated the workflow `doc:`, the `sizes` input doc, and README "Known
  limitations" 1 & 3 to mark the JOIN/enumeration gaps CLOSED and spell out the
  residual editor slot-binding.

**WF-K / WF-I / WF-J — intentionally NOT rewired** (see ONE-CLICK-READINESS.md):
- WF-K hub list:list layout is heterogeneous-axis → a constructor helper cannot
  express it; `build_trackdb` uses panel-wide scalars (out-of-band). The
  per-assembly 2bit fanout is already map-over.
- WF-I `-t/-qPrefix` is **cosmetic** (multiz_fold keys on element_identifier;
  verified in the wrapper) — no helper justified.
- WF-J N-1 fan-out needs two identifier-aligned input lists; no constructor
  closes it (the lists already exist upstream).

## Tool registration + restart
- Added a `Pangenome :: Collection helpers` section listing all three pair/cross
  tools to `~/galaxy/config/local_tool_conf.xml` and the mirror
  `brc-tools/galaxy_config_local_tool_conf.xml`.
- `./run.sh stop` then `GALAXY_SKIP_CLIENT_BUILD=1 ./run.sh --daemon` — clean
  restart, all gravity processes RUNNING.
- Post-restart `/api/tools/{id}`: `cross_product` (Cross product 1.0.0+galaxy0),
  `pair_sizes` (Pair sizes 1.0.0+galaxy0), `pair_strains` all load.

## Files changed (NOT committed)
- `tools/__cross_product__/` (NEW: cross_product.py/.xml, macros.xml, .shed.yml, test-data/*.fasta)
- `tools/__pair_sizes__/` (NEW: pair_sizes.py/.xml, macros.xml, .shed.yml, test-data/*.sizes)
- `workflows/align_chain_project/align_chain_project.gxwf.yml` (pair_sizes + cross_product wiring)
- `workflows/align_chain_project/README.md` (limitations 1 & 3 updated)
- `~/galaxy/config/local_tool_conf.xml` + `galaxy_config_local_tool_conf.xml` (Collection helpers section)
- `ONE-CLICK-READINESS.md` (NEW, repo root)
- `execution/mapover_helpers_status.md` (this file)
