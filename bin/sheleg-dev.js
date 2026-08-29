#!/usr/bin/env node
/*
 * sheleg-dev installer CLI.
 *
 * Installs every sheleg-dev skill into ~/.claude/skills/<name>
 * (same layout as install.sh). Idempotent: an existing install is skipped unless
 * --force. Zero dependencies.
 *
 * For other agents (Cursor, Codex, 70+) use: npx skills add ssheleg/sheleg-dev
 */
'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

const ROOT = path.resolve(__dirname, '..');
const REPO = 'ssheleg/sheleg-dev';

// Exit codes are the contract: 0 installed or skipped, 1 corrupted package,
// 2 usage error, 3 refused — the plugin channel owns this agent (--force overrides).
const EXIT_PLUGIN_PRESENT = 3;

/**
 * The plugin spec (`<name>@<marketplace>`) installed for `name` in this home,
 * or null.
 *
 * `installed_plugins.json` is the record of what is actually installed. The
 * `plugins/marketplaces/<name>` directory — the check other members of this
 * family keyed on until 2026-08-29 — under-reports: a marketplace added from a
 * local `directory` source has no dir there at all, and plugin names differ
 * from marketplace names, so a check keyed on it stays green while the shadow
 * lands. Absence and corruption both read as "no plugin": the fresh HOME is
 * the common case, and an installer that crashes on a parse error refuses the
 * machines that need it most.
 */
function installedPluginSpec(home, name) {
  try {
    const raw = fs.readFileSync(
      path.join(home, '.claude', 'plugins', 'installed_plugins.json'), 'utf8');
    const parsed = JSON.parse(raw);
    const plugins =
      parsed && typeof parsed === 'object' &&
      parsed.plugins && typeof parsed.plugins === 'object'
        ? parsed.plugins
        : parsed;
    if (!plugins || typeof plugins !== 'object') return null;
    for (const spec of Object.keys(plugins)) {
      if (spec === name) return `${name}@${name}`;
      if (spec.startsWith(name + '@')) return spec;
    }
  } catch {
    // missing or corrupt = no plugin — fail open on absence, never crash
  }
  return null;
}

function usage() {
  console.log(`sheleg-dev installer

Usage:
  npx @ssheleg/sheleg-dev [--force]   install all sheleg-dev skills
                                       into ~/.claude (skip existing unless --force)
  npx @ssheleg/sheleg-dev --help

Exit codes:
  0 installed or skipped   2 usage error
  1 corrupted package      3 refused: the sheleg-dev PLUGIN is installed in
                             this home — plain copies would shadow its skills
                             (pass --force to write them anyway)

Other install paths:
  Claude Code plugin:  /plugin marketplace add ${REPO}
                       /plugin install sheleg-dev@sheleg-dev
  Any agent (70+):     npx skills add ${REPO}`);
}

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, entry.name);
    const d = path.join(dest, entry.name);
    if (entry.isDirectory()) copyDir(s, d);
    else fs.copyFileSync(s, d);
  }
}

function installOne(label, src, dest, isDir, force) {
  if (fs.existsSync(dest) && !force) {
    console.log(`skip: ${label} already installed at ${dest} (rerun with --force to overwrite)`);
    return;
  }
  fs.rmSync(dest, { recursive: true, force: true });
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  if (isDir) copyDir(src, dest);
  else fs.copyFileSync(src, dest);
  console.log(`Installed ${label} -> ${dest}`);
}

