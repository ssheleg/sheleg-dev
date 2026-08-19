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

# The manual gate does not travel this way, and saying so is the whole of what this
# script can honestly do about it. `plugins/sheleg-dev/hooks/` is a PreToolUse hook that
# refuses a refund, a payout, a live key and the free-money path; the plugin channel loads
# it from the plugin manifest, and this channel copies skill directories only.
#
# `bin/sheleg-dev.js` has printed this since v0.7.0 and this script printed nothing — the
# more dangerous of the two channels, since it `rm -rf`s each destination first. Writing to
# the operator's `~/.claude/settings.json` is deliberately NOT done: it is a file they own
# and did not write, with no version control behind it, and the family umbrella carries two
# defects in its own history from doing exactly that. So the step is printed and left.
if [ -f "$ROOT/plugins/sheleg-dev/hooks/hooks.json" ]; then
  echo
  echo "Note: the manual gate (a PreToolUse hook refusing refunds, payouts, live keys"
  echo "and SKIP_BILLING in production) ships with the PLUGIN, not with this skills copy."
  echo "To get it here, register it yourself — README.md, section \"The manual gate\","
  echo "has the settings snippet, both matchers. Nothing enforces this step."
fi
