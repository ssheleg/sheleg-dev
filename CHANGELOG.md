# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [SemVer](https://semver.org/spec/v2.0.0.html).

## v0.11.0 — a trigger literal gets one home, and four facts get their dates

The 2026-08-29 skill audit found the pack's two Google skills advertising the same
end-user sign-in triggers, one skill re-teaching another's contract more weakly, and
three external facts stated without the date they were true on. All of it shipped green
through a 23-check validator, because none of it was a check yet.

- **`google-auth` and `google-signin` no longer compete for the same prompt** (audit
  DEV-01, HIGH). Both front-matter descriptions carried `"google login"`, `"GIS"`,
  `"Sign In with Google"` and «вход через Google» — four literal collisions between the
  skill that owns end-user sign-in and the skill that owns the server library surface,
  with which one loads left to the host's guess. The end-user set is stripped from
  `google-auth`, whose description now speaks the server vocabulary (ADC, service
  accounts and their keys, Workload Identity Federation, `verifyIdToken`); the
  cross-deferral sentence stays. A new validator check,
  `check_trigger_literals_have_one_home`, compares the quoted trigger literals of every
  skill pair and refuses a collision — watched failing in both directions (a re-planted
  `"google login"`, and a stale entry in `TRIGGERS_SHARED_BY_DESIGN`, the enumerated
  exemption that carries the one deliberate share: `webhook signature`, which the
  umbrella routes to `stripe-billing`). One new negative self-test in CI; the local
  floor moves 42 → 43. The verdict line moves 23 → 24 checks.
- **`google-auth` stops re-teaching ID-token verification with a weaker contract**
  (DEV-02). Its section 3 taught the sign-in verification omitting the `nonce` binding
  and `email_verified` — the two checks `google-signin`'s checklist adds above the
  library call, drifting live under a section that duplicated the other skill's core
  job. Cut to the bare `verifyIdToken` / `verify_oauth2_token` call plus an explicit
  statement of what the call does NOT check and where the sign-in contract lives. The
  partial `g_csrf_token` bullet in Security Best Practices is likewise now a pointer.
- **The Stripe `apiVersion` pins carry their date** (DEV-03). `2026-07-29.dahlia` was
  pinned undated in a document that itself says the API moves monthly — and it was
  already one release behind: checked 2026-08-30 against `docs.stripe.com/changelog`,
  where `2026-08-26.dahlia` is current. Both pin sites now say when they were true and
  send the reader to the changelog before pinning.
- **The crypto `sign()` block is labeled as ONE provider's scheme** (DEV-04). The
  SKILL taught `md5(base64(json) + apiKey)` under a provider-neutral heading two
  screens after claiming the section holds for four providers — it is Heleket's scheme
  alone. Checked 2026-08-30: Coinbase Commerce signs HMAC-SHA256
  (`X-CC-Webhook-Signature`), NOWPayments HMAC-SHA512 (`x-nowpayments-sig`), BTCPay
  HMAC-SHA256 (`BTCPay-Sig`). The pattern transfers; the algorithm does not, and the
  intro now says which is which.
- **`allow_enhanced_conversions` moves to the tag it belongs on** (DEV-05). The setup
  step put the flag on the GA4 `G-` config, where it enables nothing for Google Ads;
  where it appears at all it belongs on the `AW-` config command. Checked 2026-08-30:
  Google's current setup docs (`support.google.com/google-ads/answer/9888145`,
  `…/13258081`) no longer document the flag — the live mechanism is the account-level
  toggle plus `gtag('set', 'user_data', …)` — and the step now states both facts.
- **`ad-tracking`'s UTM Attribution section moved into
  `references/event-tracking.md`.** The DEV-05 fix pushed the body past the 4750-token
  house working limit (23 tokens of headroom going in), and the house answer at the
  limit is a split, not a trim — same seam as v0.10.0's cancellation split.
  Body ~4753 tokens after the move; `stripe-billing`'s recomputed numbers in
  `docs/evals/stripe-billing.md` moved with its dated pins (4737 tokens, 383 lines).
- **The social card now names all five trades** (umbrella deferral, 2026-08-29). The
  committed `docs/assets/social-preview.png` is compared pixel-for-pixel by the
  umbrella's site test against the card it generates from its `skills.json` role cell,
  and the role grows `errors` for the seventh skill. Regenerated with the umbrella's
  own generator from the exact cell it will adopt — `integrations: money in, tracking,
  errors, sign-in, speed` — verified by reproducing the previous committed card
  byte-for-byte from the previous cell first. README and `marketplace.json` carry the
  same five-trade phrasing. Measured while regenerating: at scale 3 the new eyebrow
  paints to 1 px of the canvas edge, because the umbrella's `fitScale` measures without
  the tracking `drawText` adds — nothing is truncated, and the fix (if wanted) belongs
  in `og-card.js`, not here.

## v0.10.5 — the installers refuse the shadow they used to write

Both install channels — `npx @ssheleg/sheleg-dev` and `install.sh` — now consult the
target home's `~/.claude/plugins/installed_plugins.json` before writing anything under
`~/.claude/skills/`. If the sheleg-dev **plugin** is installed there, the install is
**refused with exit 3**: a plain copy beside a plugin shadows the plugin's skill of the
same name and serves the frozen version forever, and until this release neither channel
looked at all. Reproduced live in the family on 2026-08-29: a bare
`npx @ssheleg/telegram-dev` shipped three shadows while the plugin was enabled.

- `installed_plugins.json` is the signal, because it is the record of what is actually
  installed. A check keyed on the `plugins/marketplaces/<name>` directory alone — the
  shape other family members carried — is the fail-open class: a marketplace added from
  a local `directory` source has no dir there, and plugin names differ from marketplace
  names. The directory is kept only as a fallback signal.
- The refusal names its remedy with the **real spec read from the JSON**
  (`claude plugin marketplace update sheleg-dev`, `claude plugin update <spec>`), plus
  the family launcher line, and offers `--force` as the explicit override for running
  two channels deliberately.
- An absent or corrupt `installed_plugins.json` reads as "no plugin": the check fails
  open and never crashes an install — the fresh HOME is the common case.
- New suite `test/installer_test.js` (11 cases, both channels, throwaway HOMEs), wired
  into `npm test` and CI. **Watched failing first**: run against the pre-refusal
  installers it went red on 7 of 11 cases, each showing the shadow landing at exit 0.
- Both success paths now end by saying how the next version arrives — the update line —
  and `install.sh` gained `--force`/usage parsing (unknown argument exits 2) to carry
  the same contract as the npm channel.
- `.claude-plugin/marketplace.json` still said "Six integration skills" while seven
  ship (the validator counts 7; README and SECURITY say seven). It now says seven and
  names error tracking — the second hand-written count this repository has caught after
  the fact, which is why the new suite derives the roster from the tree.
- `SECURITY.md`'s installer contract moved with the behaviour: the read surface now
  includes the two read-only looks at the target home, and the I/O-surface grep line
  count was re-measured (twelve, and it was already twelve before this change — the
  "eleven" had rotted when a comment naming `rm -rf` arrived).

