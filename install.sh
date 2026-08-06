#!/usr/bin/env bash
# Install every sheleg-dev skill into ~/.claude/skills/<name>.
# Idempotent: rerun to overwrite. Zero dependencies beyond coreutils.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$ROOT/plugins/sheleg-dev/skills"
DEST_ROOT="${HOME}/.claude/skills"

if [ ! -d "$SRC" ]; then
  echo "error: skill sources missing at $SRC" >&2
  exit 1
fi

count=0
for dir in "$SRC"/*/; do
  [ -d "$dir" ] || continue
  name="$(basename "$dir")"
  dest="$DEST_ROOT/$name"
  mkdir -p "$DEST_ROOT"
  rm -rf "$dest"
  cp -R "$dir" "$dest"
  echo "Installed $name -> $dest"
  count=$((count + 1))
done

if [ "$count" -eq 0 ]; then
  echo "error: no skills found under $SRC" >&2
  exit 1
fi

echo "Installed $count skill(s). Restart your agent — skills load at session start."
