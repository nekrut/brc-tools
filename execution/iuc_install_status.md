# IUC tool installs for Pv4 pipeline workflows

Date: 2026-06-07. Galaxy 26.1.rc1 @ http://localhost:8080.
Main toolshed: https://toolshed.g2.bx.psu.edu.
Method: bioblend `ToolShedInstance` (resolve repo/owner + latest installable
revision) + `GalaxyInstance.toolshed.install_repository_revision`
(`install_resolver_dependencies=True`, conda). Status polled per repo until
`Installed`/`Error`. Each tool id then confirmed in `GET /api/tools`
(flat list grew 246 -> 264).

## API key note
Two keys exist. `pangenome-admin-key-2026` is a CONFIG bootstrap admin key:
fine for admin GET/install, but it is NOT a real user — `histories.create`,
`tools.build`, and tool runs return 400 "Only real users can create histories".
The `.env` `GALAXY_API_KEY=e6684cd2946c56a48c1b59e7c0dc5255` IS a real admin
user; used it for schema probes / anything user-scoped. (Same finding as WF-B.)

## Definitive result table

| Requested | Repo / owner | Rev installed | Installed? | Loaded tool_id(s) in /api/tools | Notes / failure |
|---|---|---|---|---|---|
| **sourmash** (sketch+compare) | — | — | **NO — repo does not exist** | none | No `sourmash` repo in main OR test toolshed (verified `/api/repositories?name=sourmash` = []; full 7672-repo listing grep = none; search `q=sourmash` = 0 hits). The prompt's premise (installable IUC `sourmash`) is wrong. sourmash exists on Bioconda but has no published Galaxy wrapper. WF-A sourmash path NOT installable / NOT validatable. |
| **busco** | busco / iuc | c5a90fa4b8dd | YES | `…/iuc/busco/busco/5.8.0+galaxy2` | Loaded. Cannot run prot mode yet: `lineage_dataset` select has 0 options (no lineage DB on server). Needs `data_manager_fetch_busco` to fetch `<clade>_odb10`. Pending, per prompt. |
| **lastz** | lastz / **devteam** | bf107d23242b | YES | `…/devteam/lastz/lastz_wrapper_2/1.04.52+galaxy0`, `…/lastz_d_wrapper/1.04.52+galaxy0` | Owner is **devteam, not iuc** (no iuc lastz exists). WF tool_id `lastz` maps to `lastz_wrapper_2`. |
| ucsc_axtchain | ucsc_axtchain / iuc | ac3a3feb4cf1 | YES | `…/iuc/ucsc_axtchain/ucsc_axtchain/482+galaxy2` | |
| ucsc_chainsort | ucsc_chainsort / iuc | 07c87c2ab74b | YES | `…/iuc/ucsc_chainsort/ucsc_chainsort/482+galaxy0` | |
| ucsc_chainprenet | ucsc_chainprenet / iuc | 2a417e645e61 | YES | `…/iuc/ucsc_chainprenet/ucsc_chainprenet/482+galaxy0` | |
| ucsc_chainnet | ucsc_chainnet / iuc | 5b65a92be96c | YES | `…/iuc/ucsc_chainnet/ucsc_chainnet/482+galaxy0` | |
| ucsc_netchainsubset | ucsc_netchainsubset / iuc | 794cf52edccc | YES | `…/iuc/ucsc_netchainsubset/ucsc_netchainsubset/482+galaxy0` | |
| ucsc_chainswap | ucsc_chainswap / iuc | 6a7085c7777e | YES | `…/iuc/ucsc_chainswap/ucsc_chainswap/482+galaxy0` | |
| ucsc_axttomaf | ucsc_axttomaf / iuc | 92c81e03341c | YES | `…/iuc/ucsc_axttomaf/ucsc_axtomaf/482+galaxy1` | Repo = `ucsc_axttomaf`; tool id = **`ucsc_axtomaf`** (one t). WF references `ucsc_axtomaf` — matches. |
| **liftoff** | liftoff / iuc | 3693aa025049 | YES | `…/iuc/liftoff/liftoff/1.6.3+galaxy0` | |
| **mafft** (rbc_mafft) | mafft / rnateam | 0a507f4bd19a | YES | `…/rnateam/mafft/rbc_mafft/7.526+galaxy2` (+`rbc_mafft_add`) | tool id `rbc_mafft` as expected. |
| **pal2nal** | pal2nal / iuc | a14d5c1e1fc4 | YES | `…/iuc/pal2nal/pal2nal/14.1+galaxy0` | |
| **trimal** | trimal / iuc | c2008ab22c09 | YES | `…/iuc/trimal/trimal/1.5.1+galaxy0` | (also exists under padge/ngphylogeny; used iuc per request.) |
| **hyphy** (busted) | hyphy_busted / iuc | 38ac249e5d69 | YES | `…/iuc/hyphy_busted/hyphy_busted/2.5.96+galaxy0` | hyphy is split per-method repos; installed `hyphy_busted` (the one WF-G uses). |
| **crossmap** (vcf) | crossmap_vcf / iuc | d8649c4e4c3a | YES | `…/iuc/crossmap_vcf/crossmap_vcf/0.7.3+galaxy0` | crossmap is split per-format; installed `crossmap_vcf` (WF-J uses `crossmap_vcf`). |
| **bcftools_annotate** | bcftools_annotate / iuc | 06eaadeffb7d | YES | `…/iuc/bcftools_annotate/bcftools_annotate/1.22+galaxy0` | |
| **bcftools_concat** | bcftools_concat / iuc | c3c930926708 | YES | `…/iuc/bcftools_concat/bcftools_concat/1.22+galaxy0` | |
| **bcftools_sort** | bcftools_sort / **greg** | bb0f975d69b4 | YES | `…/greg/bcftools_sort/bcftools_sort/1.4.0` | **No iuc `bcftools_sort` repo** (sort is not split out by iuc as its own repo). Only owner = `greg`, and it is OLD (v1.4.0 vs iuc 1.22 for the others). Works/loads, but version-mismatched vs the other bcftools tools. If WF-J needs a modern sort, alternatives: install `suite_bcftools`/iuc (`189e841b9cb7`, bundles sort+all) and re-point, or use `bcftools_norm`/sort-equivalent. Left as greg/1.4.0 for now. |

