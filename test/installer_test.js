#!/usr/bin/env node
/*
 * Installer functional tests — both installers, against throwaway HOMEs.
 *
 * The case that earns this file its place is PLUGIN-PRESENT: an installer that
 * writes ~/.claude/skills/<name> while the same pack is installed as a Claude
 * Code plugin creates plain copies that shadow the plugin's skills and serve
 * this frozen version forever. Until v0.10.5 neither installer here looked at
 * all — and the family's members that did look keyed the check on the
 * plugins/marketplaces/<name> directory alone and exited 0 on refusal, the
 * fail-open class: a directory-sourced marketplace has no dir there, plugin
 * names differ from marketplace names, and exit 0 reads as success to every
 * script above. Every member's CI tested a fresh HOME only, so the
 * plugin-present case had never run anywhere; reproduced live 2026-08-29 with
 * a bare `npx @ssheleg/telegram-dev` shipping three shadows past it.
 *
 * House residue rule: a passing case loses its temp HOME at exit, a failing
 * case KEEPS it (a defect is debugged by reading the tree it landed in), and
 * the run ends with one line saying what it left, `nothing` included.
 */
'use strict';

const { spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const BIN = path.join(ROOT, 'bin', 'sheleg-dev.js');
const SH = path.join(ROOT, 'install.sh');
const POSIX = process.platform !== 'win32';

// The roster is derived from the repository, never hand-written: two releases
// of this repository have failed on a hand-counted skill number (v0.8.0 and
// the six-skill literal before it), and a count that is computed cannot rot.
const SKILLS = fs
  .readdirSync(path.join(ROOT, 'plugins', 'sheleg-dev', 'skills'), { withFileTypes: true })
  .filter((e) => e.isDirectory())
  .map((e) => e.name)
  .sort();

let failures = 0;
const homes = []; // { dir, label, failed }

function freshHome(label) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'sheleg-dev-test-home-'));
  homes.push({ dir, label, failed: false });
  return dir;
}

function run(cmd, args, home) {
  const r = spawnSync(cmd, args, {
    cwd: home, // never the repo: npx inside the package's own repo resolves locally
    env: Object.assign({}, process.env, { HOME: home, USERPROFILE: home }),
    encoding: 'utf8',
    timeout: 120000,
  });
  return { status: r.status, out: (r.stdout || '') + (r.stderr || '') };
}

const installer = (home, ...args) => run(process.execPath, [BIN, ...args], home);
const shInstaller = (home, ...args) => run('bash', [SH, ...args], home);

function skillDir(home, name) {
  return path.join(home, '.claude', 'skills', name);
}

function assertAllInstalled(home, out) {
  for (const name of SKILLS) {
    if (!fs.existsSync(path.join(skillDir(home, name), 'SKILL.md'))) {
      throw new Error(`${name}/SKILL.md missing after install\n${out}`);
    }
  }
}

function assertNothingWritten(home) {
  for (const name of SKILLS) {
    if (fs.existsSync(skillDir(home, name))) {
      throw new Error(`${name} was written despite the refusal`);
    }
  }
}

function declarePlugin(home, spec) {
  const dir = path.join(home, '.claude', 'plugins');
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'installed_plugins.json'), JSON.stringify({
    version: 2,
    plugins: { [spec]: [{ scope: 'user', installPath: '/nonexistent', version: '0.10.4' }] },
  }, null, 2));
}

function caseRun(label, fn) {
  const home = freshHome(label);
  const rec = homes[homes.length - 1];
  try {
    fn(home);
    console.log(`ok: ${label}`);
  } catch (e) {
    rec.failed = true;
    failures++;
    console.error(`FAIL: ${label}\n  ${e.message}`);
  }
}

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

// ---------------------------------------------------------------- node CLI --

