# WF-A `inventory` (Phase A)

Inventory / QC for the panel: sourmash similarity matrix + per-strain BUSCO.

## Inputs

| Input | Type | Notes |
|---|---|---|
| `assemblies` | `collection` (list) | Per-strain assembly FASTAs. Element identifier = strain name. |
| `proteomes` | `collection` (list) | Per-strain protein FASTAs, parallel to assemblies (keyed by strain). BUSCO maps over THIS, not assemblies. |
| `busco_lineage` | `string` (default `apicomplexa_odb10`) | BUSCO lineage dataset, species-configurable. |

> `proteomes` is supplied as its own collection input here (commit-one decision
> per PIPELINE_PORT_PLAN WF-A). If the panel only has assemblies+annotations,
> derive proteomes upstream via `gffread -y` over (annotations, assemblies) and
> add `proteomes` to GALAXY.md Inputs.

## Steps — wrappers vs IUC

| Step | tool_id | Source | Action |
|---|---|---|---|
| `sourmash_sketch` | `sourmash_sketch` | **IUC** | `sketch dna -p k=31,scaled=1000`, map-over `assemblies` → one `.sig` each. |
| `sourmash_compare` | `sourmash_compare` | **IUC** | N×N **similarity** matrix (1.0 = identical) → `compare.csv`. |
| `busco` | `busco` | **IUC** | `-m prot -l <lineage>`, map-over `proteomes` (per strain). |

No OUR wrappers in this workflow — all three are IUC.

## Outputs

- `similarity_matrix` — `compare.csv` (similarity). Feeds **WF-I fold order**, sorted **descending** (closest = highest similarity).
- `signatures` — per-strain `.sig` (BRC-reusable).
- `busco_summaries` — per-strain BUSCO short summaries.

## RUNNABILITY

- **IUC deps pending install** — `sourmash_sketch`, `sourmash_compare`, `busco`
  must be installed in this Galaxy before the workflow runs. Short toolshed ids
  used per house style; `planemo workflow_lint` resolves all three.
- **Phase A is not byte-diffable** vs the validated local run (which emitted
  mash `dist.tsv`, no `compare.csv`). Validate by **structural assertion**:
  N labels in header, similarities ∈ [0,1], descending fold-order sanity —
  not byte-diff. `verify_essentials.sh`'s "Mash distance matrix" check is N/A.
- **Param caveat**: sourmash/BUSCO sub-parameter `state` keys (e.g.
  `input_type|sequence_file`, `lineage|lineage_dataset`, `csv`) follow the
  conventional IUC tool form. They cannot be validated against the live tool
  forms until the IUC tools are installed; reconcile the `state:` blocks
  against the installed tools' parameter names on first run.

## Lint

```
planemo workflow_lint workflows/inventory/inventory.gxwf.yml
# WARNING: Workflow missing test cases.
# CHECK: All tool ids appear to be valid.
```

(Only the standard "missing test cases" warning; no creator/license/annotation/
schema warnings; all tool ids valid.)
