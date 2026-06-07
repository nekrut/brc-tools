#!/usr/bin/env bash
# Reconstruct v2-equivalent inputs:
# - filter Sal-I (GCA_000002415.2) to CM* + DS* contigs only (v2 dropped 2647 unplaced)
# - PanSN-rename every strain with the GCA accession as sample (matches v2 path names)
# - output one fasta per accession at data/v2like/{ACC}.fa.gz
#
# Run inside the pggb container so samtools/bgzip/seqkit are available.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RAW="/home/anton/git/Pv4-pangenome/v3/genomes/raw"
OUT="$REPO/data/v2like"
mkdir -p "$OUT"

# strain -> accession (from PANGENOME.md)
declare -A MAP=(
    [PvP01]=GCA_900093555.2
    [Sal-I]=GCA_000002415.2
    [PvW1]=GCA_914969965.1
    [PAM]=GCA_949152365.1
    [PvSY56]=GCA_003402215.1
    [PvT01]=GCA_900093545.1
    [PvC01]=GCA_900093535.1
    [MHC087]=GCA_040114635.1
)

IMG=quay.io/biocontainers/pggb:0.7.4--h9ee0642_0

for strain in "${!MAP[@]}"; do
    acc="${MAP[$strain]}"
    src="$RAW/${acc}.fa.gz"
    out="$OUT/${acc}.fa.gz"
    if [[ -s "$out" ]]; then
        echo "[skip] $strain ($acc)"
        continue
    fi
    echo "[prep] $strain ($acc)"
    if [[ "$acc" == "GCA_000002415.2" ]]; then
        # Sal-I: filter to the exact 100 contigs v2 used (extracted from v2 GFA path names)
        # CM000442.1..CM000455.1 (14 chromosomes) + DS480727.1..DS480812.1 (86 placed scaffolds)
        # PanSN-rename: ACC#1#CONTIG
        keep_file="$OUT/sal_i_v2_keep.txt"
        if [[ ! -s "$keep_file" ]]; then
            zcat /home/anton/git/Pv4-pangenome/v2/pggb_out/*.smooth.fix.gfa.gz | grep "^P" \
                | awk '{print $2}' | grep "GCA_000002415.2" \
                | awk -F'#' '{print $3}' | sed 's/#.*//' | sort -u > "$keep_file"
        fi
        docker run --rm -u "$(id -u):$(id -g)" \
                -v "$RAW:/src:ro" -v "$OUT:/dst:rw" "$IMG" bash -c "
            zcat /src/${acc}.fa.gz \
            | awk -v acc=$acc -v keep=/dst/sal_i_v2_keep.txt 'BEGIN{while((getline line < keep) > 0) k[line]=1; p=0} /^>/{name=substr(\$1,2); if (name in k) {p=1; print \">\" acc \"#1#\" name} else {p=0}; next} p {print}' \
            > /tmp/filt.fa && bgzip -c /tmp/filt.fa > /dst/${acc}.fa.gz"
    else
        # Other strains: keep all contigs, PanSN-rename with accession
        docker run --rm -u "$(id -u):$(id -g)" -v "$RAW:/src:ro" -v "$OUT:/dst" "$IMG" bash -c "
            zcat /src/${acc}.fa.gz \
            | awk -v acc=$acc '/^>/{name=substr(\$1,2); print \">\" acc \"#1#\" name; next} {print}' \
            > /tmp/filt.fa && bgzip -c /tmp/filt.fa > /dst/${acc}.fa.gz"
    fi
done

echo
echo "Per-strain PanSN-renamed FASTAs in $OUT:"
ls -la "$OUT"
echo
echo "Contig counts:"
for f in "$OUT"/*.fa.gz; do
    printf "  %-30s %d contigs\n" "$(basename $f)" "$(zcat $f | grep -c '^>')"
done
