#!/usr/bin/env node
'use strict';
/**
 * The money fixtures, run as processes, in both modes.
 *
 * Row SD-04 of the manifesto-conformance program, requirements **M-29** (a test is
 * stronger than an instruction) and **M-40** (evidence proves no more than it observed).
 * The defect it closes: this pack knew the four invariants that cost real money and
 * shipped every one of them as prose that delegated enforcement to the reader — the
 * giveaway being an instruction, in the testing reference, to *"delete each guard and
 * re-run"*.
 *
 * `test/validate.py` checks the STRUCTURE — that each invariant has a fixture, each
 * fixture a claim, each claim its paragraph. This file checks the BEHAVIOUR, and it is a
 * separate file for the reason SD-03's split existed: the structural guard can pass over a
 * pack whose assertions no longer discriminate anything.
 *
 * Three things are asserted, and only the first is the obvious one:
 *
 *   1. both packs pass against their reference handler (`node <pack>`);
 *   2. both packs pass their own `--self-test`, which deletes one rule at a time and
 *      requires every assertion to go red. A pack that cannot fail is decoration, and the
 *      audit that produced this row rated it as no evidence at all;
 *   3. **the self-test itself can fail.** An assertion neutered here must make the pack's
 *      `--self-test` exit non-zero. Without this, `--self-test` could be a print
 *      statement — which is the same defect one level up, and the one SD-03 caught when a
 *      `require` check turned out to be reading a doc comment.
 *
 * Requirement 3 is the one that had a hole in it, and the plants below are why it no longer
 * does. Until 2026-08-20 every plant here neutered an invariant's ONLY assertion, because
 * that was the only kind the packs could catch: their runner returned on the first throw and
 * their matrix compared one row per invariant, so a NON-FIRST assertion inside a multi-assert
 * invariant could be replaced by `assert.ok(true)` with `--self-test` still at exit 0 and
 * `npm test` still green. Measured that day across both packs — three neutered assertions in
 * `stripe-billing` and the PII guard in `ad-tracking`, all four undetected. The packs now
 * measure per call site, and the last three plants are the ones that would have caught it.
 *
 * Plus the placeholder sweep, because these files exist to be copied into other people's
 * repositories.
 */

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const SKILLS = path.join(ROOT, 'plugins', 'sheleg-dev', 'skills');

const PACKS = [
  { skill: 'stripe-billing', pack: 'assert-money-invariants.mjs', handler: 'reference-handler.mjs' },
  { skill: 'ad-tracking', pack: 'assert-dedup-contract.mjs', handler: 'reference-emitter.mjs' },
];

let passed = 0;
const failures = [];

function check(name, fn) {
  try {
    fn();
    passed += 1;
  } catch (e) {
    failures.push(`${name}: ${e.message.split('\n')[0]}`);
  }
}

/** Run a pack from its own directory, the way a reader who copied it would. */
function run(dir, file, args) {
  return spawnSync(process.execPath, [file].concat(args || []), {
    cwd: dir, encoding: 'utf8', env: { PATH: process.env.PATH || '' },
  });
}

// ------------------------------------------------------------- the packs, as shipped

