# Phase C — `align_chain_project/`

Phase C used to be one combined workflow (`align_chain_project.gxwf.yml`) that
did **two independent things** with no data dependency between them. It is now
**split into two workflows** in this directory:

| Workflow | File | Does |
|---|---|---|
| **WF-C** `align_chain` | `align_chain.gxwf.yml` | pairwise alignment → UCSC chain pipeline (cleaned + reciprocal-best chains) |
| **WF-C2** `project_annotations` | `project_annotations.gxwf.yml` | anchor gene-annotation projection (Liftoff → triage → merge) |

They share no steps; run them independently (re-project without realigning, or
vice-versa). Both **run one-click** — a single invocation with collection
inputs, no per-pair driving and no custom enumeration helpers — using Galaxy's
native collection-operation tools. Both were validated **bit-identical** to the
earlier per-pair driving on the Pv4 test panel (cleaned `PvP01.PvW1`: 11726
lines, chain score 293706235; merged `PvP01→PvW1`: 856 mRNA), within KegAlign GPU
run-to-run variance of the `run_all.sh` ground truth.

## How the map-over works (native built-ins, no helpers)

The historical gxformat2 blocker was that a `list:paired` slot could not be
addressed into the two separate `data` inputs of axtChain / chainNet, and the
anchor×query grid could not be co-fanned. Both are solved natively:

- **`__CROSS_PRODUCT_FLAT__`** takes two `list`s and emits **two aligned flat
  lists** (`output_a`, `output_b`). Feed `output_a`→target and `output_b`→query:
  Galaxy's element-wise (dot-product) matching then maps the two-input tool over
  every pair. This *is* the paired-slot→two-input binding, expressed natively.
- **`__FILTER_FROM_FILE__`** (`remove_if_present`) drops the diagonal/self pairs
  (chains 25→20; projection 15→12).
- **`__RELABEL_FROM_FILE__`** rewrites the `A_B` pair ids to `A.B` (the
  `join_identifier` select offers only `_ : -`, and Phase E parses `{a}.{b}` on
  dots).

## WF-C — `align_chain`

`cross_product_flat(masked_fastas, masked_fastas)` → 25 ordered pairs → filter
self → 20. KegAlign(target,query) → batched_lastz → axtChain → chainSort →
chainPreNet → chainNet → netChainSubset → chainStitchId = **20 directed cleaned
chains** (both directions come straight from the cross product). The
reciprocal-best branch (swap → sort → chainNet with swapped sizes → subset →
stitch → swap → sort) yields the rbest chains. `relabel_from_file` rewrites both
to `A.B`.

| Input | Type | Source |
|---|---|---|
| `masked_fastas` | list | WF-B softmasked FASTAs (id=strain) |
| `sizes` | list | WF-A `.sizes` (id=strain) |
| `self_pairs` | txt | strain self-pair ids `X_X` to exclude (WF-A) |
| `relabel_map` | tabular | `A_B<TAB>A.B` id map for Phase E (WF-A) |

**Outputs:** `cleaned_chains` (20, id `A.B`), `rbest_chains` (id `A.B`),
`pairwise_axt`.

> **Note — `rbest_chains` emits 20 directed, not 10 unordered.** The cross
> product yields both `A.B` and `B.A`, so a reciprocal-best chain is computed for
> each direction. Harmless downstream — Phase E `rbest_overlap` keys on the
> `{a}.{b}` stem and the union-find dedupes the redundant direction — but for
> exact GT parity, add a `__FILTER_FROM_FILE__` reducing the rbest branch to an
> `A<B` id set.

## WF-C2 — `project_annotations` (Liftoff-only)

`cross_product_flat(anchor_assemblies, assemblies)` builds the anchor×query grid
(3×5 = 15 cells; plus parallel grids for the anchor GFF/BED12 and query
softmasked FASTA, all keyed `anchor_query` and mutually aligned) → filter 3 self
→ 12. The anchor self-cell id list (`A_A`) is generated **internally** by
`collection_self_pairs` on the anchor element identifiers (no input file).
Liftoff → phase_c2_triage → phase_c4_merge (`use_toga: no`) map over the grid →
**12 merged annotations + 12 classification tables**.

`query_name` is a constant label: per-element scalars derived from a map-over
identifier are not expressible in gxformat2, but the per-cell query *data* is
correct via id-aligned collections, and Phase E keys on the collection element
id, not the internal label.

| Input | Type | Source |
|---|---|---|
| `anchor_assemblies` | list | anchor unmasked FASTAs (Liftoff reference) |
| `anchor_gene_gff3s` | list | anchor `gene.gff3` (gene-level types renamed to `gene`; Liftoff default mode finds zero `gene` features in the native `protein_coding_gene`/`ncRNA_gene`/`pseudogene` GFF3) |
| `anchor_bed12s` | list | anchor BED12 (triage/merge ref-bed) |
| `assemblies` | list | query unmasked FASTAs (Liftoff target = query) |
| `query_masked` | list | query softmasked FASTAs (triage query-fasta; WF-B) |

**Outputs:** `merged_annotations` (12, id `anchor_query`), `classifications` (12).

> **TOGA2 note.** This one-click form is **Liftoff-only**, matching the
> ground-truth run (which fell back to Liftoff-only because the TOGA1 image was
> unpullable). The TOGA2 v2.0.8 rescue branch (`toga2.py run` over the full
> anchor BED12 + cleaned chain, merged with `use_toga: yes`) is a per-anchor
> add-on; it is GPU-independent but CPU/IO-heavy and container-only
> (`toga2:local`), so it is not wired into the one-click map-over here.

## History

The earlier port used three bespoke helper tools (`__pair_strains__`,
`__pair_sizes__`, `__cross_product__`) plus per-pair API staging for the
slot-binding and anchor×query gaps. Those were replaced by the native
collection-operation built-ins. The combined `align_chain_project.gxwf.yml` was
then split into the two independent workflows above (the chaining and projection
halves never shared data).
