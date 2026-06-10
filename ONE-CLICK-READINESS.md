# One-click readiness — per-workflow map-over status

> **UPDATE 2026-06-09 — WF-C is now genuinely one-click.** The three residual
> WF-C gaps below ("paired-slot → two-input binding", "rbest relabel",
> "anchor-vs-cell") are **resolved using Galaxy's native collection-operation
> built-ins**, not the custom helpers:
> `__CROSS_PRODUCT_FLAT__` emits two aligned target/query lists (the slot binding,
> so `__UNZIP_COLLECTION__` is unnecessary), `__FILTER_FROM_FILE__` drops
> self/diagonal pairs, `__RELABEL_FROM_FILE__` rewrites `A_B`→`A.B`. The whole of
> Phase C (20 cleaned + rbest chains + 12 projections) now runs in a **single
> `planemo run`**, proven **bit-identical** to the per-pair driving. The custom
> helpers (`__pair_strains__`, `__pair_sizes__`, `__cross_product__`) have been
> **removed**. The pre-existing analysis below is kept for the rationale of the
> *other* workflows; treat the WF-C verdict as superseded.

**Date:** 2026-06-07
**Galaxy:** 26.1.rc1 @ http://localhost:8080
**Scope:** Which of the 11 gxformat2 workflows now run **one-click** (a single
"Run workflow" with collection inputs, no editor relink and no out-of-band
staging) vs. which still need the **Galaxy workflow editor** or **API staging**
at IWC-packaging time — and *why*, honestly.

All 11 workflows already **compose tool-by-tool** end-to-end on real/synthetic
data (see `execution/wf*_e2e_status.md`). "One-click" here is the stricter bar:
the gxformat2 map-over alone expresses the whole dataflow.

## New helpers built to close tractable gaps

Two `list`/`list:list`/`list:paired` constructor tools were added
(modelled on `tools/__pair_strains__`, stdlib-only Python + `discover_datasets`),
both **planemo-tested green** (2 tests each) and **loaded live** (verified via
`/api/tools/{id}` after a cold Galaxy restart):

| tool id | input → output | closes |
|---------|----------------|--------|
| `cross_product` | two `list`s (anchors, queries) → `list:list` keyed outer=`{anchor}` / inner=`{query}`, self-pairs excluded | WF-C C.4 anchor×query grid; any per-assembly directed fanout |
| `pair_sizes` | per-strain `.sizes` `list` → `list:paired` keyed `{A}__vs__{B}` (forward=A, reverse=B), enumeration **identical** to `pair_strains` | WF-C per-pair `.sizes` join (the biggest WF-C gap) |

`pair_sizes` deliberately reuses `pair_strains`'s exact `A<B` enumeration so the
two `list:paired` collections are **element-for-element identifier-aligned** and
zip under map-over.

Registered in both `~/galaxy/config/local_tool_conf.xml` and the mirror
`brc-tools/galaxy_config_local_tool_conf.xml` under a new
`Pangenome :: Collection helpers` section.

---

## Per-workflow verdict

### One-click (no editor, no staging)

These compose as a pure map-over and were already clean; nothing here needed a
new helper:

- **WF-A inventory / sourmash**, **WF-B softmask**, **WF-D consensus**,
  **WF-F msa**, **WF-G trees**, **WF-H selection** — single-axis list map-overs;
  the only caveat (WF-F/G/H) is that paired map-over inputs must share
  element identifiers, which they do because the OG ids flow unchanged
  (`execution/wffgh_e2e_status.md`). `--srv No` is unreachable in the installed
  hyphy_busted 2.5.96 — a *semantic* CLI gap, not a map-over gap.

### One-click for the JOIN, with a residual editor SLOT-binding

- **WF-C `align_chain_project`** — the per-pair `.sizes` join (previously the
  single biggest gap) is **closed** by `pair_sizes` (step `C.1b`):
  chainPreNet/chainNet now read each pair's target(forward)+query(reverse) sizes
  from `pair_sizes/pair_sizes`; the rbest chainNet uses the same collection with
  the slots swapped. The C.4 anchor×query enumeration is **closed** by
  `cross_product` (step `cross_anchor_query`). WF-C re-imports with **zero
  tool_errors** (41 steps; all three helper steps resolve).

  **Still needs the editor / API staging at packaging:**
  1. **Paired-slot → two-scalar-input binding.** axtChain takes two separate
     FASTA `data` inputs and chainPreNet/chainNet take two separate
     `in_*_ref_index` `data` inputs. The gxformat2 `in:` syntax cannot address
     "the `forward` slot of this `list:paired`" into one input and "the
     `reverse` slot" into the other; that slot binding is set in the editor.
     The *collections* are now correct and aligned — only the 2-way slot fan-out
     is manual.
  2. **rbest `element_identifier` relabel.** Phase E
     (`phase_e_rbest_overlap`) keys strains off the chain filename stem `{a}.{b}`,
     but the rbest output inherits `pair_strains`' `{A}__vs__{B}` id. A relabel
     `{A}__vs__{B}` → `{a}.{b}` is **not** expressible inline. *No clean helper
     built* — a generic "relabel collection identifiers from a regex/map" tool
     would be broadly useful but is out of scope here; the editor rename (or a
     tiny relabel tool later) is the path.
  3. **Anchor-keyed inputs vs. per-cell query.** `cross_product` gives the
     `[anchor][query]` grid (carrying the query assembly), but Liftoff also needs
     the anchor's FASTA/GFF3/BED12, which are indexed by the OUTER id only.
     Co-fanning a per-outer input with a per-cell input in one declarative
     map-over is not expressible; bound in the editor / API staging. The
     single-anchor scalar template steps are kept for the importable CI proof.
  4. **C.1 aligner (F1).** The IUC lastz wrapper emits no axt/psl, so KegAlign
     (GPU, `kegalign`→`batched_lastz`, not installed on this CPU host) is the
     only viable C.1 aligner. Unrelated to map-over — a *wrapper/aligner* choice.

