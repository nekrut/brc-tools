#!/usr/bin/env bash
# Install our wrappers into a persistent local Galaxy release_25.0 checkout.
# Symlinks tools/ into $GALAXY_ROOT/local_tools/ and registers them via tool_conf.xml.

set -euo pipefail

GALAXY_ROOT="${GALAXY_ROOT:-$HOME/galaxy}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -d "$GALAXY_ROOT" ]]; then
  echo "ERROR: GALAXY_ROOT not found at $GALAXY_ROOT" >&2
  echo "Clone first: git clone -b release_25.0 https://github.com/galaxyproject/galaxy $GALAXY_ROOT" >&2
  exit 1
fi

LOCAL_TOOLS="$GALAXY_ROOT/local_tools"
mkdir -p "$LOCAL_TOOLS"

for tool_dir in "$REPO_ROOT"/tools/*/; do
  tool=$(basename "$tool_dir")
  link="$LOCAL_TOOLS/$tool"
  if [[ -L "$link" ]]; then
    rm "$link"
  fi
  ln -s "$tool_dir" "$link"
  echo "[link] $tool"
done

# Register a local_tool_conf.xml entry pointing at $LOCAL_TOOLS
CONF="$GALAXY_ROOT/config/local_tool_conf.xml"
if [[ ! -f "$CONF" ]]; then
  cat > "$CONF" <<EOF
<?xml version="1.0"?>
<toolbox tool_path="local_tools">
  <section id="pangenome" name="Pangenome">
$(for d in "$REPO_ROOT"/tools/*/; do
  for xml in "$d"*.xml; do
    rel=$(realpath --relative-to="$GALAXY_ROOT/local_tools" "$xml")
    echo "    <tool file=\"$rel\"/>"
  done
done)
  </section>
</toolbox>
EOF
  echo "[wrote] $CONF"
fi

# Append local_tool_conf.xml to galaxy.yml tool_config_file if not already there
GALAXY_YML="$GALAXY_ROOT/config/galaxy.yml"
if [[ -f "$GALAXY_YML" ]] && ! grep -q local_tool_conf.xml "$GALAXY_YML"; then
  echo "WARNING: add 'local_tool_conf.xml' to tool_config_file in $GALAXY_YML manually" >&2
fi

echo
echo "Done. Restart Galaxy to pick up the new tools."
