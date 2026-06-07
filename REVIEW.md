# Galaxy tool wrapper IUC review

## Summary

Headline: **needs fixes** before opening tools-iuc PRs. Most wrappers are
structurally close to IUC-ready (element order, profile, `detect_errors`,
macro-based versioning all correct), but one cross-cutting correctness bug
(Cheetah Pythonic boolean tests against `truevalue="true"` booleans)
silently breaks every flag it gates. Plus: missing `.shed.yml` on two
tools, no bio.tools xrefs anywhere, no IWC packaging on the workflow,
several redundant `argument=`+`name=` pairs. None are deep design problems
— ~half-day-of-fixes.

## Per-tool findings

### tools/pansn_rename

- [MAJOR] `pansn_rename.xml:25` — `#if $gzip_output` against
  `truevalue="true" falsevalue="false"`. `"false"` is truthy in Python, so
  the `--gzip-output` branch always fires. Tests happen to set matching
  value strings so it looks fine. Fix: `#if str($gzip_output) == "true"`,
  or change truevalue to `--gzip-output` and drop the `#if`.
- [MAJOR] No `<xrefs>` (bio.tools).
- [MINOR] `pansn_rename.xml:52,55` — output labels embed `${sample}` which
  is now optional/auto-derived; when blank, label becomes `: #1#`. Use the
  computed `$sample_value`.
- [MINOR] `pansn_rename.xml:40` — haplotype help text "0 for haploid /
  single-haplotype assemblies use 1" is self-contradictory.
- [NIT] `pansn_rename.py`: `__version__` matches `@TOOL_VERSION@`, logs to
  stderr, `<required_files>` declares it.

### tools/fasta_concat

- [BLOCKER] No `.shed.yml`.
- [BLOCKER] No `macros.xml`; version hardcoded (`1.0.0+galaxy0`,
  `profile="25.0"`). IUC requires the `@TOOL_VERSION@` token pattern.
- [MAJOR] No `<requirements>`, no `version_command`, no `<citations>`.
  Tool relies on system `cat`/`gzip`/`gunzip`; even if it works in
  biocontainers, IUC will reject.
- [MAJOR] Only 1 test, uncompressed path only. Add `compressed=true` and
  mixed compressed/plain tests.
- [MINOR] Cheetah `#for` chained with `&& true` is brittle; prefer
  building a shell list and one `cat` call.
- [MINOR] Overlaps with `fasta-merge` / `cat1` — IUC may ask why this
  exists. progress.md justifies it; add a one-line note to `help`.

### tools/gfaffix

- [MAJOR] `gfaffix.xml:14,17,20` — same Pythonic `#if $bool` bug for
  `output_affixes`, `output_transformation`, `check_transformation`.
  Optional outputs and the verification flag are effectively always-on.
- [MAJOR] `gfaffix.xml:40` — `argument="--dont_collapse"` + redundant
  `name="dont_collapse_regex"`. Drop `name=`.
- [MAJOR] No `<xrefs>`.
- [MINOR] Both tests use `has_size min="0"` (no-op). Assert real content.

### tools/pggb

- [MAJOR] `pggb.xml:43,55,58,61,64,94` — six Pythonic `#if $bool` tests
  (`no_splits`, `run_abpoa`, `skip_normalization`, `skip_viz`, `stats`,
  and the post-pggb `#if not $skip_viz`) against `true/false` string
  booleans. Net effect: those flags are always passed, and the post-pggb
  `not "false"` evaluates False so the viz-output copy block never runs
  for default users — viz/layout/PNG outputs silently missing.
- [MAJOR] No `<xrefs>`.
- [MAJOR] `bgzip`/`samtools` aren't declared in `macros.xml` requirements
  despite the wrapper invoking them on stage-in.
- [MINOR] Post-pggb `;`-chain is justified (progress.md). Cleaner pattern:
  capture exit, always run the output-collection block, then exit 1 only
  when canonical outputs are absent AND pggb exited non-zero — so a
  failing optional `vg deconstruct` no longer kills the job.
- [MINOR] `pggb.xml:165` `vcf_spec` text param: filter `vcf_spec.strip()
  != ""` works, but no validator prevents whitespace-only. Add regex.