## v0.10.4 — the channel that sends the installs, on npm too

- The `skills.sh` badge and the canonical `homepage` reached GitHub in the previous cycle and stopped
  there: npm serves the README and the metadata from the last **publish**, so the package
  page still showed a badge-less README and a homepage pointing at GitHub.
  This release carries both across.
- No behaviour changes. Cut because a change that lands on `main` and never publishes is a
  change the package's own readers cannot see.

## v0.10.3 — the shared seam is explicit

Both shared validators now state `diverges: none`, completing the umbrella
mechanism contract.

## v0.10.2 — shared guards identify their owner

The eval and social-preview validators now declare their umbrella-owned shared
mechanisms, making their cross-repository provenance machine-checkable.

## v0.10.1 — seven integration skills, one reviewable public contract

The pack now publishes a root skill card, routed trigger cases, three cross-skill
behavioral scenarios and an explicit no-model-run results ledger. The README
opens with one install and one Stripe request, the workbench social preview is
committed, and CI runs the pinned house audit plus the eval validator's planted
failure. Integration behavior and provider contracts are unchanged.

## v0.10.0 — the cancel flow that offers a discount, and the two ways it leaks money

Cursor's cancel page — "Before you go… 50% off your next invoice" — is Stripe's
customer portal with `flow_data[subscription_cancel][retention]`, and `stripe-billing`
said nothing about it. Verified against the Stripe OpenAPI spec at `2026-07-29.dahlia`
and `docs.stripe.com` on 2026-08-25.

### Two defects that no screen shows

**A `duration=once` discount deletes itself, so the offer can be taken forever.** From
Stripe's own coupon documentation: once the discounted invoice finalizes, the discount is
**removed from the subscription's `discounts` array** — "a subscription may appear to have
no discount even though a coupon was applied". So the obvious eligibility check, asking
Stripe whether this customer was already discounted, answers no every cycle. A monthly
subscriber who reopens the cancel flow rides half price indefinitely, and every renewal
looks ordinary in the logs. Compounding it: `retention.coupon_offer` takes a **coupon**,
and a coupon cannot be restricted to a customer, capped per customer, or deactivated —
`max_redemptions` is a total across all customers and reading it is a race. Eligibility
is a row in your database or it does not exist.

**Under flexible `billing_mode`, a portal cancellation does not set
`cancel_at_period_end`.** It sets `cancel_at` and leaves the flag `false`, so a billing
page whose banner reads the boolean tells a customer who cancelled ten seconds ago that
their plan renews. Nothing errors. Because `billing_mode` is fixed at creation, an
established account holds both kinds of row at once.

Both are now invariants with fixtures and a mutant each —
`retention-offer-is-consumed-once` (mutant: no ledger, eligibility read from
`subscription.discounts`) and `scheduled-cancellation-survives-billing-mode` (mutant:
the flag alone). The pack goes 12 → 14 invariants, 45 → 57 assertions, 9 → 13 event
bodies, 9 → 11 mutants, each still isolated by a fixture.

### New: `references/cancellation-and-retention.md`

The single home for cancellation and the save offer: the exact `flow_data` shape and why
there is **no** `retention` field on the portal *configuration* (so a targeted offer
exists only per session); the Dashboard "Retention Coupon" switch that offers every
cancelling customer a discount with no code review and no test; the eligibility ledger
and its four conditions; the absent event (`billing_portal.session.created` exists,
`…completed` does not — absence of a cancellation is not a save); `discounts` on an
update being a **replacement**, which silently deletes a negotiated discount; the five
conditions under which the portal cancel page is not available at all, including a
subscription schedule, which is how a downgrade-at-period-end implementation removes its
own cancel page.

Also recorded: discounts read through one more level since `2025-09-30.clover` —
`discount.coupon` → `discount.source.coupon`, `promotion_code.coupon` →
`promotion_code.promotion.coupon`, `subscription.discount` → `subscription.discounts[]`.
All three fail as `undefined` rather than as an error.

### The split behind it

`stripe-billing/SKILL.md` was at ~4747 tokens against a 4750 working limit — three tokens
of headroom, stated in the gate for exactly this moment. Cancellation moved into the new
reference and three body code blocks that had a second home in
`references/subscription-lifecycle.md` (get-or-create, the seat update, the refund
compare-and-swap) now live only there: 4747 → 4683 tokens, 409 → 381 lines. The rule with
two homes is the one that drifts at one of them.

`references/stripe-agent-toolchain.md` re-read against plugin 0.6.1: Stripe ships **eight**
agent skills now, not the seven this file listed, and a grep for `retention`, `coupon` and
`churn` across all eight returns nothing about cancellation deflection — so the save offer
is this skill's ground by absence rather than by preference, and that is now stated where
the division of labour is.

`package.json` also stopped describing six skills. There have been seven since v0.9.0, and
`error-tracking` was missing from the sentence npm shows.


## v0.9.2 — the README stops claiming a command the package cannot run

The README told a reader to run commands the published package cannot run: it ships no
`test/` directory, so `npm test` resolves in a clone and nowhere else. Measured against the
published tarball on 2026-08-25. Shipping the suite does not fix it — the plants live in
`.github/workflows/`, which no packaging npm can express puts in a tarball — so the document
now names where the command runs instead of claiming it, beside a marker the umbrella's
validator reads. Naming a dead command is this family's own rule; claiming one is the defect.


## v0.9.1 — 2026-08-24

### The skill was wrong at the exact place its author then tripped

`error-tracking` shipped telling readers to take the release version from
`HEROKU_SLUG_COMMIT`. Using it on a real project the same evening produced the
failure it exists to prevent: that variable is **not a config var** — it is dyno
metadata, injected only when the `runtime-dyno-metadata` labs feature is on, and
absent in silence otherwise. With the feature off, the SDK reported no release at
all while Sentry held a release with a deploy nothing would ever attach to.
Nothing errored.

Two more measurements from the same hour: `heroku config:get` never prints it,
even when it is working, because it is never a config var; and enabling the
feature takes effect on the next **release**, not on a restart.

`references/releases.md` now names the trap, gives the three commands that tell
you which state you are in, and recommends not depending on the variable alone —
set `RELEASE` from the deploy, which needs no platform feature and cannot drift
because one command produces both sides.

Also added, from the same mistake one level up: create the Sentry release for the
**deployed** commit, not for local HEAD. They differ the moment commits are
pushed but not deployed, and the result is a release nobody's events belong to.

## v0.9.0 — 2026-08-24

### The pack that wires integrations had nothing about knowing when they break

Six skills covered taking money, tracking conversions, signing people in and
page speed. None covered the layer that says any of it stopped working: a `grep`
for `sentry` across the whole family returned two incidental mentions.

`error-tracking` is written from a measured baseline rather than an imagined
one. An agent solving this exact task without the skill, in one session, made
four failures that were recorded as they happened:

- **Called "get a DSN" a manual step needing an account.** The account existed
  and the CLI was already authenticated. Error tracking stayed off for no reason.
- **Wrote a `before_send` scrubber without knowing `EventScrubber` exists** and
  runs by default — so it could not say which layer covered what, or whether its
  own code was redundant or load-bearing.