function main(argv) {
  const args = argv.slice(2);
  if (args.includes('--help') || args.includes('-h')) {
    usage();
    return 0;
  }
  const force = args.includes('--force');
  const unknown = args.filter((a) => a !== '--force');
  if (unknown.length) {
    console.error(`unknown argument(s): ${unknown.join(' ')}`);
    usage();
    return 2;
  }

  const skillsRoot = path.join(ROOT, 'plugins/sheleg-dev/skills');
  if (!fs.existsSync(skillsRoot)) {
    console.error(`error: skill sources missing at ${skillsRoot} — corrupted package?`);
    return 1;
  }

  const names = fs
    .readdirSync(skillsRoot, { withFileTypes: true })
    .filter((e) => e.isDirectory())
    .map((e) => e.name)
    .sort();
  if (!names.length) {
    console.error(`error: no skills found under ${skillsRoot} — corrupted package?`);
    return 1;
  }

  const home = os.homedir();

  // One channel per agent. Plain copies under ~/.claude/skills/ beside the
  // installed sheleg-dev plugin are a second listing of the same skills, and
  // the stale copies win — the exact shadow this family's canon forbids.
  // Refuse rather than create them, and refuse LOUDLY: a marketplaces/-dir
  // check alone is the fail-open class (a directory-sourced marketplace has no
  // dir there, plugin names differ from marketplace names), and a refusal that
  // exits 0 reads as success to every script above it. Reproduced live
  // 2026-08-29: a bare `npx @ssheleg/telegram-dev` shipped three shadows past
  // exactly that hole while the plugin was enabled.
  const spec = installedPluginSpec(home, 'sheleg-dev');
  const marketplace = path.join(home, '.claude', 'plugins', 'marketplaces', 'sheleg-dev');
  const viaMarketplaceDir = !spec && fs.existsSync(marketplace);
  if ((spec || viaMarketplaceDir) && !force) {
    const found = spec
      ? `installed as the Claude Code plugin ${spec}\n` +
        '         (declared in ~/.claude/plugins/installed_plugins.json)'
      : `registered as a Claude Code marketplace\n         (${marketplace})`;
    console.error(
      `refused: sheleg-dev is already ${found}.\n` +
      `         Plain copies in ~/.claude/skills/ would shadow the plugin's\n` +
      `         ${names.length} skills and serve this frozen version forever. Update the\n` +
      '         plugin channel instead:\n' +
      '           claude plugin marketplace update sheleg-dev\n' +
      `           claude plugin update ${spec || 'sheleg-dev@sheleg-dev'}\n` +
      '         Family launcher (updates every member, prunes shadow copies):\n' +
      '           npx --yes sshlg-skills@latest update\n' +
      '         Pass --force to write the plain copies anyway — a deliberate choice\n' +
      '         to run two channels, where the stale one wins.'
    );
    return EXIT_PLUGIN_PRESENT;
  }

  for (const name of names) {
    installOne(
      `${name} skill`,
      path.join(skillsRoot, name),
      path.join(home, '.claude', 'skills', name),
      true,
      force
    );
  }

  // The manual gate does not travel this way, and saying so is the whole of what this
  // installer can honestly do about it. `plugins/sheleg-dev/hooks/` is a PreToolUse hook
  // that refuses a refund, a payout, a live key and the free-money path; the plugin
  // channel loads it from the plugin manifest, this channel copies skills only.
  //
  // **It is a notice, not an install.** Writing to a person's `~/.claude/settings.json`
  // is the one thing this repository must never do unasked: it is a file the operator
  // owns and did not write, with no version control behind it, and the family umbrella
  // carries two defects in its own history from doing exactly that. So the step is
  // printed and left to the reader — README.md, "The manual gate", carries the JSON.
  if (fs.existsSync(path.join(ROOT, 'plugins/sheleg-dev/hooks/hooks.json'))) {
    console.log('');
    console.log('Note: the manual gate (a PreToolUse hook refusing refunds, payouts, live');
    console.log('keys and SKIP_BILLING in production) ships with the PLUGIN, not with this');
    console.log('skills copy. To get it here, register it yourself — README.md, section');
    console.log('"The manual gate", has the settings snippet. Nothing enforces this step.');
  }
  // The last line says how the next version arrives — "Installed" is not a
  // complete sentence. Auto-update is off on purpose: this member composes
  // with its family, and per-marketplace autoUpdate moves each member on its
  // own clock, into combinations nobody tested together.
  console.log(
    '\nUpdates: rerun `npx @ssheleg/sheleg-dev@latest --force`, or refresh the\n' +
    'whole family with `npx --yes sshlg-skills@latest update` (every channel,\n' +
    'and it prunes plain copies that would shadow a plugin).'
  );
  return 0;
}

process.exit(main(process.argv));
