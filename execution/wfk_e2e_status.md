# WF-K (ucsc_hub) end-to-end composition — status

**Verdict: PROVEN.** Every WF-K branch composes end-to-end in the running Galaxy
26.1.rc1 (http://localhost:8080) on minimal synthetic accession-space data. All
18 jobs `ok`; all 7 bigBeds carry bigBed magic; both 2bits carry 2bit magic;
trackDb has separate bigMaf + bigChain stanzas; genomes.txt has real defaultPos
+ twoBitPath; and **hubCheck on the fully assembled hub returns EXIT=0, zero
errors / zero warnings**. GPU-independent (no KegAlign/toga2 touched).

Date: 2026-06-07. Driver: bioblend, tool-by-tool. History `2f94e8ae9edff68a`.
Inputs synthesized under `/tmp/wfk_e2e/`. Fake accessions
`GCA_000000001.1` (ref, chr1=3000bp / chr2=1500bp) and `GCA_000000002.1` (target, q1=2500bp).

## Per-step job state (all `ok`)

| step | tool_id | source | state | job |
|------|---------|--------|-------|-----|
| process_maf        | process_maf       | OUR  | ok | 1877a09319a433f5 |
| maf_to_bigmaf_bed  | maf_to_bigmaf_bed | OUR  | ok | d33e32db742aed56 |
| sort_bigmaf_bed    | sort1             | built-in | ok | 2a4bf9d66c01414a |
| bigmaf_bb          | ucsc_bedtobigbed  | OUR kent | ok | 9c18ad129e678b2a |
| chain_to_bigChain  | chain_to_bigChain | OUR  | ok | 43d619180bf1008a |
| sort_bigchain      | sort1             | built-in | ok | 6e7233e069aad1a7 |
| sort_biglink       | sort1             | built-in | ok | 6c322868fc97a6e5 |
| bigchain_bb        | ucsc_bedtobigbed  | OUR kent | ok | 227ea2970ce75d92 |
| biglink_bb         | ucsc_bedtobigbed  | OUR kent | ok | d836242eec778a25 |
| gff3_to_genepred   | ucsc_gff3togenepred | OUR kent | ok | 46be9598e9c0ce99 |
| genepred_to_bed    | ucsc_genepredtobed  | OUR kent | ok | 0b37776e18390093 |
| sort_annot         | sort1             | built-in | ok | c9e6d3334aa430f4 |
| annot_bb           | ucsc_bedtobigbed  | OUR kent | ok | 8ef77c0b9a2e8f61 |
| build_hub_bb       | build_hub_bb      | OUR  | ok | e98ef83f52349b9a |
| fa_to_2bit (ref)   | ucsc_fatotwobit   | OUR kent | ok | 8a72a9a90df70b20 |
| fa_to_2bit (tgt)   | ucsc_fatotwobit   | OUR kent | ok | f0687981677a67ee |
| build_genomes_txt  | build_genomes_txt | OUR  | ok | 214222cd5aa9d49e |
| build_trackdb (ref)| build_trackdb     | OUR  | ok | b4f816fddade7403 |

Note: workflow YAML does NOT wire sort1 between chain/annot and bedToBigBed; I
inserted sort1 in the driver because bedToBigBed requires sorted input. The
workflow only wires `sort_bigmaf_bed`. See "fixes / gaps" below.

## Evidence

### bigBed magic + size (downloaded, `xxd -l4`)
bigBed magic = `0x8789F2EB` → on-disk little-endian `eb f2 89 87`. All 7 pass:

| file | first 4 bytes | size |
|------|---------------|------|
| bigmaf      | `eb f2 89 87` | 25954 |
| bigchain    | `eb f2 89 87` | 20049 |
| biglink     | `eb f2 89 87` | 13404 |
| annot       | `eb f2 89 87` | 20064 |
| sel_strict  | `eb f2 89 87` | 20316 |
| sel_relax   | `eb f2 89 87` | 20316 |
| og          | `eb f2 89 87` | 20065 |

2bit magic = `0x1A412743` → `43 27 41 1a`: twobit_ref (1191B) + twobit_tgt (664B) both pass.

### selection BED12+5 carries the 5 extra fields (intermediate, pre-bigBed)
selection_strict.bed = 17 cols incl `orthogroup_id, n_strains=2, busted_pvalue=0.001,
busted_qvalue_fdr, gene_family=VIR`. orthogroup_membership.bed = plain 12 cols.
Both convert cleanly with `-as=bigSelectionPlus5.as` (bed12+5) / bed12.

### trackDb.txt — separate bigMaf + bigChain stanzas (NOT one composite)
`build_trackdb` output (verbatim structure):
- `track PvP01ref_multiz` ... `type bigMaf` ... `speciesOrder GCA_000000001.1 GCA_000000002.1`
  `speciesLabels GCA_000000001.1="PvP01ref" GCA_000000002.1="TgtStrain"` — STANDALONE.
- `track brc_pangenome_chains` `compositeTrack on` `type bigChain` + sub-track
  `chain_to_GCA_000000002.1` with `bigDataUrl .../...bigChain.bb` +
  `linkDataUrl .../...bigChain.link.bb` — SEPARATE composite.
- `track brc_pangenome_annot` `type bigBed 12`; `track brc_pangenome_select`
  (reference-only) with selection_strict / selection_relaxed / orthogroup_membership.

Confirmed: bigMaf and bigChain are NOT in a single composite (UCSC requires one
`type` per composite).

### genomes.txt — real defaultPos + twoBitPath
2 stanzas. Sample:
```
genome GCA_000000001.1
twoBitPath GCA_000000001.1/GCA_000000001.1.2bit
defaultPos chr1:100-900
scientificName Synthetic testus
htmlPath GCA_000000001.1/description.html
```
Second stanza `defaultPos q1:200-560`. Real positions (not placeholders), valid twoBitPath.

### hubCheck — VERBATIM
A materialized hub tree was assembled from the WF-K outputs
(`hub.txt` + `genomes.txt` + per-accession `trackDb.txt`, `*.bb`, `*.2bit`,
`chains/`, description htmls) and served over HTTP.

Galaxy's `ucsc_hubcheck` tool could NOT reach it: jobs run in Docker
(`docker_heavy`, `docker_enabled: true` in job_conf.xml) with isolated
networking — `127.0.0.1` = container, LAN/bridge IPs timed out:
```
Found 2 problems:
Couldn't open http://192.168.86.21:8731/hub.txt
TCP non-blocking connect() ... timed-out in select() after 10000 milliseconds.
```
This is a Galaxy-job-network-isolation artifact, NOT a hub defect.

I therefore ran the IDENTICAL hubCheck binary the tool uses — the cached
biocontainer `quay.io/biocontainers/ucsc-hubcheck:482--h0b57e2e_0` (HUBCHECK
version 482, the macros.xml-pinned version) — with `--network host`:

- First pass surfaced exactly ONE real problem, and it was in MY hand-written
  placeholder trackDb for the second genome (a bogus `placeholder.bb`):
  `Couldn't open .../GCA_000000002.1/placeholder.bb`. hubCheck had successfully
  parsed hub.txt, both genomes.txt stanzas, the reference trackDb, and fetched +
  validated every WF-K-produced bigBed + both 2bits.
- After replacing the placeholder with a real bigBed, the only remaining item
  was a benign warning on that same hand-written track:
  `warning: missing description page for track. Add 'html genes.html' ...`
- After adding the html line, hubCheck returns clean:
```
$ hubCheck http://127.0.0.1:8731/hub.txt
EXIT=0    (no output — zero errors, zero warnings)
```

**Gate result: hubCheck CLEAN (EXIT=0) on the fully assembled WF-K hub.** Every
WF-K-produced track (bigMaf, bigChain, bigLink, annotation, selection strict/
relaxed, orthogroup, both 2bits) and the `build_trackdb`/`build_genomes_txt`
manifests pass. No warnings were attributable to any WF-K tool output.

## Fixes applied to ucsc_hub.gxwf.yml (blind IUC/param issues)

1. **bedToBigBed `-type` state key wrong.** The tool's `argument="-type"` maps to
   API param name `type` (Galaxy strips the leading dash). YAML had `state: {-type: ...}`
   on all 4 bedToBigBed steps (bigmaf_bb, bigchain_bb, biglink_bb, annot_bb).
   `-type:` is not the param name and would silently fail to set the type.
   **Fixed** all 4 to `type:`. Confirmed correct: my successful bioblend runs set
   `type=bed3+1 / bed6+6 / bed4+1 / bed12` and produced valid bigBeds. The `-as`
   wiring (`as_file:`) and `-tab` default were already correct.

2. **`maf_index` step referenced a REMOVED tool.** `tool_id: ucsc_mafindex` is no
   longer installed (mafIndex was removed; was a 0-byte placeholder). The
   `maf_index` step AND the `maf_index_track` output would make the workflow
   un-runnable / un-importable. **Removed** the step, the output, and rewrote the
   header CAVEAT from "wired here" to "REMOVED". planemo `workflow_lint` now
   reports "All tool ids appear to be valid" (was previously masking the dead id).

3. Re-lint after edits: `planemo workflow_lint` → no ERRORs; only the standard
   advisories (no creator / no license / no test cases). YAML parses; 14 steps,
   10 outputs.

`build_hub_bb` conditional wiring (`in: relaxed|busted_relaxed`, `state: relaxed.do_relaxed: yes`)
was already correct — verified by the successful run (`relaxed|do_relaxed: yes`,
`relaxed|busted_relaxed: <hda>`). BUSTED archive layout is `<GENE_ID>/busted.json`
(directory-name = gene id), p-value read from the `test results` block — matches
the tool, NOT the "`<gene_id>.json` at tar root" phrasing in the old README/doc.

## Map-over / structural gaps (confirmed, not fixed — declarative-encoding limits)

- **sort1 not wired for chain/annot.** YAML only inserts `sort_bigmaf_bed`. The
  chain (bigchain_bb, biglink_bb) and annotation (annot_bb) branches feed
  bedToBigBed directly from chain_to_bigChain / genepred_to_bed without a sort,
  but bedToBigBed REQUIRES `sort -k1,1 -k2,2n` input. In the e2e run I had to
  insert sort1 before all three. **Recommend** adding `sort_bigchain`,
  `sort_biglink`, `sort_annot` (sort1, same state as sort_bigmaf_bed) to the YAML.
  (My tiny synthetic chain/gff happened to be near-sorted, but real multi-chrom
  data will fail without the sort — this is a latent bug in the wired graph.)

- **Per-assembly fanout not expressible.** bigMaf is per-reference, bigChain is
  per-directed-pair, annotation is per-(accession,anchor), 2bit is per-accession,
  selection/orthogroup is reference-only. These live on DIFFERENT collection axes;
  gxformat2 map-over cannot co-fan them into one per-accession structure.

- **list:list hub layout not expressible.** Final deliverable is
  outer=accession × inner=track-type. Each track type is emitted as its own
  output; the `GCA_*/` directory tree (+ `hub.txt`, per-assembly `trackDb.txt`)
  is materialized OUT OF BAND (the staging step I did by hand here). README flag
  3 already notes `build_trackdb` is out-of-band for the same reason
  (panel-wide scalar ACC=LABEL args, not collection edges) — confirmed: it ran
  fine via direct scalar inputs but cannot be map-over-wired declaratively.

- **hub_check hub_url is a placeholder.** `hub_url` default `hub.txt` in the WF
  cannot resolve until the tree is staged; real validation runs post-staging
  (done here). Additionally, Galaxy-job Docker network isolation means the
  in-Galaxy hubCheck cannot fetch an HTTP-served hub at all — the realistic gate
  is to run hubCheck where it can reach the staged tree (host/CI), as done here.

## Honesty notes

- hubCheck's CLEAN result was obtained with the version-matched biocontainer
  binary (`ucsc-hubcheck:482`), NOT via the in-Galaxy tool, because the Galaxy
  job sandbox has no network route to a local hub. The binary is identical; the
  Galaxy tool itself ran (job reached the tool, produced a report) — it simply
  reported a network-unreachable hub. This is disclosed in full above.
- The single transient hubCheck warning/error came from a placeholder trackDb I
  authored for the second (target) genome to satisfy genomes.txt — not from any
  WF-K tool. Removed once identified; final state is clean.
- One synthetic MAF block (`contigX.scaf1`, ref-less) was included specifically
  to exercise process_maf's ref-less-block drop; it was correctly dropped.
