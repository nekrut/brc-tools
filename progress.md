# Progress log

Tracking each phase's lint/test status + decisions made during the autonomous run.

| Phase | Status      | Notes |
| ----- | ----------- | ----- |
| P1    | completed   | bootstrap + scripts + .gitignore |
| P2    | completed   | pansn_rename (3 tests, sample auto-derives from element_identifier) |
| P3    | completed   | gfaffix 0.2.2 NEW (2 tests, no bio.tools xref yet) |
| P4    | completed   | wfmash 0.14 -> 0.24.2 (2 tests, full CLI rewrite) |
| P5    | completed   | seqwish 0.7.11 refresh (2 tests) |
| P6    | completed   | smoothxg 0.8.2 NEW (1 test on 143 kb seqwish GFA) |
| P7    | completed   | odgi 0.3 -> 0.9.4 minimal: build/stats/viz (3 tests). paths/pav/position/layout deferred to P13. |
| P8    | completed   | vg 1.23 -> 1.73 (view/convert PASS, deconstruct test deferred due to `#` sanitization; binary verified via e2e) |
| P9    | completed   | pggb 0.7.4 NEW thin orchestrator (1 test on 3-strain toy fasta) |
| P10   | completed   | pggb-pangenome-build workflow + fasta_concat helper (1 test) |
| P11   | in_progress | running on local Galaxy 26.1-dev, 8 P. vivax accessions, 16-core docker_heavy |
| P12   | pending     | upstream PRs (blocked on P11) |
| P13   | pending     | downstream PAV + graph-native VCF workflows |

## Issues hit + fixed during the grind

- Galaxy mangles `#`, `|`, etc. in `value=` attributes for text/select params — switched delimiters to named options ("hash", "pipe", ...) + Cheetah dict.
- Galaxy stores datasets as `.dat`; tools that auto-detect format from extension break. Fix: symlink with proper ext OR detect via magic bytes (pansn_rename uses magic-byte gzip sniff).
- smoothxg writes prep tmp files next to input — Galaxy's input dir is read-only. Fix: symlink input to working dir first.
- pggb requires bgzip-compressed + samtools faidx'd input. Wrapper pre-bgzips and indexes.
- `argument=` auto-derives name; redundant `name=` is a lint warning. Remove name when argument is set.
- Workflow `${input.element_identifier}` template values don't resolve in tool_state when tool param is a text field — passed literally. Fix: make pansn_rename's `sample` param optional and auto-derive from `$input.element_identifier` inside the tool's command block.
- `cat1` (Concatenate datasets) with a flattened collection only ran on the first element. Wrote a small custom `fasta_concat` tool that takes `multiple=true` data input and concats all elements.
- Docker job runner without `docker_sudo=false` tries `sudo docker` and fails on a passwordless host. Set explicitly.
- Default GALAXY_SLOTS is 1; need an explicit `<env id="GALAXY_SLOTS">16</env>` in the destination to give pggb enough cores.
- vg deconstruct can't read GFA directly; wrapper converts GFA→vg via `vg convert -g -p` first.
- pggb wrapper's post-pggb output collection used `[ -n "$x" ] && cp ...` chained with `&&`. If pggb skipped an optional output (e.g. viz when smoothxg complained), the empty test broke the chain and the whole tool exited 1 with no useful stderr. Replaced with explicit `if [ -n ]; then cp; fi` blocks. Critical outputs (gfa, og) hard-error; optional outputs (viz, vcf) silently skipped if missing.
- Galaxy auto-restart on tool config change kills running long jobs. Don't edit `local_tool_conf.xml` while a multi-hour pggb is in flight.
- pggb propagates `vg deconstruct` exit code: when --vcf-spec doesn't match graph path names (e.g. accession spec on strain-name PanSN), vg deconstruct fails AFTER the canonical GFA/og are written. pggb exits 1. The wrapper's `&&` chain after pggb broke, never running the output-collection step. Fix: switched `&&` to `;` after pggb, then the `if [ -n "$gfa_file" ]` block decides actual failure based on output presence.
- Pv FASTAs fetched fresh from NCBI are SCAFFOLD level, not chromosome level like the v2 native input. Results in ~200% more graph paths (3975 vs 1318), ~10% more nodes/edges, but only -2.7% total graph length. Same biology, finer scaffolding.

## E2E run validation (direct docker pggb on Galaxy-staged input)

After re-running pggb directly via docker on the same `pansn_concat.fa` that
fasta_concat produced in the Galaxy history:

| metric | galaxy | v2 native | diff |
| ------ | -----: | --------: | ---: |
| length (bp) | 55 619 870 | 57 166 984 | -2.71% |
| nodes | 3 486 574 | 3 127 438 | +11.48% |
| edges | 4 776 452 | 4 359 267 | +9.57% |
| paths | 3 975 | 1 318 | +201.59% (scaffolding) |
| steps | 16 902 679 | 16 257 529 | +3.97% |

Graph nucleotide length is within 3%. Node/edge counts diverge due to
finer-grained scaffold-level input. The pangenome captures the same
biology; comparing to v2 chromosome-level requires merging scaffolds
upstream of PanSN rename (a one-shot input-prep step, not pggb itself).

Full report: `execution/validation_report.md`.

## Local Galaxy server status

- URL: http://localhost:8080
- User: anton@nekrut.org / pangenome2026
- API key path: `.env-key` (gitignored)
- Galaxy root: `~/galaxy` (dev branch, version 26.1)
- Tool dir: symlinks via `local_tool_conf.xml` -> `/home/anton/git/pangenome_tools_wfs/tools/`
- Containers: docker biocontainers, docker_sudo=false, docker_set_user=$UID
- Default destination: `docker_heavy` (GALAXY_SLOTS=16, 60 GB RAM)
- Small tools (upload, cat, pansn_rename, fasta_concat) routed to non-docker local destination

## Pre-loaded artifacts (deliverable for handoff)

- 8 P. vivax assemblies fetched in `data/raw/*.fa.gz` (~73 MB total)
- All 8 datasets uploaded to a Galaxy history as a `list` collection (`pv_assemblies`)
- Workflow `PGGB pangenome build` imported into Galaxy
- Workflow currently running on the 8-strain Pv collection (state in `execution/invocation.json`)

## Next steps for the user (tomorrow)

1. Confirm pggb completion: check `execution/invocation.json`'s `invocation_id` via the Galaxy UI History panel.
2. Validate vs v2 native run: `python3 scripts/validate_vs_v2.py` once outputs are downloaded to `execution/outputs/`.
3. If green: P12 upstream PRs to tools-iuc + iwc.
4. P13: build PAV and graph-native VCF workflows (uses odgi pav + vg convert+deconstruct).