caseRun('fresh HOME installs every skill, says how updates arrive, and names the gate', (home) => {
  const r = installer(home);
  assert(r.status === 0, `exit ${r.status}, expected 0\n${r.out}`);
  assert(/^Installed/m.test(r.out), `no "Installed" line:\n${r.out}`);
  assertAllInstalled(home, r.out);
  // one deep file per install channel, so a copy that only creates the
  // directories cannot pass
  assert(
    fs.existsSync(path.join(
      skillDir(home, 'stripe-billing'), 'references', 'webhook-events.md')),
    'references/webhook-events.md did not travel');
  // the last thing an installer states is how the next version arrives
  assert(r.out.includes('sshlg-skills@latest update'), `no update path named:\n${r.out}`);
  // and this channel carries no hook, which it must say (the manual gate ships
  // with the plugin only)
  assert(/manual gate/i.test(r.out), `the gate notice is gone:\n${r.out}`);
});

caseRun('rerun skips every skill, --force overwrites, unknown arg exits 2', (home) => {
  assert(installer(home).status === 0, 'first install failed');
  const skip = installer(home);
  const skips = (skip.out.match(/^skip:/gm) || []).length;
  assert(skip.status === 0 && skips === SKILLS.length,
    `rerun: exit ${skip.status}, ${skips} skip line(s) for ${SKILLS.length} skills\n${skip.out}`);
  const forced = installer(home, '--force');
  const installs = (forced.out.match(/^Installed/gm) || []).length;
  assert(forced.status === 0 && installs === SKILLS.length,
    `--force: exit ${forced.status}, ${installs} Installed line(s)\n${forced.out}`);
  const bad = installer(home, '--wat');
  assert(bad.status === 2, `unknown arg exit ${bad.status}, expected 2`);
});

caseRun('plugin present in installed_plugins.json: refuse, exit 3, remedy, nothing written', (home) => {
  declarePlugin(home, 'sheleg-dev@sheleg-dev');
  const r = installer(home);
  assert(r.status === 3, `exit ${r.status}, expected 3\n${r.out}`);
  assert(r.out.includes('refused'), `no "refused" in output:\n${r.out}`);
  assert(r.out.includes('claude plugin update sheleg-dev@sheleg-dev'),
    `remedy does not name the plugin spec:\n${r.out}`);
  assert(r.out.includes('--force'), `override flag not offered:\n${r.out}`);
  assertNothingWritten(home);
});

caseRun('plugin under a differently-named marketplace: remedy names the real spec', (home) => {
  declarePlugin(home, 'sheleg-dev@sshlg-skills');
  const r = installer(home);
  assert(r.status === 3, `exit ${r.status}, expected 3\n${r.out}`);
  assert(r.out.includes('claude plugin update sheleg-dev@sshlg-skills'),
    `remedy does not carry the spec from the JSON:\n${r.out}`);
  assertNothingWritten(home);
});

caseRun('--force overrides the refusal, deliberately', (home) => {
  declarePlugin(home, 'sheleg-dev@sheleg-dev');
  const r = installer(home, '--force');
  assert(r.status === 0, `exit ${r.status}, expected 0\n${r.out}`);
  assertAllInstalled(home, r.out);
});

caseRun('corrupt installed_plugins.json reads as "no plugin" — install, never crash', (home) => {
  const dir = path.join(home, '.claude', 'plugins');
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'installed_plugins.json'), '{ this is not json');
  const r = installer(home);
  assert(r.status === 0, `exit ${r.status}, expected 0 (fail open)\n${r.out}`);
  assertAllInstalled(home, r.out);
});

caseRun('other plugins, and a prefix-collider, do not trigger a false refusal', (home) => {
  const dir = path.join(home, '.claude', 'plugins');
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(path.join(dir, 'installed_plugins.json'), JSON.stringify({
    version: 2,
    plugins: {
      'telegram-dev@telegram-dev': [{ scope: 'user', installPath: '/x', version: '1.0.0' }],
      'sheleg-dev-extra@somewhere': [{ scope: 'user', installPath: '/y', version: '1.0.0' }],
    },
  }));
  const r = installer(home);
  assert(r.status === 0, `exit ${r.status}, expected 0\n${r.out}`);
  assertAllInstalled(home, r.out);
});

