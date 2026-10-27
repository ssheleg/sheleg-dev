## v0.16.3: product analytics routes to ad-tracking (2026-10-27)

- **Done.** Hub board row B-267 (sheleg-dev part): `ad-tracking`'s `## Triggers` gains "product
  analytics" / «аналитика продукта». The skill's architecture diagram already names Mixpanel as the
  product analytics tag behind its consent layer, so the ground is its own. Body 4,748 of 4,750
  tokens after a shorter opening sentence. Gate: `npm test`.
- **Next task.** After merge: tag `v0.16.3`, watch the release, then the hub adds the route row with
  a fixture (B-267) and bumps the pin.

## v0.16.2: descriptions within a 300-character budget (2026-10-25)

- **Done.** Every skill description cut to at most 300 characters (hub B-255 (a)); total 2875 → 2078
  characters, whitespace collapsed. Dropped quoted triggers moved to each body's `## Triggers`.
  Per-skill numbers are in CHANGELOG.md.
- **Next task.** After merge: tag `v0.16.2`, watch the release, then the sshlg-skills pin bump; then
  the highest open board row.

## v0.16.1: the family member gate (2026-10-24)

- **Done.** the family member gate: the family member gate (`test/family_gate.py`, with its shared-mechanism
  declaration) and the documentation merged since v0.16.0, released.
- **Next task.** After merge: tag `v0.16.1`, watch the release, then the sshlg-skills pin bump; then
  the highest open board row.

## v0.16.0: a pause in the cancel path; B-86 closed (2026-10-22)

- **Objective.** Hub M2 wave 2, gap G8: offer a pause in place of cancellation without
  lengthening the cancel path; close board row B-86.
- **Done.** `stripe-billing/references/cancellation-and-retention.md` → *A pause instead of
  a cancellation* (screen rule; `pause_collection` against the Pause endpoint; the three
  roads to `paused`; four test-matrix lines), every Stripe fact cited to `docs.stripe.com`,
  read 2026-10-22. B-86 was already implemented by PR #25 (v0.13.4); the board row is now
  closed with that evidence and `price-integrity.md` cites the key-prefix source.
- **Decision.** Stripe's docs added a GA Pause endpoint in `2026-09-30.endive` (flexible
  `billing_mode`); the section presents both mechanisms rather than `pause_collection` alone,
  because `pause_collection` keeps the customer's access on.
- **Checks.** `npm test` exit 0 on branch `feat/m2-pause-b86`.
- **Also fixed.** `subscription-lifecycle.md`'s status map folded `paused` into `canceled`; a
  paused subscription resumes, so it now maps to its own `paused`, with a note.
- **Open.** B-107 (the SKILL client pins `2026-07-29.dahlia`, before the Pause endpoint) and
  B-108 (`billing_mode` described as fixed, while Stripe links a migration to flexible).
- **Released (2026-10-22).** PR #34 squash `5842df5`, tag `v0.16.0`, release run 39785238543 green, npm `@ssheleg/sheleg-dev` 0.16.0; sshlg-skills pins it in 1.74.0 and the install reads back verified for Claude and current for Codex.
- **Next task.** B-98 (priority 2.0, tied highest with B-105): `v0.7.0` is a lightweight tag where `v0.6.0` was annotated; then B-107, the client's API pin before the Pause endpoint.

## 0.15.1 released and pinned (2026-10-22)

- **State.** sheleg-dev 0.15.1 is tagged, on npm and pinned by sshlg-skills 1.73.2; installed on the operator machine.
- **Next task.** B-86: ship the boundary assertion `stripe-billing` prescribes; then the pause and win-back items of the hub's [M2 plan](https://github.com/ssheleg/sshlg-skills/blob/main/docs/runs/2026-10-22-m2-subscription-growth-plan.md) (wave 2).

## v0.15.1: a neutral example brand (2026-10-22)

- **Objective.** Remove a private project name from a shipped example (operator, 2026-10-22: no project names in public skills).
- **Done.** `references/accessibility-perf.md` uses `Acme`; version 0.15.1.
- **Next task.** After merge: tag `v0.15.1`, watch the release run, then the sshlg-skills pin bump.

## Short router descriptions, v0.15.0 (2026-10-20)

