# Galaxy integration status — all pangenome wrappers loaded

Date: 2026-06-06

## Result: SUCCESS via ~/galaxy (preferred path)

Running Galaxy **26.1.rc1** (dev tip) serving ALL 41 of our tool XMLs (31 dirs; some
are multi-tool suites: odgi, vg, ucsc_kent).

- URL: http://localhost:8080
- Started: `cd ~/galaxy && GALAXY_SKIP_CLIENT_BUILD=1 ./run.sh --daemon`
- Stop:    `cd ~/galaxy && ./run.sh stop`
- Process mgr: gravity/supervisor (gunicorn + handler + celery + celery-beat all RUNNING)

## Tool loading — 41/41 OK, 0 failed

Verified via `GET /api/tools?in_panel=true`. All 11 pangenome sections present;
every expected tool id loaded, none missing, none unexpected:

| Section | tools |
|---|---|
| Input prep | pansn_rename, fasta_concat, anchor_prep, build_genomes_txt (4) |
| Graph build | pggb, wfmash, seqwish, smoothxg, gfaffix (5) |
| odgi | odgi_build, odgi_stats, odgi_viz, odgi_paths (4) |
| vg | vg_convert, vg_deconstruct, vg_view (3) |
| Masking/repeats | sdust, longdust (2) |
| MAF/multiz | process_maf, multiz_fold, maf_to_bigmaf_bed (3) |
| Chains/liftover | chainStitchId, chain_to_bigChain (2) |
| Annotation/genes | gene_bed, group_cds_by_og, toga2 (3) |
| Phylogenetics | pair_strains, iqtree3 (2) |
| Phase tools | phase_c2_triage, phase_c4_merge, phase_e_consensus, phase_e_graph_edges, phase_e_rbest_overlap (5) |
| UCSC hub | build_hub_bb, build_trackdb, ucsc_fatotwobit, ucsc_bedtobigbed, ucsc_genepredtobed, ucsc_gff3togenepred, ucsc_mafindex, ucsc_hubcheck (8) |

**Total: 41/41 loaded. No tool parse/load errors** in gunicorn.log.
Spot-checked `GET /api/tools/odgi_build` -> "odgi build" 0.9.4+galaxy0 and
`GET /api/tools/toga2` -> "TOGA2 ortholog rescue": both return full tool detail.

## Config changes made

- Rewrote `pangenome_tools_wfs/galaxy_config_local_tool_conf.xml` to list all 31
  dirs / 41 XMLs (was only 13) and copied it to `~/galaxy/config/local_tool_conf.xml`
  (galaxy.yml already references local_tool_conf.xml).

## odgi .og datatype

Latest dev Galaxy **ships the `odgi` datatype natively**
(`config/datatypes_conf.xml.sample`, registered as Binary subclass; confirmed via
`GET /api/datatypes` -> odgi present). The patch_og_datatype.sh append to binary.py
was therefore redundant and was reverted (galaxy source tree left clean). odgi tools
load fine.

## Blockers hit and resolved

1. **OutdatedDatabaseError** — the SQLite DB (universe.sqlite) was one alembic
   revision behind the dev-tip code (6925fe4c8a17 -> 28885b317f78). First daemon
   start failed in gunicorn. Fixed: backed up universe.sqlite, ran
   `./manage_db.sh upgrade` (single migration, succeeded), restarted. No data loss.
2. Client/static build: skipped via GALAXY_SKIP_CLIENT_BUILD=1 (prebuilt static/dist
   from May 25 present). API + tool loading fully functional; UI JS bundle may be
   stale vs dev tip but does not affect tool registration/verification.

## Not done (per scope)

- Did NOT install IUC deps (sourmash/busco/bedtools/liftoff/etc.) or run workflows.
- No git commit.
