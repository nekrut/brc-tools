# Changelog

## 0.1.0 (2026-05-26)

Initial release.

Workflow: PanSN rename (map over strain collection) -> fasta_concat ->
pggb -> odgi stats. Replicates the v3 PGGB pangenome build recipe for
*Plasmodium vivax* (8 strains, ~25 Mb each).

Validated end-to-end on local Galaxy 26.1-dev against the 8 P. vivax
accessions in PANGENOME.md; graph nucleotide length within 2.7% of the
v2 native reference build (full reproducibility blocked by upstream
pggb 0.7 vs 0.6 algorithm drift, not the workflow).
