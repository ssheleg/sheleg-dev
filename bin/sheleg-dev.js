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

function usage() {
  console.log(`sheleg-dev installer

Usage:
  npx @ssheleg/sheleg-dev [--force]   install all sheleg-dev skills
                                       into ~/.claude (skip existing unless --force)
  npx @ssheleg/sheleg-dev --help

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
  return 0;
}

process.exit(main(process.argv));
