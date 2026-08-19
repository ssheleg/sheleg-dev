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

## Unreleased — verified locally, not yet shipped

Rows for work that has landed on `main` and **not** been released. They are kept apart
from the shipped block on purpose: this file's own rule is that a row is `verified` once
its check has been watched passing on the *shipped* artifact, and the version converges at
the family level rather than here. At the next release these move up and are re-measured
against the tarball.

Row **SD-01** of the cross-repository manifesto-conformance program, 2026-08-19,
requirements **M-44** (one authoritative home; references resolve) and **M-07** (a claim
points to an address another actor can resolve). Board rows: `docs/evidence/backlog.md`
B-79 through B-84.

| REQ | Requirement | Verified by | Result | Observed at | Status |
|---|---|---|---|---|---|
| 011 | `SECURITY.md` describes THIS pack, and every path it names exists here | `python3 test/validate.py` | `OK: sheleg-dev structurally valid (13 checks, 6 skill(s), v0.6.0)`, exit 0. The six dead references the audit cited — `SECURITY.md:10,11,17,35,54,56` of the old file — are gone; the document now names 29 path tokens and all 29 resolve | 2026-08-19 | **verified locally · unreleased** |
| 012 | Every command in *Verifying for yourself* runs, and prints what the document claims | each command run from the repo root, verbatim | `python3 test/validate.py` → 0; `git ls-files plugins \| wc -l` → `27`; `git ls-files plugins \| grep -v '.md$'` → 1 line, the plugin manifest; the installer I/O grep → `11` lines; the live-key grep → `1` line, the RSA placeholder; `npm pack --dry-run` → `total files: 33`. The old block's second and third commands exited 2 | 2026-08-19 | **verified locally · unreleased** |
| 013 | The guard refuses a recurrence, and has been watched doing it | three plants into `/tmp` copies, then `python3 test/validate.py` in each | all three refused with exit 1: a dead path (`SECURITY.md:58 names 'scripts/page_audit.py', which this repository has nowhere`), a citation past the end of a file (`cites install.sh:9001, but that file has 32 lines`), and a stale exemption (`FOREIGN_BY_DESIGN carries 'benchmarks.md' … but the document no longer names it`). It also refused the **real** defect before anything was fixed — 8 failures, the audit's 6 plus 2 it found itself | 2026-08-19 | **verified locally · unreleased** |
| 014 | The guard is bounded, not blanket — no false positive on the current tree | count the tokens it inspects and the exemptions it uses | 67 path tokens across the four self-describing documents, 10 of them `file:line` citations, 0 failures; 5 `FOREIGN_BY_DESIGN` entries and every one still matched by its document. The 41 reader-project paths inside the skill payload (`next.config.ts`, `src/lib/heleket.ts`, `web/auth.py`) are outside the corpus by design — board B-82 | 2026-08-19 | **verified locally · unreleased** |
| 015 | The two dead references in `.github/PULL_REQUEST_TEMPLATE.md` are gone | `python3 test/validate.py`; read the file | the evidence block is one command, `python3 test/validate.py`; the `cursor/rules/*.mdc` checklist item is replaced by the `references/` ↔ `SKILL.md` rule the validator actually enforces | 2026-08-19 | **verified locally · unreleased** |

**What is NOT verified in this block.** The three new negative self-tests have been run
locally as real processes against real copies, and **not yet by CI** — the step-level
conclusions REQ-002 reads do not exist for them. The negative count moved from nine to
twelve in `.github/workflows/validate.yml` and `CONTRIBUTING.md` says twelve; the first CI
run on this branch is what turns that into a measurement. Nothing here was released: no
tag, no publish, no version bump.

Row **SD-02** of the same program, 2026-08-19, requirement **M-06** (a credential that
cannot reach production is stronger than a sentence saying not to use it there, because
the last control still works after context loss). Board rows: `docs/evidence/backlog.md`
B-85 through B-87.