- [MINOR] POA params (`poa-length-target`, `poa-params`, `poa-padding`)
  are free text with permissive regex. Consider a `<conditional>` with
  `asm5/10/15/20` presets vs custom.
- [NIT] `format="gfa1.gz"` on `output_gfa` — verify Galaxy has this
  composite type registered.

### tools/wfmash

- [MAJOR] `wfmash.xml:110` — `argument="--sam" name="sam_output"`
  redundant pair. Drop `name=`.
- [MAJOR] Two inconsistent boolean conventions in one file: most flags
  use `truevalue="-m"` + bare `$flag` (clean), but `--sam`/`--md-tag`
  use `truevalue="true" falsevalue="false"` + `#if str($x) == "true"`.
  Standardize on the first.
- [MAJOR] No `<xrefs>`.
- [MINOR] `--threads=` `=`-separator style is non-idiomatic; match
  upstream `--flag value`.
- [MINOR] Text params with `regex="[0-9]*"` accepting blanks are awkward;
  use `type="integer" optional="true"` with `min=`.

### tools/seqwish

- [MAJOR] `seqwish.xml:33,35,38,41` — every param uses redundant
  `name="..."` + short-form `argument="-r"`/`-k`/`-B`/`-m`. SKILL §5 says
  long-form. Switch to `--repeat-max`, `--min-match-len`, etc.
- [MAJOR] `seqwish.xml:30` — `format="fastq,fastq.gz"`. IUC requires
  `fastqsanger,fastqsanger.gz`.
- [MAJOR] No `<xrefs>`.
- [MINOR] Both tests use the same input file; second test only flips
  params, no new code path.

### tools/smoothxg

- [MAJOR] `smoothxg.xml:72` — redundant `argument="--abpoa" name="run_abpoa"`.
- [MAJOR] Only 1 test; add coverage for `--abpoa` or
  `--change-alignment-mode`.
- [MAJOR] No `<xrefs>`.
- [MINOR] `smoothxg.xml:10` `ln -s` doesn't use `-f`; second invocation in
  same workdir will fail.

### tools/odgi

- [MAJOR] `build.xml:17` — `#if $to_gfa` Pythonic test against
  `true/false` booleans. `--to-gfa` always passed; the data is then
  filtered out by `<filter>to_gfa</filter>` (filter sees a real Python
  bool and works), so the command does the work and discards the result.
- [MAJOR] `viz.xml:16` — same bug on `color_by_mean_depth`.
- [MAJOR] `stats.xml:25,30` — redundant `name=` + `argument=` on
  `weak_components` and `nondet_edges`.
- [MAJOR] No `<xrefs>`.
- [MAJOR] `viz.xml` test asserts only `has_size min="100"` on a PNG —
  trivially passing. Add `has_image_width`/`has_image_height`.
- [MINOR] `stats.xml`: if all stat-options are unchecked the command
  produces an empty TSV; add a `no_options` validator on the stat group.
- [MINOR] Mention deferred subcommands (paths/pav/position/layout) in
  `.shed.yml` long_description.

### tools/vg

- [MAJOR] `view.xml:18-43` — verify `--bam` is still a `vg view` flag in
  1.73; the CLI changed between 1.23 and 1.73.
- [MAJOR] `deconstruct.xml:48,55` — redundant `name="paths"`/`name="path_prefixes"`
  + `argument=`. Drop `name=`.
- [MAJOR] `deconstruct.xml:72-89` — the test sidesteps `#` sanitization
  with a non-PanSN path. Reviewer will still ask: add a second test with
  a `--path-prefix` value that contains no `#` (e.g. `>ref_a` and
  `>ref_b` paths, prefix `ref_`) to prove the prefix branch.
- [MAJOR] No `<xrefs>`.
- [MINOR] `convert.xml:9` — `#set $in_ext = ... 'gfa1' else 'gfa'`
  doesn't account for `gfa1.gz`; symlink becomes `input.gfa1.gz`.
- [MINOR] `.shed.yml` mixes 2-space and 1-space indentation.

## Workflow

### workflows/pggb-pangenome-build

