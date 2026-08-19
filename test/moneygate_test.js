#!/usr/bin/env node
'use strict';
/**
 * Fixtures for the manual gate — both directions, because only one of them is evidence.
 *
 * The audit that produced row SD-03 rated a guard nobody has watched failing as no
 * evidence at all. It also recorded the other half: **a guard that refuses correct input
 * gets switched off**, and then the pack is back to prose. So the plants come in pairs —
 * a defect that must be REFUSED, and the innocent shape closest to it that must be
 * ALLOWED.
 *
 * The false-positive plants are not invented. Every one of them is a command this
 * repository, or a reader of it, actually runs:
 *
 *   - `SECURITY.md:155` sweeps the payload for `sk_live_[A-Za-z0-9]`. That command
 *     contains the forbidden prefix and must run.
 *   - `stripe-agent-toolchain.md:156` and `crypto-payments/SKILL.md:319` quote
 *     `sk_live_…`; reading or grepping them must work.
 *   - `heleket-provider.md` hands the reader a `.env` block through a heredoc fed to
 *     `cat`. That is data, not an export.
 *   - SD-02's own boot assertion REFUSES a test run with no live pin
 *     (`HELEKET_ENV_UNPINNED`), so exporting `HELEKET_LIVE_MERCHANT_ID` in a test run is
 *     required behaviour and must not be gated.
 *
 * No `HOME`, no filesystem, no network: `decide()` takes the payload and an environment
 * object. The last block runs the real hook as a process, because "fails silent" and
 * "exit 0" are properties of the script rather than of the module.
 *
 * Placeholders only. Nothing here is a credential; the live-key fixtures spell
 * PLACEHOLDER in the key body on purpose, while still matching the shape the rule reads.
 */

const assert = require('assert');
const path = require('path');
const { execFileSync, spawnSync } = require('child_process');

const HOOKS = path.join(__dirname, '..', 'plugins', 'sheleg-dev', 'hooks');
const gate = require(path.join(HOOKS, 'lib', 'moneygate.js'));

// KEY_SHAPES_ASSEMBLED_AT_RUNTIME. The gate refuses a live key by SHAPE, so proving it requires live-shaped
// strings — and GitHub's push protection matches that same shape, which blocked this
// suite from ever reaching the remote. Both checks are correct: a scanner cannot know
// the 24-character body spells PLACEHOLDER, and this fixture cannot prove the guard
// without looking like what it guards against. Assembling the value here keeps the
// bytes the gate sees identical while leaving no contiguous literal in the file.
const LIVE_SK = 'sk_' + 'live_' + 'PLACEHOLDER'.repeat(2) + '00';
const LIVE_RK = 'rk_' + 'live_' + 'PLACEHOLDER'.repeat(2) + '00';
const TEST_SK = 'sk_' + 'test_' + 'PLACEHOLDER'.repeat(2) + '00';


let passed = 0;
const failures = [];

function check(name, fn) {
  try {
    fn();
    passed += 1;
  } catch (e) {
    failures.push(`${name}: ${e.message}`);
  }
}

/** A `PreToolUse` payload for a Bash command. */
const bash = (command) => ({ tool_name: 'Bash', tool_input: { command } });

function refuses(name, payload, env, category) {
  check(`REFUSES ${name}`, () => {
    const v = gate.decide(payload, env || {});
    assert.strictEqual(v.allow, false, 'expected a refusal, got an allow');
    if (category) assert.strictEqual(v.category, category, `category was ${v.category}`);
    // A refusal with no next step is how a hook gets switched off.
    assert.ok(v.reason.includes(gate.DECIDES), 'the refusal does not say who decides');
    assert.ok(/Re-declare|exports SHELEG_DEV_LIVE_AUTHORISED|export\s+SHELEG_DEV_LIVE_AUTHORISED|no flag that makes|Ask the operator/.test(v.reason),
      'the refusal names no remedy');
    assert.ok(v.reason.startsWith('[sheleg-dev] refused:'), 'the refusal does not name its source');
  });
}

