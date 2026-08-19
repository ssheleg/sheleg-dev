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

Row **SD-04** of the same program, 2026-08-19, requirements **M-29** (a test is stronger than
an instruction — `manifesto.md:200`) and **M-40** (evidence proves no more than it observed —
`:289`, "the one green dashboards routinely lose"). Board rows: `docs/evidence/backlog.md`
B-94 through B-97.

| REQ | Requirement | Verified by | Result | Observed at | Status |
|---|---|---|---|---|---|
| 034 | The defect is what the audit said it was: four money invariants, stated and unproven | `git show 90e9621:` over the two cited files | **all four stated, none tested.** `ad-tracking/SKILL.md:264` ("carry the SAME `event_id` / `transaction_id`, or both are counted"), `:268` ("**A purchase is not a browser event…**"), `stripe-billing/references/webhook-events.md:163` ("`amount_refunded` is **cumulative**"), `:183` ("**Never derive state from arrival order.**"). And the giveaway at `testing-and-local-dev.md:157` — a section titled *Mutation testing — the only proof that counts* whose method was the sentence "For every guard, delete it and re-run", closing at `:172` with "Skip it and you have a green build". No fixture file existed anywhere in the payload | 2026-08-19 | **verified locally · unreleased** |
| 035 | Real provider payloads ship, shaped the way the provider sends them | `ls plugins/sheleg-dev/skills/*/fixtures/*.json`; read each against the pack's own references | **12 payloads**, 9 Stripe event bodies and 3 Meta ones. The Stripe bodies carry the period on the invoice **line** (not the top-level field the reference warns returns `undefined`), the subscription id under `parent.subscription_details` as `references/webhook-events.md:97-108` describes, `amount_refunded` cumulative, minor units throughout, and `billing_reason` on every invoice. The Meta pair is the four `fbq` arguments and the CAPI request body; the third is the body a thank-you-page-sourced emitter produces, kept as the payload that must never exist | 2026-08-19 | **verified locally · unreleased** |
| 036 | The four named invariants each have a fixture, and each fails a wrong handler | `node assert-money-invariants.mjs`; `node assert-dedup-contract.mjs` | **12 + 6 = 18 assertions, both exit 0.** The four the row names: the proration `invoice.paid` (`proration-invoice-grants-nothing`), the duplicate `evt_` (`sequential-redelivery-grants-once` and `concurrent-redelivery-grants-once`), the two-step cumulative refund (`refund-total-is-cumulative`), the out-of-order pair (`out-of-order-pair-does-not-rewind-state`). Plus the ones the references demand and the row did not enumerate: the unpaid async session and its failure, the positive control that keeps a refuse-everything handler from passing it, the reconciliation re-grant, the conversion id read out of subscription metadata, the `event_name` half of the Meta contract, the browser event kept, and hashed identifiers | 2026-08-19 | **verified locally · unreleased** |
| 037 | Every assertion has been watched failing, against a handler with exactly one rule removed | `node assert-money-invariants.mjs --self-test`; the same for the ad-tracking pack | **both exit 0**, printing `12 assertions, each watched failing; 9 rules, each isolated by a fixture` and `6 assertions … 5 rules, each isolated`. The wrong handler is the reference handler with a named rule deleted — `fixtures/README.md` → *What each mutant deletes* shows the code each flag removes. The self-test fails if the measured break set differs from the declared one **in either direction**, so a mutant that stops breaking an assertion and an assertion that starts breaking under an extra rule are both failures | 2026-08-19 | **verified locally · unreleased** |
| 038 | The masking pairs are measured, not assumed — SD-03's lesson applied | the `invariant x mutant` matrix printed by `--self-test` | **two pairs found, both by the tool rather than by inspection, and both changed the design.** (1) *the event claim and the per-period grant marker*: a redelivery judged by the grant count alone is refused by either, so the pack's first version declared `breaks: ['cumulative-refund']` for a fixture that measured **nothing** — `--self-test` printed `no mutant breaks it`. Multi-rule mutants were added, the fixture now declares `claim+grant-marker`, and the claim's real isolator is the **concurrent** delivery (the marker reads before it writes; a read is a round trip) while the marker's is the **reconciliation** entry point, which has no event id. (2) *the claim and the refund compare-and-swap*: `duplicate-refund-claws-back-once` declares `claim+cumulative-refund` for the same reason, and the arithmetic is measured by the two-step pair, whose events carry different ids | 2026-08-19 | **verified locally · unreleased** |
| 039 | A third masking pair was found in ad-tracking and closed by moving the boundary | the same matrix, first run of the ad-tracking pack | **`keep-browser-event` was masking both id rules.** Reading the pixel side out of the same emitter meant deleting the browser event turned `pixel-and-capi-carry-one-event-id` and `pixel-and-capi-carry-one-event-name` red as well, so neither the id rule nor the name rule was proven alone — the matrix said so in the words `no fixture isolates shared-event-id`. Fixed by comparing the server's output against the **shipped fixture** rather than against the emitter's own pixel call: the browser contract is now held at a boundary the server does not control, which is also M-40's preference for evidence further from the component that produced the claim | 2026-08-19 | **verified locally · unreleased** |
| 040 | The fixtures cannot rot: the claim, the fixture and the pointer are checked in both directions | `python3 test/validate.py` | exit **0**, `OK: sheleg-dev structurally valid (16 checks, 6 skill(s), v0.6.0)` — the count moved 15 → 16 with `check_money_fixtures()`. It reads each `fixtures/manifest.json` (the single home, shipped to the reader) and requires: both skills ship a `fixtures/`, the manifest's assertion pack / reference handler / runbook exist, the manifest and the pack declare the **same** invariant ids, every fixture a row names exists and parses, every `*.json` beside the manifest is claimed by a row, every claiming document still carries its recorded phrase **and** names the invariant id **and** names a path under `fixtures/`, every `fixtures/…` token in the skill's markdown resolves, the runbook names every fixture and every invariant, the pack is findable from the skill's own markdown, and `npm test` plus CI both run the suite | 2026-08-19 | **verified locally · unreleased** |
| 041 | The new guard has been watched failing, in both directions the row asked for and three more | five plants into `/tmp` copies, then the gate in each | **all five refused.** A claimed invariant whose fixture is deleted (`manifest.json: refund-total-is-cumulative claims …/charge-refunded-remainder.json, which does not exist`); a fixture no invariant claims (`…/nobody-claims-me.json is claimed by no invariant`); a reference pointing at a fixture that is not there (`webhook-events.md:… points at fixtures/charge-refunded-renamed.json, which is not there`); a claim reworded away from its fixture (`no longer says '**Never derive state from arrival order.**'`); and an assertion neutered so it can no longer fail, which the *fixture suite* rejects rather than the validator. It also refused the **real** state before the pointers were written — the first run of the guard named the orphan `checkout-session-completed-paid.json`, which is why `paid-session-grants-once` exists | 2026-08-19 | **verified locally · unreleased** |
| 042 | `--self-test` can itself fail — the check one level up | `node test/fixtures_test.js` | exit **0**, `13 checks (both packs, both modes, 3 neutered-assertion plants)`. The three plants: the by-count-alone assertion replaced with `assert.ok(true)` (its `breaks` list then measures empty and the pack reports `no mutant breaks it`), the ad-tracking shared-id assertion compared against itself, and the `grant-marker` guard wired in unconditionally so the rule can no longer be removed. Each requires `--self-test` to exit non-zero. Without this, `--self-test` could be a print statement — the defect SD-03 caught when a `require` check turned out to be reading a doc comment | 2026-08-19 | **verified locally · unreleased** |
| 043 | The packs are safe to run: they read the fixtures beside them and nothing else | `grep -rnE` over the four `*.mjs` for network, spawn, write and env access | **no output, grep exits 1.** No `child_process`, no `fetch`, no `http`/`net`/`dns`/`tls` require, no `spawn`, no `execFile`, no `writeFileSync`/`appendFileSync`/`unlinkSync`, and **no `process.env.` read at all**. The only I/O is `readFileSync` of the JSON beside them. Asserted in `test/fixtures_test.js` by name, not just measured once, because a reader is being asked to execute these | 2026-08-19 | **verified locally · unreleased** |
| 044 | No credential, token or real id is anywhere in the payload | the `SECURITY.md` live-key sweep over `plugins`; the per-fixture shape sweep in both the validator and the suite | **1 line, unchanged** — still the RSA placeholder at `google-auth/references/adc-and-service-accounts.md:236`. Every id in the fixtures spells `PLACEHOLDER`; the one 64-hex string is the SHA-256 of `placeholder@example.invalid`, recomputed here; the IP is `203.0.113.10` from the documentation range. Four shapes are refused by name in two places (`sk_/rk_/pk_` live or test, `whsec_`, a PEM header, a Meta `EAA…` token) so a future fixture cannot quietly carry one | 2026-08-19 | **verified locally · unreleased** |
| 045 | The 23 pre-existing negatives still refuse their plants | every `Negative self-test` step extracted from `validate.yml` and run as a process from the repo root | **28/28 refused.** The five new ones plus the twenty-three SD-01, SD-02 and SD-03 left, none broken by the edits to `test/validate.py`, `package.json`, `README.md`, `SECURITY.md`, `CONTRIBUTING.md` or the five skill documents | 2026-08-19 | **verified locally · unreleased** |
| 046 | Nothing about the shipped artifact regressed | `claude plugin validate . --strict` and on the plugin; `audit_skill.py --house` on all six skills; both installers against fake HOMEs | both validations **`✔ Validation passed`**. Five skills `0 GAP, 14 PASS`; `crypto-payments` `1 GAP` on `BODY_HEADROOM` and **pre-existing** (`git diff HEAD` for that directory is empty in this change), filed as B-95. `stripe-billing/SKILL.md` is ~4747 tokens against a 4750 working limit — one token *lower* than before, because the routing row was reworded three characters shorter rather than grown; `ad-tracking/SKILL.md` moved 4643 → 4727. Both installers install six skills, the `fixtures/` directories travel (13 and 7 files), the packs run from the installed copy, the rerun still prints `6` `^skip:` lines and `install.sh`'s last line is unchanged | 2026-08-19 | **verified locally · unreleased** |
| 047 | `SECURITY.md`'s counted numbers were recomputed, and one of its claims was falsified | every command in *Verifying for yourself* run from the repo root, verbatim | `git ls-files plugins` → **50** (30 + 20 fixture files); `\| grep -v '.md$'` → **22**; `npm pack --dry-run` → `total files: 56`. And the sentence *"There is still no runtime code inside the six skills"* became **false** with this change — two skills now ship runnable `.mjs`. It is replaced by a statement of what that code does and by the grep that proves the boundary, rather than deleted | 2026-08-19 | **verified locally · unreleased** |

