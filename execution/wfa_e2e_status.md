# WF-A sourmash e2e status (2026-06-07)

Galaxy 26.1.rc1 @ http://localhost:8080. Runs used the real user API key from
`.env` (history creation needs it; bootstrap admin key only used for tool reload).

## 1. Tool registration — DONE / GREEN

Added a new section `Pangenome :: QC / sketch` to BOTH:
- `~/galaxy/config/local_tool_conf.xml` (running config)
- `galaxy_config_local_tool_conf.xml` (repo mirror)

```xml
<section id="pangenome_qc" name="Pangenome :: QC / sketch">
  <tool file="sourmash_sketch/sourmash_sketch.xml"/>
  <tool file="sourmash_compare/sourmash_compare.xml"/>
</section>
```

Restarted Galaxy (`./run.sh stop`; then `GALAXY_SKIP_CLIENT_BUILD=1 ./run.sh
--daemon`). Both ids confirmed via `GET /api/tools`:
`['sourmash_sketch', 'sourmash_compare']`. No load errors in gravity logs.

## 2. WF-A sourmash path e2e — GREEN

Ran the two tools directly via bioblend (cleaner than the workflow given the
workflow params were authored against a wrong/assumed schema — see §4).

Input: 3 chr1 contigs (~0.93–1.02 Mb) extracted with `samtools faidx` from
`data/raw/{PvP01,PvC01,PvSY56}.fa.gz`:
- PvP01  LT635612.2  (1,021,664 bp)
- PvC01  LT615256.1  (977,217 bp)
- PvSY56 QMFC01000001.1 (932,095 bp)

Uploaded as a `list` collection (element_identifier = strain). `sourmash_sketch`
mapped over the collection (3 jobs ok) -> mapped signature list collection ->
`sourmash_compare` (ksize=31) -> CSV. All jobs state=ok.

compare.csv (3x3, strain labels in header, 1.0 diagonal, symmetric):

```
PvC01,PvP01,PvSY56
1.0,0.6348178137651822,0.21742021276595744
0.6348178137651822,1.0,0.21227621483375958
0.21742021276595744,0.21227621483375958,1.0
```

Sanity: PvP01<->PvC01 ~0.63 (both reference-grade Pv chr1, closer); PvSY56 (WGS
strain) ~0.21 to both — biologically plausible.

Verified compare command line (labels staged by strain):
```
... ln -s ... stage/PvP01.sig && ln -s ... stage/PvC01.sig && ln -s ... stage/PvSY56.sig
&& sourmash compare --ksize 31 --csv <out> stage/*.sig
```

### Wrapper bug found + fixed (sourmash_sketch)
First run produced a correct N×N / 1.0-diagonal matrix but the labels were all
`input.fasta` instead of strain names. Root cause: `sourmash compare` labels
rows/cols by each signature's internal `name`/`filename`, NOT by the staged
`.sig` filename. The sketch wrapper symlinked input to a fixed `input.fasta` and
set no name, so every signature's name was empty -> fell back to `input.fasta`.

Fix applied to `tools/sourmash_sketch/sourmash_sketch.xml` (command block):
```
--name '$input.element_identifier'
```
`element_identifier` resolves to the strain for collection elements (and to the
dataset name for standalone HDAs). Reloaded the tool via the admin reload API
(`PUT /api/configuration/toolbox` + per-tool reload) and re-ran: labels now
carry the strain names (the compare.csv above is the post-fix result).
NOTE: this is a behavior change to a committed wrapper; planemo test-data uses
k=21 sigs with names already baked in, so the existing tool tests are unaffected,
but worth a re-run of `planemo test` before re-commit. NOT committed per request.

## 3. busco — PENDING (not blocking), blockers verified

busco IS loaded (`toolshed.g2.bx.psu.edu/repos/iuc/busco/busco/5.8.0+galaxy2`).
Did not run. Exact blockers, verified on this server 2026-06-07:

1. No lineage DB. `lineage_dataset` SELECT has ZERO options;
   `tool-data/shed/busco_database.loc` and `busco_database_options.loc` are
   empty (0 non-comment lines). The busco lineage data manager
   (`data_manager_fetch_busco`) is NOT installed (absent from /api/tools), so a
   lineage cannot be fetched through Galaxy without first installing that DM.
   Needed: install data_manager_fetch_busco, then fetch plasmodium_odb10 /
   apicomplexa_odb10.
2. Input modality. WF-A authored busco as `-m prot` over a proteome collection,
   but test_data ships only genomes. Would need `gffread -y` from annotations
   (test_data lacks annotations) OR switch to `-m genome`.

A standalone `busco -m genome --auto-lineage` smoke outside Galaxy would still
download a lineage from the busco server (network/slow) and would NOT exercise
the Galaxy path, so it was skipped. Marked PENDING with the two concrete blockers
above.

## 4. inventory.gxwf.yml fixes

The sourmash steps were authored against an assumed IUC sourmash schema and were
wrong vs the now-loaded local wrappers. Real schemas (from /api/tools io_details):
- sourmash_sketch: inputs = {`input`:data}; output = `output` (json). No
  input_type/molecule/parameter_k/scaled.
- sourmash_compare: inputs = {`signatures`:data_collection, `ksize`:integer};
  output = `output` (csv). No `csv` boolean.

Fixes made (NOT committed):
- outputSource `sourmash_compare/out1` -> `sourmash_compare/output`
- outputSource `sourmash_sketch/signatures` -> `sourmash_sketch/output`
- sketch step `in:` -> `input: assemblies`; removed the bogus
  state (molecule/input_type/parameter_k/scaled). k=31/scaled=1000 are
  hardcoded in the wrapper.
- compare step `in:` -> `signatures: sourmash_sketch/output`; state -> `ksize: 31`
  (dropped `csv: true`).
- Updated step docs: removed stale "no sourmash wrapper exists" note; marked
  validated e2e. busco doc updated to record verified empty .loc + missing DM.

## Bottom line
- sourmash sketch+compare: GREEN e2e on real Pv chr1 data; 3x3 matrix with
  strain labels (PvC01,PvP01,PvSY56) and 1.0 diagonal.
- one real sketch-wrapper bug fixed (--name from element_identifier).
- inventory.gxwf.yml sourmash steps corrected to the real schemas.
- busco PENDING: needs data_manager_fetch_busco install + lineage fetch, and
  proteome inputs (or -m genome).
- Nothing committed. Did not touch toga2 / /tmp/toga2_build.
```