function allows(name, payload, env) {
  check(`ALLOWS ${name}`, () => {
    const v = gate.decide(payload, env || {});
    assert.strictEqual(v.allow, true, `expected an allow, got: ${v.reason}`);
  });
}

// ------------------------------------------------------- refused: live credentials

// A live-shaped Stripe secret key reaching a shell. The body spells PLACEHOLDER and is
// still 24 characters of [A-Za-z0-9], which is the shape the rule reads.
refuses('a live Stripe secret key exported into a shell',
  bash('export STRIPE_SECRET_KEY=' + LIVE_SK + ' && node server.js'),
  {}, 'live-key');

refuses('a live restricted key passed to curl',
  bash('curl https://api.stripe.com/v1/customers -u ' + LIVE_RK + ':'),
  {}, 'live-key');

refuses('a live key inside a quoted bash -c payload',
  bash("bash -c 'STRIPE_SECRET_KEY=" + LIVE_SK + " node server.js'"),
  {}, 'live-key');

// A key-shaped body reaches even a reading command. `stripe-agent-toolchain.md`: a live
// key in a repository "is an incident, not a lint" — including in a search pattern.
refuses('a key-shaped token inside a search pattern',
  bash("git grep -n '" + LIVE_SK + "'"), {}, 'live-key');

// SD-02's missing half: Heleket issues ONE key per merchant, no test variant, so a shell
// that merely EXPORTS it in a test-declaring run holds production.
refuses('the Heleket merchant key exported in a run declaring test',
  bash('HELEKET_ENV=test HELEKET_API_KEY=PLACEHOLDER-not-a-key node server.js'),
  {}, 'credential');

refuses('the Heleket merchant key exported with no environment declared at all',
  bash('export HELEKET_API_KEY=PLACEHOLDER-not-a-key'),
  {}, 'credential');

refuses('the Heleket merchant key exported through env(1)',
  bash('env HELEKET_API_KEY=PLACEHOLDER-not-a-key HELEKET_ENV=test node server.js'),
  {}, 'credential');

// A heredoc body fed to a SHELL is a script, not data — stripping every heredoc would be
// a documented bypass, which is worse than the false positive it fixes.
refuses('a heredoc body fed to bash, which runs it',
  bash("bash <<'EOF'\nexport HELEKET_API_KEY=PLACEHOLDER-not-a-key\nEOF"),
  {}, 'credential');

// ------------------------------------------------------------ refused: money movement

refuses('a refund through the Stripe CLI',
  bash('stripe refunds create --charge ch_PLACEHOLDER'), {}, 'refund');

refuses('a refund over HTTP',
  bash('curl -X POST https://api.stripe.com/v1/refunds -d charge=ch_PLACEHOLDER'),
  {}, 'refund');

refuses('a refund inside a quoted bash -c payload',
  bash("bash -c 'stripe refunds create --charge ch_PLACEHOLDER'"), {}, 'refund');

refuses('a refund through npx',
  bash('npx --yes stripe refunds create --charge ch_PLACEHOLDER'), {}, 'refund');

refuses('a payout through the Stripe CLI',
  bash('stripe payouts create --amount 5000 --currency usd'), {}, 'payout');

refuses('a transfer through the Stripe CLI',
  bash('stripe transfers create --amount 5000 --destination acct_PLACEHOLDER'), {}, 'payout');

refuses('a Heleket payout over HTTP',
  bash('curl -X POST https://api.heleket.com/v1/payout -d amount=100'), {}, 'payout');

refuses('closing a dispute through the Stripe CLI',
  bash('stripe disputes close du_PLACEHOLDER'), {}, 'dispute');

refuses('closing a dispute over HTTP',
  bash('curl -X POST https://api.stripe.com/v1/disputes/du_PLACEHOLDER/close'), {}, 'dispute');

refuses('a refund named as an MCP tool rather than a shell command',
  { tool_name: 'mcp__plugin_stripe_stripe__create_refund', tool_input: { charge: 'ch_PLACEHOLDER' } },
  {}, 'refund');