for (const { skill, pack, handler } of PACKS) {
  const dir = path.join(SKILLS, skill, 'fixtures');

  check(`${skill}: the pack is syntactically valid`, () => {
    for (const file of [pack, handler]) {
      const r = spawnSync(process.execPath, ['--check', path.join(dir, file)], { encoding: 'utf8' });
      assert.strictEqual(r.status, 0, `node --check ${file}: ${r.stderr}`);
    }
  });

  check(`${skill}: every assertion holds against the reference implementation`, () => {
    const r = run(dir, pack, []);
    assert.strictEqual(r.status, 0, `exit ${r.status}\n${r.stdout}${r.stderr}`);
    assert.match(r.stdout, /^OK: \d+ /m, 'the pack printed no verdict');
    assert.ok(!/^FAIL/m.test(r.stdout + r.stderr), 'a failure was printed with exit 0');
  });

  check(`${skill}: every assertion has been watched failing, and every rule is isolated`, () => {
    const r = run(dir, pack, ['--self-test']);
    assert.strictEqual(r.status, 0, `exit ${r.status}\n${r.stdout}${r.stderr}`);
    assert.match(r.stdout, /isolation —/, 'the self-test printed no isolation report');
    assert.match(r.stdout, /assertion x mutant/, 'the self-test printed no per-assertion matrix');
    assert.match(r.stdout, /watched failing ONE CALL SITE AT A TIME/,
      'the self-test printed no verdict');
  });

  check(`${skill}: the pack reads no network, writes no file, spawns nothing`, () => {
    const src = fs.readFileSync(path.join(dir, pack), 'utf8')
      + fs.readFileSync(path.join(dir, handler), 'utf8');
    // A reader is being asked to run this. The only I/O it may do is read the fixtures
    // beside it, which is `readFileSync`; everything else is refused by name.
    const forbidden = /child_process|\bfetch\(|require\('(http|https|net|dns|tls)'\)|spawn\(|execFile|writeFileSync|appendFileSync|unlinkSync|process\.env\./;
    const hit = src.match(forbidden);
    assert.strictEqual(hit, null, `the pack reaches for ${hit && hit[0]}`);
  });

  check(`${skill}: no fixture carries anything key-shaped`, () => {
    for (const name of fs.readdirSync(dir).filter((f) => f.endsWith('.json'))) {
      const blob = fs.readFileSync(path.join(dir, name), 'utf8');
      for (const shape of [
        /\b(sk|rk|pk)_(live|test)_[A-Za-z0-9]{8,}/,
        /\bwhsec_[A-Za-z0-9]{8,}/,
        /BEGIN [A-Z ]*PRIVATE KEY/,
        /\bEAA[A-Za-z0-9]{20,}/,
      ]) {
        assert.strictEqual(shape.test(blob), false, `${name} matches ${shape}`);
      }
    }
  });
}

// ----------------------------------------------------- the self-test can itself fail
//
// Each entry neuters ONE assertion in a copy of the tree and requires `--self-test` to
// notice. The plant is chosen so the pack's own bookkeeping is what catches it: a
// declared `breaks` list that no longer matches what the mutants measure.

const PLANTS = [
  {
    name: 'an assertion that can no longer fail (stripe: the masked redelivery)',
    skill: 'stripe-billing',
    pack: 'assert-money-invariants.mjs',
    file: 'assert-money-invariants.mjs',
    // The by-count-alone fixture carries exactly one assertion, which is what makes it a
    // clean plant: neuter it and no mutant, single or combined, turns it red.
    from: "      assert.equal(store.grants.length, 1, 'the redelivery granted a second time');\n    },\n  },\n  {\n    id: 'duplicate-refund-claws-back-once',",
    to: "      assert.ok(true);\n    },\n  },\n  {\n    id: 'duplicate-refund-claws-back-once',",
  },
  {
    name: 'an assertion that can no longer fail (ad-tracking: the shared event id)',
    skill: 'ad-tracking',
    pack: 'assert-dedup-contract.mjs',
    file: 'assert-dedup-contract.mjs',
    from: "      assert.equal(serverId, pixelId,",
    to: "      assert.equal(serverId, serverId,",
  },
  {
    name: 'a rule that can no longer be removed (stripe: the grant marker)',
    skill: 'stripe-billing',
    pack: 'assert-money-invariants.mjs',
    file: 'reference-handler.mjs',
    // Wire the marker in unconditionally and it stops being a mutant: no run of the suite
    // has then watched the pack fail without it, which is the state the audit rated as no
    // evidence. The `breaks` bookkeeping is what notices.
    from: "    if (has('grant-marker') && granted.has(period.start)) {",
    to: "    if (granted.has(period.start)) {",
  },
  {
    name: 'a NON-FIRST assertion neutered inside a multi-assert invariant '
      + '(stripe: the cumulative clawback list)',
    skill: 'stripe-billing',
    pack: 'assert-money-invariants.mjs',
    file: 'assert-money-invariants.mjs',
    // The third of three assertions in `refund-total-is-cumulative`, and the exact plant
    // that used to pass: the `total` equality above it discriminates the same rule, so the
    // invariant still went red and the old per-invariant matrix saw nothing. Per call site,
    // this assertion is now broken by no mutant, which is the whole finding.
    from: '      assert.deepEqual(store.clawbacks.map((c) => c.amount), [4000, 5000]);',
    to: '      assert.ok(true);',
  },
  {
    name: 'a NON-FIRST assertion neutered inside a multi-assert invariant '
      + '(ad-tracking: the PII guard meta-linkedin.md advertises by name)',
    skill: 'ad-tracking',
    pack: 'assert-dedup-contract.mjs',
    file: 'assert-dedup-contract.mjs',
    // Second of two in `identifiers-reach-the-server-hashed`. The `assert.match` above it
    // catches the same mutant, so neutering this one left the pack green while the
    // reference that names it kept telling a reader it was enforced.
    from: "      assert.ok(!JSON.stringify(userData).includes('@'),\n"
      + "        'user_data carries something with an @ in it');",
    to: '      assert.ok(true);',
  },
  {
    name: 'a live discriminator silenced by declaring it unmutated (stripe: the renewal grant)',
    skill: 'stripe-billing',
    pack: 'assert-money-invariants.mjs',
    file: 'assert-money-invariants.mjs',
    // The other direction of the same guard. `assert.unmutated` is the escape hatch for an
    // assertion no rule varies, and an escape hatch nobody checks is how a real
    // discriminator gets quietly parked in it. Measured breakable while declared
    // unbreakable has to be a failure, or the hatch is a bypass.
    from: "      assert.equal(store.grants.length, 1, 'a paid renewal granted nothing');",
    to: "      assert.unmutated.equal(store.grants.length, 1, 'a paid renewal granted nothing');",
  },
];

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'sd04-'));

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, entry.name);
    const d = path.join(dest, entry.name);
    if (entry.isDirectory()) copyDir(s, d);
    else fs.copyFileSync(s, d);
  }
}

for (const plant of PLANTS) {
  check(`the self-test refuses: ${plant.name}`, () => {
    const dir = path.join(tmp, `${plant.skill}-${PLANTS.indexOf(plant)}`);
    copyDir(path.join(SKILLS, plant.skill, 'fixtures'), dir);
    const target = path.join(dir, plant.file);
    const src = fs.readFileSync(target, 'utf8');
    assert.ok(src.includes(plant.from), 'PLANT DID NOT LAND — the code it edits moved');
    fs.writeFileSync(target, src.replace(plant.from, plant.to));
    const r = run(dir, plant.pack, ['--self-test']);
    assert.notStrictEqual(r.status, 0,
      `--self-test passed with the plant in place\n${r.stdout}`);
  });
}

fs.rmSync(tmp, { recursive: true, force: true });

// ------------------------------------------------------------------------- verdict

if (failures.length) {
  console.error(`FAIL: ${failures.length} of ${passed + failures.length} fixture checks`);
  for (const f of failures) console.error(`  - ${f}`);
  process.exit(1);
}
console.log(`OK: money fixtures — ${passed} checks (both packs, both modes, `
  + `${PLANTS.length} plants: neutered assertions, an unremovable rule, and a live `
  + 'discriminator parked in the unmutated escape hatch)');