**Summary: 17/18 installed & loaded. 1 not installable (sourmash — no wrapper exists anywhere).**
All bcftools/crossmap/hyphy "suite" requests satisfied via the relevant
per-tool iuc repos (those toolshed suites are split per tool, not one repo).

## Per-repo install was fast
Conda envs for nearly all repos resolved in <10s each (caches warm on this
host) — `status=Installed` on first poll. No hangs, no timeouts, none had to be
skipped. liftoff (own env w/ minimap2) and hyphy were the only ones that took
appreciable build time, still well under the 560s box.

## WF-A param fixes (authored-blind, corrected against real schemas)
File: `workflows/inventory/inventory.gxwf.yml`. Edited (NOT committed):

1. **busco `mode` nesting was wrong.** Real IUC busco 5.8.0+galaxy2 schema:
   the mode conditional is `busco_mode` with test_param `mode`
   (values geno|tran|prot). WF-A had a top-level `state.mode: prot`, which does
   not exist. Fixed to:
   ```yaml
   busco_mode:
     mode: prot
   ```
   (`lineage.lineage_mode: select_lineage` and `adv.evalue` were already correct
   against the real schema — `lineage` cond test_param is `lineage_mode`,
   `adv` section has `evalue`.)
2. **busco `lineage_dataset` is a SELECT with 0 options** on this server (no
   lineage DB fetched). So even with correct nesting, busco prot cannot RUN
   until `data_manager_fetch_busco` downloads `apicomplexa_odb10`. Also the
   `busco_lineage` string input cannot directly feed a select param at runtime.
   Documented inline; busco e2e left PENDING (per prompt).
3. **sourmash steps flagged inline** as not-installable (no wrapper exists). The
   step `state` blocks are unverified (cannot probe a tool that isn't installed).

## BONUS WF-A sourmash e2e — NOT DONE (blocked, not skipped)
Cannot run: there is no sourmash Galaxy tool to install or invoke (see table
row 1). Verified against both toolsheds. No sketch/compare to map-over, so no
compare.csv producible. This is a hard blocker, not a time-box skip. busco e2e
also pending (needs lineage DB download — noted, not blocking).
