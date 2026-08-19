# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [SemVer](https://semver.org/spec/v2.0.0.html).

## Unreleased

No version heading yet, deliberately: the version converges at the family level, and a
`## vX.Y.Z` here would make this the release notes for a tag that does not exist.

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

Rewritten against what the tree actually returns: 27 files in the skill payload, 26 of them
markdown and one a plugin manifest; two installers using nothing but Node built-ins and
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
