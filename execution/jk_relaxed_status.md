# Phases J / K / relaxed-MSA — completion status (2026-06-10)

Follow-on to the A→K run (`galaxy_full_run_status.md`). All through the live
Galaxy @ localhost:8080, 12 local workers.

## Relaxed MSA set (min_intact=3)
- group_cds mi=3 → **776 OGs**; mafft/pal2nal 776; 3 failed elements filtered
  (`__FILTER_FAILED_DATASETS__`) → **773 trees + 773 BUSTED**.
- vs GT core_relaxed: 810 codon / 514 trees. 96% codon; Galaxy ran the *full*
  tree+BUSTED set (GT built a partial 514).
- Driven by bioblend batch map-over; restart-robust resume after a worker-bump
  Galaxy restart.

## J — vcf_projection (was BLOCKED, now done)
- Synthesized a **360-variant PvP01 cohort VCF** (no MalariaGEN data).
- bcftools_annotate (rename) → CrossMap onto 4 targets via cleaned chains →
  bcftools_sort → bcftools_concat. All jobs ok.
- Projected variants: **PvW1 247, PAM 245, PvT01 342, MHC087 350** of 360 — rates
  track alignment divergence (closer strains map more).
- **Workflow bug found:** `vcf_projection.gxwf.yml` uses bare tool_ids
  (`bcftools_annotate`, `crossmap_vcf`, `bcftools_sort`, `bcftools_concat`) which
  pass planemo lint but make the **invocation fail to schedule**. Drove via
  bioblend with full toolshed ids. Fix: version the tool_ids.

## K — ucsc_hub (was "inputs ready", now an assembled, validated hub)
- Workflow built **all tracks green**: bigMaf, 4×(bigChain+bigLink), annotation,
  selection_strict, selection_relaxed (real relaxed BUSTED), orthogroup, 5 2bits,
  genomes.txt.
- **Two real fixes:** (1) multiz s-lines were tab-separated → `maf_to_bigmaf_bed`
  + `bedToBigBed -tab` split the packed bigMaf field (14 cols vs bed3+1);
  normalized the MAF to space-separated. (2) the in-Galaxy `hubCheck` step always
  fails ("Couldn't open hub.txt") because the workflow emits tracks + genomes.txt
  but **not** hub.txt/trackDb — that's the out-of-band assembly.
- Assembled the hub tree out-of-band (`K/hub/`): hub.txt, genomes.txt, 5 genome
  dirs (2bit/groups/description), PvP01 trackDb with 9 track stanzas + per-track
  description pages. **hubCheck → EXIT=0, zero errors, zero warnings.** All
  bigBeds carry bigBed magic; all 2bits carry 2bit magic.

## Infra
- Docker relocation to fast disk **abandoned** — containerd image store isn't
  rsync-relocatable; reverted. Strategy: periodic `docker container prune -f`.
- Local workers **4 → 12** (24-core box) — the 776-OG relaxed run was starving
  J/K on the 4-slot cap.