### Fundamental gxformat2 limits — NOT forced into a bad solution

- **WF-I `multiz`** — **`-tPrefix` / `-qPrefix` per-element scalars are COSMETIC,
  not functional.** `multiz_fold` keys ordering purely on the MAF collection
  `element_identifier` + `compare.csv` labels (verified in the wrapper:
  `multiz_fold.xml` symlinks `${el.element_identifier}.maf` and writes
  `queries.txt` from the identifiers — prefixes are never read). The fold
  **composes one-click without prefixes** (proven live,
  `execution/wfij_e2e_status.md`). The prefixes only affect s-line *naming*
  (`strain.chrom`), which WF-K's strain→GenBank rename overrides anyway. A
  per-element scalar derived from a map-over identifier is a known gxformat2
  limit (same one that forces the `hinge_names` parallel-label collection); since
  it is **cosmetic here**, no helper is justified. Documented as a doc-note in the
  YAML; restoring production `strain.chrom` naming is a pre-staging step if ever
  needed. **Verdict: functionally one-click; cosmetic naming needs pre-staging.**

- **WF-J `vcf_projection`** — one-click for the single-target case; the N−1
  per-target fan-out requires two **identifier-matched** input collections
  (`cleaned_chains` and `target_fastas`, both keyed on target). gxformat2 does
  not *enforce* the zip — the user supplies two aligned collections. This is
  collection-construction discipline, not a tool gap; no helper closes it
  (the chains/fastas already exist as upstream lists). **Verdict: one-click given
  identifier-aligned inputs.**
  > **UPDATE 2026-06-10 — proven one-click on real data.** Synthetic 360-variant
  > PvP01 cohort projected onto 4 targets (247/245/342/350). One real fix: the
  > step `tool_id`s were **bare** and broke invocation scheduling — now versioned.

- **WF-K `ucsc_hub`** — **`cross_product` does NOT fully solve it, and I did not
  force it in.** WF-K's two structural gaps are genuinely fundamental:
  1. **Heterogeneous list:list hub layout.** The deliverable is
     outer=accession × inner=track-type, where the track types
     (bigMaf per-reference, bigChain per-directed-pair, annotation
     per-(accession,anchor), 2bit per-accession, selection reference-only) live
     on **different collection axes**. A map-over cannot co-fan heterogeneous
     per-track-type datasets into one nested per-accession collection.
     `cross_product` crosses two *homogeneous* lists; it cannot merge five
     different-axis track collections. **Unsolvable with a constructor helper.**
  2. **`build_trackdb` panel-wide scalars.** It assembles the `GCA_*/` tree from
     scalar `ACC=LABEL` args, not collection edges, so it runs out-of-band.
  The per-assembly 2bit fanout (`fa_to_2bit` map-over `assemblies`) is *already*
  one-click. **Verdict: science tracks build one-click; the hub directory-tree
  assembly + per-assembly trackDb is materialized by an out-of-band staging step
  (API staging at IWC packaging), as it was before — confirmed in
  `execution/wfk_e2e_status.md`.**
  > **UPDATE 2026-06-10 — done on real data.** All tracks built green on the Pv4
  > panel (PvP01-reference hub: bigMaf, 4 bigChain+bigLink, annotation, strict +
  > relaxed BUSTED selection, orthogroup, 5 2bits, genomes.txt). The hub tree was
  > assembled out-of-band (`execution/assemble_hub.py`) and **`hubCheck` returns
  > exit 0, zero errors / zero warnings** (5 genomes, PvP01 = 9 tracks). Confirms
  > the "science tracks one-click, hub tree out-of-band" verdict. Two input/
  > packaging requirements documented in `workflows/ucsc_hub/README.md` (multiz
  > must be `species.chrom` + space-separated; hub.txt/trackDb is out-of-band).

---

## Summary table

| WF | per-pair/grid JOIN | residual | one-click? |
|----|--------------------|----------|------------|
| A,B,D,F,G,H | single-axis map-over | (paired ids must align) | **yes** |
| C | `pair_sizes` + `cross_product` (closed) | paired-slot→2-input bind; rbest relabel; anchor-vs-cell; F1 aligner | join one-click; **editor slot-bind + relabel at packaging** |
| I | n/a | `-t/-qPrefix` **cosmetic** | **functionally yes** (cosmetic naming = pre-stage) |
| J | n/a | two identifier-aligned input lists | **yes given aligned inputs** |
| K | tracks map-over per-assembly | list:list hub layout + build_trackdb scalars **fundamental** | tracks yes; **hub tree = API staging** |

## Honesty notes

- Both new helpers are **real, planemo-green, and live-loaded** (cold-restart
  verified). The `cross_product` `list:list` nesting and `pair_sizes`
  identifier-alignment were proven by the planemo `output_collection` assertions
  (nested `qry1:qry2`-style ids, self-pair exclusion).
- WF-C now imports with **zero tool_errors** including the two new steps.
- I did **not** invent helpers for the fundamentally-unsolvable gaps (WF-K
  heterogeneous list:list layout, WF-I cosmetic prefixes, WF-C rbest relabel /
  paired-slot binding). Those are documented as editor / API-staging tasks rather
  than wired with a tool that would not actually express them.
- No git commit performed.
