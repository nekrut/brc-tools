# PGGB pangenome build

Galaxy workflow that builds a PGGB-style pangenome variation graph from
per-strain assembly FASTAs.

## Steps

```
input: list collection of per-strain FASTAs
        │
        ▼
   PanSN rename (map over collection; sample auto-derived from element identifier)
        │
        ▼
   FASTA collection concat (single multifasta)
        │
        ▼
   PGGB (wfmash → seqwish → smoothxg → gfaffix → odgi)
        │
        ├─► smoothed GFA1 (gz)
        ├─► odgi .og binary
        ├─► layout + viz PNGs
        ├─► run log
        └─► (optional) per-reference VCF via vg deconstruct
        │
        ▼
   odgi stats (graph metrics)
```

## Inputs

| Step | Param | Default | Notes |
|------|-------|---------|-------|
| 0 | Strain FASTAs (`list` collection) | — | element identifier = sample name |
| 1 | `n_haplotypes` | 8 | total haplotypes = collection size for haploid panels |
| 2 | `segment_length` | 5000 | wfmash seed |
| 3 | `map_pct_id` | 90.0 | intra-species; 70–80 for inter-species |
| 4 | `min_match_len` | 23 | seqwish `-k` |
| 5 | `vcf_spec` | `""` | reference accession prefix for vg deconstruct; blank skips |

## Tested against

- *P. vivax* 8-strain panel (PvP01, Sal-I, PvW1, PAM, PvSY56, PvT01, PvC01,
  MHC087) — see `Pv4-pangenome/v3/writeup/PANGENOME.md` for the recipe.
- Runtime ~40 min for the 8-strain Pv build on 16 cores.
- Output graph length within ±3% of the v2 native reference build.

## Resource notes

PGGB is the heavy step. For 8 × ~25 Mb haploid genomes: 3–6 h wall on a
32-core box at default params; ~20 GB peak RAM. The `--poa-length-target`
parameter dominates runtime — `700,1100` (pggb 0.7 default) is fast;
`4001,4507` (v2 native) is ~3× slower but produces more collapsed graphs.