- **Did not know the MCP is OAuth**, and would have declared it in the machine's
  shared gateway, where an OAuth flow cannot complete.
- **Would have set a DSN and stopped**, leaving every issue attached to a release
  with no commits and suspect-commit attribution permanently dead.

### The measurement the skill is built on

`sentry-sdk` 2.19.2, run 2026-08-24. The built-in `EventScrubber` is enabled by
default and matches on KEY NAMES against a 32-entry denylist. It does not inspect
string values, and neither `dsn` nor `database_url` is on that list.

```python
event = {"message": "could not connect to postgresql://u:SUPERSECRET@host/db"}
EventScrubber().scrub_event(event)
assert "SUPERSECRET" in str(event)   # passes — not scrubbed
```

A service that writes a database URL near an error therefore starts forwarding
that password to a third party the moment Sentry is added, with wider reach than
the log had. The skill ships both layers — and, more usefully, the test that
asserts layer one alone still leaks, so the day Sentry starts scrubbing values a
red test says the second layer may now be redundant.

### Also in this release

- The 403 that reads as an auth failure and is not: `allowMemberProjectCreation:
  false` blocks `project create` **even for an org owner**, because the policy is
  evaluated against the token's scopes and the device-flow token carries no
  `org:write`. The team-scoped endpoint fails identically. Measured, with the
  three ways out ranked.
- Two different tools are called `sentry`. Commands from one silently do not
  exist in the other, and they install into prefixes where the older copy tends
  to win — 0.38.0 shadowing 0.43.0, observed here. The shadow check is one line.
- `$schema` was missing from `plugin.json` and from the marketplace entry. Added.

## v0.8.0 — 2026-08-20

**The self-test that proved the money invariants was measuring one thing and claiming
another.** `--self-test` deleted a rule, ran an invariant, and asked whether the invariant
went red. Twelve invariants carried **45 `assert.` calls**, and the verdict line called
them *"12 assertions, each watched failing"* — so any assertion that was not the sole
discriminator of a rule could be replaced by `assert.ok(true)` and nothing anywhere would
notice. Measured against the shipped v0.7.0 pack: three neutered assertions (the
`clawbacks.map` deepEqual, the `mirror.periodEnd` equality, the `response.body` deepEqual)
left `--self-test` at exit 0 and `npm test` at 0. The same hole in `ad-tracking`, in the PII
guard `references/meta-linkedin.md` advertises by name.

The `assert` an invariant receives is now a recorder: a failure is remembered instead of
thrown, so the assertions after it still run, and each call site is one measurement
identified by its line. **37 of 45 watched failing, one call site at a time. Eight declared
`assert.unmutated`** — an assertion no rule in the pack varies — **and measured unbreakable,
with the reason at the call site.** Both directions: an `unmutated` assertion a mutant does
break is a failure too, or the escape hatch is the bypass. Four assertions that were being
pre-empted by a `TypeError` on the line above them became measurable rather than declared
away. `test/fixtures_test.js` grew three plants, one of them the NON-first assertion inside
a multi-assert invariant — the plant that used to pass.

Then the sweep that started there and did not stop:

- **The validator's check count did not count checks.** `checks = 10 + len(skill_dirs)`, so
  adding a skill moved the number and adding a check did not — and five ledger rows read it
  as evidence a guard had arrived. Every check is registered; the verdict prints the
  registry's length, and the ledger's quoted copy of that line is compared against it.
- **The ledger described an artifact nobody ships.** Its shipped block was headed `v0.6.0`
  while `v0.7.0` was tagged and on npm, and 37 rows read *verified locally · unreleased*
  under four blocks closing *"Nothing was released."* The heading is now compared against
  `git describe --tags` and against `package.json`.
- **The `mcp__.*` half of the manual gate had no guard.** Deleting that entry from
  `hooks/hooks.json` left all three suites green, while the decision module does refuse
  `mcp__…__create_refund` by name. And `README.md`'s copy-channel snippet registered one
  matcher against the plugin's two — a weaker gate handed out by the document that exists
  because the channel has none. Both are now checked; the snippet by matcher set.
- **This repository measured no body budget at all**, so `crypto-payments/SKILL.md` sat past
  the house working limit and was caught by another repository's auditor. Measured here now,
  and the skill was **split rather than trimmed**: `references/callback-route-hardening.md`
  and `references/testing-and-local-dev.md`, 4894 → 4387 tokens. All six skills `0 GAP`.
- **Counted numbers became computed ones.** Seven in `SECURITY.md` (all four correct on the
  day they were written, three of them moved by this change) and two in
  `docs/evals/stripe-billing.md`, which restated `4994` tokens / `441` lines / `0 GAP, 13
  PASS` against a measured 4747 / 409 / `0 GAP, 14 PASS`.
- **A document that ships now resolves against the tarball, not only against a clone.**
  `SECURITY.md` sent a reader to two documents `npm pack` does not contain.
- **`docs/` joined the checked corpus**, with every document in it classified as live or as
  a dated record — `docs/AGENT_SYNC.md` had been naming six paths this repository does not
  have.
- **`.claude/agent-sync.json` pointed at a file that did not exist** and guarded the ledger
  without guarding the board.
- **`CONTRIBUTING.md` called the gate two suites and it runs three**; the PR template asked
  for one third of it. Both derive the list from `package.json` → `scripts.test` now.
- **`install.sh` — the channel that `rm -rf`s each destination — printed no notice** that
  the gate does not travel with it, while the npm installer did.

Fourteen negative self-tests were added, one per guard, and all **42** were watched refusing
their plants on a green tree. CI run `32293489020` at `6f66255` — 39 steps, 39 `success`,
28 of 28 negatives — retires the *"CI has not seen any of this"* limitation the ledger had
recorded four separate times.

## v0.7.0 — 2026-08-19

**The pack that takes money had the weakest controls in the family, and every one of them
was a sentence.** A conformance audit against the Proof of Done manifesto scored this
member last on both counts it measured — most requirements absent, fewest mechanically
enforced — and all three of its enforced rows were the artifact layer, none the money
layer. The manifesto's own test failed here literally: *a credential that cannot reach
production is stronger than a sentence saying not to use it there.*

Four changes, in the order they were built: the security document stopped describing a
different skill, the crypto provider gained a credential boundary, the four manual-gate
categories became a hook that refuses, and the money invariants became fixtures a reader
runs.

### The four money invariants were prose, and prose delegates enforcement to the reader

This pack already knew the invariants a generated integration gets wrong in the ways no
screen shows — the webhook is the payment and the redirect only proves a browser, the same
`event_id` on both sides or the revenue counts twice, `amount_refunded` arrives cumulative,
delivery is not ordered — and shipped every one of them as a paragraph. The giveaway was in
the document whose whole subject is proving a money defect would be caught: *Mutation testing
— the only proof that counts* (`references/testing-and-local-dev.md:157` at `90e9621`), whose
method was the sentence **"For every guard, delete it and re-run."** An instruction where a
test belongs, in the section arguing that tests are what count.

`manifesto.md:200` is that a test is stronger than an instruction, and `:289` that evidence
proves no more than it observed. So the invariants ship as something a reader runs.

