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
  return 0;
}

process.exit(main(process.argv));
