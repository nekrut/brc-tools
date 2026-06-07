# Pangenome Galaxy Tools + Workflow — Autonomous Build Plan

Goal: surface the v3 *P. vivax* PGGB pangenome build as a Galaxy workflow. Three deliverables:

1. **Tool wrappers** (new + version-bumped) committed under `tools/`.
2. **Workflow** (`.ga`) that re-creates the 8-strain PGGB graph end-to-end, plus IWC packaging.
3. **End-to-end execution** of the workflow on a real Galaxy instance against the 8 P. vivax assemblies — produce the same `.smooth.fix.gfa.gz` / `.og` / VCF outputs as the v2 native run.

Source of truth for the recipe: `/home/anton/git/Pv4-pangenome/v3/writeup/PANGENOME.md` §"How we built the graph". The native pggb invocation:

```
pggb -i pggb_input.fa.gz -o pggb_out -s 5000 -p 90 -n 8 -k 23 -t 18 -V GCA_900093555.2 -Y '#'
```

---

## 0. Repo layout (this directory)

```
pangenome_tools_wfs/
├── PLAN.md                           # this file
├── tools/                            # tool wrappers (one dir per tool/suite)
│   ├── pansn_rename/                 # NEW custom
│   ├── pggb/                         # NEW
│   ├── gfaffix/                      # NEW
│   ├── smoothxg/                     # NEW
│   ├── wfmash/                       # FORK from tools-iuc, version bump 0.14→0.24.2
│   ├── seqwish/                      # FORK from tools-iuc, verify against 0.7.11
│   ├── odgi/                         # FORK from tools-iuc, 0.3→0.9.4 + add paths/pav/position/layout/stats
│   └── vg/                           # FORK from tools-iuc, 1.23→1.73 + ensure deconstruct/convert solid
├── workflows/
│   └── pggb-pangenome-build/
│       ├── pggb-pangenome-build.ga
│       ├── pggb-pangenome-build-tests.yml
│       ├── .dockstore.yml            # IWC format
│       ├── .workflowhub.yml
│       ├── CHANGELOG.md
│       ├── README.md
│       └── test-data/                # tiny test inputs (<1 MB each)
├── execution/                        # artifacts of the real Pv run
│   ├── inputs.tsv                    # 8 accessions + URIs
│   ├── invocation.json               # bioblend invocation record
│   └── outputs/                      # downloaded final products
└── scripts/                          # automation helpers
    ├── fetch_pv_assemblies.sh
    ├── upload_history.py             # bioblend uploader
    └── run_workflow.py               # bioblend invocation + wait
```

**Branch / push strategy: LOCAL-ONLY until full e2e passes.** All work happens in this directory (`pangenome_tools_wfs/`), committed to a local git repo. No PRs to `galaxyproject/tools-iuc` or `galaxyproject/iwc` until:

1. every wrapper passes `planemo lint && planemo test --biocontainers` locally,
2. the workflow passes `planemo test_workflow` on toy data locally,
3. the real 8-strain Pv e2e run on a local Galaxy completes and `odgi stats` matches the v2 native run within ±0.5 %.

Only then do we rebase each tool onto a fresh tools-iuc fork branch and file PRs; the workflow goes to an iwc fork under `workflows/comparative_genomics/pggb-pangenome-build/`. Upstreaming is **post-validation** — see §6.

---

## 1. Inventory of wrappers — what's there, what's missing

(Confirmed by inspecting tools-iuc `tools/` listing + each `macros.xml`/`.shed.yml` HEAD on 2026-05-25.)

| Tool         | Upstream (bioconda)     | tools-iuc state         | Action                                                 |
| ------------ | ----------------------- | ----------------------- | ------------------------------------------------------ |
| wfmash       | 0.24.2                  | 0.14.0                  | **Version bump** + re-test                             |
| seqwish      | 0.7.11                  | 0.7.11                  | Verify, refresh profile, add `+galaxy0` suffix         |
| smoothxg     | 0.8.2                   | **missing**             | **NEW wrap**                                           |
| odgi         | 0.9.4                   | 0.3 (build, viz only)   | **Major bump** + new subcommands: paths/pav/position/layout/stats |
| vg           | 1.73.0                  | 1.23.0 (view, convert, deconstruct) | **Version bump**, verify deconstruct + convert flags |
| pggb         | 0.7.4                   | **missing**             | **NEW wrap** — wraps the entire shell pipeline; pin image digest |
| gfaffix      | 0.2.2                   | **missing**             | **NEW wrap** — single Rust binary                      |
| PanSN rename | N/A                     | N/A                     | **NEW custom** — Python wrapper, ~30 lines             |
| fasta-merge / bgzip | already in IUC   | OK                      | Use as-is in workflow                                  |