| REQ | Requirement | Verified by | Result | Observed at | Status |
|---|---|---|---|---|---|
| 016 | The provider's real credential model is established from the document, not assumed | read `references/heleket-provider.md` §1, §3, §7, §15 | **Heleket offers no separate test credential.** One key per merchant (`:62`), which is *also* the webhook signing secret (`:126`); one host, `api.heleket.com` (`:60`, `:376`); no environment marker in the key, so the Stripe-style prefix read is unavailable; "test mode" is a toggle in merchant settings (`:1155`), a property of the **account** over the same key. The brief's imagined fix — assert the key's declared environment against the key itself — was therefore not buildable as written | 2026-08-19 | **verified locally · unreleased** |
| 017 | The boundary is built on what the provider actually exposes | read the shipped `assertHeleketEnv()` | it compares the declared `HELEKET_ENV` against the two **non-secret** discriminators Heleket does give: the merchant UUID pinned as `HELEKET_LIVE_MERCHANT_ID`, and a 12-hex SHA-256 prefix of the live key as `HELEKET_LIVE_KEY_FINGERPRINT`. Same shape as the house pattern at `plugins/sheleg-dev/skills/stripe-billing/references/price-integrity.md:62-64` — a declaration separate from the secret — with a different comparand because the key carries no mode | 2026-08-19 | **verified locally · unreleased** |
| 018 | Both mismatches are refused, and the logic has been run | the shipped snippet transliterated to JS with types stripped, control flow unchanged, driven over 11 cases | **11/11.** A live credential declared test is refused by UUID *and* by fingerprint alone (`HELEKET_ENV_TEST_HOLDS_LIVE_CREDENTIAL`); a test credential declared live is refused (`HELEKET_ENV_LIVE_HOLDS_TEST_CREDENTIAL`); unset refuses rather than defaults; an unpinned *test* run refuses because it cannot prove it is not live; `SKIP_BILLING=true` with `HELEKET_ENV=production` refuses; and the two correct configurations pass — a boundary that refuses everything is switched off within a day | 2026-08-19 | **verified locally · unreleased** |
| 019 | The control is a snippet and a check, not a paragraph | `python3 test/validate.py`; `npm test` | both exit **0**, `OK: sheleg-dev structurally valid (14 checks, 6 skill(s), v0.6.0)` — the count moved 13 → 14 with `check_credential_boundary()`, which requires that every copyable block assigning `HELEKET_API_KEY` also assigns `HELEKET_ENV`, that `assertHeleketEnv` exists to be copied, that both refusal codes are present, and that the residual exposure is written down | 2026-08-19 | **verified locally · unreleased** |
| 020 | The new guard has been watched failing, in both directions and on the original defect | three plants into `/tmp` copies, then `python3 test/validate.py` in each | all three refused with exit 1: the live-declared-test code renamed (`the boot assertion cannot refuse HELEKET_ENV_TEST_HOLDS_LIVE_CREDENTIAL`), the test-declared-live code renamed (`… HELEKET_ENV_LIVE_HOLDS_TEST_CREDENTIAL`), and the environment deleted from the Option B block (`heleket-provider.md:1362 — a copyable block sets HELEKET_API_KEY without HELEKET_ENV`). It also refused the **real** defect before anything was fixed: 6 failures on the unmodified tree, naming both credential-handover blocks at `:135` and `:1137` | 2026-08-19 | **verified locally · unreleased** |
| 021 | The twelve pre-existing negatives still refuse their plants | every `Negative self-test` step extracted from `validate.yml` and run as a process from the repo root | **15/15 refused.** The three new ones plus the twelve SD-01 left, none broken by edits to `test/validate.py` or `crypto-payments/SKILL.md` | 2026-08-19 | **verified locally · unreleased** |
| 022 | The new cross-references resolve | slugify every heading, then resolve every in-page and relative link in the two edited files | **0 broken** — 15 in-page links against 17 headings in `SKILL.md`, 27 against 37 in `heleket-provider.md`, and both relative links, including the new one to `stripe-billing/references/price-integrity.md` | 2026-08-19 | **verified locally · unreleased** |

**What is NOT verified in this SD-02 block.**

- **Nothing was checked against Heleket.** No network call was made to any payment or auth
  provider, by constraint. Every statement about the credential model above is a reading of
  `references/heleket-provider.md`, not of the vendor's current documentation — the same
  vendor-drift exposure the section below names as this repository's largest.
