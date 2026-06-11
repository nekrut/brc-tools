#!/usr/bin/env python3
"""Generate the WF-C (align_chain_project) one-click config inputs for a panel.

Usage: gen_wfc_config.py <out_dir> <STRAIN1,STRAIN2,...> <ANCHOR1,ANCHOR2,...>
Emits into <out_dir> (put it on the shared SSD artifacts root):
  self_pairs.txt         one X_X per strain  (FILTER_FROM_FILE remove self pairs)
  anchor_self_pairs.txt  one A_A per anchor  (projection grid self-cells)
  relabel_map.tsv        A_B<TAB>A.B for every ordered strain pair (Phase E ids)
These are the panel-specific config the native cross-product/filter/relabel
built-ins need (no native primitive computes the self-cross diagonal; the
join separator can't be '.').
"""
import sys, os, itertools
out, strains_s, anchors_s = sys.argv[1], sys.argv[2], sys.argv[3]
strains = [s for s in strains_s.split(",") if s]
anchors = [a for a in anchors_s.split(",") if a]
os.makedirs(out, exist_ok=True)
with open(f"{out}/self_pairs.txt", "w") as f:
    f.writelines(f"{s}_{s}\n" for s in strains)
with open(f"{out}/anchor_self_pairs.txt", "w") as f:
    f.writelines(f"{a}_{a}\n" for a in anchors)
with open(f"{out}/relabel_map.tsv", "w") as f:
    for a, b in itertools.product(strains, strains):
        f.write(f"{a}_{b}\t{a}.{b}\n")
n = len(strains)
print(f"strains={n} anchors={len(anchors)}")
print(f"  self_pairs.txt: {n}")
print(f"  anchor_self_pairs.txt: {len(anchors)}")
print(f"  relabel_map.tsv: {n*n} rows ({n}x{n}); directed non-self chains = {n*(n-1)}")
