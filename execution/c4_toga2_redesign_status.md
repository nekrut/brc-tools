# C.4 annotation-projection redesign for TOGA2 v2.0.8 — status

Decision: modernize C.4. TOGA2 v2.0.8 (`toga2:local`, ~20.7 GB image) classifies
the FULL anchor annotation itself (no `--filter_bed`); the Phase C.2 triage
subset no longer filters TOGA2. Liftoff handles the clean majority; TOGA2 runs
on the whole anchor BED12; `phase_c4_merge` folds both, using TOGA2 intactness +
orthology for the rescued set.

## 1. TOGA2 v2.0.8 output schema (verified against `toga2:local` source)

Inspected `docker run --rm toga2:local toga2.py run --help` and the image source
under `/opt/TOGA2/src/python/modules/` (`constants.py`, `filter_loss_file.py`,
`finalise_orthology_files.py`, `toga_main.py`, `results_checks.py`). The four
final files land DIRECTLY in the run's `--output` dir (`toga_out/`) — confirmed
by `toga_main.py` lines ~603–630 (`os.path.join(self.output, ...)`), which is
exactly what the `toga2.xml` wrapper declares with `from_work_dir="toga_out/..."`.

| TOGA2 file (toga_out/) | format (verified, with source) | phase_c4_merge use |
|---|---|---|
| `loss_summary.tsv` | header `level<TAB>entry<TAB>status` (constants.py `LOSS_FILE_HEADER`). `level` ∈ {PROJECTION, TRANSCRIPT, GENE}; PROJECTION `entry` = `<transcript>#<chain>` (separator `#`, may carry `#paralog`/`#retro`); `status` ∈ {FI,I,PI,UL,M,L,PG,PP,N} (`ALL_LOSS_SYMBOLS`). filter_loss_file.py writes 3-col rows. | intactness per rescued gene (matched via `<t_transcript>#` prefix against PROJECTION entries) |
| `orthology_classification.tsv` | header `t_gene<TAB>t_transcript<TAB>q_gene<TAB>q_transcript<TAB>orthology_class` (constants.py `ORTHOLOGY_TABLE_HEADER`). `orthology_class` ∈ {one2one, one2many, many2one, many2many, one2zero} (results_checks.py). `q_transcript` = projection id `<transcript>#<chain>`. | ref↔query gene linkage + orthology class |
| `query_annotation.bed` | BED12; col4 = projection id `<transcript>#<chain>` (constants.py `QUERY_BED_CLEAN`). | transcript-level query coords (optional input) |
| `query_genes.bed` | BED (≥4 col); col4 = final query gene id (== `q_gene`) (finalise_orthology_files.py `modify_gene_bed`). | gene-level query coords → CESAR2 GFF lines |

Also present in `toga_out/` but unused by the merge: `query_genes.tsv`
(`query_gene<TAB>projection`), `orthology_scores.tsv`, `transcript_meta.tsv`,
`query_annotation.with_utrs.bed`, `query_annotation.gtf`, `processed_pseudogenes.bed`,
`inactivating_mutations.tsv`, `summary.txt`, etc.

### Mapping vs what phase_c4_merge.py expected (TOGA1 port)

The TOGA1-era loaders already matched the TOGA2 columns 1:1 — no field renames
were needed:
- `load_toga2_loss_summary`: skips `level` header, keys PROJECTION rows by `entry`
  → matches `level/entry/status` exactly.
- `load_toga2_orthology`: `DictReader` on `t_gene,t_transcript,q_gene,q_transcript,orthology_class`
  → matches the real header exactly.
- `load_toga2_query_bed`: keys on col4 → query_genes.bed col4 == q_gene (gene
  lookup works); query_annotation.bed col4 == projection id.
- Intactness matched by `<t_transcript>#` prefix → correct given the `#` separator.

Net: the wrapper (`toga2.xml`, committed in `fa869ce`) and the merge loaders are
already correct for the real TOGA2 v2.0.8 schema. The redesign work was (a)
re-verifying the schema against the actual image, (b) wiring TOGA2 into the
workflow on the FULL annotation, (c) adding a TOGA2-format merge test, (d) docs.

## 2. phase_c4_merge changes

- `tools/phase_c4_merge/phase_c4_merge.py`: documented the verified TOGA2 v2.0.8
  output schema (filenames, columns, loss alphabet, projection `#` separator) in
  the module docstring. No logic change needed — the loaders already consume the
  real formats; the Liftoff-only path (`--toga-dir` empty/absent) still
  short-circuits. Output contract unchanged: `{q}.annotation.gff3` +
  `{q}.classification.tsv` with source/intactness columns.
