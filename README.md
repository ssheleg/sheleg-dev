# sheleg-dev

The integration layer a product reaches once it has users: **money in, tracking,
sign-in, and speed.**

Part of the [ssheleg skill family](https://github.com/ssheleg/sshlg-skills).

---

## The seven skills

| Skill | Answers |
|---|---|
| **`stripe-billing`** | how does a Stripe payment become an entitlement in my database, exactly once |
| **`crypto-payments`** | how do I take crypto without losing money to under-payment, duplicate webhooks or rate drift |
| **`ad-tracking`** | how do GA4, Google Ads, Meta and LinkedIn fire correctly under Consent Mode v2 |
| **`google-signin`** | how do I let people sign in with Google without handing someone their account |
| **`google-auth`** | how does my *server* authenticate to Google — OAuth, ADC, service accounts, federation |
| **`frontend-performance`** | why is the Lighthouse score bad and which fix actually moves it |
| **`error-tracking`** | how do I know it broke, without mailing my own credentials to Sentry |

Each carries its own references and loads them only when the work reaches them.

**Two of them ship a suite rather than a warning.** `stripe-billing` and `ad-tracking`
carry a `fixtures/` directory — real provider webhook bodies, an assertion pack, and a
`--self-test` that deletes one rule at a time so you can watch every assertion fail — one
call site at a time, which is not the same thing as one invariant at a time. Copy the
directory in and run it:

```bash
node plugins/sheleg-dev/skills/stripe-billing/fixtures/assert-money-invariants.mjs --self-test
node plugins/sheleg-dev/skills/ad-tracking/fixtures/assert-dedup-contract.mjs --self-test
```

That covers the invariants whose failure is money rather than an error page: the webhook is
the payment and the redirect only proves a browser, one `event_id` on both sides or the
revenue counts twice, a refund total that arrives cumulative, and delivery that is not
ordered. Each skill's `fixtures/README.md` is the map.

**`stripe-billing`** — Stripe's own agent toolchain first (CLI, `stripe agent
setup`, a sandbox without an account, the MCP implementation planner), then the
seam it cannot help with: a pinned API version and SDK retries instead of a loop
that buys two subscriptions for one intent; metadata written twice, because
renewal events never see the checkout session; claim-first webhook idempotency
with a release on failure; `billing_reason` as the difference between a renewal
and a $0.40 proration invoice; proration with a compensating revert when the
local write fails; `amount_refunded` as a cumulative total, not an increment; a
reconciliation job that leaves non-Stripe rows alone; and price drift, which
fails no request and reaches only customers. Which Stripe primitive to use is
deferred to Stripe's own `stripe-best-practices` skill.

**`crypto-payments`** — status mapping with an explicit terminal set;
signature verification in constant time, with the forward-slash escaping trap
that makes signatures valid for some payloads and not others; idempotency as a
compare-and-swap (`updateMany` with a non-final status guard) instead of the
read-then-write race; proxy-aware IP allowlisting that counts hops from the
right; CSRF exemption scoped to exactly one path; the conversion buffer; the
reconciliation fields that make "what did we actually receive" answerable six
months later; refunds and AML holds as states, not events.

**`ad-tracking`** — one unified consent update across four platforms, standard
event mapping, e-commerce with deduplication, per-platform CSP, Next.js
patterns. Four deep references on the Google tag: consent mode, the gtag API,
event schema design, and performance/security.

**`google-signin`** — the ID-token flow treated as a security problem: the
three-way account-linking branch with the **pre-hijacking guard**, login-CSRF
covering both delivery flows, nonce and replay protection, and a checklist where
every item maps to a named attack.

**`google-auth`** — OAuth 2.0 web-server flow, Application Default Credentials
and its search order, service-account JWT including domain-wide delegation,
Workload and Workforce Identity Federation, impersonation, downscoping. Node and
Python side by side throughout.

**`frontend-performance`** — Core Web Vitals with an audit workflow and a budget
template; font loading; GPU-composited animation and what to do instead of
animating `background-position`; code splitting, cache headers, CSP; and the
accessibility rules — contrast, heading order, alt text, target size — that move
a Lighthouse score.

---

## Install

**Claude Code plugin** (recommended):

```bash
/plugin marketplace add ssheleg/sheleg-dev
/plugin install sheleg-dev@sheleg-dev
```

**npm installer** — copies all seven skills into `~/.claude/skills/`:

```bash
npx @ssheleg/sheleg-dev
```

**Any of 70+ agents:**

```bash
npx skills add ssheleg/sheleg-dev
```

**Whole family at once:**

```bash
npx --yes sshlg-skills@latest update
```

Restart your agent afterwards — skills load at session start.

---

## The manual gate

Four things this pack tells you to route to a human — a refund, a payout, closing a
dispute, a live credential — used to be **sentences**. `crypto-payments/SKILL.md` says
"Never auto-refund from the webhook. Route holds and refunds to a queue a human can
see"; `stripe-billing/references/webhook-events.md` says a dispute is "money already
gone plus a fee … route it to a human". An agent reading neither, and a shell nobody
read, were unaffected by both.

So the plugin ships a `PreToolUse` hook. It refuses eight things unless the authorised
person has signed the category off **for this session**:

| Category | What it stops |
|---|---|
| `live-key` | a live-shaped `sk_live_…` / `rk_live_…` reaching a command |
| `credential` | exporting a credential whose provider issues no test value — `HELEKET_API_KEY` — in a run that declares `test`, or declares nothing |
| `refund` | `stripe refunds create`, a POST to a `…/v1/refunds` URL, or a `create_refund` tool |
| `payout` | `stripe payouts\|transfers create`, a POST to `…/v1/payouts`, `…/v1/transfers` or Heleket's `…/v1/payout` |
| `dispute` | `stripe disputes close`, or `…/v1/disputes/…/close` — closing one accepts the loss |
| `live-flag` | an explicit `--live` / `--live-mode` flag |
| `self-authorisation` | a command that sets this gate's own switch. Never authorisable |
| `skip-billing` | `SKIP_BILLING=true` in a run declaring production — the free-money path. Never authorisable |

**Authorising one.** The authorised person exports the category — or `all` — in the
shell that starts the session, and starts a new one:

```bash
SHELEG_DEV_LIVE_AUTHORISED=refund claude
```

Two properties of that make it a decision rather than a formality. It is read from the
environment the **hook** was spawned with, so a value exported inside a tool call never
reaches it — and a command that tries is refused as `self-authorisation`. And **a run
declaring a non-production environment can never be authorised**: if `SHELEG_DEV_ENV`,
`HELEKET_ENV`, `STRIPE_ENV`, `PAYMENTS_ENV`, `APP_ENV` or `NODE_ENV` says anything other
than production, no variable makes a live operation pass. A run that says it is a test and
then refunds a real card is incoherent whichever half is true.

`SHELEG_DEV_MONEY_GATE=off` disables it. That is deliberate and documented: a gate with no
off switch gets deleted instead of disabled.

**Registration, and what enforces it.** Nothing in this repository writes to your
settings, by design.

- **Installed as a Claude Code plugin** — `plugins/sheleg-dev/hooks/hooks.json` travels
  with the plugin and the hook is live as soon as the plugin is enabled. Nothing further
  to do, and no per-hook switch: enablement is the whole control.
- **Installed by `npx @ssheleg/sheleg-dev`, `install.sh` or `npx skills add`** — those
  copy the seven skills into `~/.claude/skills/` and **carry no hook**. The gate is prose
  again until you register it yourself, in `~/.claude/settings.json` or a project's
  `.claude/settings.json`:

  ```json
  { "hooks": { "PreToolUse": [
    { "matcher": "Bash",
      "hooks": [ { "type": "command",
        "command": "node \"$HOME/.claude/skills/.sheleg-dev-hooks/money-gate.js\"",
        "timeout": 15 } ] },
    { "matcher": "mcp__.*",
      "hooks": [ { "type": "command",
        "command": "node \"$HOME/.claude/skills/.sheleg-dev-hooks/money-gate.js\"",
        "timeout": 15 } ] }
  ] } }
  ```

  **Both entries, not just the first.** A refund does not care which door it came
  through: `create_refund` on an MCP server never touches a shell, and the table above
  advertises it. Until 2026-08-20 this snippet carried the `Bash` matcher alone — a
  weaker gate than the plugin's, handed out by the document that exists because the copy
  channels have no gate at all. `test/validate.py` now compares the two matcher sets.

  Copy `plugins/sheleg-dev/hooks/` to that path first. `npx @ssheleg/sheleg-dev` prints
  this reminder; **nothing enforces it**, which is why the plugin channel is the
  recommended one.

The deciding is a pure function in
[`plugins/sheleg-dev/hooks/lib/moneygate.js`](plugins/sheleg-dev/hooks/lib/moneygate.js) —
payload and environment in, verdict out, no filesystem and no `HOME`.
[`plugins/sheleg-dev/hooks/money-gate.js`](plugins/sheleg-dev/hooks/money-gate.js) only
moves bytes, catches everything and exits 0: a hook that throws breaks every turn in
every session, including sessions of packs that never asked for this one. There is
deliberately **no `if` filter** on the hook entry — the Claude Code reference calls that
filter best-effort and says it fails open on a command it cannot parse.

Both directions are fixtured in
[`test/moneygate_test.js`](test/moneygate_test.js), and the allow-plants are real commands
from this repository: `SECURITY.md`'s own sweep for `sk_live_[A-Za-z0-9]`, a `.env`
heredoc fed to `cat`, a commented-out `stripe refunds create`, and the non-secret
`HELEKET_LIVE_MERCHANT_ID` pin that `assertHeleketEnv()` *requires* in a test run. A guard
that refuses correct input gets switched off, and then there is no gate at all.

---

## A note on `crypto-payments`

The skill is provider-neutral on purpose. The reusable engineering — signature
verification, idempotency, the buffer, reconciliation — is provider-shaped, and
the invariants hold across Coinbase Commerce, NOWPayments, BTCPay and others.
One gateway's concrete wire format lives in a reference, together with the
compliance position on record for it.

**Choosing a payment processor is a business and compliance decision, not a
technical one.** Processors differ in licensing, AML programme and sanctions
exposure, and that standing changes. This pack tells you how to integrate one
correctly. It does not tell you which one to trust.

---

## Verify

```bash
npm test    # the validator, the manual gate's 65 fixtures, the money fixtures' 13 checks
```

One version across `package.json`, `plugin.json`, `marketplace.json` and the top
`CHANGELOG` entry; front matter inside the Agent Skills limits (over-long front
matter does not error — hosts truncate it silently, which is worse); and
`SKILL.md` ↔ `references/` agreement in **both** directions, so neither a
dangling link nor a file nobody loads can ship.

Plus, for the money fixtures, that every assertion has been watched failing and that no
two rules are covering for each other — `test/fixtures_test.js` neuters assertions,
including one that is **not** the first inside a multi-assert invariant, and requires each
pack's `--self-test` to notice. That last plant is the one that used to pass.

CI plants a defect against every one of those guards and requires the validator
to fail. A green from a check nobody has watched fail is not evidence.

---

## License

MIT © ssheleg