Note: PANGENOME.md table was slightly stale — `vg deconstruct` / `vg convert` already exist in tools-iuc, only need bumping.

---

## 2. Tool wrapper specs

For every wrapper: profile `25.0`, `@TOOL_VERSION@+galaxy@VERSION_SUFFIX@` versioning, `detect_errors="aggressive"`, `format="markdown"` help, bio.tools xref, DOI citation, conda dependency from bioconda. Tests use `<assert_contents>` with `<has_text>` (not golden files >1 MB). Run `planemo format && planemo lint && planemo test --biocontainers` until green.

### 2.1 pansn_rename (NEW custom)

- Python wrapper: reads a FASTA, prefixes every `>contig` header with `SAMPLE#HAP#` per PanSN spec.
- Inputs: `input` (fasta/fasta.gz), `sample` (text), `haplotype` (integer, default 1), `delimiter` (text, default `#`).
- Output: PanSN-renamed FASTA, optionally bgzipped.
- Tests: tiny 2-contig FASTA → assert header rewrite.
- Requirements: `python`, `pyfastx` (or biopython).

### 2.2 pggb (NEW)

- Wrap the full `pggb` pipeline binary (bioconda recipe).
- Inputs: multi-FASTA (bgzip), `-s` segment length, `-p` mapping identity, `-n` n_haplotypes, `-k` min-match, `-V` ref-strain for VCF, `-Y` PanSN delimiter, `--poa-params`. `-t` from `$GALAXY_SLOTS`. Group advanced flags in `<section>`.
- Outputs: `.smooth.fix.gfa.gz` (gfa1), `.smooth.fix.og`, `.smooth.fix.og.lay`, `.smooth.fix.affixes.tsv.gz`, `.params.yml`, `.log`, viz PNGs, optional deconstruct VCF (only when `-V` set, gated by `<filter>`).
- `from_work_dir` per output; create staging dir `pggb_out`.
- Tests: minimal 3-sequence FASTA, default-ish params, assert GFA header `H\tVN:Z:1.0`, assert `.og` magic bytes via `<has_size min="...">`.
- Memory: add `<stdio>` OOM regex (PGGB orchestrates wfmash + smoothxg, both can OOM).
- Note: PGGB is a bash orchestrator; conda gives us the binary but pins all the sub-tool versions. Surface `--version` so users see the bundle version.

### 2.3 gfaffix (NEW)

- Single Rust binary. Inputs: GFA in. Outputs: GFA out + affixes TSV.
- Trivial wrapper, ~50 lines XML.
- Test: 4-node GFA with one shared prefix → assert collapse.

### 2.4 smoothxg (NEW)

- Inputs: GFA in, `--block-id-min` (float, default 0.9), `--poa-params`, `--max-edge-jump`, etc.
- Outputs: smoothed GFA.
- Surface only the params used by pggb's invocation + commonly-tweaked ones.
- Memory: `<stdio>` OOM regex (smoothxg is the memory-heaviest step).

### 2.5 odgi (BUMP + EXPAND)

Bump `@TOOL_VERSION@` 0.3 → 0.9.4. Keep `build.xml` + `vis.xml`; add new files:

- `odgi_paths.xml` — extract paths / list path names
- `odgi_pav.xml` — presence/absence by sample (`-S`, `-B` BED region)
- `odgi_position.xml` — coordinate translation
- `odgi_layout.xml` — 2D layout
- `odgi_stats.xml` — graph stats
- `odgi_sort.xml` (optional but commonly chained)
- `odgi_view.xml` (og→gfa export)

Shared `macros.xml` holds requirements + version tokens. Test data: tiny `.og` (build from a 4-seq toy FASTA in the build test, then reuse via test-data symlinks).

Watch: `.og` format changed across major versions — old test fixtures must be regenerated. Set datatype: `odgi` (already registered in Galaxy datatypes; verify in current `lib/galaxy/datatypes/binary.py`).

### 2.6 vg (BUMP)

Bump 1.23 → 1.73 across existing `view.xml`, `convert.xml`, `deconstruct.xml`. Audit flag set against `vg convert --help` / `vg deconstruct --help` of 1.73 (run via biocontainer). Cover at minimum:

- `vg convert -g <gfa> -p > out.gbz` (GFA → GBZ for the graph-native VCF projection)
- `vg deconstruct -P <ref> graph.gbz > vcf` (per-target VCF emission)

Bump test golden files. If `.gbz` datatype missing in Galaxy, add it (PR to galaxyproject/galaxy core).

### 2.7 wfmash, seqwish (BUMP / verify)

- wfmash 0.14 → 0.24.2: re-audit flags (`-s`, `-p`, `-n`, `-Y`, `-X`, etc.).
- seqwish 0.7.11 stays; refresh profile to 25.0, add `+galaxy0` suffix, add bio.tools xref if missing.

---

## 3. Workflow design (`pggb-pangenome-build.ga`)

### Inputs

- `assemblies` — `list:paired`? No — a flat `list` collection of FASTAs, element identifier = strain accession (e.g., `GCA_900093555.2`).
- `ref_strain` (text) — accession used for `-V`.
- `n_haplotypes` (integer, default 8) — derived from collection size if possible (Galaxy doesn't auto-derive, expose param).
- Numeric params: `segment_length` (5000), `mapping_id` (90), `min_match` (23), `pansn_delim` (`#`).

### Steps

```
[in: assembly collection]
  ├─► PanSN rename (map-over collection)  — one PanSN-prefixed FASTA per strain
  ├─► fasta-merge (collapse list → single fasta)
  ├─► bgzip + samtools faidx
  └─► pggb (s/p/n/k/V/Y from params)
        ├─ out: smoothed GFA (gz)
        ├─ out: odgi .og
        ├─ out: odgi .og.lay
        ├─ out: viz PNG
        ├─ out: params.yml + log
        └─ (optional) per-ref VCF via -V
[downstream block — separate workflow modules, NOT required for build]
   ▸ odgi stats / viz on .og
   ▸ vg convert GFA→GBZ → vg deconstruct per non-ref strain
   ▸ odgi pav over CORE-1:1 BED regions
```

Each downstream module is a separate `.ga` so the build workflow stays focused. Initial deliverable is the build wf only.

### Workflow tests (IWC layout)

- `pggb-pangenome-build-tests.yml` (planemo workflow-test format): tiny 3×~5 kb mock assemblies in `test-data/`. Assert output exists + GFA header present + non-empty `.og`.
- Real-data execution lives in `execution/` (separate, not a unit test).

### IWC packaging

- `.dockstore.yml` (subclass Galaxy, points at the `.ga`).
- `.workflowhub.yml` (CC-BY-4.0, author = Nekrutenko + Claude as contributor).
- `CHANGELOG.md` + `README.md` (problem, inputs, params, outputs, runtime estimate).

---

## 4. End-to-end run on Galaxy (the "replicate v2 PGGB" deliverable)

**Primary target: local Galaxy.** Spin up a local Galaxy server, install our fork-built wrappers from the local toolshed, run the workflow on the 8 Pv assemblies. usegalaxy.org/.eu are a follow-up once wrappers are upstreamed.

### 4.1 Local Galaxy setup — two-stage

**Stage A — `planemo serve` for P2–P10 wrapper/workflow dev** (ephemeral, auto-reloads on XML edits):

```bash
planemo serve --port 8080 --galaxy_root ~/galaxy \
  tools/pansn_rename tools/pggb tools/gfaffix tools/smoothxg \
  tools/wfmash tools/seqwish tools/odgi tools/vg
```

**Stage B — persistent `release_25.0` Galaxy for P11 e2e + P13 downstream runs** (stable, survives the 3-6h pggb job):

```bash
git clone -b release_25.0 https://github.com/galaxyproject/galaxy ~/galaxy
cd ~/galaxy && ./run.sh --daemon         # http://localhost:8080
bash scripts/install_local_tools.sh      # symlinks our tools/ into config/tool_conf.xml.sample
bash scripts/patch_og_datatype.sh        # adds odgi 0.9 .og to lib/galaxy/datatypes/binary.py
```

Bioconda required on host: `mamba install -c bioconda -c conda-forge planemo bioblend`. Pin Galaxy to `release_25.0` so the `profile="25.0"` token matches.

Resource budget confirmed: ≥64 GB RAM, ≥32 cores, ≥50 GB scratch. Run pggb with `-t 32`.

### 4.2 Preflight

- `python scripts/galaxy_tool_checker.py --workflow workflows/pggb-pangenome-build/*.ga --url http://localhost:8080` — fail-fast if any tool ID/version is wrong.
- Generate an admin API key via the local Galaxy UI → save to `.env`.
- Verify each tool loads in the UI (no XML parse errors); `planemo serve` surfaces these in stderr.

### 4.3 Inputs

Fetch the 8 P. vivax assemblies listed in PANGENOME.md (PvP01, Sal-I, PvW1, PAM, PvSY56, PvT01, PvC01, MHC087) via `scripts/fetch_pv_assemblies.sh` (NCBI datasets CLI → local `data/raw/`). Upload to a fresh history via bioblend; tag as `pv-pangenome-build-2026-05-25`. Local file uploads are fast (no network egress).

### 4.4 Invocation

```python
# scripts/run_workflow.py
from bioblend.galaxy import GalaxyInstance
gi = GalaxyInstance("http://localhost:8080", key=os.environ["GALAXY_API_KEY"])
inv = gi.workflows.invoke_workflow(
    workflow_id, history_id=hist_id,
    inputs={"0": {"id": coll_id, "src": "hdca"}},
    params={"ref_strain": "GCA_900093555.2", "segment_length": 5000,
            "mapping_id": 90, "n_haplotypes": 8, "min_match": 23,
            "pansn_delim": "#"})
```

Wait via `wait_for_invocation` (no polling). Log invocation_id + history_id to `execution/invocation.json`. Expected wall time ~3–6 h on a 32-core box (per PANGENOME.md §"Re-running on a different species").

### 4.5 Validation against native v2 outputs

Download final GFA + `.og` to `execution/outputs/`. Compare to `Pv4-pangenome/v2/pggb_out/*.smooth.fix.gfa.gz`:

- `odgi stats` on both → expect node/edge counts within ±0.5% (non-deterministic POA can shift by tiny amounts).
- `md5sum` on canonicalized GFA (sort by S/L/P lines) as bonus stability check.
- Run `odgi viz` on the Galaxy `.og` and visually diff against `Pv4-pangenome/v2/pggb_out/*.draw.png`.

If outputs match → workflow is production. Mismatch → triage, log, iterate.

### 4.6 After local pass → public Galaxy

Once the local run is green, re-run on `usegalaxy.org` (or `.eu`) as a second validation — same workflow `.ga`, same inputs (re-upload), same params. Confirms the wrappers behave identically under a production-scale runner / job destination.

---

## 5. Autonomous execution sequence

Each phase has a single owner-loop: implement → `planemo lint` → `planemo test --biocontainers` → if green, commit + PR; if red, fix and retry. No human checkpoints between phases unless explicitly flagged.

All phases land **local-only** (commits in this repo) until P12. No upstream PRs filed before then. Commits use `Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>` trailer.

| Phase | Item | Block-time est. | Output (local) |
| ----- | ---- | --------------: | -------------- |
| P1    | Bootstrap repo: skeleton dirs, this PLAN.md, scripts stubs | 30 min | local git init |
| P2    | `pansn_rename` (custom Python wrapper) | 2 h | `tools/pansn_rename/` green |
| P3    | `gfaffix` (simplest external wrap) | 2 h | `tools/gfaffix/` green |
| P4    | `wfmash` version bump 0.14→0.24.2 | 2 h | `tools/wfmash/` green |
| P5    | `seqwish` refresh | 1 h | `tools/seqwish/` green |
| P6    | `smoothxg` NEW | 4 h | `tools/smoothxg/` green |
| P7    | `odgi` major bump + 5 new subcommands | 8 h | `tools/odgi/` green |
| P8    | `vg` 1.23→1.73 + deconstruct/convert audit | 4 h | `tools/vg/` green |
| P9    | `pggb` NEW (the boss) | 6 h | `tools/pggb/` green |
| P10   | Workflow `.ga` + `planemo test_workflow` on toy data | 6 h | `workflows/.../*.ga` green |
| P11   | Stand up local Galaxy, install all 8 wrappers, e2e on 8 Pv assemblies, validate vs v2 native | 4 h wall + ~3-6 h compute | `execution/outputs/` + diff report |
| P12   | (gated on P11 green) Rebase each tool onto tools-iuc fork branch, file PRs; file iwc PR for workflow | 4 h | tools-iuc PRs + iwc PR |
| P13   | Downstream module workflows: (a) odgi pav over CORE-1:1 BED regions, (b) vg convert→deconstruct graph-native VCF projection. Local first, then iwc PRs after P11 gate. | 8–12 h dev + ~6 h compute | `workflows/pggb-pav/`, `workflows/pggb-vcf-projection/` |

P2–P9 can run in parallel-ish (independent dirs). The hard ordering is: **all wrappers green → P10 workflow → P11 e2e → P12 upstream**.

### Per-phase autonomy loop

```
1. git checkout -b phase-<N>-<tool> (in this local repo)
2. scaffold via `planemo tool_init` (or `curl` the existing tools-iuc dir for bumps)
3. edit XML, write tests, write test-data
4. planemo format && planemo lint && planemo test --biocontainers
5. iterate up to N=5 retries per failure class; if N exceeded, write phase-blocker note + continue with next phase
6. git commit locally; merge into a local `main` branch (no remote push)
7. record state + lint/test summary in progress.md
```

Failure-mode handling (no human in loop):
- `planemo test` fails on Docker → switch to `--no_conda_auto_init --no_dependency_resolution` after building a conda env (skill SKILL.md §8).
- biocontainer not yet on quay → fall back to mulled or wait + retry.
- lint warns on tokens vs xml-macro confusion → auto-fix per skill SKILL.md §3.

---

## 6. Verification matrix (definition of done)

**Local validation gate** (must all be ✅ before any upstream push):

- [ ] All 8 wrappers pass `planemo lint` locally (no errors, ≤2 warnings allowed).
- [ ] All 8 wrappers pass `planemo test --biocontainers` locally.
- [ ] Workflow `.ga` passes `planemo test_workflow` on toy 3-sample data locally.
- [ ] Local Galaxy spins up with all 8 wrappers installed; workflow imports cleanly.
- [ ] Real-data run on 8 P. vivax assemblies completes on local Galaxy; GFA + .og artifacts in `execution/outputs/`.
- [ ] `odgi stats` of local-Galaxy run matches v2 native run within ±0.5 %.

**Upstream phase** (only after the gate is green):

- [ ] (Optional) re-run workflow on `usegalaxy.org` / `.eu` as second validation.
- [ ] tools-iuc PRs filed, one per wrapper.
- [ ] iwc PR filed with `.dockstore.yml`, tests.yml, CHANGELOG, README.

---

## 7. References (consult during work)

- Galaxy tool-dev skill: `~/.claude/skills/galaxy/tool-dev/SKILL.md` (canonical)
- Galaxy integration / bioblend: `~/.claude/skills/galaxy/galaxy-integration/`
- IUC standards: https://galaxy-iuc-standards.readthedocs.io/en/latest/best_practices.html
- tools-iuc repo: https://github.com/galaxyproject/tools-iuc
- iwc repo (workflow PR format): https://github.com/galaxyproject/iwc
- planemo docs: https://planemo.readthedocs.io/
- galaxy-brain (jmchilton): https://github.com/jmchilton/galaxy-brain — for AI-assisted scaffolding patterns
- Pv recipe + params source: `/home/anton/git/Pv4-pangenome/v3/writeup/PANGENOME.md`
- Native v2 outputs to diff against: `/home/anton/git/Pv4-pangenome/v2/pggb_out/`

---

## Decisions (resolved 2026-05-25)

1. **Local Galaxy:** two-stage. `planemo serve` during P2–P10 wrapper dev. Persistent `release_25.0` checkout for P11 e2e + P13 downstream runs.
2. **Compute box:** plenty (≥64 GB RAM, ≥32 cores). Run pggb with `-t 32`, no OOM concerns.
3. **pggb wrap:** thin orchestrator only. Wrap the binary as-is, preserve internal smoothxg loop. Exploded variant is *not* in scope.
4. **Pv inputs:** fetch fresh via NCBI datasets CLI. `scripts/fetch_pv_assemblies.sh` hits the 8 accessions in PANGENOME.md.
5. **`.og` datatype bump:** patch local Galaxy in-place (`lib/galaxy/datatypes/binary.py`). Core PR deferred to P12 upstreaming.
6. **PR attribution:** co-authored with Claude Opus 4.7 (`Co-Authored-By` trailer on each commit).
7. **P13 in scope:** downstream PAV + graph-native VCF workflows are part of this autonomous run, not a follow-up. Updates the phase table — P13 is no longer "stretch".