caseRun('marketplaces/<name> dir alone still refuses (fallback signal, exit 3)', (home) => {
  fs.mkdirSync(path.join(home, '.claude', 'plugins', 'marketplaces', 'sheleg-dev'),
    { recursive: true });
  const r = installer(home);
  assert(r.status === 3, `exit ${r.status}, expected 3\n${r.out}`);
  assert(r.out.includes('claude plugin update sheleg-dev@sheleg-dev'),
    `no default remedy spec:\n${r.out}`);
  assertNothingWritten(home);
});

// --------------------------------------------------------------- install.sh --

if (POSIX) {
  caseRun('install.sh: fresh install of every skill, the update line, unknown arg exits 2', (home) => {
    const r = shInstaller(home);
    assert(r.status === 0, `exit ${r.status}, expected 0\n${r.out}`);
    assertAllInstalled(home, r.out);
    assert(new RegExp(`Installed ${SKILLS.length} skill`).test(r.out),
      `no summary counting ${SKILLS.length} skills:\n${r.out}`);
    assert(r.out.includes('sshlg-skills@latest update'), `no update path named:\n${r.out}`);
    assert(/manual gate/i.test(r.out), `the gate notice is gone:\n${r.out}`);
    const bad = shInstaller(home, '--wat');
    assert(bad.status === 2, `unknown arg exit ${bad.status}, expected 2`);
  });

  caseRun('install.sh: plugin present — refuse, exit 3, nothing written; --force installs', (home) => {
    declarePlugin(home, 'sheleg-dev@sheleg-dev');
    const r = shInstaller(home);
    assert(r.status === 3, `exit ${r.status}, expected 3\n${r.out}`);
    assert(r.out.includes('claude plugin update sheleg-dev@sheleg-dev'),
      `remedy does not name the plugin spec:\n${r.out}`);
    assertNothingWritten(home);
    const forced = shInstaller(home, '--force');
    assert(forced.status === 0, `--force exit ${forced.status}\n${forced.out}`);
    assertAllInstalled(home, forced.out);
  });

  caseRun('install.sh: marketplaces dir alone refuses; corrupt JSON fails open', (home) => {
    fs.mkdirSync(path.join(home, '.claude', 'plugins', 'marketplaces', 'sheleg-dev'),
      { recursive: true });
    const r = shInstaller(home);
    assert(r.status === 3, `marketplace-dir exit ${r.status}, expected 3\n${r.out}`);
    assertNothingWritten(home);
    fs.rmSync(path.join(home, '.claude', 'plugins', 'marketplaces'), { recursive: true });
    fs.writeFileSync(path.join(home, '.claude', 'plugins', 'installed_plugins.json'),
      '{ this is not json');
    const ok = shInstaller(home);
    assert(ok.status === 0, `corrupt-JSON exit ${ok.status}, expected 0 (fail open)\n${ok.out}`);
    assertAllInstalled(home, ok.out);
  });
} else {
  console.log('skip: install.sh cases (POSIX only — use npx, the plugin, or the skills CLI on Windows)');
}

// ----------------------------------------------------------------- residue --

let removed = 0;
const kept = [];
for (const h of homes) {
  if (h.failed) {
    kept.push(h);
  } else {
    fs.rmSync(h.dir, { recursive: true, force: true });
    removed++;
  }
}
if (kept.length === 0) {
  console.log(`residue: this run left nothing — ${homes.length} temp home(s) created, ${removed} removed`);
} else {
  console.log(`residue: ${kept.length} of ${homes.length} temp home(s) KEPT`);
  for (const h of kept) {
    console.log(`  ${h.dir}  (case: ${h.label})  — rm -rf '${h.dir}' when done`);
  }
}

if (failures) {
  console.error(`FAIL: installer — ${failures} case(s) red`);
  process.exit(1);
}
console.log(`PASS: installer — ${homes.length} case(s)${POSIX ? '' : ' (install.sh skipped on win32)'}`);
