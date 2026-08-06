# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [SemVer](https://semver.org/spec/v2.0.0.html).

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