- [BLOCKER] No IWC packaging: missing `.dockstore.yml`, `.workflowhub.yml`,
  `tests.yml`. None of the three workflow dirs has them.
- [BLOCKER] `test-data/` is empty (only `.gitkeep`); IWC requires at least
  one minimal `*-test.yml` with input data.
- [MAJOR] Step graph is otherwise minimal and correct: inputs (0-5) →
  pansn_rename (6) → fasta_concat (7) → pggb (8) → odgi_stats (9).
  Indices contiguous.
- [MAJOR] Step 8 hardcodes `skip_viz: "false"`; combined with the pggb
  Cheetah bug, viz outputs are dropped despite the intent. Re-test after
  fixing the tool bug.
- [MINOR] Step 6 has only `input` connected; `sample=""` triggers
  element-identifier auto-derive — surprising. Document in annotation.
- [MINOR] Only 3 workflow_outputs labeled; PNGs/layout/VCF aren't
  surfaced even when produced.
- [MINOR] `workflows/pggb-pav` and `workflows/pggb-vcf-projection` are
  empty placeholder dirs — drop or populate before submission.

## Cross-cutting issues

1. **Cheetah Pythonic `#if $bool` bug** across pansn_rename, gfaffix,
   pggb (6x), odgi/build, odgi/viz. `"false"` is truthy. Suite-wide fix:
   either convert to `truevalue="--actual-flag" falsevalue=""` and drop
   the `#if`, or use `#if str($x) == "true"`. Pattern A is cleaner and
   already used in wfmash for most flags.
2. **No `<xrefs>` anywhere** — all 9 tools. bio.tools IDs exist for pggb,
   wfmash, seqwish, smoothxg, gfaffix, odgi, vg.
3. **Missing `.shed.yml`** on `fasta_concat` and `wfmash`.
4. **Redundant `argument=` + `name=`** in gfaffix, smoothxg, odgi/stats,
   vg/deconstruct, wfmash, seqwish.
5. **bibtex citations alongside DOIs** (pggb, wfmash, smoothxg macros) —
   drop the bibtex blocks.
6. **`has_size min="0"`** in gfaffix tests is a no-op assertion.
7. **`bgzip`/`samtools` not declared** in pggb's requirements macro
   despite the wrapper invoking them on stage-in.

## Punch list (in order of severity)

1. Fix the Cheetah `#if $bool` bug suite-wide (~10 occurrences:
   pansn_rename:25; gfaffix:14,17,20; pggb:43,55,58,61,64,94;
   odgi/build:17; odgi/viz:16).
2. Add `.shed.yml` to `fasta_concat` and `wfmash`.
3. Build out `fasta_concat`: macros.xml, requirements, version_command,
   citations, more tests.
4. Add IWC packaging to `workflows/pggb-pangenome-build/` (`.dockstore.yml`,
   `.workflowhub.yml`, `tests.yml`, real test-data).
5. Add `<xrefs><xref type="bio.tools">…</xref></xrefs>` to every tool.
6. Drop redundant `name=` when `argument=` is set (gfaffix:40,
   smoothxg:72, odgi/stats:25,30, vg/deconstruct:48,55, wfmash:110,
   seqwish:33,35,38,41).
7. seqwish: switch short-flags `-r/-k/-B/-m` to long form;
   `fastq` → `fastqsanger`.
8. vg/deconstruct: add a `--path-prefix` test using a non-`#` prefix.
9. odgi/viz test: assert image dimensions, not just file size.
10. gfaffix tests: replace `has_size min="0"` with real content checks.
11. Drop bibtex citations where DOI exists (pggb, wfmash, smoothxg).
12. pggb: rework post-pggb error handling to exit 1 only when canonical
    outputs missing AND pggb non-zero (so vg deconstruct failures don't
    kill the job); add `bgzip`/`samtools` to requirements; consider POA
    preset `<conditional>`; verify `gfa1.gz` datatype.
13. pansn_rename: fix output label to use `$sample_value`; clarify
    haplotype help.
14. wfmash: standardize boolean conventions; consider switching text+regex
    integer-or-blank pattern to `type="integer" optional="true"`.
15. Drop or populate empty `workflows/pggb-pav` and
    `workflows/pggb-vcf-projection` directories.
