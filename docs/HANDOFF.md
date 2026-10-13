# FW03 release packaging — 2026-10-13

Branch `release/fw03-0.13.4` prepares patch 0.13.4 from accepted source
`9703d5ece1b1f135f0c7cc50c50c78563b894bbf` (PR25). Genuine validation
[38336515558](https://github.com/ssheleg/sheleg-dev/actions/runs/38336515558)
passed at candidate `40bf0f1f23a19651806f1efd0a20a418938ee2c3` before normal merge.
Independent review and local gates: [FW03 receipt](evidence/runs/2026-10-13-fw03-credentials.md).
Registry `@ssheleg/sheleg-dev` and remote tags read 0.13.3 before this preparation.
This branch changes manifests, card and release documentation only.

Packaging validator passed: `python3 test/validate.py`, 28 checks, exit 0.
Next: independent diff review, frozen PR promotion,
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