- **Whether a second Heleket merchant account is actually available.** The strongest control
  in the shipped advice — a sandbox merchant, so the dev credential authorises nothing live —
  is written as *"check whether your account permits one"* precisely because the document
  does not establish that it does, and confirming it would mean logging into a dashboard.
- **The assertion has not been run as TypeScript.** REQ-018 ran a transliteration with types
  stripped; there is no TS toolchain in this repository and adding one to type-check a
  snippet in a markdown reference is not a trade this row made.
- **CI has not seen the three new negatives.** Same gap SD-01 recorded: the step-level
  conclusions REQ-002 reads do not exist for them yet. The negative count moved from twelve
  to **fifteen** in `.github/workflows/validate.yml` and `CONTRIBUTING.md` now says fifteen.
- **`stripe-billing` is untouched and still has the same defect** (B-86), and the other three
  credential-holding skills were not looked at (B-87). Enforcing `CREDENTIAL_BOUNDARIES`
  over `stripe-billing` in this change would have turned the gate red for work this row did
  not do.
- **The reference this row grew is a size outlier** — 1696 lines / ~18.8k tokens against a
  next-largest reference of ~4.8k. `audit_skill.py` returns `0 GAP` and the 5000-token budget
  is a `SKILL.md` rule, so nothing is violated; it is filed as B-88 rather than left as an
  unmeasured consequence, and the fix is a split rather than a trim.
- **Nothing was released**: no tag, no publish, no version bump.

**Noted for the sibling row SD-03**, which owns the `PreToolUse` hook: the boundary shipped
here is a boot assertion *in the reader's project*, and it cannot see a shell that merely
exports a live key. A hook refusing a Bash command that sets a production merchant
credential in a run declaring `test` is the missing half, and it belongs there rather than
here — the same argument that keeps `sk_live_` out of an agent's hands.

Row **SD-03** of the same program, 2026-08-19, requirement **M-30** (the manual gate: ambiguity,
external publication, irreversible action, money movement, production access, destructive
operations and changes of scope are the authorised person's to decide — `manifesto.md:204` — and
`:200`, a precondition is stronger than a warning). Board rows: `docs/evidence/backlog.md`
B-89 through B-93.

