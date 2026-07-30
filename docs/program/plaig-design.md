# PLAIG (Pathogen Lineage Analysis & Inference of Genotypes) — Galaxy Read-Level Population Genomics Design

*Companion to `comparative-genomics-program.md` (§4.2, §5, §7, §8). Design doc for the Galaxy workflow suite generalizing crypto protocol Modules 1–2. Style follows the ANCOR design docs: workflows, subworkflows, tool availability, principles.*

Status: design stage, 2026-07-30

## What it is

A Galaxy workflow suite for **read-level population and divergence genomics of haploid-dominant eukaryotic pathogens**: reads → haploid all-sites VCF → population analysis (structure, diversity, recombination, selection scans, demography) → MK divergence. Derived from the crypto protocol's Module 1 (§5–6, within-species) and Module 2 (§7, polymorphism–divergence), generalized from a single-organism study design into a reusable, organism-configurable suite. The **most-demanded** program component (program doc §7.5): drug-resistance surveillance, transmission/outbreak tracking, vaccine escape — and currently the worst Galaxy tooling story (§8 gaps).

## Scope

- **In scope (config-level port, no code changes)**: organisms with a **haploid-dominant life stage** — Cryptosporidium (reference instance), Plasmodium, Toxoplasma, Babesia, Theileria, Trypanosoma, haploid fungi (Cryptococcus, Aspergillus). Minimum target: all apicomplexans.
- **Edge case — Leishmania**: haploid calling standard, but aneuploidy is first-class biology; promote the depth/CNV module from provisional to primary.
- **Out of scope for v1**: diploid/polyploid pathogens, bacteria (mature ecosystem: snippy/roary), Giardia (ploidy weirdness). See §"Beyond haploid" below for what a diploid extension would require.
- **Boundary principle**: the architecture is organism-agnostic; the real boundaries are **ploidy and reproductive mode, not taxonomy** (program doc §7).

## Design principles

1. **Generic subworkflows + thin organism-specific parent.** All reusable logic lives in generic subworkflows parameterized by workflow parameters; organism specifics (tier gating, typing loci, named outgroups) are parameters/optional steps in a thin parent — same pattern as pangenome-helpers.
2. **All-sites discipline is non-negotiable.** Variants-only VCFs make π/dXY uncomputable or computed against an unknown denominator (crypto §5.6, Appendix B). Diversity/divergence tracks require joint-called all-sites VCFs + callable BED; the callable genome is defined per sample and masked everywhere downstream.
3. **Ploidy is asserted, not assumed.** Protocol's four-point assertion (crypto §4.5): ploidy argument = 1, job log = 1, no diploid separators in GT fields, ploidy-file = 1 — checked before and after every calling job. Failure fails the job.
4. **Contamination handling in two passes.** Pass 1: taxonomic screen (Kraken2/Bracken). Pass 2: competitive mapping against a per-organism decontamination panel (mixed-species infection called as within-species polymorphism is a named failure mode, crypto §5.3/Appendix B).
5. **Mixed infection is first-class.** F_WS-style within-host multiplicity filtering to a dominant-genotype subset for population analyses; dedicated mixed-infection analyses kept separate (crypto §5.9, §6.9). Candidate validation harness: PlasmoGenEpi `recombuddy` simulations (program doc §7.4).
6. **Batch/geography confounding is checked, not hoped away.** Batch covariates in every structure analysis (crypto Appendix B).
7. **Library-prep provenance gates eligibility.** Tier system (WGA/capture/direct) with per-analysis eligibility rules (crypto §2.4) — assembly-free analyses are not immune to prep artifacts. Per-organism parents define tiers; eligibility stays config.
8. **Documented tool divergence.** Where the suite uses different tools than other suites (or offers two callers), the choice is justified in one place (program doc §9).
9. **Credited borrowing.** Reference manifest semantics and NCBI-query reference fetching borrowed from nf-core/`pathogensurveillance`; optional PMO export inspired by PlasmoGenEpi (program doc §7.4).

## Workflow decomposition

Generic subworkflows (no organism-specific parent needed — all organism specifics are workflow parameters):

| Subworkflow | Contents | Crypto section | Tool gaps |
|---|---|---|---|
| `read-qc-decontam` | fastp, MultiQC, Kraken2/Bracken pass 1 + competitive-mapping pass 2 | §5.1–5.3 | none — reuse IWC `short-read-qc-trimming` + `quality-and-contamination-control-raw-reads`; add pass 2 as optional extension |
| `haploid-read-to-vcf` | BWA-MEM2 → markdup → GATK `--sample-ploidy 1` joint calling → variants-only + **all-sites** VCFs + callable BED + masks; ploidy assertion built in | §5.4–5.8 | none — all tools IUC-wrapped |
| `popgen-analysis` | All population-level analyses from the all-sites VCF, as toggleable steps: **structure** (PLINK LD-prune/PCA, ADMIXTURE; batch covariates), **diversity** (pixy π/dXY/FST, SFS stats), **recombination** (pyrho ρ/LD decay — estimated before sweep scans, Appendix B), **selection scans** (selscan iHS/nSL/XP-EHH), **demography** (dadi-cli, stairwayplot2). User/parent selects which analyses to run. | §6.1–6.7 | **pixy, pyrho, selscan, dadi-cli wrappers**; vet or re-wrap ADMIXTURE (dereeper, 2015-era) |
| `mk-divergence` | masked consensus (`bcftools consensus --haplotype 1`, callable-complement mask → N, never silent reference), MACSE **or** PRANK codon alignment, MK/asymptotic-MK/DoS, outgroup polarization | §7.1–7.5 | **MACSE or PRANK wrapper** + custom scripts |

