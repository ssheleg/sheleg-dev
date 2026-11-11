#!/usr/bin/env node
'use strict';
/**
 * The manual gate, at the one moment it can still prevent something.
 *
 * `PreToolUse`, because manifesto M-30 (`pod-manifesto/manifesto.md:200`) says a
 * precondition is stronger than a warning, and `:204` says the categories — money
 * movement, irreversible action, production access, destructive operations — are the
 * authorised person's to decide. A report after the refund has cleared is a warning.
 *
 * **This file moves bytes and nothing else.** The verdict is `lib/moneygate.js`, a pure
 * function of the payload and an environment object, fixtured in
 * `test/moneygate_test.js` without a `HOME`. Three invariants from the family umbrella's
 * `CLAUDE.md` are load-bearing here and all three are honoured:
 *
 * 1. **A guard decides in a pure module; the hook only moves bytes.** Nothing below
 *    inspects the filesystem, the process table or the clock.
 * 2. **A hook fails silent, and a refusal names its remedy.** Every throw is swallowed
 *    and the exit code is always 0 — a hook that throws breaks every turn in every
 *    session, including sessions of packs that never asked for this one. The refusal text
 *    always carries the next step, because a refusal with no remedy is how an operator
 *    learns to switch a hook off.
 * 3. **No reliance on a hook entry's `if` filter.** `hooks.json` here declares a matcher
 *    and no `if`: the reference calls `if` best-effort and says it FAILS OPEN on a command
 *    it cannot parse, so a gate resting on it ships with a documented bypass. The filter
 *    would also have been the natural place to write `Bash(stripe refunds*)`, which is
 *    exactly the shape a `bash -c '…'` wrapper defeats.
 *
 * Also: nothing here reads state the command is about to change (the UM-09 lesson — the
 * umbrella's own gate asked "is anything staged?" at `PreToolUse`, and an add-then-commit
 * line walked straight through). The payload and the spawning environment are the only
 * inputs, and the command cannot alter either before this decides.
 */

/*
 * The fast path. This hook is registered on every `Bash` and every `mcp__*` call, so for
 * almost every call it should cost one Node start and nothing more. Before any module is
 * loaded, the payload is checked for the substrings a refusable call must contain; a call
 * with none of them exits 0 here.
 *
 * TRIGGERS is a literal copy of `lib/moneygate.js` `TRIGGERS`, which is computed from the
 * rules themselves. `test/moneygate_test.js` fails when the two differ and replays every
 * refusal fixture through this script, so a rule cannot be added without its token.
 * It reads the same fields `decide()` reads: the tool name for a non-Bash tool, the
 * command for Bash. Backslashes and quotes are removed first, because the lexer removes
 * them too (`S\KIP_BILLING=true` and `"SKIP"_BILLING=true` are both assignments).
 */
const TRIGGERS = [
  '--live', '_live_', 'dispute', 'google_client_secret', 'google_credentials',
  'heleket_api_key', 'payout', 'refund', 'sheleg_dev_money_gate', 'skip_billing',
  'transfer',
];

function mayGate(data) {
  const tool = String((data && data.tool_name) || '');
  const input = (data && data.tool_input) || {};
  const text = tool === 'Bash' ? String(input.command || '') : tool;
  const hay = text.replace(/[\\'"]/g, '').toLowerCase();
  return TRIGGERS.some((t) => hay.includes(t));
}

function deny(reason) {
  process.stdout.write(`${JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason: reason,
    },
  })}\n`);
}

let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('error', () => process.exit(0));
process.stdin.on('data', (chunk) => { raw += chunk; });
process.stdin.on('end', () => {
  try {
    const data = raw.trim().startsWith('{') ? JSON.parse(raw) : {};
    if (!mayGate(data)) return process.exit(0);
    let gate = null;
    try {
      gate = require([__dirname, 'lib', 'moneygate.js'].join('/'));
    } catch (e) {
      /* A gate that cannot load must not break the session. It exits 0 below. */
    }
    if (!gate) return process.exit(0);
    const verdict = gate.decide(data, process.env);
    if (verdict && !verdict.allow) deny(verdict.reason);
  } catch (e) {
    /* Silence, on purpose. See invariant 2 above. */
  }
  process.exit(0);
});