| REQ | Requirement | Verified by | Result | Observed at | Status |
|---|---|---|---|---|---|
| 023 | The defect is what the audit said it was, and the pack shipped no gate of any kind | `git ls-tree -r --name-only 00285e7 plugins` | **27 files, 26 markdown and one manifest — no `hooks/`, no `hooks.json`, no permission list.** The two prose sites were `crypto-payments/SKILL.md:310` ("Never auto-refund from the webhook. Route holds and refunds to a queue a human can see") and `stripe-billing/references/webhook-events.md:170` ("route it to a human — evidence has a deadline"). SD-02's `assertHeleketEnv()` was the one real control and it runs inside the reader's application, so a shell that merely exports the live merchant credential never reaches it | 2026-08-19 | **verified locally · unreleased** |
| 024 | The gate refuses everything the row requires, and each refusal has been watched | `node test/moneygate_test.js` | **65 fixtures, exit 0** — 27 deny-plants, 25 allow-plants and 13 direct checks of the lexer, the environment reading and the category table. The deny-plants cover all eight categories: a live-shaped `sk_live_`/`rk_live_` key (three shapes, including inside `bash -c '…'`), `HELEKET_API_KEY` exported in a test-declaring run / with nothing declared / through `env(1)` / in a heredoc fed to `bash`, `stripe refunds create` (bare, quoted, via `npx`), a `…/v1/refunds` POST, `stripe payouts create`, `stripe transfers create`, a Heleket `…/v1/payout` POST, `stripe disputes close`, a `…/v1/disputes/…/close` POST, the `create_refund` MCP tool by name, `--live`, `--live-mode`, a command setting the gate's own switch, and `SKIP_BILLING=true` in production | 2026-08-19 | **verified locally · unreleased** |
| 025 | It does NOT refuse correct input — the direction that decides whether it stays switched on | same command; the allow-plants | **25 allow-plants, all allowed.** Every one is a command this repository or its readers actually run: `SECURITY.md:155`'s own sweep for `sk_live_[A-Za-z0-9]` verbatim; reading and grepping the two references that quote `sk_live_…`; a secret scanner given the bare prefix as its pattern; a `.env` heredoc fed to `cat`; a refund line inside a heredoc fed to `python3`; two whole-line comments; a bare `/v1/refunds` path in a grep and in a route-audit script; `HELEKET_API_KEY=` as an argument to grep; `echo --live`; `stripe refunds list`; the non-secret `HELEKET_LIVE_MERCHANT_ID` pin `assertHeleketEnv()` *requires* in a test run; a `sk_test_` key; `SKIP_BILLING=true` in development; a `Write` tool whose content is a live-shaped key; and an authorised refund in a production-declaring run, because a gate that cannot be passed is a gate that gets removed | 2026-08-19 | **verified locally · unreleased** |
| 026 | The fixtures can actually see a broken gate — they were mutation-tested | ten targeted mutations of `hooks/lib/moneygate.js`, `node test/moneygate_test.js` in each | **10/10 caught, after two rounds.** The first round caught 8: narrowing `LIVE_KEY` to the bare prefix and deleting the reader denylist both passed, because every prefix allow-plant was leaning on the denylist while every reader allow-plant was leaning on the key's shape — **two overlapping mechanisms, neither individually proven.** Three fixtures were added to isolate them (a non-reader scanner given the prefix; a reader given a full endpoint URL; a non-reader given a bare path) and all ten mutations then failed the suite | 2026-08-19 | **verified locally · unreleased** |
| 027 | The hook is a byte-mover, fails silent, and exits 0 on every path | five payload shapes driven through `plugins/sheleg-dev/hooks/money-gate.js` as a real process | **exit 0 in all five.** A refund payload → one JSON line, `permissionDecision: "deny"`, the reason naming `refunds create`; an ordinary `npm test` payload → empty stdout; garbage stdin → empty stdout **and empty stderr**; empty stdin → nothing; a payload with no `tool_input` → nothing. `node --check` passes on both files. The decision module `require`s nothing at all and the hook `require`s `path` plus the module — measured, and `child_process`, `fetch`, `http`, `fs`, `spawn`, `writeFile` return **no lines** across both | 2026-08-19 | **verified locally · unreleased** |
| 028 | The three umbrella invariants are enforced by the gate rather than by intention | `python3 test/validate.py`; `npm test` | both exit **0**, `OK: sheleg-dev structurally valid (15 checks, 6 skill(s), v0.6.0)` — the count moved 14 → 15 with `check_manual_gate()`, which requires a `PreToolUse` entry running `money-gate.js`, a `Bash` matcher, **no `if` key anywhere in the manifest**, the `require` of the pure module, a `catch` and a `process.exit(0)`, every category present in both module and fixtures, allow-plants at least half the deny-plants, `npm test` and CI both running the fixtures, and the two prose sites naming the mechanism | 2026-08-19 | **verified locally · unreleased** |
| 029 | The new guard has been watched failing, in eight ways | eight plants into `/tmp` copies, then the gate in each | **all eight refused.** Five against the shipped shape — the hook moved to `PostToolUse` ("a gate that can only report after the money moved"), an `if` filter reintroduced, the `require` renamed, `process.exit(0)` removed, the allow-plants deleted — and three against the decision module, which require the *fixtures* to go red: `LIVE_KEY` narrowed to the prefix, the heredoc rule inverted, and `allowedFor` letting a test-declaring run be authorised. **One escaped first**: the require check was satisfied by the hook's own doc comment, which names the module four times, so it read prose; it now reads the `require` expression | 2026-08-19 | **verified locally · unreleased** |
| 030 | The 15 pre-existing negatives still refuse their plants | every `Negative self-test` step extracted from `validate.yml` and run as a process from the repo root | **23/23 refused.** The eight new ones plus the fifteen SD-01 and SD-02 left, none broken by the edits to `test/validate.py`, `package.json`, `CONTRIBUTING.md`, `SECURITY.md`, `README.md` or the two skill documents | 2026-08-19 | **verified locally · unreleased** |
| 031 | The registration shape is the one Claude Code accepts | `claude plugin validate . --strict`; `claude plugin validate plugins/sheleg-dev --strict`; then two plants into a copy | both **`✔ Validation passed`**. And the validator genuinely reads the file: a truncated `hooks.json` → `Invalid JSON syntax … At runtime this breaks the entire plugin load`; a valid-JSON manifest declaring `NotAnEvent` → `hooks.NotAnEvent: Invalid key in record`. So `PreToolUse` + `matcher` + `command` + `statusMessage` + `timeout` as written are schema-valid, not merely plausible | 2026-08-19 | **verified locally · unreleased** |
| 032 | Nothing about the installers regressed, and the new notice does not break their contracts | the CI installer block run verbatim against `HOME=/tmp/fakehome-sd03` | six skills installed; second run `6` `^skip:` lines; `--force` `6` `^Installed` lines; `--wat` refused; `install.sh` last line still `Installed 6 skill(s). Restart your agent — skills load at session start.` The gate notice prints after the six install lines and matches neither grep | 2026-08-19 | **verified locally · unreleased** |
| 033 | `SECURITY.md`'s moved numbers are computed, not restated | each command in *Verifying for yourself* run from the repo root, verbatim | `git ls-files plugins` → **30** (27 + three gate files); `\| grep -v '.md$'` → **4** lines, the manifest and the three; the `require` grep → **2** lines, both in the hook, `0` in the decision module; the unreachable-API grep → **no output, exit 1**; the installer I/O grep → **11** lines, unchanged; the live-key sweep → **1** line, still the RSA placeholder at `adc-and-service-accounts.md:236`; `npm pack --dry-run` → `total files: 36`. Every key-shaped string in the new fixtures spells `PLACEHOLDER` in its body | 2026-08-19 | **verified locally · unreleased** |

