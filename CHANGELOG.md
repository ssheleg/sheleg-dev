# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [SemVer](https://semver.org/spec/v2.0.0.html).

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