**`stripe-billing/fixtures/` and `ad-tracking/fixtures/`** — copy either directory in and run
it. Twelve provider webhook bodies shaped the way the provider sends them: the January
renewal, the same `evt_` re-delivered, a mid-cycle proration invoice with two proration lines,
the February renewal (delivered *first*, it is the out-of-order pair), a `4000`-then-`9000`
cumulative refund against a `9000` charge, a bank-debit session that completed `unpaid` and
the `async_payment_failed` that followed it, a card session that cleared, and the pixel
arguments plus the Conversions API body one purchase produces. Plus one payload that must
never exist, kept as a fixture: the CAPI body a thank-you-page-sourced emitter sends for a
charge that never cleared.

**Eighteen assertions across two packs, and every one has been watched failing.**
`node assert-money-invariants.mjs --self-test` deletes one rule at a time from the reference
handler and requires the matching assertion to go red; it fails if the measured set differs
from the declared one in *either* direction. Nine rules on the Stripe side, five on the
tracking side, each with a fixture that isolates it.

**Isolating them is the whole engineering, and three masking pairs were found by the tool
rather than by inspection.** SD-03's mutation sweep reached 10/10 only on its second attempt
because two mechanisms were each leaning on the other's fixtures; the same shape appeared
three times here. A redelivery judged by the grant count alone is refused by the event claim
**or** by the per-period grant marker, so it proves neither — the fixture is kept, declares
`claim+grant-marker` as a multi-rule mutant, and the claim's real isolator is a **concurrent**
delivery (the marker reads before it writes, and a read is a round trip) while the marker's is
the **reconciliation** entry point, which carries no event id at all. A duplicate
`charge.refunded` is stopped by the claim and by `increment <= 0` alike, so the arithmetic is
measured by the two-step pair, whose events carry different ids. And in `ad-tracking`, reading
both sides out of one emitter meant deleting the browser event turned the id *and* name
assertions red — fixed by comparing the server's output against the shipped pixel fixture, a
boundary the server does not control.

**The fixtures cannot rot.** `check_money_fixtures()` in `test/validate.py` (15 → 16 checks)
reads each `fixtures/manifest.json` and requires both directions: every claimed invariant has
a fixture that exists and an assertion by that name, every fixture is claimed by a row, every
claiming document still carries its recorded phrase and names both the invariant and a path
under `fixtures/`, and every `fixtures/…` token in the skill's markdown resolves — the bounded
widening of the B-79 path guard that B-82 asked for. `test/fixtures_test.js` (13 checks) runs
both packs as processes in both modes and then neuters three assertions to prove `--self-test`
notices, because a self-test that cannot fail is the same defect one level up.

Five negative self-tests, 23 → **28**: a claimed invariant whose fixture is gone, a fixture no
invariant claims, a reference pointing at a fixture that is not there, a claim reworded away
from its fixture, and an assertion that can no longer fail. The guard's own first run found a
real orphan — `checkout-session-completed-paid.json`, claimed by nothing — which is why
`paid-session-grants-once` exists: without a positive control, a handler refusing *every*
checkout session would have satisfied `unpaid-session-grants-nothing`.

`SECURITY.md` moved with it, including one claim this change **falsified**: *"There is still
no runtime code inside the six skills"* stopped being true, because two of them now ship
runnable `.mjs`. It is replaced by what that code does and by the grep that proves the
boundary — no `child_process`, no `fetch`, no socket, no write, and no `process.env` read at
all; `readFileSync` of the JSON beside it is the entire I/O surface. Recounted: 30 → **50**
files in the payload, 4 → **22** non-markdown, 36 → **56** in the tarball.

### `SECURITY.md` described a different skill, in the published tarball

The document was a wholesale copy of `seo-aeo-audit`'s. It opened *"documentation plus one
small Python script"* and named `scripts/page_audit.py`, a `commands/` directory, a
`cursor/rules/` directory and `references/threats-and-defense.md` — this repository has
never contained any of them; there is no runtime code in the skill payload at all. A whole
section described the network behaviour of that auditor, down to `--url`, `--timeout` and
`--max-bytes`. It closed with *Verifying for yourself*, three commands of which **two could
not run**: `python3 test/test_page_audit.py` exits 2, and a `grep` at
`plugins/sheleg-dev/skills/sheleg-dev/scripts/page_audit.py` exits 2 under a skill
directory named `sheleg-dev` that has never existed.

`package.json` ships `SECURITY.md` in the tarball, so the pack was inviting an outside
reader to verify its safety with commands that fail — for a pack whose subject is payment
credentials and sign-in. **Six dead references** in one document.

Rewritten against what the tree actually returns: 27 files in the skill payload at that
commit, 26 of them markdown and one a plugin manifest — 30 once the manual gate shipped
three files beside them, see below; two installers using nothing but Node built-ins and
coreutils, with no network, no subprocess and no npm lifecycle script; the one destructive
difference between them (`install.sh` runs `rm -rf` on the destination every time,
`bin/sheleg-dev.js` skips unless `--force`); credential *names* in examples and no key, with
the one live-key-shaped line in the payload named and explained; and the five vendor commands
the advice can lead an agent to run, each with the `file:line` that says it. Every command in
the new *Verifying for yourself* block was run and its output is what the document claims.

### The guard the B-47 guard was waiting for

B-47 fixed this disease inside one table of `CONTRIBUTING.md` and said, in the guard's own
docstring, that going wider would flag paths being *discussed* rather than used. This is the
widening, bounded twice instead of not at all:

- **By corpus** — the documents whose subject is this repository: `README.md`, `SECURITY.md`,
  `CONTRIBUTING.md`, `.github/PULL_REQUEST_TEMPLATE.md`. A skill reference naming the
  reader's `next.config.ts` or `src/lib/heleket.ts` is describing their project; 41 such
  names in the payload would have been false positives, and a guard with 41 of those gets
  switched off.
- **By `FOREIGN_BY_DESIGN`** — the cross-repo signposts, enumerated one document at a time
  with a reason. An exemption the document stops naming **fails**, so the list cannot widen
  into a blanket.

It reads fenced blocks as well as inline spans, because the worst reference in the old
document was a fenced command, and it understands `path:line`: an address past the end of the
file resolves to nothing, which is the same defect one level down.

Watched refusing three plants and the real defect. Turned up two more of its own on the first
run: `.github/PULL_REQUEST_TEMPLATE.md` asked every contributor to paste output from
`python3 test/test_page_audit.py` and to avoid relative links in `cursor/rules/*.mdc` — both
inherited from the same copy. Also `CONTRIBUTING.md` named `agent_sync.py` with no owner; it
now says the script ships with the `agent-sync` skill.

### `crypto-payments` had no test/live credential boundary, in the skill about taking money

There was one `HELEKET_API_KEY`. It is *also* the webhook signing secret, so it cannot be
scoped down; the key carries no `test`/`live` marker; there is one host; and "test mode" is a
**toggle in merchant settings** — a property of the account, over the same key. The document
handed that key to the reader in a local-development block with no environment declared beside
it and then pointed at the dashboard toggle, so a dev, CI or agent run held the production
credential and nothing in the pack said so. Manifesto M-06 — *a credential that cannot reach
production is stronger than a sentence saying not to use it there, because the last control
still works after context loss* — failed literally, in the one skill whose subject is money.

