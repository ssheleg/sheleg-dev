'use strict';
/**
 * The manual gate, as a decision a hook can make.
 *
 * Four of this pack's own rules are prose that stops nothing:
 *
 *   - `crypto-payments/SKILL.md` — "Never auto-refund from the webhook. Route holds and
 *     refunds to a queue a human can see."
 *   - `stripe-billing/references/webhook-events.md` — "`charge.dispute.created` is money
 *     already gone plus a fee. Treat it as a refund for entitlement purposes and route it
 *     to a human — evidence has a deadline."
 *   - `crypto-payments/SKILL.md` — "`SKIP_BILLING=true` in production is not a shortcut,
 *     it is a free-money path."
 *   - `crypto-payments/references/heleket-provider.md` — the boot assertion
 *     `assertHeleketEnv()` refuses a run that merely *holds* a live merchant credential
 *     while declaring `test`.
 *
 * The fourth is a control, and it lives in the reader's application. It cannot see a
 * SHELL that exports the same credential before any application starts — which is the
 * gap this module closes. The other three were sentences.
 *
 * **The pure part is here on purpose.** Everything below is a function of a payload and
 * an environment object handed in as an argument: no `process`, no `HOME`, no
 * filesystem, no clock. `hooks/money-gate.js` moves bytes and this decides. That split
 * is what makes a refusal reproducible in `test/moneygate_test.js` without a live
 * session, and it is the umbrella's invariant ("a guard decides in a pure module; the
 * hook only moves bytes").
 *
 * Two defects measured elsewhere in this program shaped the reading:
 *
 * - **UM-09** — the umbrella's gate decided ownership by asking whether anything was
 *   staged, at `PreToolUse`, *before* the command ran; an `add`-then-commit line
 *   bypassed it. So nothing here reads state the command is about to change. The only
 *   inputs are the payload and the environment the hook was spawned with.
 * - **UM-10** — its `isCommit` matched the target verb inside a quoted JSON payload, an
 *   argument to `node` rather than an invocation, and denied it. So `executablePart()`
 *   drops the data (a heredoc body fed to something that is not a shell, whole-line
 *   comments) and `simpleCommands()` reads the invocation rather than the text: a token
 *   in a `grep` pattern is not a call.
 */

// ---------------------------------------------------------------- lexing

/**
 * The part of a payload that could actually run, with data stripped out.
 *
 * Adapted from the umbrella's `lib/hygiene.js` — same boundary, and the boundary is the
 * whole design:
 *
 * - **A heredoc body fed to something that is not a shell** is data. `cat > .env <<EOF …
 *   EOF` and `python3 - <<'PY' … PY` cannot charge a card. `bash <<EOF … EOF` is a
 *   script, so its body is KEPT — stripping every heredoc would be a documented bypass,
 *   which is worse than the false positive it fixes.
 * - **A whole-line comment** does not run.
 *
 * **Quoted strings are deliberately NOT stripped.** `bash -c 'stripe refunds create'` is
 * a real invocation living inside quotes. `simpleCommands()` expands that instead of
 * guessing.
 */
const HEREDOC_SHELLS = new Set(['bash', 'sh', 'zsh', 'dash', 'ksh', 'eval', 'source', '.']);

