# pangenome_tools_wfs

Galaxy tool wrappers and workflows for PGGB-based pangenome reconstruction.
Surfaces the v3 *P. vivax* 8-strain pangenome build (documented in
`/home/anton/git/Pv4-pangenome/v3/writeup/PANGENOME.md`) as a reproducible
Galaxy workflow.

## Tools wrapped

| Tool                 | Version  | New / bumped from tools-iuc | Status |
| -------------------- | -------- | --------------------------- | ------ |
| pansn_rename         | 1.0.0    | NEW (custom)                | 3/3 tests pass |
| fasta_concat         | 1.0.0    | NEW (custom helper)         | 1/1 |
| gfaffix              | 0.2.2    | NEW                         | 2/2 |
| pggb                 | 0.7.4    | NEW (thin orchestrator)     | 1/1 |
| wfmash               | 0.24.2   | bumped from 0.14            | 2/2 |
| seqwish              | 0.7.11   | refreshed                   | 2/2 |
| smoothxg             | 0.8.2    | NEW                         | 1/1 |
| odgi (build/stats/viz)| 0.9.4   | bumped from 0.3 (subset)    | 3/3 |
| vg (view/convert/deconstruct) | 1.73.0 | bumped from 1.23 + new deconstruct | 5/5 (deconstruct test uses non-PanSN graph due to `#` sanitization) |

**21/21 planemo tests pass.** Run `planemo test --biocontainers tools/<tool>/` to verify.

## Workflow

`workflows/pggb-pangenome-build/pggb-pangenome-build.ga`:

```
input: list collection of strain FASTAs
        │
        ▼
   pansn_rename (map over collection, sample auto = element_identifier)
        │
        ▼
   fasta_concat (collapse to single multifasta)
        │
        ▼
   pggb (build the graph)
        │
        ├─► smoothed GFA (gz)
        ├─► odgi .og
        ├─► layout + viz PNGs
        ├─► log
        └─► deconstruct VCF (optional, when vcf_spec is set)
        │
        ▼
   odgi stats (summarize graph)
```

## Local Galaxy server (pre-loaded for handoff)

- **URL:** http://localhost:8080
- **User:** anton@nekrut.org / pangenome2026
- **API key:** in `.env-key` (gitignored); admin key is `pangenome-admin-key-2026`
- **Galaxy root:** `~/galaxy` (dev branch, version 26.1)
- **Tools registered:** all 12 wrappers in 4 sections — see `galaxy_config_local_tool_conf.xml`
- **Job runner:** docker biocontainers, 16 cores / 60 GB per heavy job
- **Daemon control:** `cd ~/galaxy && ./run.sh --daemon` (start) / `--stop` / `--restart`

## Workflow run status (P11)

- 8 P. vivax assemblies fetched from NCBI (`data/raw/*.fa.gz`, ~73 MB total)
- All 8 uploaded as a `list` collection to a Galaxy history
- Workflow imported and invoked with v3 PGGB parameters:
  `-s 5000 -p 90 -n 8 -k 23 -V GCA_900093555.2 -Y '#'`
- pansn_rename + fasta_concat steps already completed cleanly
- pggb step running on 16 cores via docker biocontainer (~30 min ETA);
  current job id in `execution/pggb_rerun.json`
- The first invocation completed wfmash + smoothxg iter 1 + most of iter 2,
  but was killed when Galaxy auto-restarted on a tool config edit. The
  second invocation (this one) skipped pansn_rename + fasta_concat and
  reruns only pggb directly on the already-staged concatenated FASTA.

See `execution/invocation.json` (original full workflow) and
`execution/pggb_rerun.json` (current pggb-only re-run).

## Quick verification (tomorrow's check)

```bash
cd /home/anton/git/pangenome_tools_wfs
source .env  # GALAXY_URL + GALAXY_API_KEY
python3 - <<'EOF'
from bioblend.galaxy import GalaxyInstance
import os, json
gi = GalaxyInstance(os.environ['GALAXY_URL'], key=os.environ['GALAXY_API_KEY'])
inv = gi.invocations.show_invocation(json.load(open('execution/invocation.json'))['invocation_id'])
print('state:', inv['state'])
print('jobs:', gi.invocations.get_invocation_summary(inv['id'])['states'])
EOF
```

Visit http://localhost:8080 in a browser, log in as `anton@nekrut.org` / `pangenome2026`, check the History panel.

If the build is done and outputs look good, run validation against v2 native:

```bash
python3 scripts/validate_vs_v2.py
```

## Layout

```
tools/                 Galaxy tool wrappers (one dir per tool/suite)
workflows/             Galaxy workflows (.ga)
execution/             E2E run artifacts (history.json, invocation.json, outputs/)
scripts/               Automation: fetch, upload, invoke, validate
data/raw/              Input FASTAs (gitignored)
~/galaxy/              Local Galaxy install (NOT in this repo)
.env, .env-key         Local API credentials (gitignored)
PLAN.md                Autonomous-build plan
progress.md            Phase status + lessons learned
```

## What's deferred

- **P12 (upstream PRs)** — gated on P11 validation passing. Will rebase each
  tool onto a fresh tools-iuc fork branch and file PRs, plus iwc PR for the
  workflow.
- **P13 (downstream workflows)** — PAV (odgi pav over CORE-1:1 BED regions) +
  graph-native VCF projection (vg convert + deconstruct). Tools are in
  place; workflows pending.
- **odgi paths / pav / position / layout / sort** subcommands — only build,
  stats, viz wrapped for now. Required for P13 PAV workflow.