**Established the provider's model before designing for it**, and it is worse than the brief
assumed: Heleket offers no separate test credential at all, so the Stripe-shaped fix of
reading the environment out of the key prefix does not exist here. The boundary is therefore
built on the two non-secret things Heleket does expose — the merchant UUID, and a 12-hex
SHA-256 prefix of the live key — pinned as `HELEKET_LIVE_MERCHANT_ID` and
`HELEKET_LIVE_KEY_FINGERPRINT`. Same shape as the house pattern in
`stripe-billing/references/price-integrity.md` (*a declaration separate from the secret, so
the two can be checked against each other*), different comparand.

Shipped: `HELEKET_ENV` with **no default**, because a default is the control disappearing the
first time somebody copies a `.env`; `assertHeleketEnv()` as a copy-whole snippet that runs at
module load rather than in the checkout handler, so a run that merely *holds* the key fails
too; refusals in **both** directions — a live credential declared test, and the quiet one, a
test credential declared live, where invoices settle to a merchant nobody reconciles and
nothing errors until the revenue is missing; a refusal for `SKIP_BILLING=true` under
`HELEKET_ENV=production`, which is a free-money path rather than a shortcut; and a refusal
when nothing is pinned and a *test* run therefore cannot prove it is not live, because "could
not prove it was safe" must never read as "it was safe". Named error codes, not sentences, so
a rewording cannot silently remove a control and an operator can alert on them.

**And the exposure that remains, written down.** The assertion checks the declaration; it does
not limit the credential. Unless a second merchant account is available — which this document
cannot confirm and now says so instead of implying it — a developer following Option B holds a
production key, the verifier cannot be issued without the invoice-creating power attached, and
rotation is the only revocation. An unavoidable risk that is named is a different object from
one that is silent.

The gate went from 13 checks to 14: `check_credential_boundary()` requires that every copyable
block assigning the secret also assigns the declared environment, that the assertion exists to
be copied, that both refusal codes are present, and that the residual exposure is written.
Table-driven, one row, and the empty-corpus case fails rather than passing. Three negative
self-tests (12 → 15), one per direction plus the original defect restored verbatim. The
assertion's logic was run over 11 cases, 11/11. `stripe-billing` states the same control at
`references/price-integrity.md:62-64` and asks for it at `testing-and-local-dev.md:210` while
shipping no assertion — filed as B-86 rather than fixed here, because a guard added in the
same breath as the defect it flags turns the gate red for work this change did not do. The
other three credential-holding skills were not looked at (B-87), and this reference is now
a 4× size outlier among references, filed as B-88 with a split rather than a trim as the
remedy — the precedent this repository set at v0.6.0.

### The four manual-gate categories were prose, and prose stops nothing

`pod-manifesto/manifesto.md:204` names money movement, irreversible action, production
access and destructive operations as the authorised person's to decide: *"The agent
prepares the decision and its evidence. The authorised person decides."* And `:200`: *"a
precondition is stronger than a warning."*

This pack named all four and stopped none. `crypto-payments/SKILL.md:310` said **"Never
auto-refund from the webhook. Route holds and refunds to a queue a human can see"**;
`stripe-billing/references/webhook-events.md:170` said a dispute is **"money already gone
plus a fee … route it to a human — evidence has a deadline"**. The plugin shipped no hooks,
no permission list and no gate, so both were advice to a reader who could skip it and to an
agent that never saw it. SD-02's boot assertion was the one real control here, and it runs
*inside the reader's application* — it cannot see a shell that merely **exports** the same
live merchant credential before any application starts.

**Shipped: a `PreToolUse` hook, `plugins/sheleg-dev/hooks/`.** Eight refusals, unless the
authorised person has signed the category off for the session: a live-shaped
`sk_live_…`/`rk_live_…` key reaching a command; an export of `HELEKET_API_KEY` — the one
credential SD-02 established has no test variant — in a run declaring `test` or declaring
nothing; `stripe refunds create` or a POST to a `…/v1/refunds` URL or a `create_refund`
tool; a payout or transfer, including Heleket's `…/v1/payout`; `stripe disputes close`; an
explicit `--live` flag; a command setting the gate's **own** switch; and `SKIP_BILLING=true`
in a run declaring production. The last two are never authorisable, and **no** category is
authorisable in a run that declares a non-production environment — a run that says it is a
test and then refunds a real card is incoherent whichever half is true.

Three invariants borrowed from the family umbrella, each one enforced by the validator so
it cannot be quietly collapsed. **The deciding is a pure module** —
`hooks/lib/moneygate.js`, payload and environment in, verdict out, no `require` of its own
and no filesystem — and the hook only moves bytes. **The hook fails silent**: it catches
everything and exits 0, because a guard that throws breaks every turn in every session,
including sessions of packs that never asked for this one; and every refusal names its
remedy, because one without a next step teaches an operator to switch the hook off.
**There is no `if` filter** on the hook entry: the reference calls that filter best-effort
and says it fails open on a command it cannot parse, and `Bash(stripe refunds*)` is exactly
the shape a `bash -c '…'` wrapper defeats.

Two defects this program proved elsewhere shaped the reading. Nothing here decides from
state the command is about to change (the umbrella's own gate asked "is anything staged?"
at `PreToolUse`, and an add-then-commit line walked through it). And the gate **reads what
would run**: a heredoc body fed to `cat` is data while a body fed to `bash` is a script; a
whole-line comment does not run; an assignment-shaped token is only an assignment in
command-prefix position, so `grep 'HELEKET_API_KEY=' plugins/` searches rather than
exports; a money endpoint must be a URL rather than a bare path; and a live key is
recognised by its **shape**, not its prefix, so `SECURITY.md`'s own sweep for
`sk_live_[A-Za-z0-9]` still runs.

`node test/moneygate_test.js` — **65 fixtures, both directions**, and the allow-plants are
real commands from this repository: that sweep, a `.env` heredoc fed to `cat`, a
commented-out `stripe refunds create`, a test-mode `sk_test_` key, and the non-secret
`HELEKET_LIVE_MERCHANT_ID` pin `assertHeleketEnv()` *requires* in a test run. `npm test`
now runs the validator and then the fixtures.

The gate went from 14 checks to 15 with `check_manual_gate()`. Eight negative self-tests
(15 → 23): five plant a defect in the gate's shipped shape and require the validator to
refuse, three break its decision module and require its own fixtures to go red. **Two of
those three were written because the first attempt went uncaught** — every `sk_live_`
allow-plant was leaning on the reader denylist while every reader allow-plant was leaning
on the key's shape, so neither mechanism was individually proven. A third plant escaped
because the validator's "the hook must require the pure module" check was satisfied by the
hook's own doc comment; it now reads the `require` expression.

