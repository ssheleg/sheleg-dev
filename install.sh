#!/usr/bin/env bash
# Install every sheleg-dev skill into ~/.claude/skills/<name>.
# Idempotent: rerun to overwrite. Zero dependencies beyond standard shell tools.
# Refuses to write beside an installed sheleg-dev plugin; --force overrides.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$ROOT/plugins/sheleg-dev/skills"
DEST_ROOT="${HOME}/.claude/skills"

FORCE=0
if [[ "${1:-}" == "--force" ]]; then
  FORCE=1
elif [[ -n "${1:-}" ]]; then
  echo "usage: $0 [--force]" >&2
  exit 2
fi

if [ ! -d "$SRC" ]; then
  echo "error: skill sources missing at $SRC" >&2
  exit 1
fi

# One channel per agent: plain copies beside the installed sheleg-dev plugin
# are a second listing of the same skills, and the stale copies win. Refuse
# rather than create that, and refuse loudly — a marketplaces/-dir check alone
# is the fail-open class: a directory-sourced marketplace has no dir there,
# plugin names differ from marketplace names, and an exit 0 reads as success
# to every script above it. installed_plugins.json is the record of what is
# installed; a missing or unparsable one reads as "no plugin".
INSTALLED_JSON="${HOME}/.claude/plugins/installed_plugins.json"
MARKETPLACE="${HOME}/.claude/plugins/marketplaces/sheleg-dev"
SPEC=""
if [[ -f "$INSTALLED_JSON" ]]; then
  SPEC="$(sed -n 's/.*"\(sheleg-dev@[^"]*\)".*/\1/p' "$INSTALLED_JSON" 2>/dev/null | head -n 1)" || true
fi
if [[ ( -n "$SPEC" || -e "$MARKETPLACE" ) && "$FORCE" -eq 0 ]]; then
  {
    if [[ -n "$SPEC" ]]; then
      echo "refused: sheleg-dev is already installed as the Claude Code plugin $SPEC"
      echo "         (declared in ~/.claude/plugins/installed_plugins.json)."
    else
      echo "refused: sheleg-dev is already registered as a Claude Code marketplace"
      echo "         ($MARKETPLACE)."
    fi
    echo "         Plain copies in ~/.claude/skills would shadow the plugin's skills and"
    echo "         serve this frozen version forever. Update the plugin channel instead:"
    echo "           claude plugin marketplace update sheleg-dev"
    echo "           claude plugin update ${SPEC:-sheleg-dev@sheleg-dev}"
    echo "         Family launcher: npx --yes sshlg-skills@latest update"
    echo "         Pass --force to write the plain copies anyway."
  } >&2
  exit 3
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
# How the next version arrives — "Installed" is not a complete sentence.
echo "Updates: git pull && ./install.sh, or npx --yes sshlg-skills@latest update"

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