**What is NOT verified in this SD-03 block.**

- **The hook has never fired in a live session.** REQ-027 runs the script as a process and
  REQ-031 proves the manifest is schema-valid, but nothing here observes Claude Code
  spawning it, blocking a `Bash` call on its `deny`, or failing to leak a variable exported
  inside a tool call into the hook's environment. That last assumption is why
  `SHELEG_DEV_LIVE_AUTHORISED` is an environment variable, and the `self-authorisation`
  refusal exists so the gate still holds at the payload layer if the assumption is wrong.
  Filed as **B-92**.
- **No network call was made to any payment or auth provider**, by constraint. Every claim
  about a Stripe or Heleket endpoint shape is a reading of this pack's own references.
- **The gate knows two providers.** `google-auth`, `google-signin` and `ad-tracking` hand
  the reader service-account keys, OAuth client secrets and CAPI tokens and have **no row**
  in `NO_TEST_VARIANT` — so exporting a production service-account key in a test-declaring
  run is not refused. Filed as **B-91**; each row needs the provider's credential model
  established from the documentation first, the way SD-02 did for Heleket.
- **Two bounded gaps in the rules, chosen rather than missed.** A money endpoint on
  `localhost` is allowed (it is the reader's own test server, and refusing it would refuse
  the sad-path testing the pack asks for). And a live-shaped key inside a reading command
  IS refused, including in a `git grep` — deliberate, because a real key in a shell history
  is an incident, and the shape rule is what keeps `SECURITY.md`'s own sweep passing.
- **The copy install channels carry no hook and nothing enforces registering one** (B-90).
  A printed reminder is a warning, which is the thing M-30 calls weaker than a precondition.
  Writing to `~/.claude/settings.json` was not done and must not be.
- **CI has not seen any of this.** Same gap SD-01 and SD-02 recorded: the step-level
  conclusions REQ-002 reads do not exist for the eight new negatives or for the fixtures
  step. The negative count moved from fifteen to **twenty-three** in
  `.github/workflows/validate.yml` and `CONTRIBUTING.md` now says twenty-three.
- **Nothing was released**: no tag, no publish, no version bump.

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