**Registration, and what enforces it.** As a Claude Code plugin the hook is live when the
plugin is enabled, and `claude plugin validate --strict` schema-validates
`hooks/hooks.json`. Installed by `npx @ssheleg/sheleg-dev`, `install.sh` or `npx skills
add`, only the six skills are copied and **the gate is absent**: `README.md` → *The manual
gate* carries the settings snippet, the installer now prints the reminder, and **nothing
enforces it** — filed as B-90. Nothing writes to a person's settings file; that is the one
thing this repository must never do unasked. `SECURITY.md`'s counts move with the three new
files: 27 → **30** in the payload, 33 → **36** in the tarball, and the gate's whole reach is
two `require` calls with no `child_process`, no `fetch` and no `fs` on either path.

## v0.6.0 — 2026-08-16

### The file that promised the deduplication contract contained none of it

`ad-tracking/references/meta-linkedin.md` advertised *"deduplication against the
Conversions API"* in its own first line and in its Contents, ended at line 104, and
contained the word `event_id` exactly twice — both times in those promises. Its
Contents row for the missing half was `[Everything below](#)`, a dead anchor. The
pack's entire statement of the contract was one clause elsewhere: *"must carry the
SAME `event_id`"*.

That clause is **not the contract**, and the gap is money. Verified against Meta's
own documentation, 2026-08-16:

- **Two fields must match, not one** — `eventID`↔`event_id` **and**
  `event`↔`event_name`. An integration that shares an id and lets the two sides
  disagree on the name (`Purchase` vs `purchase`) never deduplicates, and the
  revenue is counted twice. The id half is obvious; the name half is not.
- **The window is 48 hours**, measured from when Meta receives the *first* event
  carrying that `event_id` — not from the purchase. A server event retried out of a
  dead-letter queue two days later is a second conversion.
- **The `fbp`/`external_id` alternative has a direction**: *"server events will not
  be discarded if a browser event has not been received in the past 48 hours, even
  if an identical browser event arrives after"*. For a purchase confirmed by a
  webhook — the pattern this skill teaches, because the webhook is the payment —
  the server event arrives first and that method does nothing.

The file also now carries **what must never be sent**, which it promised and
omitted: the categories Meta's Business Tools Terms prohibit (health, financial,
consumer-report, SSNs, card numbers, under-13 data), the fact that **event and
audience names are covered too** — `trackCustom('DiabetesPlanPurchase')` is a
breach with an empty parameter object — and that SHA-256 is a matching mechanism,
not a permission. And the LinkedIn conversion detail it promised.

### Two bodies over the 5000-token budget, split rather than trimmed

`ad-tracking` was ~5273 tokens and `stripe-billing` ~5367, both against `< 5000`,
and `ad-tracking`'s own text said *"the tables, schemas and per-framework wiring
live in `references/`"* while carrying five tables. Both are under the **4750
working limit** now, and every move went to a file that already owned the subject:

| Moved | To | Why there |
|---|---|---|
| Meta standard-events table, LinkedIn setup + conversions | `meta-linkedin.md` | the file that advertises them |
| User identification: cross-platform, alias-vs-identify, timing | `event-tracking.md` | an event name says what happened; identity says who to |
| Stripe CLI/MCP commands | `stripe-agent-toolchain.md` | every command was already there |
| Provider concentration | `provider-concentration.md` | the section already closed by pointing at it |
| Local dev + test matrix | `testing-and-local-dev.md` | one home, and they were two pointers to it |

The security checklist and the pitfalls table were **deleted rather than moved**:
every row restated a rule stated in its own section above, and a rule with two
homes drifts at one of them. Four rules whose failure is money are kept inline.

### `billing_mode` — a one-way choice this skill did not mention

Stripe creates every subscription in flexible or classic mode, the choice is made
at creation, **cannot be reversed**, and Stripe recommends flexible. Under flexible
a credit proration is computed from the amount **originally debited**, so one
change can emit **several** credit prorations where classic emitted one, and
discounts apply proportionally rather than evenly. Code that takes `[0]` of the
proration lines is correct under classic and wrong under flexible — silently, in
the refund clawback path. The pinned example `apiVersion` moved from
`2026-01-28.clover`, a major train behind and older than a feature the same file
recommended two sections later, to `2026-07-29.dahlia`.

### FCP, TBT and Speed Index are not Core Web Vitals

`frontend-performance` said they were, in its description and over its threshold
table. web.dev is explicit — the Core Web Vitals are LCP, INP and CLS, and TBT *"is
not part of the Core Web Vitals set because they are not field-measurable"*. An
agent asked *"are my Core Web Vitals passing?"* was being told a Speed Index of 4s
is a failing Core Web Vital, which is not a thing Google measures or ranks on. The
two sets are separate tables now, with what each lab metric stands in for.

Its **Related Skills** block named five skills, four of which resolve nowhere
(`landing-page-design`, `next-best-practices`, `responsive-design`, and
`frontend-design`, which resolves only to a third party) and one — `seo-audit` —
that is one character-class away from the real `seo-aeo-audit`, which is how a typo
survives review. Replaced with the family's actual routers.

### Fixed

- Three documents said CI runs **eight** negative self-tests; it runs **nine**, and
  the ninth arrived in the same commit that restated eight.
- The verification ledger was pinned to **v0.5.0** with two releases shipped since,
  reading green for a version npm no longer served. Re-pinned to v0.6.0, with the
  two rows that can only be read after publish marked `never` rather than assumed.

Found by the nine-repository audit of 2026-08-16 (umbrella `B-73`, `B-66`, `B-70`;
`F-sheleg-dev-01` through `-08`, `-17`).

## v0.5.2 — 2026-08-16

**`CONTRIBUTING.md` described a different repository.** Its *Where things go* table routed
contributions to `benchmarks.md`, `growth-plays.md`, `myths.md`, `algorithm-updates.md`,
`aeo-geo.md` and `scripts/page_audit.py` — all six belong to `seo-aeo-audit`, and
`git ls-files` here matched none of them. Sweeping every file name in the document found
**eleven** absent, not six: also `deliverable-templates.md`, `technical-checks.md`,
`threats-and-defense.md`, `test_page_audit.py`, and an `evidence-tiers.md` under a skill
directory named `sheleg-dev` that has never existed — the six skills are `stripe-billing`,
`crypto-payments`, `ad-tracking`, `google-signin`, `google-auth` and
`frontend-performance`.

Most of the document was a sibling's, adapted only at the edges. It claimed a
standard-library auditor and a second test command; there is no runtime code in this
repository at all, and `python3 test/validate.py` is the whole gate. Rewritten against what
`git ls-files` actually returns: six skills, twenty reference files, one executable
(`install.sh`), a four-way version sync, and the eight negative self-tests CI really runs.

**The guard is narrow on purpose.** Only the *Where things go* table is checked, because a
general "every path must exist" rule cannot tell a path being used from a path being
discussed — the rewrite deliberately names three `seo-aeo-audit` files to send a reader to
the right repository. The first draft of the guard read the whole section and flagged
exactly those, one paragraph after the comment explaining why it must not. A bare filename
resolves by basename, so `SKILL.md` passes as the generic it is while `benchmarks.md` still
fails. Watched rejecting the original row verbatim.

## v0.5.1 — 2026-08-16