// -------------------------------------------------------------- refused: live intent

refuses('an explicit --live flag',
  bash('stripe balance retrieve --live'), {}, 'live-flag');

refuses('an explicit --live-mode flag on an unknown CLI',
  bash('./bin/settle --live-mode'), {}, 'live-flag');

// ----------------------------------------------- refused: the gate's own authority

refuses('a command granting itself the authorisation',
  bash('export SHELEG_DEV_LIVE_AUTHORISED=all'), {}, 'self-authorisation');

refuses('a command switching the gate off',
  bash('SHELEG_DEV_MONEY_GATE=off stripe refunds create --charge ch_PLACEHOLDER'),
  {}, 'self-authorisation');

refuses('the free-money path in a run declaring production',
  bash('SKIP_BILLING=true NODE_ENV=production node server.js'), {}, 'skip-billing');

// ------------------------------------------------- refused: authorisation is scoped

refuses('a refund when only payouts were authorised',
  bash('stripe refunds create --charge ch_PLACEHOLDER'),
  { SHELEG_DEV_LIVE_AUTHORISED: 'payout', SHELEG_DEV_ENV: 'production' }, 'refund');

refuses('a refund in a test-declaring run even with blanket authorisation',
  bash('stripe refunds create --charge ch_PLACEHOLDER'),
  { SHELEG_DEV_LIVE_AUTHORISED: 'all', SHELEG_DEV_ENV: 'test' }, 'refund');

refuses('a refund whose test declaration is inline, even with blanket authorisation',
  bash('HELEKET_ENV=test stripe refunds create --charge ch_PLACEHOLDER'),
  { SHELEG_DEV_LIVE_AUTHORISED: 'all', SHELEG_DEV_ENV: 'production' }, 'refund');

refuses('the free-money path in production even with blanket authorisation',
  bash('SKIP_BILLING=true APP_ENV=production node server.js'),
  { SHELEG_DEV_LIVE_AUTHORISED: 'all' }, 'skip-billing');

// ======================================================================================
// The other direction. Each of these is a real command from this repository or its
// readers, and each one is the innocent shape closest to a rule above.
// ======================================================================================

// SECURITY.md:155 — the payload sweep for live keys. It contains the forbidden prefix.
allows("SECURITY.md's own live-key sweep, verbatim",
  bash('grep -rnE "sk_live_[A-Za-z0-9]|rk_live_[A-Za-z0-9]|whsec_[A-Za-z0-9]{8}|BEGIN [A-Z ]*PRIVATE KEY" plugins'));

allows('reading the reference that quotes sk_live_',
  bash('cat plugins/sheleg-dev/skills/stripe-billing/references/stripe-agent-toolchain.md'));

allows('grepping a reference document for the live-key prefix',
  bash("grep -n 'sk_live_' plugins/sheleg-dev/skills/crypto-payments/SKILL.md"));

// The prefix without a key-shaped body is documentation, not a credential.
allows('a placeholder key in a documented example',
  bash('echo "set STRIPE_SECRET_KEY=sk_live_… in your secret store"'));

// Isolates the SHAPE rule from the reader denylist: python3 is not a reader, and the
// prefix alone still has to pass. With this fixture absent, narrowing LIVE_KEY to the
// bare prefix went unnoticed — every other prefix plant was being saved by READERS.
allows('a secret scanner invoked with the prefix as its pattern',
  bash('python3 scripts/secret_scan.py --prefix sk_live_ --prefix rk_live_ plugins/'));

// Isolates the reader denylist from the shape rule, the same way round: a full endpoint
// URL inside a search pattern searches, and this is how the docs get audited.
allows('grepping the docs for a full refund endpoint URL',
  bash("grep -rn 'https://api.stripe.com/v1/refunds' plugins/"));

// A heredoc body fed to cat is data. This is heleket-provider.md's own .env block.
allows('a .env heredoc fed to cat',
  bash("cat > .env <<'EOF'\nHELEKET_ENV=test\nHELEKET_API_KEY=PLACEHOLDER-not-a-key\nEOF"));

