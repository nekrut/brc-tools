# TOGA2 local Docker build + wrapper rewire — STATUS: SUCCESS

Date: 2026-06-07
Author: build agent (Claude)

## Outcome

**Build SUCCEEDED.** A local Docker image `toga2:local` (6.01 GB) was built from the
upstream apptainer.def, the real TOGA2 CLI was discovered, and the Galaxy wrapper at
`tools/toga2/` was re-mapped from the TOGA1 guess to the genuine `toga2.py run` interface.
`planemo lint` passes (only the unavoidable `TestsMissing` warning remains). No git commit made.

## 1. Dockerfile

Written to `/tmp/toga2_build/Dockerfile` (+ `/tmp/toga2_build/entrypoint.sh`).
Faithful translation of `supply/containers/apptainer.def`:

- `FROM continuumio/anaconda3`
- `%post` -> RUN layers: apt (curl, openjdk-17-jdk, git, bsd-mailx, mailutils, build-essential, wget),
  rustup/cargo, Nextflow (`get.nextflow.io` -> `/opt/nextflow`), pip uninstall gensim/numba/datashader,
  pip upgrade streamlit/pyarrow/bottleneck, bash-as-default-sh, `git clone --recurse-submodules
  https://github.com/hillerlab/TOGA2 /opt/TOGA2`, `python3 -m venv toga2 && source ... && make`.
- `%environment` -> ENV + entrypoint PATH (cargo, /opt/nextflow, /opt/conda/bin, /opt/TOGA2 + bin subdirs).
- SLURM/passwd runscript bits **SKIPPED** (no SLURM in Docker), as instructed.
- Runscript `exec "$@"` -> `ENTRYPOINT ["/usr/local/bin/toga2-entrypoint.sh"]` which sources the venv,
  fixes PATH (the upstream `%environment` PATH gets clobbered by a login shell, so PATH is set
  explicitly in the entrypoint), then `exec "$@"`. `CMD ["toga2.py","--help"]`.

Note: first build used `ENTRYPOINT bash -lc 'source...; exec "$@"'` which broke (login shell reset PATH;
`$@` arg passing). Fixed with a dedicated entrypoint script; rebuild used cached layers (fast).

## 2. Build

`docker build -t toga2:local /tmp/toga2_build/` — completed well within the time-box.
`make` ran ~155 s and **all sub-steps succeeded**:
- pip `requirements.txt`: tensorflow-2.20.0, spliceai-1.3.1, xgboost, scikit-learn, ete3, etc. (venv = python 3.12).
- UCSC binaries downloaded (faToTwoBit, twoBitToFa, bigBedToBed, bedToBigBed, ixIxx).
- install_third_party: PRANK compiled, IqTree2 installed.
- install_postoga: `maturin develop --release` OK.
- build_c (gcc), build_cesar (CESAR2.0 make), build_cython (.pyx), build_rust (cargo release; src/rust + bed2gtf) all OK.
- train_models: me_model.dat (acc 99.2%), ld_model.dat (acc 98.9%) saved.

Full build log: `/tmp/toga2_build/build.log`.

## 3a. Real CLI discovered

`toga2.py` is a **click group** (TOGA2 v2.0.8f), not the TOGA1 positional interface. Commands:
`cookbook from-config integrate merge postoga prepare-input run sequence-alignment spliceai summary test`.

`toga2.py run` (the projection command) key options (verified in-container):
- Inputs (all required for non-`input_directory` mode): `--ref_2bit` (**.2bit**, not FASTA),
  `--query_2bit` (.2bit), `--chain_file`, `--ref_annotation` (BED12).
- `-i/--isoform_file` (mutex `--no_isoform_file`); `-u12/--u12_file` (mutex `--no_u12_file`);
  `-sai/--spliceai_dir` (mutex `--no_spliceai`).
- `-o/--output PATH`; `-c/--parallel_strategy` (default `local` = Nextflow over local CPUs, no SLURM);
  `-fj/--feature_jobs`, `-oj/--orthology_jobs`, `-rc/--tree_cpus`; `-k/--keep_temporary_files`.