**This gate can now see an invariant it breaks one repository away.** The family umbrella
routes work by matching a prompt against a table in `lib/triggers.js`, and every trigger
there must be a word this skill's own `description` advertises. Nothing here knew that
table existed. On 2026-08-16 `sheleg-design` 1.37.0 shipped green having dropped a phrase
that was still a live trigger, the umbrella found out minutes after the tag, and it cost a
patch release — because the member releases FIRST and the umbrella re-pins after.

`test/validate.py` now asks the umbrella's own checker (`test/advertised_check.js`), which
reads the module the hook itself calls. **No copy of the table lives here**, so there is
nothing to drift. With no umbrella above this checkout — a standalone clone, and CI — it
discloses rather than passing, because a check that cannot look must never read as one
that looked.

Watched refusing a real drop before shipping: every one of the seven members carrying
routed triggers had one of its own advertised phrases removed and every one of them failed
its own gate.

## v0.5.0 — 2026-08-14

Two gaps found by reading a web2app funnel guide against the pack. Both are about
the same seam: the payment layer is where a funnel's money and its measurement
actually live, and both skills were treating it as somebody else's concern.

### Added

- **`stripe-billing` → `references/provider-concentration.md`.** The skill covered
  dunning *inside* Stripe and never dependence *on* Stripe. The new reference is
  about the seam rather than about adding a second provider: the entitlement keyed
  to your own user id with provider ids as fields, the customer identity resolved
  before checkout, and the reconciliation job as the only number in the system
  that is not your own telemetry. `SKILL.md` → **Reconciliation** already excluded
  "rows that were never Stripe's", which is that seam half-built and was never
  named as one.

  It also declines the obvious answer: a generic `PaymentProvider` interface
  written against one provider encodes that provider's model and gets rewritten
  for the second one anyway. The seam is in the data, not in the code shape.

  **Automatic card updates are documented with their two limits**, both taken from
  Stripe's own text rather than from recall: coverage varies by country, and Stripe
  states it is **not possible to identify which cards support it** — so any plan
  that assumes a reissue will be caught has an unmeasurable branch. Handle
  `payment_method.automatically_updated` and `payment_method.updated`, write the
  new expiry and last four to your own records, and review anything keyed on
  `fingerprint`, which moves when the card number does.

  And the distinction the pack had no field for: a subscription that ended because
  someone chose to leave, versus one that ended because a bank reissued a number.
  A single `canceled` status for both is how a recoverable failure gets a farewell
  email.

### Changed

- **`ad-tracking` now says where a purchase event comes from.** Deduplication by
  `event_id` was already covered; what was missing is the reason the server side
  is not optional. Every other event on the list is something a person did in a
  tab. A purchase is the outcome of a charge that succeeded inside a payment
  system, and the only thing that knows it succeeded is the provider's webhook —
  so firing it from the thank-you page fires it from the one place with no idea
  whether the charge cleared, which is why a browser-only purchase count has an
  event for every session that reached the page and a refund for none of them.

  The ordering that follows: the webhook handler is the source of truth and sends
  the server-side conversion; the browser event stays for the signals only it
  carries and is subordinate on conflict; and everything the browser loses, it
  loses closest to the money, so the bias is downward by an amount that cannot be
  measured from inside the browser. Reconcile against the provider's count of
  succeeded charges, which is the only external check on this event that is not
  itself telemetry.

Both `SKILL.md` bodies stay inside the 500-line progressive-disclosure budget:
`stripe-billing` went to 502 lines when this was written inline, which is what
moved the full treatment into a reference and left a pointer behind.

## v0.4.3 — 2026-08-14

A red `validate` could not stop a publish, and this repository proved it.

### Fixed

- **The release now runs the whole validate suite before anything is published.** On
  2026-08-12 this repository tagged v0.4.1 while its own `validate` run for that exact tag
  **failed**, and npm served 0.4.1 four minutes later. Two separate workflows, nothing
  connecting them: `release.yml` ran the structural validator and never the negative
  self-tests, which are steps in `validate.yml`.
- `validate.yml` gained a `workflow_call` trigger and `release.yml` calls it with
  `needs: validate`, so the release runs **after** the real suite rather than beside a
  copy of it. No plant is duplicated: there is still exactly one home for each.
- **A guard keeps the connection there** — `check_release_gates_on_validate()` fails when
  the trigger, the call, or the `needs` goes missing. A dependency nobody checks is a
  dependency somebody removes. Watched failing against each of the three removals, with a
  negative self-test in CI.

## v0.4.2 — 2026-08-13

Its own negative self-tests could not be run on a developer's machine, and one of
them had been reporting a healthy guard as broken since 2026-08-12.

### Fixed

- **`main` was red for two days over a guard that works.** The over-long-description
  plant replaced the literal `"BTCPay".`; the description stopped containing it, so
  `str.replace` changed nothing, the validator honestly passed, and the step printed
  *ERROR: validator accepted a description past the 1024-char limit*. Re-anchored on the
  folded `>-` block's SHAPE and proven: the plant now produces a 1204-char description
  and the validator rejects it. Standing instruction #6 of the family's retro, which
  names this exact failure in another member.
- **Three plants used `sed -i` and were no-ops on macOS.** BSD sed requires an argument
  to `-i`, so they errored and changed nothing; they could only ever be exercised in CI,
  which is how the broken one went unnoticed. Converted to Python — the rule
  `task-pipeline` has enforced on itself for months.
- **Every plant now asserts that it changed the file.** A plant that stops landing says
  `PLANT DID NOT LAND: <why>` instead of blaming the guard it can no longer disarm.

All four verified by running them: each lands, and each makes the validator fail.

## [0.4.1] — 2026-08-12

### Changed

- **`ad-tracking`'s body is back inside the token budget** — ~5076 → ~4802 of 5000.
  The `Deep references` table was carrying a paragraph per file; each reference now
  opens with its own `Load this when` line, so the trigger has one home, the table is
  an index, and the two cannot drift apart.

## [0.4.0] — 2026-08-12

### Changed

- **Five of the six skills now open with `Use when …` and carry paired Russian
  triggers** — `ad-tracking`, `crypto-payments`, `frontend-performance`, `google-auth`,
  `google-signin`. `stripe-billing` already did, which is how the gap stayed invisible:
  the pack looked migrated because the one skill anybody checked was. The other five
  were unreachable from a request written in Russian.

  v0.3.0 brought three of these descriptions inside the 970 headroom by dropping
  duplicate triggers; this release rebuilds all five to the house shape — capability,
  coverage, English and Russian triggers, exclusion — and every one lands between 821
  and 884 chars.

## [0.3.1] — 2026-08-11

### Changed

- **Thirteen references over 100 lines now open with a `## Contents` list**,
  generated from each file's own `##` headings. A partial read is what an agent
  does with a long reference, and without the list it gets an arbitrary slice.

## [0.3.0] — 2026-08-11

### Changed