### Why not existing IWC workflows (for IWC review)

IWC `variant-calling/haploid-variant-calling-wgs-pe` (fastp→BWA→Picard→LoFreq→snpEff) and `ploidy-aware-genotype-calling` (FreeBayes) are both **variants-only, per-sample, no joint genotyping, no all-sites output**. LoFreq is additionally mistargeted (within-host low-frequency variants, not population-consensus genotypes). The all-sites joint-calling gap is exactly what justifies `haploid-read-to-vcf`.

### Optional surveillance export

PMO-compatible allele table (PlasmoGenEpi Portable Microhaplotype Object) for typing-plugin loci → plugs into plasmodiumdrugres-style prevalence reporting (program doc §7.4).

## Per-organism parameters (port = parameters, no code)

Workflow parameters that must be supplied per organism (only what can't be computed from the data):

| Parameter | Used by | Crypto instance |
|---|---|---|
| Reference assembly + annotation | all subworkflows | CpBGF + cgd IDs |
| Mappability/repeat/subtelomere masks | diversity, MK, scans | §5.7.1 |
| Decontamination panel (competitive mapping) | read-qc-decontam pass 2 | Cryptosporidium spp. panel |
| Outgroups | mk-divergence | §7.3: CmTU1867 (primary), C. ubiquitum (secondary), C. muris RN66 (deeper check); C. tyzzeri excluded |
| Ploidy | haploid-read-to-vcf | 1 |
| Tier definitions (library-prep eligibility) | popgen-analysis (gates which analyses run) | WGA/capture/direct (crypto §2.4) |
| Fws threshold (mixed-infection filtering) | popgen-analysis (structure step) | crypto §5.9 threshold |
| Typing plugin (optional) | popgen-analysis + PMO export | gp60 subtyping (crypto §6.8: targeted local assembly against repeat-collapsed reference) |

## Tool availability summary (program doc §8)

- **Available (IUC)**: fastp, MultiQC, Kraken2 (+DMs), Bracken, bwa_mem2, samtools/bcftools, GATK4, PLINK (1.9-era), mosdepth, seqkit, sra_tools; ADMIXTURE (dereeper — **vet or re-wrap**).
- **Needs wrappers (PLAIG owns)**: pixy, selscan, pyrho, MACSE or PRANK, dadi-cli (+ stairwayplot2, SweeD/OmegaPlus, fineSTRUCTURE parked as open questions).
- **Data fetching**: IWC `data-fetching/parallel-accession-download` + `sra-manifest-to-concatenated-fastqs` cover archive-sweep mechanics.

## Beyond haploid — what a diploid/polyploid extension would require

PLAIG v1 is haploid-only by design. Extending to diploid or polyploid organisms is not a parameter change — it requires new analytical paths for several workflows:

| Workflow | Haploid (current) | Diploid extension |
|---|---|---|
| Variant calling | GATK `--sample-ploidy 1` | GATK handles diploid natively; polyploid supported but less tested |
| Ploidy assertion | Four-point check: ploidy=1, no diploid separators, etc. | Becomes ploidy-aware rather than haploid-asserting; check against declared ploidy, not against 1 |
| Mixed-infection detection | Fws / dominant-genotype collapse — heterozygosity signals mixed infection | **Hard conceptual shift**: heterozygosity is normal diploid biology. Need allele-balance, read-backed phasing, or depth heuristics to distinguish true heterozygosity from mixed infection |
| Selection scans (selscan) | Trivially phased — one haplotype per sample | Requires **phasing pipeline** (whatshap for long reads, SHAPEIT/BEAGLE for short reads) — new subworkflow + new wrappers |
| Recombination (pyrho) | Estimates ρ from haploid haplotypes | Needs phased data; methodology may need adaptation |
| Demography (dadi-cli, stairwayplot2) | Works with haploid SFS | **Gets easier** — dadi is designed for diploid SFS |
| MK divergence | `bcftools consensus --haplotype 1` picks one haplotype | Need to phase and handle both haplotypes, or use a different consensus strategy |

**Bottom line**: variant calling and demography adapt easily. Selection scans and recombination need a phasing pipeline. Mixed-infection detection is the real blocker — the Fws framework assumes haploid, and there's no drop-in replacement for diploids. A diploid PLAIG would be a parallel analytical path, not a parameterized version of the haploid one.

## Open questions (program doc §10 + here)

- fineSTRUCTURE worth wrapping? (painful deps; ADMIXTURE+PCA+LD may suffice)
- SweeD/OmegaPlus as complement to selscan, or out?
- Depth/CNV module: provisional everywhere vs primary for aneuploid organisms (Leishmania) — one module with config severity, or two?
- pyrho vs LDhat: pyrho-primary adopted; keep LDhat wrapper on the queue or drop?
- Diploid extension: worth designing now, or revisit after haploid v1 is delivered?
- UCSC assembly hub output: PANTEON produces hubs (WF-K). Should PLAIG also emit a hub (e.g. variant tracks, selection-scan peaks, callable-regions BED) for visualization on the BRC site?

## Sources

- Crypto protocol v2.1c: §2.4, §3.2, §3.5, §4.5, §5, §6, §7, Appendix B
- Program doc §4.2 (shared subworkflows + near-misses), §5 (decomposition), §7 (generalization), §8 (ToolShed audit)
- IWC near-miss workflows verified: `variant-calling/haploid-variant-calling-wgs-pe`, `variant-calling/ploidy-aware-genotype-calling`, `genome-assembly/quality-and-contamination-control-raw-reads`, `read-preprocessing/short-read-qc-trimming`
