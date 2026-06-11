# WF-K `ucsc_hub` (Phase K)

Build a UCSC assembly hub from the Phase I/C/H/E/B artifacts. **Least-validated
stage** — no impl artifact to diff against; validation gate = `hubCheck` clean +
one manual UCSC-browser load (Decision 15).

File: `ucsc_hub.gxwf.yml` (gxformat2, `class: GalaxyWorkflow`).

## Status — proven on real data (2026-06-10)

All track artifacts build green on the Pv4 panel (PvP01-reference hub): bigMaf,
4×(bigChain+bigLink), annotation, strict + relaxed BUSTED selection, orthogroup,
5 2bits, genomes.txt. The assembled hub passes **`hubCheck` with exit 0, zero
errors, zero warnings** (5 genomes; PvP01 carries 9 tracks). Two operational
requirements surfaced — neither is a workflow bug, both are input/packaging steps:

1. **Multiz s-lines must be `species.chrom`-named AND single-space-separated**
   before `process_maf` / `maf_to_bigmaf_bed`. WF-I emits bare-contig, tab-
   separated MAF; if left tab-separated, `bedToBigBed -tab` splits the packed
   bigMaf field (sees 14 cols vs `bed3+1`). Rename to `{species}.{chrom}` and
   normalize whitespace to single spaces first.
2. **`hub.txt` + per-genome `trackDb.txt` assembly is out-of-band.** The workflow
   emits the *tracks* + `genomes.txt`, not `hub.txt`/`trackDb`, so the in-Galaxy
   `hub_check` step always fails ("Couldn't open hub.txt"). Assemble the hub
   directory tree (hub.txt, genomes.txt, `{genome}/{2bit,trackDb.txt,groups.txt,
   description.html}`, PvP01 track stanzas) outside Galaxy, then run `hubCheck`
   on that tree. A reference assembler is `execution/assemble_hub.py`.

## Inputs

| input | type | doc |
|-------|------|-----|
| `multiz_mafs` | `list` | Per-reference multiz MAFs (WF-I), **assumed already accession-renamed**. `element_identifier = reference accession`. |
| `cleaned_chains` | `list` | Full N(N−1) directed cleaned chains (Phase C). `element_identifier = directed pair`. |
| `annotation_gffs` | `list` | Native self-annotation per anchor AND cross-strain `{anchor}-as-ref/{strain}.annotation.gff3` (C.4). |
| `ortholog_table` | data | Phase E `ortholog_table.tsv`. |
| `ref_bed12` | data | Reference gene models BED12 (WF-C anchor_prep `{A}.bed12`). |
| `busted_strict` | data | Strict BUSTED archive (Phase H, core_v3): `tar.gz` of `<gene_id>.json` at tar root. |
| `busted_relaxed` | data | Relaxed BUSTED archive (Phase H, core_relaxed). |
| `assemblies` | `list` | Per-accession genome FASTAs (Phase B). |
| `ref_sizes` | data | Reference `{ACC}.fa.fai` / chrom sizes (accession space). |
| `hub_metadata` | data | Per-assembly metadata TSV for `build_genomes_txt`. |
| `bigmaf_as` / `bigchain_as` / `biglink_as` | data | The autoSql `.as` assets required by `bedToBigBed -as=`. |
| `ref_acc` / `ref_column` / `gene_prefix` | string | REF_ACC + ortholog-table reference column/prefix params. |

## Steps — our wrappers vs IUC / kent suite

| step | tool_id | source | notes |
|------|---------|--------|-------|
| `process_maf` | `process_maf` | **OUR** | ref-first normalize (drop ref-less blocks, reorder, sort). |
| `maf_to_bigmaf_bed` | `maf_to_bigmaf_bed` | **OUR** | bigMaf BED3+1, bypasses `mafToBigMaf` overlap rejection. |
| `sort_bigmaf_bed` | `sort1` | built-in | `sort -k1,1 -k2,2n` equivalent. |
| `bigmaf_bb` | `ucsc_bedtobigbed` | **OUR kent suite** | `-type=bed3+1 -as=bigMaf.as`. |
| `maf_index` | `ucsc_mafindex` | **OUR kent suite** | **CAVEAT — unvalidated** (see below). |
| `chain_to_bigchain` | `chain_to_bigChain` | **OUR** | bigChain.bed (bed6+6) + bigLink.bed (bed4+1). |
| `bigchain_bb` | `ucsc_bedtobigbed` | **OUR kent suite** | `-type=bed6+6 -as=bigChain.as`. |
| `biglink_bb` | `ucsc_bedtobigbed` | **OUR kent suite** | `-type=bed4+1 -as=bigLink.as`. |
| `gff3_to_genepred` | `ucsc_gff3togenepred` | **OUR kent suite** | annotation source (native + cross-strain). |
| `genepred_to_bed` | `ucsc_genepredtobed` | **OUR kent suite** | genePred → BED12. |
| `annot_bb` | `ucsc_bedtobigbed` | **OUR kent suite** | `-type=bed12` (no `.as`). |
| `build_hub_bb` | `build_hub_bb` | **OUR** | selection BED12+5 (strict+relaxed) + orthogroup BED12; internal `bedToBigBed`. |
| `fa_to_2bit` | `ucsc_fatotwobit` | **OUR kent suite** | per-accession 2bit. |
| `build_genomes_txt` | `build_genomes_txt` | **OUR** | global `genomes.txt`. |
| `hub_check` | `ucsc_hubcheck` | **OUR kent suite** | validation gate. |

