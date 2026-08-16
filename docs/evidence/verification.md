# Verification ledger — sheleg-dev

One row per shipped requirement, with the command that confirmed it and what that
command printed. A row sits at `never` until somebody has watched its check pass on the
**shipped** artifact — not on a branch, not in a plan.

This file exists because its absence read as zero exposure. `sshlg-skills` board row
**B-30** measured this repository returning 0 REQ rows and named the reading that
produces: *"an absent ledger and a clean one are indistinguishable from the number
alone."* An empty ledger and a clean one now differ.

**It starts at the shipped state, not at the repository's history.** Every row below was
confirmed against v0.6.0 as it stands on `main` and on npm; nothing was back-filled from
a CHANGELOG entry, because a claim restated is not a claim verified.

---

## Shipped state — v0.6.0

Released: `@ssheleg/sheleg-dev@0.6.0` (npm), tag `v0.6.0` (annotated).

> **v0.5.1 and v0.5.2 shipped with no row here**, and this heading said `v0.5.0`
> while npm served `0.5.2`. A ledger describing an artifact nobody ships reads
> green for a version that no longer exists, which is worse than the absence it
> was created to fix. The rows below are re-measured against v0.6.0.
CI: `validate` run `31812223879` → `completed success`; `release` run `31812293485`
→ `completed success`. The validate verdict was read **before** the tag was cut,
which is the ordering v0.4.1 got wrong in this very repository.

Six skills ship: `ad-tracking`, `crypto-payments`, `frontend-performance`, `google-auth`,
`google-signin`, `stripe-billing`.

| REQ | Requirement | Verified by | Result | Status |
|---|---|---|---|---|
| 001 | The structural validator passes on the shipped tree | `python3 test/validate.py` | `OK: sheleg-dev structurally valid (12 checks, 6 skill(s), v0.6.0)` — and it counts the skills, so a lost one changes the line | **verified** |
| 002 | Every guard has been watched failing against a planted defect | CI run `31749477902`, step-level conclusions of every `Negative self-test` step | **9 of 9 `success`**, 0 failed steps in the run — the count was restated as eight in three documents while CI ran nine, and the ninth arrived in the same commit that restated eight | **verified** |
| 003 | Version is synchronised across every surface | read back from `package.json`, `.claude-plugin/marketplace.json`, `plugins/sheleg-dev/.claude-plugin/plugin.json`, the top `## vX.Y.Z` in `CHANGELOG.md` | all four → `0.6.0` | **verified** |
| 004 | A release cannot publish over a red suite | `grep -c workflow_call .github/workflows/validate.yml`; `grep -n` in `release.yml` | `workflow_call` 2; `uses: ./.github/workflows/validate.yml` at line 29, `needs: validate` at line 32. This is the repository where the failure was observed: v0.4.1 was tagged while its own validate run for that tag failed, and npm served it four minutes later | **verified** |
| 005 | Every reference a skill links resolves, and none is orphaned | walk each `SKILL.md` for `](references/…)` and each `references/*.md` for a mention | **0 unresolved, 0 orphans** across all six skills; the count moved with `references/provider-concentration.md`, which the check requires to be linked **and** the link to resolve | **verified** |
| 006 | The installer installs all six skills into a fresh HOME | `HOME=/tmp/fakehome-sd node bin/sheleg-dev.js`, then list `$HOME/.claude/skills/` | six directories: `ad-tracking crypto-payments frontend-performance google-auth google-signin stripe-billing` | **verified** |
| 007 | A second run skips rather than re-writing | re-run the installer against the same HOME and count `^skip:` | `6` — one per skill, none re-installed | **verified** |
| 008 | Both workflows are parseable by the parser GitHub uses | `yaml.safe_load` over `validate.yml` and `release.yml` | both parse | **verified** |
| 009 | npm serves exactly the version this tree claims | `npm view @ssheleg/sheleg-dev version` | `0.6.0`, and the published tarball carries the deduplication contract (`grep -c event_name` in the shipped `meta-linkedin.md` → 5, where the pre-release file had 0) | **verified** |
| 010 | The tag exists at the released version | `git tag --sort=-v:refname \| head -2`; `git cat-file -t v0.6.0` | `v0.6.0`, `v0.5.2` — newest tag matches, and it is **annotated**, so `git describe` and `git submodule status` name it (umbrella B-69) | **verified** |

## What these checks do not cover

Named rather than left to be inferred, because a ledger that lists only its successes
reads as coverage it does not have.

- **Whether the integration advice is correct against the live vendors.** These six
  skills describe Stripe, Heleket/BTCPay, Google Sign-In, Workload Identity, ad networks
  and web performance. Every row above measures the *artifact*: valid, linked, budgeted,
  released. Nothing here re-checks a vendor's current API against the page describing
  it, and vendor drift is this repository's largest untested exposure.
- **`--force` and the bad-argument path.** CI exercises both against a fake HOME; REQ-006
  and REQ-007 cover the fresh and rerun-skip paths locally and stop there.
- **The nine negatives, one by one, locally.** REQ-002 reads their step conclusions from
  the CI run rather than re-running each — a run's verdict, not eight local
  reproductions.
