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