function bareName(token) {
  // Shell quoting is not part of a name. The umbrella lost a real invocation to a
  // trailing quote here (B-59's sibling bypass, 2026-08-16), so strip both ends.
  let t = String(token || '').replace(/^['"]+/, '').replace(/['"]+$/, '');
  t = t.replace(/@[^/]*$/, '').replace(/^.*\//, '');
  return t;
}

function executablePart(command) {
  const lines = String(command || '').split('\n');
  const out = [];
  let terminator = null;
  let dropping = false;
  for (const line of lines) {
    if (terminator !== null) {
      // The terminator may be indented when the heredoc used `<<-`.
      if (line.trim() === terminator) { terminator = null; dropping = false; continue; }
      if (dropping) continue;
      out.push(line);
      continue;
    }
    if (/^\s*#/.test(line)) continue;
    const here = /<<-?\s*(['"]?)([A-Za-z_][A-Za-z0-9_]*)\1/.exec(line);
    if (here) {
      terminator = here[2];
      // Which command is being fed? The last simple-command word before the `<<`, taken
      // after the final pipe or `&&` so `foo | python3 - <<EOF` reads as python3.
      const before = line.slice(0, here.index);
      const segment = before.split(/\|\||&&|[|;]/).pop();
      const words = segment.trim().split(/\s+/).filter(Boolean).map(bareName);
      const cmd = words.find((w) => !w.includes('=')) || '';
      dropping = !HEREDOC_SHELLS.has(cmd);
      out.push(before);
      continue;
    }
    out.push(line);
  }
  return out.join('\n');
}

/** Split on the operators that end one simple command, ignoring quoted text. */
function segments(text) {
  const out = [];
  let cur = '';
  let quote = null;
  const s = String(text || '');
  for (let i = 0; i < s.length; i += 1) {
    const c = s[i];
    if (quote) {
      cur += c;
      if (c === '\\' && quote === '"') { cur += s[i + 1] || ''; i += 1; continue; }
      if (c === quote) quote = null;
      continue;
    }
    if (c === "'" || c === '"') { quote = c; cur += c; continue; }
    if (c === '\n' || c === ';') { out.push(cur); cur = ''; continue; }
    if ((c === '&' && s[i + 1] === '&') || (c === '|' && s[i + 1] === '|')) {
      out.push(cur); cur = ''; i += 1; continue;
    }
    if (c === '|' || c === '&') { out.push(cur); cur = ''; continue; }
    cur += c;
  }
  out.push(cur);
  return out.filter((x) => x.trim());
}

/** Words, with their quotes removed and the fact that they were quoted remembered. */
function tokenize(text) {
  const out = [];
  const s = String(text || '');
  let cur = '';
  let has = false;
  let quoted = false;
  for (let i = 0; i < s.length; i += 1) {
    const c = s[i];
    if (c === '\\' && i + 1 < s.length && !/\s/.test(s[i + 1])) {
      cur += s[i + 1]; has = true; i += 1; continue;
    }
    if (c === "'" || c === '"') {
      const q = c;
      quoted = true; has = true;
      i += 1;
      while (i < s.length && s[i] !== q) {
        if (q === '"' && s[i] === '\\' && i + 1 < s.length) { cur += s[i + 1]; i += 2; continue; }
        cur += s[i]; i += 1;
      }
      continue;
    }
    if (/\s/.test(c)) {
      if (has) { out.push({ value: cur, quoted }); cur = ''; has = false; quoted = false; }
      continue;
    }
    cur += c; has = true;
  }
  if (has) out.push({ value: cur, quoted });
  return out;
}

const ASSIGN = /^([A-Za-z_][A-Za-z0-9_]*)=([\s\S]*)$/;

/**
 * Wrappers that stand in front of the command that matters. `env` and `sudo` also carry
 * the prefix assignments, so peeling them is what makes `env HELEKET_API_KEY=… node app`
 * read the same as `HELEKET_API_KEY=… node app`.
 */
const RUNNERS = new Set([
  'sudo', 'doas', 'env', 'time', 'nice', 'nohup', 'command', 'exec', 'stdbuf',
  'npx', 'pnpx', 'bunx', 'pipx', 'uvx', 'dlx',
]);
const SHELLS = new Set(['bash', 'sh', 'zsh', 'dash', 'ksh', 'fish']);

/**
 * A payload as the list of simple commands it would run.
 *
 * Each entry is `{cmd, argv, assignments, positionals, text}`:
 *
 * - `assignments` is a Map of the PREFIX assignments only — the ones the shell applies to
 *   this command. `grep 'HELEKET_API_KEY=' f` therefore has an empty map, because `grep`
 *   is the command word and everything after it is an argument. That distinction is the
 *   whole of UM-10's lesson: an assignment-shaped string in an argument sets nothing.
 * - `cmd` is the command word with any path and version suffix removed.
 * - `argv` keeps every remaining word; `positionals` drops the flags.
 *
 * `bash -c '<payload>'` is expanded rather than guessed at, to `depth` 3. A gate that
 * ignored the inside of `-c` would ship with a one-token bypass.
 */
function simpleCommands(command, depth) {
  const limit = typeof depth === 'number' ? depth : 3;
  const out = [];
  for (const seg of segments(executablePart(command))) {
    const tokens = tokenize(seg);
    const assignments = new Map();
    let i = 0;
    let cmd = '';
    while (i < tokens.length) {
      const raw = tokens[i].value;
      const m = ASSIGN.exec(raw);
      if (m) { assignments.set(m[1], m[2]); i += 1; continue; }
      if (raw === 'export' || RUNNERS.has(bareName(raw))) { i += 1; continue; }
      if (/^-/.test(raw)) { i += 1; continue; }   // a runner's own flag
      cmd = bareName(raw); i += 1; break;
    }
    // `export FOO=bar` puts the assignment after the keyword, so keep collecting.
    while (i < tokens.length && ASSIGN.test(tokens[i].value) && !cmd) {
      const m = ASSIGN.exec(tokens[i].value);
      assignments.set(m[1], m[2]);
      i += 1;
    }
    const argv = tokens.slice(i);
    // `export A=1 B=2` — no command word at all, only assignments.
    if (!cmd) {
      for (const t of argv) {
        const m = ASSIGN.exec(t.value);
        if (m) assignments.set(m[1], m[2]);
      }
    }
    const positionals = argv.filter((t) => !/^-/.test(t.value)).map((t) => t.value);
    out.push({
      cmd,
      argv: argv.map((t) => t.value),
      assignments,
      positionals,
      text: seg,
    });
    if (SHELLS.has(cmd) && limit > 0) {
      const at = argv.findIndex((t) => /^-[a-z]*c$/.test(t.value));
      if (at >= 0 && argv[at + 1]) {
        for (const inner of simpleCommands(argv[at + 1].value, limit - 1)) out.push(inner);
      }
    }
  }
  return out;
}

// -------------------------------------------------------------- the rules

/**
 * Command words that read rather than run.
 *
 * A **denylist**, not an allowlist, and the direction is deliberate: an invoker this
 * module has never heard of must be gated, not waved through. The price is that the
 * documented false positives are enumerated here instead of being discovered — which is
 * the trade the audit asks for, because a guard that cannot be watched failing is no
 * evidence and a guard that refuses correct input gets switched off.
 */
const READERS = new Set([
  'echo', 'printf', 'cat', 'bat', 'head', 'tail', 'less', 'more', 'nl', 'tee',
  'grep', 'egrep', 'fgrep', 'rg', 'ag', 'ack', 'sed', 'awk', 'cut', 'tr', 'column',
  'sort', 'uniq', 'wc', 'diff', 'comm', 'ls', 'find', 'fd', 'tree', 'stat', 'file',
  'git', 'jq', 'yq', 'man', 'glow', 'xxd', 'md5sum', 'shasum', 'sha256sum', 'true',
]);

/**
 * Credentials whose provider issues **no test variant**, so any shell holding one holds
 * production. Established from the document rather than assumed —
 * `crypto-payments/references/heleket-provider.md` §1 and §7: one key per merchant,
 * which is also the webhook signing secret, one host, and no `test`/`live` marker.
 *
 * **`HELEKET_LIVE_MERCHANT_ID` and `HELEKET_LIVE_KEY_FINGERPRINT` are NOT here**, and
 * leaving them out is a reading of SD-02 rather than an omission: they are non-secret
 * pins, and `assertHeleketEnv()` *refuses* a test run that does not set one
 * (`HELEKET_ENV_UNPINNED`). A gate refusing to export them would contradict the boot
 * assertion it exists to extend.
 *
 * **`STRIPE_SECRET_KEY` is not here either**, for the opposite reason: Stripe stamps the
 * environment into the key, so `STRIPE_SECRET_KEY=sk_test_…` is correct and common. The
 * live half is caught by its shape (`LIVE_KEY`), not by the variable's name.
 */
const NO_TEST_VARIANT = new Map([
  ['HELEKET_API_KEY',
    'Heleket issues one key per merchant, it is also the webhook signing secret, and it ' +
    'carries no test/live marker — so there is no test value this can hold ' +
    '(crypto-payments/references/heleket-provider.md, "The test/live boundary").'],
]);

/**
 * A live Stripe key, by shape rather than by prefix.
 *
 * The prefix alone is documentation: this repository writes `sk_live_…` in
 * `stripe-billing/references/stripe-agent-toolchain.md` and sweeps for
 * `sk_live_[A-Za-z0-9]` in `SECURITY.md`. Requiring a key-shaped body is what separates
 * the artifact from the sentence about it — the same distinction UM-10 got wrong.
 */
const LIVE_KEY = /\b(sk|rk)_live_[A-Za-z0-9]{16,}/;

/** The environment a run DECLARES. Nothing is inferred from the credential itself. */
const ENV_VARS = ['SHELEG_DEV_ENV', 'HELEKET_ENV', 'STRIPE_ENV', 'PAYMENTS_ENV', 'APP_ENV', 'NODE_ENV'];

function normaliseEnv(value) {
  const s = String(value == null ? '' : value).trim().replace(/^['"]|['"]$/g, '').toLowerCase();
  if (!s) return null;
  if (['production', 'prod', 'live'].includes(s)) return 'production';
  // Everything that is not production is not production. SD-02's rule, kept verbatim:
  // "Could not prove it was safe" must never read as "it was safe".
  return 'test';
}

/**
 * `test` | `production` | `null` (undeclared).
 *
 * A declaration made **inline in the payload** wins over the session's environment,
 * because it describes the run that is about to happen: `HELEKET_ENV=test node app.js`
 * declares test no matter what the operator exported yesterday.
 */
function declaredEnv(env, commands) {
  for (const c of commands || []) {
    for (const v of ENV_VARS) {
      if (c.assignments.has(v)) {
        const got = normaliseEnv(c.assignments.get(v));
        if (got) return got;
      }
    }
  }
  for (const v of ENV_VARS) {
    const got = normaliseEnv((env || {})[v]);
    if (got) return got;
  }
  return null;
}

const AUTH_VAR = 'SHELEG_DEV_LIVE_AUTHORISED';
const GATE_VAR = 'SHELEG_DEV_MONEY_GATE';

/** The categories the authorised person has signed off for this session. */
function authorised(env) {
  const raw = (env || {})[AUTH_VAR];
  if (!raw) return new Set();
  return new Set(String(raw).split(/[,\s]+/).map((x) => x.trim().toLowerCase()).filter(Boolean));
}

/**
 * The categories this gate stops, in the order they are checked.
 *
 * `authorisable: false` means no environment variable makes it pass. Both cases are
 * about the gate itself rather than about money: granting yourself authority and running
 * a free-money path in production are not decisions an operator can pre-approve for an
 * agent, because approving them removes the gate rather than passing it.
 */
const CATEGORIES = {
  'live-key': { authorisable: true },
  credential: { authorisable: true },
  refund: { authorisable: true },
  payout: { authorisable: true },
  dispute: { authorisable: true },
  'live-flag': { authorisable: true },
  'self-authorisation': { authorisable: false },
  'skip-billing': { authorisable: false },
};

/** A money-moving path on a provider's API, as a URL rather than as a bare path. */
const MONEY_URL = [
  { category: 'refund', re: /(?:https?:\/\/|\$\{?[A-Z_][A-Z0-9_]*\}?|[a-z0-9-]+(?:\.[a-z0-9-]+)+)\/v1\/refunds\b/ },
  { category: 'payout', re: /(?:https?:\/\/|\$\{?[A-Z_][A-Z0-9_]*\}?|[a-z0-9-]+(?:\.[a-z0-9-]+)+)\/v1\/(?:payouts?|transfers)\b/ },
  { category: 'dispute', re: /(?:https?:\/\/|\$\{?[A-Z_][A-Z0-9_]*\}?|[a-z0-9-]+(?:\.[a-z0-9-]+)+)\/v1\/disputes\/[^\s"']+\/close\b/ },
];

/** `stripe <noun> <verb>` — the CLI shape, read from the positionals of a `stripe` call. */
const MONEY_CLI = [
  { category: 'refund', nouns: ['refunds', 'refund'], verbs: ['create'] },
  { category: 'payout', nouns: ['payouts', 'payout', 'transfers', 'transfer'], verbs: ['create'] },
  { category: 'dispute', nouns: ['disputes', 'dispute'], verbs: ['close'] },
];

/**
 * Tool names that move money by themselves.
 *
 * Matched on the NAME only, never on the tool's input. A tool input is where a document
 * quoting `sk_live_…` arrives — `Write`, `Edit`, `NotebookEdit` all carry file text — and
 * scanning it would refuse this repository's own references. The name is enough for the
 * case that matters: `mcp__plugin_stripe_stripe__create_refund` is a refund whatever its
 * arguments say.
 */
const MONEY_TOOL = [
  { category: 'refund', re: /(?:^|_)(?:create_refunds?|refunds?_create|issue_refund)$/i },
  { category: 'payout', re: /(?:^|_)(?:create_(?:payouts?|transfers?)|(?:payouts?|transfers?)_create)$/i },
  { category: 'dispute', re: /(?:^|_)(?:close_disputes?|disputes?_close)$/i },
];

const LIVE_FLAG = /^--live(?:-?mode)?$/;

// ------------------------------------------------------------- the verdict

/**
 * The one sentence a refusal must carry. Manifesto M-30, `manifesto.md:204`.
 *
 * A refusal with no next step is how an operator learns to switch a hook off, so every
 * denial names the remedy AND the fact that the remedy is somebody else's to apply.
 */
const DECIDES = 'The agent prepares the decision and its evidence. The authorised person decides.';

function remedy(category, runEnv) {
  const spec = CATEGORIES[category] || { authorisable: true };
  if (!spec.authorisable) {
    if (category === 'self-authorisation') {
      return `Authorisation is not this run's to grant. Ask the operator to export ` +
        `${AUTH_VAR} in the shell that starts the session, then start a new one — a value ` +
        'set from inside a tool call is not the environment this gate reads.';
    }
    return 'Run the mock path with a non-production declaration, or take the production ' +
      'path with real billing. There is no flag that makes this one pass.';
  }
  if (runEnv === 'test') {
    return 'This run declares a non-production environment, and a test-declaring run cannot ' +
      'be authorised for a live operation — no variable overrides that. Re-declare the ' +
      'environment deliberately, or hand the prepared decision to the authorised person.';
  }
  return `If this is intended, the authorised person exports ` +
    `${AUTH_VAR}="${category}" (or "all") in the shell that starts the session and starts a ` +
    'new one. Setting it from inside a tool call does not reach this gate.';
}

function deny(category, what, evidence, runEnv) {
  return {
    allow: false,
    category,
    reason: [
      `[sheleg-dev] refused: ${what}`,
      `  ${evidence}`,
      `  ${DECIDES}`,
      `  ${remedy(category, runEnv)}`,
    ].join('\n'),
  };
}

const ALLOW = { allow: true, category: null, reason: '' };

/**
 * Would this payload cross a manual gate?
 *
 * `payload` is the `PreToolUse` hook input; `env` is the environment the hook was spawned
 * with, passed in rather than read, so a fixture needs no `HOME`.
 *
 * Order matters only in what the operator is told first, never in what passes: every rule
 * is checked against the same commands and the first hit is reported.
 */
function decide(payload, env) {
  const e = env || {};
  const data = payload || {};
  const tool = String(data.tool_name || '');
  const input = data.tool_input || {};

  // The off switch is honest about being one: an operator who sets it has decided, and a
  // gate with no documented off switch gets removed instead of disabled. It is read from
  // the environment only — a payload that sets it is `self-authorisation` below.
  if (String(e[GATE_VAR] || '').trim().toLowerCase() === 'off') return ALLOW;

  // Not Bash: decide from the tool NAME alone. See MONEY_TOOL for why the input is never
  // read — that is where a reference document quoting a live key arrives.
  if (tool !== 'Bash') {
    const sessionEnv = declaredEnv(e, []);
    for (const m of MONEY_TOOL) {
      if (!m.re.test(tool)) continue;
      if (allowedFor(m.category, e, sessionEnv)) return ALLOW;
      return deny(m.category, `\`${tool}\` moves money and no authorisation covers it`,
        'The tool name is the whole evidence — its arguments were not read.', sessionEnv);
    }
    return ALLOW;
  }

  const command = String(input.command || '');
  const commands = simpleCommands(command);
  const runEnv = declaredEnv(e, commands);

  for (const c of commands) {
    // 7. Granting yourself the authority the gate exists to withhold.
    for (const v of [AUTH_VAR, GATE_VAR]) {
      if (!c.assignments.has(v)) continue;
      return deny('self-authorisation',
        `this command sets ${v}`,
        `${v} is the authorised person's switch. A run that can set it is a run with no gate.`,
        runEnv);
    }

    // 8. The free-money path, in production. crypto-payments/SKILL.md names it as such.
    if (String(c.assignments.get('SKIP_BILLING') || '').replace(/['"]/g, '').toLowerCase() === 'true'
        && runEnv === 'production') {
      return deny('skip-billing',
        'SKIP_BILLING=true in a run declaring production',
        'crypto-payments/SKILL.md: "SKIP_BILLING=true in production is not a shortcut, it is ' +
        'a free-money path." The branch credits without a payment.', runEnv);
    }

    // 2. A credential whose provider issues no test value, in a test or undeclared run.
    for (const [name, why] of NO_TEST_VARIANT) {
      if (!c.assignments.has(name)) continue;
      if (allowedFor('credential', e, runEnv)) break;
      if (runEnv === 'production') {
        return deny('credential',
          `this command exports ${name} — a live merchant credential`, why, runEnv);
      }
      return deny('credential',
        `this command exports ${name} in a run declaring ${runEnv || 'nothing at all'}`,
        `${why} SD-02's boot assertion refuses the same pair as ` +
        'HELEKET_ENV_TEST_HOLDS_LIVE_CREDENTIAL, but it runs inside the application — a shell ' +
        'that merely holds the key never reaches it.', runEnv);
    }
  }

  // 1. A live-shaped key anywhere in what would run.
  //
  // **No reader exemption here, deliberately.** The other rules skip `grep` and `cat`
  // because a path or a flag inside a search pattern invokes nothing; a live key is
  // different — `stripe-agent-toolchain.md` calls one in a repository "an incident, not a
  // lint", and that is as true of a search pattern as of an export. The shape is what
  // separates the artifact from the sentence about it, so `SECURITY.md`'s own sweep for
  // `sk_live_[A-Za-z0-9]` passes on the prefix while a key-shaped body does not. Both
  // directions are fixtured; overlapping the two mechanisms here once left each of them
  // individually unproven.
  const keyHit = commands.find((c) => LIVE_KEY.test(c.text));
  if (keyHit && !allowedFor('live-key', e, runEnv)) {
    const m = LIVE_KEY.exec(keyHit.text);
    return deny('live-key',
      `a live ${m[1] === 'sk' ? 'secret' : 'restricted'} key (${m[1]}_live_…) reaches \`${keyHit.cmd || 'the shell'}\``,
      'stripe-billing/references/stripe-agent-toolchain.md: "sk_live_… or rk_live_… in a ' +
      'repository is an incident, not a lint." The key itself is not echoed here.', runEnv);
  }

  for (const c of commands) {
    if (READERS.has(c.cmd)) continue;

    // 3-5. A money-moving call through the Stripe CLI.
    if (bareName(c.cmd) === 'stripe') {
      for (const m of MONEY_CLI) {
        const nouns = m.nouns.some((n) => c.positionals.includes(n));
        const verbs = m.verbs.some((v) => c.positionals.includes(v));
        if (!nouns || !verbs) continue;
        if (allowedFor(m.category, e, runEnv)) continue;
        return deny(m.category, `\`stripe ${c.positionals.slice(0, 2).join(' ')}\``,
          categoryEvidence(m.category), runEnv);
      }
    }

    // 3-5. The same operations over HTTP. A URL, not a bare path, so that grepping for
    // `/v1/refunds` in a document is not a refund.
    for (const m of MONEY_URL) {
      if (!c.argv.some((a) => m.re.test(a))) continue;
      if (allowedFor(m.category, e, runEnv)) continue;
      return deny(m.category, `a call to a ${m.category} endpoint from \`${c.cmd || 'the shell'}\``,
        categoryEvidence(m.category), runEnv);
    }

    // 6. The explicit statement of live intent.
    if (c.argv.some((a) => LIVE_FLAG.test(a)) && !allowedFor('live-flag', e, runEnv)) {
      return deny('live-flag', `an explicit --live flag on \`${c.cmd || 'the shell'}\``,
        'A --live flag is a request for production access, which manifesto M-30 puts on the ' +
        'manual-gate side by name.', runEnv);
    }
  }

  return ALLOW;
}

function categoryEvidence(category) {
  if (category === 'refund') {
    return 'crypto-payments/SKILL.md: "Never auto-refund from the webhook. Route holds and ' +
      'refunds to a queue a human can see." A refund is money movement and it is not undoable.';
  }
  if (category === 'payout') {
    return 'A payout or transfer moves money out. Manifesto M-30 names money movement and ' +
      'irreversible action as manual-gate territory.';
  }
  return 'stripe-billing/references/webhook-events.md: a dispute is "money already gone plus a ' +
    'fee … route it to a human — evidence has a deadline." Closing one accepts the loss.';
}

/**
 * Is this category signed off for this run?
 *
 * Two conditions, and the second is not negotiable by any variable: the category must be
 * authorisable at all, and **a test-declaring run can never be authorised for a live
 * operation**. A run that says it is a test and then refunds a real card is incoherent
 * whichever half is true, and SD-02's rule applies — refuse on the test side.
 */
function allowedFor(category, env, runEnv) {
  const spec = CATEGORIES[category];
  if (spec && !spec.authorisable) return false;
  if (runEnv === 'test') return false;
  const set = authorised(env);
  return set.has('all') || set.has(category);
}

module.exports = {
  decide, allowedFor, declaredEnv, normaliseEnv, authorised,
  executablePart, segments, tokenize, simpleCommands, bareName,
  CATEGORIES, NO_TEST_VARIANT, LIVE_KEY, READERS, AUTH_VAR, GATE_VAR, ENV_VARS, DECIDES,
};