The kent-suite tools (`ucsc_bedtobigbed`, `ucsc_mafindex`, `ucsc_gff3togenepred`,
`ucsc_genepredtobed`, `ucsc_fatotwobit`, `ucsc_hubcheck`) are **our** loaded
wrappers (shared `ucsc-kent-tools` container), not IUC. No external IUC install
is required for WF-K.

## CAVEAT 1 — accession space + `mafIndex` (flag per task)

- **Accession space.** Phase K works in **GenBank accession** space (e.g.
  `GCA_900093555.2`), NOT strain space. `process_maf` and `maf_to_bigmaf_bed`
  require **accession-named s-lines** and **accession sizes**, so a
  **strain→accession s-line rename must happen BETWEEN WF-I and WF-K**. That
  rename is not yet a wrapped tool; this workflow **assumes the incoming
  `multiz_mafs` are already accession-renamed** and that `ref_acc` / `ref_sizes`
  are in accession space. This is the chief reason WF-K is the least-validated
  stage. A strain→accession map is the missing explicit WF-K input that a future
  rename step (between WF-I and WF-K) must consume.

- **`mafIndex`.** `ucsc_mafindex` has **NO validated reference invocation** —
  `v3/tools/mafIndex` is a 0-byte placeholder, the reference run hit
  *Permission denied*, and impl tolerated it via `|| true`. It is wired here
  (`maf_index` step) but **must be validated independently** against the
  `ucsc-kent-tools` container (confirm it produces a usable index). It does not
  block the rest of the hub.

## RUNNABILITY

- No GPU / KegAlign / toga2 dependence (WF-K consumes finished artifacts).
- No IUC install needed — all tools are our loaded wrappers + built-in `sort1`.
- Gate: **`hubCheck` clean + one manual UCSC-browser load** on `test_data`.
  `genomes.txt` failure mode: hub won't load without a real `defaultPos` +
  resolvable `twoBitPath` (handled by `build_genomes_txt` from `hub_metadata`).

## gxformat2 flags (honest, best-effort encoding)

1. **Nested-collection output not expressible.** The spec's final deliverable is
   a `list:list` (outer=accession, inner=track-type). gxformat2 cannot cleanly
   assemble heterogeneous per-track-type datasets (bigMaf, bigChain, bigLink,
   annotation, selection, orthogroup, 2bit, manifests) into ONE nested
   collection inside a pure map-over. **Encoded as best attempt:** each track
   type is a **separate per-accession output collection**; the per-accession
   `ucsc_hub/GCA_*/` directory tree is materialized by a downstream staging step
   **out of band** of this workflow. Flagged here as the known gap.

2. **`hub_check` hub_url.** `ucsc_hubcheck` takes a text path to the staged
   `hub.txt`; the hub directory tree (2bit, trackDb, .bb tracks) must be
   materialized **before** this step can resolve track data. In this declarative
   WF `hub_url` is a placeholder default; real validation runs after staging.

3. **`build_trackdb` omitted from the wired graph.** `build_trackdb` emits a
   per-assembly `trackDb.txt` from many space-separated `ACC=LABEL` text args
   (`--strain-label`, `--anchor`) that are panel-wide scalars, not collection
   edges. Wiring it per-accession in gxformat2 would require per-accession
   scalar text inputs that the map-over cannot supply declaratively; it is part
   of the same out-of-band manifest/staging step as the directory assembly
   (alongside `hub.txt`). `build_genomes_txt` (global, single metadata TSV) IS
   wired.

4. **`build_hub_bb` runs once** for the reference set (strict + relaxed via the
   `relaxed` conditional, `do_relaxed: yes`), producing `selection_core_v3.bb`,
   `selection_core_relaxed.bb`, and `orthogroup_membership.bb`.

5. **Annotation fan-out.** `gff3_to_genepred` maps over `annotation_gffs`, which
   carries both native self-annotation and cross-strain projections fanned over
   anchors × strains; the per-(accession,anchor) split into `annot_from_{anchor}.bb`
   names is an element-identifier/staging concern, not encodable as distinct
   declarative outputs here.

6. Step `label:` omitted (see WF-I README for the planemo step-label/paren quirk).

## Lint

`planemo workflow_lint ucsc_hub.gxwf.yml` → no ERRORs. Only standard advisory
warnings (no creator / no license / no test cases).
