#!/usr/bin/env bash
# Fetch the 8 P. vivax assemblies for the pangenome e2e run.
# Stores FASTAs as data/raw/{strain}.fa.gz, named by strain not accession.
# Source: /home/anton/git/Pv4-pangenome/v3/writeup/PANGENOME.md "How we built the graph".

set -euo pipefail

OUT_DIR="${OUT_DIR:-data/raw}"
mkdir -p "$OUT_DIR"

# strain    accession            source
ASSEMBLIES=(
  "PvP01:GCA_900093555.2"
  "Sal-I:GCA_000002415.2"
  "PvW1:GCA_914969965.1"
  "PAM:GCA_949152365.1"
  "PvSY56:GCA_003402215.1"
  "PvT01:GCA_900093545.1"
  "PvC01:GCA_900093535.1"
  "MHC087:GCA_040114635.1"
)

if ! command -v datasets >/dev/null 2>&1; then
  echo "ERROR: NCBI 'datasets' CLI not on PATH." >&2
  echo "Install: mamba install -c conda-forge -c bioconda ncbi-datasets-cli" >&2
  exit 1
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

for entry in "${ASSEMBLIES[@]}"; do
  strain="${entry%%:*}"
  acc="${entry##*:}"
  out="$OUT_DIR/${strain}.fa.gz"

  if [[ -s "$out" ]]; then
    echo "[skip] $strain ($acc) already at $out"
    continue
  fi

  echo "[fetch] $strain ($acc)"
  datasets download genome accession "$acc" \
    --include genome --filename "$tmp/${strain}.zip"
  unzip -p "$tmp/${strain}.zip" '*/GCA_*_genomic.fna' \
    | gzip -c > "$out"
  rm "$tmp/${strain}.zip"
done

echo
echo "Fetched assemblies in $OUT_DIR:"
ls -la "$OUT_DIR"/*.fa.gz
