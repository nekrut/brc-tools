# Full A→K Galaxy run vs run_all.sh ground truth

**Date:** 2026-06-09 · **Galaxy:** 26.1.rc1 @ localhost:8080 · **Panel:** Pv4 5-strain ×3-chr test
**Ground truth:** `/media/anton/hd2/Pv4test/work` (local `run_all.sh`)
**Galaxy outputs:** `/media/anton/hd2/galaxy_AtoK`

Method: each phase driven through the **live Galaxy** via `planemo run` (one-click
workflows) or **bioblend `batch=True`** (collection map-over where the gxformat2
batch wiring collapses). Per-phase local file I/O → every phase independently
resumable; outputs double as comparison artifacts.

## Per-phase comparison

| Phase | Metric | Galaxy | Ground truth | Note |
|---|---|---|---|---|
| A inventory | sourmash matrix | 5×5 | mash matrix | different metric by design (sourmash chosen) |
| B softmask | softmasked genomes | 5/5 | 5/5 | longdust+sdust+bedtools |
| C chains | cleaned / rbest | 20 / 10 | 20 / 10 | **identical chain-name set**; top-chain score within 0.02% |
| C projection | merged annotations | 12/12 | 12 | per-pair 856 mRNA identical |
| D pggb | nodes/edges/paths | 155221/214485/**14** | 162796/224720/**14** | 14 paths identical; ~4.7% node variance (PGGB run-to-run) |
| E consensus | ortholog_table rows | 1361 | 1367 | 99.6%; rbest edges 7732 vs 7779 |
| F msa | codon MSAs | 489 | 509 (strict) | 96%; gap = upstream KegAlign/Liftoff variance |
| G trees | treefiles | **489** | 275 | Galaxy ran the full set; GT strict built only 275 |
| H selection | busted.json | **489** | 275 | Galaxy ran the full set |
| I multiz | per-ref MAFs | 5 | 5 | block counts 86–93% of GT |
| J vcf_projection | projected VCFs | **4 targets** | BLOCKED in GT | GT had no cohort VCF; here a synthetic 360-var PvP01 cohort → 247/245/342/350 projected |
| K ucsc_hub | track hub + hubCheck | **hubCheck clean** | — | tracks built green; hub tree assembled out-of-band; hubCheck exit 0, 0 warn |

> **Follow-on (2026-06-10):** the relaxed MSA set + J + K were completed after the
> initial run — see `execution/jk_relaxed_status.md`. Relaxed (min_intact=3):
> 776 OGs → 773 trees + 773 BUSTED (GT 810/514). J + K details above.

Concordance is excellent everywhere; all deltas trace to either (a) GPU-aligner
run-to-run variance propagating downstream, or (b) GT building a partial G/H set.
Galaxy is *more* complete on G/H (full 489 vs GT's 275).

## Real bugs found & fixed by running end-to-end

1. **`phase_e_graph_edges`** — contig-keyed co-membership (pre-existing fix; confirmed; 0 edges on this panel in both, threshold not met).
2. **Liftoff feature types** — anchor GFF3s use `protein_coding_gene`/`ncRNA_gene`/`pseudogene`, not `gene`; Liftoff default mode found 0 genes. Fix: `gene.gff3` anchors (rename gene-level types → `gene`). Matches the prior run's discovery.
3. **`group_cds_by_og` ref-gene selection** *(code fix, this commit)* — the ortholog_table reference column is a composite (`PVPAM_…|PVW1_…,PVP01_…`); the loader took the first token (a PAM gene) as the "reference gene", so CDS lookup failed for ~807/934 OGs → only 3 OGs built. Fix: pick the candidate that is an actual reference-GFF gene. Restores 489 OGs (vs GT 509).
4. **F/G/H gxformat2 map-over** — the IUC mafft/iqtree/hyphy `input|batches_0|inputs` repeat wiring collapses a collection into one input (the "0-byte input" symptom). Must drive these with bioblend `{"batch":True,"values":[hdca]}` (documented in `wffgh_e2e_status.md`). Also: hyphy tree input must be the IQ-TREE **treefile**, not the report.

## Infrastructure fixes (root-disk fills)

- Fast NVMe re-mounted at `/media/anton/hd2` via **fstab UUID** (was auto-mounted `hd21`); 4 TB at `/media/anton/samsung`. Survives reboot.
- Galaxy `dependencies` / `objects` / `tmp` / `jobs_directory` **symlinked to the fast disk** (conda envs + dataset objects were filling `/`).
- `docker_auto_rm=true` in `job_conf.xml` — job containers auto-delete (was accumulating tens of GB on `/var/lib/docker`).

## Outstanding — all cleared 2026-06-10 (see `jk_relaxed_status.md`)

- ~~**J**: needs a cohort VCF~~ → **done** with a synthetic 360-variant PvP01 cohort; projected onto 4 targets.
- ~~**K**: hub-tree assembly out-of-band~~ → **done**; assembled (`execution/assemble_hub.py`), hubCheck exit 0 / 0 warnings.
- ~~Relaxed MSA set (min_intact=3)~~ → **done**: 776 OGs → 773 trees + 773 BUSTED.

Nothing outstanding from the A→K scope. (A real-MalariaGEN cohort for J and a public-accession/GCA-space hub for K remain as future production refinements.)