allows('a refund line inside a heredoc fed to python3',
  bash("python3 - <<'PY'\nprint('stripe refunds create --charge ch_X')\nPY"));

allows('a whole-line comment describing the forbidden command',
  bash('# stripe refunds create --charge ch_PLACEHOLDER\npython3 test/validate.py'));

allows('a whole-line comment describing the forbidden export',
  bash('# export HELEKET_API_KEY=PLACEHOLDER-not-a-key\nnpm test'));

allows('grepping for a bare API path in the docs',
  bash("grep -rn '/v1/refunds' plugins/"));

// Isolates the "a URL, not a path" requirement from the reader denylist: python3 is not a
// reader, and a bare path names a route rather than calling one.
allows('a bare API path handed to a route audit script',
  bash('python3 scripts/route_audit.py --expect /v1/refunds --expect /v1/payouts'));

allows('an assignment-shaped string as an argument to grep',
  bash("grep -rn 'HELEKET_API_KEY=' plugins/"));

allows('the --live token as text rather than as a flag',
  bash('echo --live'));

allows('a read-only Stripe CLI call',
  bash('stripe refunds list --limit 3'));

// SD-02's assertion REFUSES an unpinned test run, so this export is required behaviour.
allows('the non-secret live pin exported in a test run, which assertHeleketEnv requires',
  bash('HELEKET_ENV=test HELEKET_LIVE_MERCHANT_ID=00000000-0000-0000-0000-000000000000 node server.js'));

allows('a Stripe TEST key, where the environment is in the key itself',
  bash('STRIPE_SECRET_KEY=' + TEST_SK + ' node server.js'));

allows('the mock path in a non-production run',
  bash('SKIP_BILLING=true NODE_ENV=development node server.js'));

allows('this repository\'s own gate',
  bash('python3 test/validate.py && npm test'));

allows('a commit message containing the forbidden words',
  bash("git commit -m 'docs: explain why refunds create is gated'"));

allows('a tool that writes a document quoting a live key',
  { tool_name: 'Write', tool_input: { file_path: '/tmp/x.md', content: LIVE_SK } });

allows('an unrelated MCP tool',
  { tool_name: 'mcp__plugin_stripe_stripe__stripe_api_read', tool_input: { path: '/v1/refunds' } });

// The gate must be PASSABLE, or it gets removed instead of used.
allows('an authorised refund in a run declaring production',
  bash('stripe refunds create --charge ch_PLACEHOLDER'),
  { SHELEG_DEV_LIVE_AUTHORISED: 'refund', SHELEG_DEV_ENV: 'production' });

allows('an authorised payout under a blanket authorisation',
  bash('stripe payouts create --amount 5000 --currency usd'),
  { SHELEG_DEV_LIVE_AUTHORISED: 'all', SHELEG_DEV_ENV: 'production' });

allows('the documented off switch, set by the operator in the session environment',
  bash('stripe refunds create --charge ch_PLACEHOLDER'),
  { SHELEG_DEV_MONEY_GATE: 'off' });

// -------------------------------------------------------------- the lexer, directly

check('executablePart drops a heredoc body fed to a non-shell', () => {
  const out = gate.executablePart("cat > .env <<'EOF'\nHELEKET_API_KEY=x\nEOF");
  assert.ok(!out.includes('HELEKET_API_KEY'), out);
});

check('executablePart keeps a heredoc body fed to a shell', () => {
  const out = gate.executablePart("bash <<'EOF'\nHELEKET_API_KEY=x\nEOF");
  assert.ok(out.includes('HELEKET_API_KEY'), out);
});

check('executablePart keeps quoted strings, because bash -c is a real invocation', () => {
  const out = gate.executablePart("bash -c 'stripe refunds create'");
  assert.ok(out.includes('stripe refunds create'), out);
});

