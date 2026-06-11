# WF-J `vcf_projection` (Phase J — Path A2 only)

Project a reference-coordinate cohort VCF onto every non-reference target via
CrossMap over the cleaned ref→target chains. Production Path A2 only (graph-native
Path B is cut per Decision 6). **NO new wrappers — every step is an IUC tool.**

File: `vcf_projection.gxwf.yml` (gxformat2, `class: GalaxyWorkflow`).

## Status — proven on real data (2026-06-10)

Runs **one-click** on the Pv4 panel. With no MalariaGEN cohort available (GT
skips Phase J entirely), a synthetic 360-variant PvP01 cohort VCF was projected
onto the four targets: **PvW1 247, PAM 245, PvT01 342, MHC087 350** of 360 — the
mapping rate tracks alignment divergence (closer strains carry more).

> **Fix (this commit):** the step `tool_id`s were **bare** (`bcftools_annotate`,
> `crossmap_vcf`, `bcftools_sort`, `bcftools_concat`). These pass `planemo
> workflow_lint` but the **invocation fails to schedule** (planemo crashes in
> `structured_data` with no invocation created). They are now full versioned
> toolshed ids, which schedules cleanly.

## Inputs

| input | type | doc |
|-------|------|-----|
| `cohort_vcf` | data | External reference-coordinate cohort VCF (`cohort_vcfs`), CHROM in internal `_v1` naming. |
| `chrom_rename` | data | 2-col TSV `_v1`→GenBank accession for `bcftools annotate --rename-chrs`. |
| `cleaned_chains` | `list` | N−1 subset of Phase C cleaned chains where source = REF_STRAIN, one per non-ref target. `element_identifier = target strain`. |
| `target_fastas` | `list` | Per-target genome FASTAs (Phase B), `element_identifier = target strain`, paired with `cleaned_chains`. |

## Steps — all IUC (no our wrappers)

| step | tool_id | source | notes |
|------|---------|--------|-------|
| `rename_chroms` | `bcftools_annotate` | IUC | `--rename-chrs` via `sec_annotate|rename_chrs`; runs once over whole cohort. |
| `crossmap_project` | `crossmap_vcf` | IUC | map-over target; history-mode inputs nested under `seq_source` / `chain_source`. |
| `sort_vcf` | `bcftools_sort` | IUC | map-over; CrossMap output is unsorted — sort + bgzip/index. |
| `concat_vcfs` | `bcftools_concat` | IUC | `--allow-overlaps` (`-a`); the `sort_vcf` collection reduces into `input_files`. |

**IUC dependencies to install before running:** `bcftools_annotate`,
`crossmap_vcf`, `bcftools_sort`, `bcftools_concat`. (`bcftools_sort` is a
separate toolshed tool — it is NOT part of the local IUC `bcftools` dir checked
during authoring.)

## RUNNABILITY

- No new wrappers; no GPU / toga2 / KegAlign dependence. WF-J depends only on
  C (cleaned chains), B (target FASTAs), and the external `cohort_vcfs` — it does
  NOT sit downstream of E/F.
- Once the four IUC tools are installed, this workflow is runnable as-is.
- Output: per-target `cohort_on_{target}.vcf.gz` (sorted, indexed) — Pv4: 7 — plus
  a combined `--allow-overlaps` concat across targets.

## gxformat2 flags (honest notes)

- **Conditional / section paths** are wired with the `section|param` pipe form
  (`sec_annotate|rename_chrs`, `seq_source|input`,
  `seq_source|chain_source|input_chain`) and selector defaults set via `state:`
  (`index_source_s: history`, `index_source: history`). This is the standard
  gxformat2 idiom and lints clean.
- **`concat_vcfs` collection→multi-data reduce.** `bcftools_concat`'s
  `input_files` is a `multiple="true"` data param; feeding it the `sort_vcf`
  output collection performs an implicit reduce (all targets → one concat job).
- Both `projected_vcfs` (the per-target collection) and `cohort_concat` are
  exposed as outputs.
- Step `label:` omitted (see WF-I README for the planemo step-label/paren quirk).

## Lint

`planemo workflow_lint vcf_projection.gxwf.yml` → no ERRORs. Only standard
advisory warnings (no creator / no license / no test cases).
