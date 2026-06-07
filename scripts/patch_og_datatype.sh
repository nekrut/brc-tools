#!/usr/bin/env bash
# Patch Galaxy's binary.py to register the odgi 0.9 .og datatype.
# Idempotent: skips if 'class Odgi' or similar already present.
# The core galaxyproject/galaxy PR for this lands in P12.

set -euo pipefail

GALAXY_ROOT="${GALAXY_ROOT:-$HOME/galaxy}"
BIN_PY="$GALAXY_ROOT/lib/galaxy/datatypes/binary.py"
DT_CONF="$GALAXY_ROOT/config/datatypes_conf.xml"

if [[ ! -f "$BIN_PY" ]]; then
  echo "ERROR: $BIN_PY not found. Set GALAXY_ROOT correctly." >&2
  exit 1
fi

if grep -q "class Odgi" "$BIN_PY"; then
  echo "[skip] odgi datatype already present in $BIN_PY"
else
  cat >> "$BIN_PY" <<'EOF'


class Odgi(Binary):
    """odgi binary graph (.og), magic bytes vary by version."""
    file_ext = "odgi"
    edam_format = "format_3464"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "odgi binary graph"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"
EOF
  echo "[append] Odgi datatype -> $BIN_PY"
fi

if [[ -f "$DT_CONF" ]] && ! grep -q 'extension="odgi"' "$DT_CONF"; then
  echo "WARNING: add the following line to $DT_CONF under <registration>:" >&2
  echo '    <datatype extension="odgi" type="galaxy.datatypes.binary:Odgi" mimetype="application/octet-stream"/>' >&2
fi

echo "Done. Restart Galaxy."