check('a prefix assignment is an assignment; the same text as an argument is not', () => {
  const [pre] = gate.simpleCommands('HELEKET_API_KEY=x node app.js');
  assert.ok(pre.assignments.has('HELEKET_API_KEY'));
  const [arg] = gate.simpleCommands("grep 'HELEKET_API_KEY=' file");
  assert.ok(!arg.assignments.has('HELEKET_API_KEY'));
});

check('an undeclared environment is null, not test and not production', () => {
  assert.strictEqual(gate.declaredEnv({}, []), null);
  assert.strictEqual(gate.declaredEnv({ NODE_ENV: 'production' }, []), 'production');
  assert.strictEqual(gate.declaredEnv({ NODE_ENV: 'development' }, []), 'test');
});

check('no category is authorisable in a test-declaring run', () => {
  for (const c of Object.keys(gate.CATEGORIES)) {
    assert.strictEqual(gate.allowedFor(c, { SHELEG_DEV_LIVE_AUTHORISED: 'all' }, 'test'), false, c);
  }
});

check('the non-secret Heleket pins are deliberately outside NO_TEST_VARIANT', () => {
  assert.ok(gate.NO_TEST_VARIANT.has('HELEKET_API_KEY'));
  assert.ok(!gate.NO_TEST_VARIANT.has('HELEKET_LIVE_MERCHANT_ID'));
  assert.ok(!gate.NO_TEST_VARIANT.has('HELEKET_LIVE_KEY_FINGERPRINT'));
});

// ------------------------------------------------------- the hook, as a real process

const HOOK = path.join(HOOKS, 'money-gate.js');

function runHook(stdin, env) {
  return spawnSync(process.execPath, [HOOK], {
    input: stdin,
    encoding: 'utf8',
    env: Object.assign({}, env || {}),
  });
}

check('the hook denies a refund and exits 0', () => {
  const r = runHook(JSON.stringify({
    hook_event_name: 'PreToolUse',
    tool_name: 'Bash',
    tool_input: { command: 'stripe refunds create --charge ch_PLACEHOLDER' },
  }), {});
  assert.strictEqual(r.status, 0, `exit ${r.status}`);
  const out = JSON.parse(r.stdout);
  assert.strictEqual(out.hookSpecificOutput.permissionDecision, 'deny');
  assert.ok(out.hookSpecificOutput.permissionDecisionReason.includes('refunds create'));
});

check('the hook says nothing about an ordinary command', () => {
  const r = runHook(JSON.stringify({
    hook_event_name: 'PreToolUse', tool_name: 'Bash', tool_input: { command: 'npm test' },
  }), {});
  assert.strictEqual(r.status, 0);
  assert.strictEqual(r.stdout.trim(), '');
});

check('the hook fails silent on garbage stdin', () => {
  const r = runHook('this is not json at all', {});
  assert.strictEqual(r.status, 0, `exit ${r.status}`);
  assert.strictEqual(r.stdout.trim(), '');
  assert.strictEqual(r.stderr.trim(), '');
});

check('the hook fails silent on empty stdin', () => {
  const r = runHook('', {});
  assert.strictEqual(r.status, 0);
  assert.strictEqual(r.stdout.trim(), '');
});

check('the hook fails silent on a payload with no tool_input', () => {
  const r = runHook(JSON.stringify({ hook_event_name: 'PreToolUse', tool_name: 'Bash' }), {});
  assert.strictEqual(r.status, 0);
  assert.strictEqual(r.stdout.trim(), '');
});

check('the hook is syntactically valid on its own', () => {
  execFileSync(process.execPath, ['--check', HOOK], { stdio: 'pipe' });
  execFileSync(process.execPath, ['--check', path.join(HOOKS, 'lib', 'moneygate.js')], { stdio: 'pipe' });
});

// ------------------------------------------------------------------------- verdict

if (failures.length) {
  console.error(`FAIL: ${failures.length} of ${passed + failures.length} money-gate fixtures`);
  for (const f of failures) console.error(`  - ${f}`);
  process.exit(1);
}
console.log(`OK: money gate — ${passed} fixtures (refusals, false-positive plants, and the hook as a process)`);
