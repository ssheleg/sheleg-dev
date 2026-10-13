#!/usr/bin/env python3
"""FW03 pure/source controls: no real keys, provider calls or temporary trees."""
import importlib.util
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("validator", ROOT / "test/validate.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
errors = []

def check(name, fn):
    try:
        fn()
    except (AssertionError, AttributeError) as exc:
        errors.append(name)
        print("FAIL:", name, exc)
    else:
        print("OK:", name)

def paths():
    for token in ["plugins/missing/SKILL.md", "test/missing/validate.py", "bin/absent.js",
                  "plugins/missing/file.mjs", "plugins/missing/file.cjs"]:
        assert list(v.skill_repo_path_gaps("`" + token + "`")), token
    for ref in ["999999", "0", "1-999999", "2-1", "0-1"]:
        assert list(v.skill_repo_path_gaps("`test/validate.py:" + ref + "`")), ref
    assert not list(v.skill_repo_path_gaps("`test/validate.py:1`"))
    assert not list(v.skill_repo_path_gaps("`test/validate.py:1-2`"))
    assert not list(v.skill_repo_path_gaps(
        "`plugins/sheleg-dev/skills/stripe-billing/scripts/assert-stripe-env.mjs:1-2`"))
    assert not list(v.skill_repo_path_gaps("`src/web/auth.py` and `next.config.ts`"))

def stripe():
    path = ROOT / "plugins/sheleg-dev/skills/stripe-billing/scripts/assert-stripe-env.mjs"
    program = r"""
import assert from 'node:assert/strict';
const {assertStripeEnv} = await import(process.argv[1]);
const key = (kind, mode) => kind + '_' + mode + '_' + 'FIXTURE';
let total = 0;
for (const kind of ['sk', 'rk']) {
  assert.equal(assertStripeEnv('test', key(kind, 'test')), 'test'); total++;
  assert.equal(assertStripeEnv('production', key(kind, 'live')), 'production'); total++;
  assert.throws(() => assertStripeEnv('test', key(kind, 'live')), /STRIPE_ENV_TEST_HOLDS_LIVE_CREDENTIAL/); total++;
  assert.throws(() => assertStripeEnv('production', key(kind, 'test')), /STRIPE_ENV_LIVE_HOLDS_TEST_CREDENTIAL/); total++;
}
for (const mode of [undefined, '', 'staging', 'live']) {
  assert.throws(() => assertStripeEnv(mode, key('sk', 'test')), /STRIPE_ENV_INVALID/); total++;
}
for (const value of [undefined, '']) {
  assert.throws(() => assertStripeEnv('test', value), /STRIPE_KEY_MISSING/); total++;
}
for (const value of [key('pk', 'test'), key('sk', 'org'), 'fixture', key('sk', 'test') + '\n']) {
  assert.throws(() => assertStripeEnv('test', value), /STRIPE_KEY_MODE_UNVERIFIED/); total++;
}
console.log('Stripe environment assertions:', total);
"""
    result = subprocess.run(['node', '--input-type=module', '-e', program, path.as_uri()],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    print(result.stdout.strip())

def docs():
    ref = "stripe-billing/references/price-integrity.md"
    assert ref in v.CREDENTIAL_BOUNDARIES, "Stripe copy boundary is not guarded"
    v.FAILURES.clear()
    v.check_credential_boundary()
    assert not v.FAILURES, v.FAILURES
    body = (ROOT / "plugins/sheleg-dev/skills/google-auth/SKILL.md").read_text()
    assert "console.log(tokens.access_token)" not in body
    assert "google_auth_tokens_refreshed" in body

for name, fn in [('internal payload paths and reader-project counterexample', paths),
                 ('Stripe boot assertion modes and unknown keys', stripe),
                 ('copyable boundary and token-free logging', docs)]:
    check(name, fn)
print(f'FW03 credentials: {3 - len(errors)}/3 groups passed')
sys.exit(bool(errors))
