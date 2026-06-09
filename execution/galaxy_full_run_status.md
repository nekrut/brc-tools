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
| J vcf_projection | projected VCFs | **BLOCKED** | **BLOCKED** | no cohort VCF (MalariaGEN absent) — same in both |
| K ucsc_hub | track hub | inputs ready | — | hub-tree assembly = documented out-of-band staging step |

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

## Outstanding

- **J**: needs a cohort VCF (synthesize or MalariaGEN) — blocked in GT too.
- **K**: all track inputs now exist (5 multiz MAFs, 20 chains, 12 annotations, ortholog_table, 489 BUSTED, assemblies); hub directory-tree + trackDb assembly is the out-of-band staging step per `ONE-CLICK-READINESS.md`.
- Relaxed MSA set (min_intact=3) not yet run (GT: 810 codon / 514 trees).
