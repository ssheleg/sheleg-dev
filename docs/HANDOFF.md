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