- **`ad-tracking`'s body went from 891 lines / 9160 tokens to 429 / 4747** —
  both caps are 500 lines and 5000 tokens, so it had been running at nearly
  double each. Measured with `cl100k`, not estimated.

  Nothing was deleted. Consent, event naming, e-commerce, CSP, Next.js and
  verification were duplicating `consent-mode.md`, `event-tracking.md`,
  `gtag-api.md` and `performance-security.md` — which cover the same ground in
  more depth — so the body keeps a load trigger and the trap, and the depth
  stays where it already was. The GA4 command table and the recommended-event
  table were verbatim subsets of two references.

  What had **no** reference to go to was moved into a new one:
  `references/meta-linkedin.md` (parameter objects per standard event, the
  firing wrapper, advanced matching, CAPI deduplication).

  The traps stay in the body on purpose — an agent cannot know to open a file
  about a trap it does not know exists. The consent ordering, the
  `NEXT_PUBLIC_*` build-time inlining, purchase deduplication and the
  double-counted SPA page view are all still inline.

- **Three descriptions brought inside the 5% headroom** the canon asks for
  (≤970 of 1024): `google-signin` 1021 → 968, `crypto-payments` 993 → 966,
  `ad-tracking` 988 → 959. Only duplicate trigger phrases were dropped —
  "crypto invoice" beside "crypto checkout", "ad pixel" beside "pixel". A
  description at 99% of the cap has nowhere to put the "NOT for …" clause a
  near-miss neighbour will eventually force.

## [0.2.0] — 2026-08-11

A sixth skill, and the one the pack was missing: cards. `crypto-payments`
covered the gateway that calls you back; nothing covered the gateway that holds
the money and the subscription state.

### Added

- **`stripe-billing`** — the seam between Stripe and your own database, which is
  where subscription integrations actually fail. Stripe's agent toolchain first
  (CLI, `stripe agent setup`, `stripe sandbox create` for keys without an
  account, the MCP server's implementation planner, `.md` docs), then the
  invariants: a lazily-built client with a pinned API version and
  `maxNetworkRetries` rather than a hand-rolled loop that buys two subscriptions
  for one intent; product-to-price resolution with pinned ids and both modes'
  ids in every allowlist; the get-or-create customer race as a conditional
  update with orphan cleanup; metadata written to the session **and**
  `subscription_data`, because renewal events never see the session;
  claim-first webhook idempotency with a release on failure, and the response
  codes that decide whether Stripe retries; the verify endpoint as a safety net,
  with the ownership check that stops one user claiming another's purchase;
  `billing_reason` as the difference between a renewal and a $0.40 proration
  invoice; proration with `error_if_incomplete` and a compensating Stripe revert
  when the local write fails; cumulative `amount_refunded` handled as a
  compare-and-swap; a sequential reconciliation job that leaves non-Stripe rows
  alone; and price drift, which fails no request and reaches only customers.

  Five references: `stripe-agent-toolchain.md`, `webhook-events.md`,
  `subscription-lifecycle.md`, `price-integrity.md`,
  `testing-and-local-dev.md`.

  Stripe-side decisions — Checkout vs PaymentIntents, Connect, Tax, Metronome
  for new usage-based billing — are deferred by name to Stripe's own
  `stripe-best-practices` skill, which wins any disagreement. The rules taken
  from Stripe's documentation (no `payment_method_types` on subscription
  Checkout Sessions, one Product per plan a customer can choose, restricted keys
  over secret keys, a secrets vault over environment variables) were read from
  `docs.stripe.com` on 2026-08-11 against Stripe CLI 1.45.2 and the official
  plugin 0.5.1.

### Changed

- CI installs and asserts six skills, not five, and requires a `stripe-billing`
  reference to land with them.

## [0.1.0] — 2026-08-06

First release. Five skills, ported out of a Cursor-only skills directory where
they had no version, no validator and no way to reach any other agent. Every
external claim with a shelf life was re-checked against its source on
2026-08-06 before shipping; what changed is listed under *Corrected on the way
in*.

### Added

- **`crypto-payments`** — accepting crypto without losing money to the three
  things that make it unlike cards: a payer who sends the wrong amount, a
  webhook that arrives more than once, and a rate that moves between quote and
  transfer. Status mapping with an explicit terminal set, signature verification
  with constant-time compare and the JSON-escaping trap, idempotency as a
  compare-and-swap rather than read-then-write, proxy-aware IP allowlisting,
  CSRF exemption scoped to one exact path, the conversion buffer, the
  reconciliation fields that make "what did we receive" answerable, the credit
  waterfall, refunds and AML holds, tunnelled local development with signed mock
  callbacks, a ten-case test matrix and a security checklist.
  `references/heleket-provider.md` carries one gateway's concrete wire format.
- **`ad-tracking`** — GA4, Google Ads, Meta Pixel and LinkedIn Insight under
  Consent Mode v2, with unified consent updates, cross-platform event mapping,
  e-commerce and deduplication, CSP per platform, and Next.js patterns. Four
  deep references on the Google tag itself: consent mode, the gtag API, event
  design, and performance/security.
- **`google-signin`** — the GIS ID-token flow as a security problem: the
  three-way account-linking branch with the pre-hijacking guard, login-CSRF
  defence covering **both** delivery flows, nonce and replay protection, GCP
  setup, and a checklist where each item maps to a real attack.
- **`google-auth`** — the server side: OAuth 2.0 web-server flow, Application
  Default Credentials, service accounts and JWT, Workload and Workforce Identity
  Federation, impersonation and downscoping — Node and Python throughout.
- **`frontend-performance`** — Core Web Vitals with an audit workflow, font
  loading, GPU-composited animation and the gradient-animation alternatives,
  bundle and cache work, CSP, and the accessibility rules that actually move a
  Lighthouse score. References for CSS, Next.js and accessibility.

### Corrected on the way in

- **FedCM is mandatory, not upcoming.** The source described the migration as
  having happened; it did not say the opt-out is gone. FedCM has been required
  for One Tap and Sign-In button implementations since **August 2025**, so
  `use_fedcm` and the traffic exemption no longer exist, and code branching on
  the old `isNotDisplayed()` moment callbacks needs revisiting. Corrected in
  both `google-auth` and `google-signin`.
- **Consent Mode v2 now expects a certified CMP.** Required since March 2024 for
  EEA/UK traffic; by 2026 Google additionally expects a CMP from its
  certification programme, so a correct hand-rolled banner is no longer
  sufficient on its own. Noted in `references/consent-mode.md`.
- **`crypto-payments` is provider-neutral by design.** The source was written
  around a single gateway. The reusable engineering — signature verification,
  idempotency, the buffer, reconciliation — is provider-shaped, and pinning it
  to one processor made the skill narrower and tied it to that processor's
  standing. The gateway's own wire format moved to a reference, which states the
  compliance position on record for it and says plainly that choosing a
  processor is not a technical decision.

### Infrastructure

- Structural validator (`test/validate.py`): one version across four files,
  Agent Skills front-matter limits, and `SKILL.md` ↔ `references/` agreement in
  **both** directions — no dangling link, no file nobody loads.
- Installer CLI and `install.sh`, both installing all five skills, both
  exercised by running them rather than syntax-checking them.
- CI with negative self-tests: every guard is planted against and required to
  fail before it is trusted.