- **No `--filter_bed`** in `run` (TOGA1's per-gene rescue filter has no TOGA2 `run` equivalent).

Outputs land at top level of `--output`: `query_annotation.bed`, `query_genes.bed`,
`orthology_classification.tsv`, `loss_summary.tsv` (verified in `src/python/modules/toga_main.py`).

## 3b. Wrapper updates (`tools/toga2/`)

**macros.xml**
- `@TOGA_IMAGE@` -> `toga2:local` (local Docker image; was the ghcr `:latest` placeholder).
- `@TOOL_VERSION@` 1.1.7 -> **2.0.8**. Profile kept at **26.0**.
- Container note rewritten (upstream ships only apptainer.def; we translated to Dockerfile and built locally).

**toga2.xml** — command re-mapped from TOGA1 to TOGA2 `run`:

| TOGA1 (old guess)              | TOGA2 `run` (now)                            |
|--------------------------------|----------------------------------------------|
| 4 positional (bed,chain,ref.fa,query.fa) | `--ref_annotation --chain_file --ref_2bit --query_2bit` |
| (FASTA inputs)                 | **2bit** — FASTAs converted in-tool via bundled `faToTwoBit` |
| `--cb`                         | `--isoform_file`                             |
| `--u12 ""`                     | `--no_u12_file`                              |
| (n/a)                          | `--no_spliceai`                              |
| `--kt`                         | `--keep_temporary_files`                     |
| `--nc N`                       | `--feature_jobs/--orthology_jobs/--tree_cpus N` + `--parallel_strategy local` |
| `--pn DIR`                     | `--output DIR`                               |
| `--filter_bed needs_cesar2.bed`| **dropped** (no per-gene filter in `run`)    |

- Added the missing **`query_genes.bed`** output (now 4 outputs: query_annotation.bed, query_genes.bed,
  orthology_classification.tsv, loss_summary.tsv) — matches the 4 files `phase_c4_merge.py --toga-dir` consumes
  (`v3/scripts/phase_c4_merge.py` and `v3/pipeline/impl/scripts/phase_c4_merge.py`).
- `filter_bed` input param removed (TOGA2 `run` has no equivalent; the upstream driver still gates whether
  the tool is invoked, so no functionality lost).
- `version_command` -> `toga2.py --version`.

## 3c. Smoke tests (against `toga2:local`, all pass)

- `docker run --rm toga2:local toga2.py --help` -> RC 0 (click group, 11 commands listed).
- `docker run --rm toga2:local toga2.py --version` -> `TOGA2, version v2.0.8f`, RC 0.
- `docker run --rm toga2:local toga2.py run --help` -> RC 0 (all wrapped flags present).
- Galaxy-style `sh -c`: `faToTwoBit` + `toga2.py` both resolve on PATH; `toga2.py run --help` RC 0.
- Binaries on PATH: faToTwoBit, twoBitToFa, nextflow, cargo, toga2.py — all found.

A Galaxy `<test>` element is NOT included: all 5 inputs are `required`, so an input-less test cannot
validate on a modern profile, and the tool cannot run a meaningful projection on toy data. The CLI smoke
test is documented in the XML comment and run directly against the image instead (rather than faked).

## planemo lint

```
.. WARNING (TestsMissing): No tests found, most tools should define test cases.
.. CHECK (HelpValidRST) / ToolIDValid / ToolNameValid / ToolProfileValid [26.0]
.. CHECK ToolVersionValid [2.0.8+galaxy0] / CitationsFound (2) / HelpPresent
.. INFO OutputsNumber: 4 / InputsNum: 5 / CommandInfo
```
"Failed linting" is solely the `TestsMissing` warning (matches the original wrapper's posture).

## Caveats / follow-ups

- Image is **local only** (`toga2:local`); not pushed. Upstream publishes no Docker image. For deployment,
  push to a registry and pin a digest (`@sha256:...`), per Decision 12.
- TOGA2 clone is unpinned in the Dockerfile (`hillerlab/TOGA2` HEAD; was `b0662fd`/v2.0.8f at build time).
  Pin a commit for reproducibility before deploying.
- Host disk was at 97-99% throughout; the 6 GB image fit but the layer export was slow. Watch space on rebuild.
- The pipeline driver (`impl/04_annotate_project.sh`) still calls the TOGA1 `cmd toga ...` form with FASTA +
  `--filter_bed`. The Galaxy wrapper now diverges from that shell driver (it targets TOGA2). If the shell
  pipeline is also meant to use TOGA2, `04_annotate_project.sh` needs the same re-mapping (out of scope here;
  not touched).
- Did NOT touch `~/galaxy` or other `tools/` dirs. Only `tools/toga2/` and `/tmp/toga2_build/`. No git commit.