Objective: free Claude Code's shared skill-listing budget (about 30,000 chars; 81 of
134 skills showed no description on 2026-10-20). All seven descriptions are now
386-459 chars (6,174 to 2,875 in total); the removed trigger phrases moved verbatim
into each body's `## Triggers`. `test/validate.py` caps a description at 500 chars.
Checks: `npm run test:all` exit 0; every routed trigger in the umbrella's
routing table (42) found in its SKILL.md text by a scratch check.

Open: the umbrella's advertised-trigger check still reads the description only, so
it reports the 7 triggers that now live only in a body until the umbrella's
context-diet change makes it read the whole SKILL.md. The umbrella re-pin is the
umbrella's task. Next task: none in this repository for this change.

## WebKit (Safari) first in frontend-performance — 0.14.0 candidate (2026-10-16)

Branch `docs/safari-first` (family iteration ITER-1016, REQ R14): `frontend-performance`
gains *Test browser — WebKit (Safari) first*; Lighthouse, PSI, CrUX, CDP traces and the
chrome-devtools MCP stay as the stated Chromium exception. Measure/Validate steps,
Degradation and the contrast check in `references/accessibility-perf.md` carry it.
Other skills (ad-tracking, google-auth, crypto-payments) mention Chrome only
incidentally and prescribe no test browser — left unchanged. Version 0.13.4 → 0.14.0;
ledger block moved. Regression `test/audit_regressions/safari-first.py` (watched failing
5 of 5 first). Gate: `npm test` exit 0.

Next task: review the draft PR; the coordinator owns the annotated tag, publication and
the umbrella pin.

## FW07 shared scratch lock — active bounded port

[Owner entry](evidence/runs/2026-10-13-fw07-scratch-lock/README.md) binds the
accepted canonical mechanism, own source and pending tests. Exact next task:
port byte-identical helper and runner adapter, run owned-namespace focused checks,
independent review, then serial owner gate. No public scratch execution while the
coordinator owns the full-suite slot; no package version/release in this change.

# FW03 release packaging — 2026-10-13

Branch `release/fw03-0.13.4` prepares patch 0.13.4 from accepted source
`9703d5ece1b1f135f0c7cc50c50c78563b894bbf` (PR25). Genuine validation
[38336515558](https://github.com/ssheleg/sheleg-dev/actions/runs/38336515558)
passed at candidate `40bf0f1f23a19651806f1efd0a20a418938ee2c3` before normal merge.
Independent review and local gates: [FW03 receipt](evidence/runs/2026-10-13-fw03-credentials.md).
Registry `@ssheleg/sheleg-dev` and remote tags read 0.13.3 before this preparation.
This branch changes manifests, card and release documentation only.

Packaging validator passed: `python3 test/validate.py`, 28 checks, exit 0.
Independent packaging review passed at `47e8391e7c2e619c0802d56cca4e406f3d23fef9`: metadata
and release documentation only; no implementation or workflow changes.
Next: frozen PR promotion,
normal merge and exact-source checks before an annotated release tag. No tag,
publication, parent pin or installed/native update has occurred. Meta CAPI's
credential contract, B-90 copy-channel hooks and B-92 native-host observations
remain open; local fixtures do not establish provider acceptance.

---

# sheleg-dev handoff

## FW03 — credential boundaries, 2026-10-13

Objective: close the reproducible B-82/B-86 defects and reconcile B-87/B-91 with
current source. Branch: `fix/fw03-credential-boundaries`; baseline
`f946ce6625ae8458b6963e9c2a9fe29b4c642bdd`. No release or installed-skill update.

Start with [the bounded receipt](evidence/runs/2026-10-13-fw03-credentials.md).
It maps requirements, source, negative controls and residual work. The
[owner board](evidence/backlog.md) preserves its historical measurements.

Implemented: explicit repository-path validation inside skill Markdown; executable
Stripe mode assertion and copy instructions; named Google secret assignment refusals
with public metadata counterexamples; token-free logging and credential documentation.

Next task: independently review this branch, replay the focused regression and owner
suite, then integrate under the current CI policy. Do not treat local success as a
native-host or provider result. Resolve the current Meta CAPI credential contract
from official documentation before adding a provider row. B-90 copy-channel hook
registration and B-92 live-host residual evidence remain separate work.

Checks: `npm test` passes locally; see the receipt for measured counts and scope.
Prerequisites for live work: the project's existing authority, separately scoped
credentials and native-host evidence. This slice needs none of those secrets.