- `tools/phase_c4_merge/phase_c4_merge.xml`: added a second planemo test
  exercising the TOGA2-merge path against synthetic TOGA2-format fixtures
  (`use_toga: yes`, all four inputs). Asserts geneA = liftoff/I and geneB =
  cesar2/I/one2one with coords from query_genes.bed, and the TOGA2 GFF gene line.
- New synthetic fixtures (real TOGA2 schema): `tools/phase_c4_merge/test-data/`
  `toga2_loss_summary.tsv`, `toga2_orthology_classification.tsv`,
  `toga2_query_annotation.bed`, `toga2_query_genes.bed`.

## 3. Workflow + README changes

`workflows/align_chain_project/align_chain_project.gxwf.yml`:
- Renamed to "Liftoff + TOGA2 C.4"; rewrote the `doc` for the TOGA2 model.
- New scalar inputs: `anchor_masked` (→ TOGA2 `--ref_2bit`), `anchor_isoforms`
  (→ `--isoform_file`), `cleaned_chain_in` (→ `--chain_file`); `query_masked`
  now also feeds TOGA2 `--query_2bit`.
- New `toga2` step on the FULL anchor BED12 (anchor_bed12 + anchor_isoforms +
  cleaned chain + anchor/query masked FASTAs). NO needs_cesar2.bed wire (TOGA2
  has no `--filter_bed`).
- `phase_c4_merge` switched to `use_toga: yes`, wired to TOGA2's four outputs
  (`toga|loss_summary`, `toga|orthology`, `toga|query_annotation`, `toga|query_genes`).

`workflows/align_chain_project/README.md`: new "C.4 model (TOGA2 v2.0.8
modernization)" section with the output→merge mapping table; "GPU-independent but
heavy (Nextflow + ~20 GB image, local-only)" note; updated RUNNABILITY + wrapper
list + provenance to reflect `use_toga: yes`.

## 4. Real TOGA2 run — NOT attempted (honest note)

Per the guard ("do not run unless clearly quick + fits ~36 GB disk"), a real
`toga2.py run` was NOT executed. Reasons:
- Disk: root FS at **99% used, only ~17 GB free** — below the ~36 GB budget. A
  Nextflow-driven TOGA2 run materializes a work dir + 2bit + CESAR2 intermediates
  and risks filling the FS.
- The wrapper's own `<tests>` comment documents that TOGA2 cannot run a
  meaningful projection on tiny synthetic data (Nextflow + tensorflow + CESAR2
  over REAL genome alignments).

What a real C.4 TOGA2 run needs (shape confirmed from the image's bundled
`/opt/TOGA2/test_input/{hg38,mm10}`): `ref.2bit` + `query.2bit` (from soft-masked
FASTA via `faToTwoBit`), a cleaned `ref→query` chain, anchor BED12
(`*.transcripts.bed`), anchor `isoforms.tsv`, plus disk for the Nextflow work dir
(well beyond the synthetic footprint). Flags fixed by the wrapper: `--no_u12_file
--no_spliceai --parallel_strategy local --keep_temporary_files
--feature_jobs/--orthology_jobs/--tree_cpus ${GALAXY_SLOTS} --output toga_out`.

Validation performed instead: `phase_c4_merge` composes correctly on SYNTHETIC
TOGA2-format inputs (verified the real `level/entry/status` and
`t_gene/.../orthology_class` schemas, the `<transcript>#<chain>` projection ids,
and query_genes.bed q_gene linkage), and the workflow lints clean with both new
steps resolving.

## 5. Results

- `planemo test --biocontainers tools/phase_c4_merge/` → **All 2 test(s) passed**
  (Test #1 Liftoff-only, Test #2 TOGA2-merge).
- `planemo workflow_lint align_chain_project.gxwf.yml` → **0 ERROR**, "All tool
  ids appear to be valid" (incl. `toga2` + `phase_c4_merge`). Remaining warnings
  are the pre-existing cosmetic ones (per-step annotations, top-level `name`
  key, missing workflow test cases).
- `toga2.py run --help` confirmed the v2.0.8 CLI (run subcommand, `--ref_2bit
  --query_2bit --chain_file --ref_annotation --isoform_file`, no `--filter_bed`).

## Files changed (all in scope; NOT committed)

- `tools/phase_c4_merge/phase_c4_merge.py` (docstring: verified schema)
- `tools/phase_c4_merge/phase_c4_merge.xml` (TOGA2-merge test)
- `tools/phase_c4_merge/test-data/toga2_{loss_summary.tsv,orthology_classification.tsv,query_annotation.bed,query_genes.bed}` (new)
- `workflows/align_chain_project/align_chain_project.gxwf.yml` (toga2 step + rewire)
- `workflows/align_chain_project/README.md` (C.4 TOGA2 model)

Stayed out of workflows/{ucsc_hub,msa,selection,trees,multiz,vcf_projection,consensus}
and tools/{anchor_prep,iqtree3,ucsc_kent}. No git commit.