**What is NOT verified in this SD-04 block.**

- **No network call was made to any payment or auth provider**, by constraint. Every payload
  is shaped from this pack's own references, not from a live Stripe or Meta response, and
  **no fixture was captured from a real account** — which is precisely what
  `references/testing-and-local-dev.md` recommends doing ("run the flow once against test
  mode, copy the event JSON out of the Dashboard"). So the fixtures are faithful to the
  *documented* shapes and unverified against the current API. The pack's largest standing
  exposure, vendor drift, applies to them exactly as it applies to the prose.
- **The reference handler is not the reader's handler.** REQ-036 and REQ-037 measure a
  40-line in-memory model, not a Prisma schema or a Next.js route. What is proven is that the
  *assertions* discriminate; whether they can be pointed at a real handler unchanged is
  claimed in the README and not measured here.
- **A new invariant claimed in a reference with no fixture cannot be caught** (B-96). The
  guard is bounded by the manifest's enumeration, the same way `FOREIGN_BY_DESIGN` is: it
  refuses a *recorded* claim losing its fixture and a fixture losing its claim, and it cannot
  decide that a new paragraph states a fifth money invariant.
- **The two runners are duplicated** (B-97), deliberately — a reader installs one skill — and
  the stripe one has already grown multi-rule mutant support the ad-tracking one lacks.
- **CI has not seen any of this.** Same gap SD-01 through SD-03 recorded: the step-level
  conclusions REQ-002 reads do not exist for the five new negatives or for the fixture-suite
  step. The negative count moved from twenty-three to **twenty-eight** in
  `.github/workflows/validate.yml` and `CONTRIBUTING.md` now says twenty-eight.
- **`crypto-payments` ships no fixtures**, and it is the other skill whose subject is taking
  money. Its own invariants — under-payment, duplicate webhooks, rate drift — are the same
  class and were not in this row's scope. Not filed as a new row: it is the natural next
  step of B-94 rather than a separate defect, and its SKILL.md is over the working limit
  (B-95), so the pointers cannot be written until the split happens.
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
