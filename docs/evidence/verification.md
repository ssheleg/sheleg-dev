# Verification ledger — sheleg-dev

One row per shipped requirement, with the command that confirmed it and what that
command printed. A row sits at `never` until somebody has watched its check pass on the
**shipped** artifact — not on a branch, not in a plan.

This file exists because its absence read as zero exposure. `sshlg-skills` board row
**B-30** measured this repository returning 0 REQ rows and named the reading that
produces: *"an absent ledger and a clean one are indistinguishable from the number
alone."* An empty ledger and a clean one now differ.

**It starts at the shipped state, not at the repository's history.** Nothing here is
back-filled from a CHANGELOG entry, because a claim restated is not a claim verified.

**Two headings move with every release, and now something checks them.** On 2026-08-20 the
shipped block below was headed `v0.6.0` while `v0.7.0` was tagged and on npm, and 37 rows
under it read *verified locally · unreleased* — four of them closing with *"Nothing was
released: no tag, no publish, no version bump."* All four sentences were false the moment
the tag was cut, and nothing connected either heading to the release. `test/validate.py`
now compares the shipped heading against `git describe --tags` **and** against
`package.json`, and compares the verdict REQ-001 quotes against the line the validator
actually prints. Both were watched refusing a plant; see the SD-05 block.

---

## Shipped state — v0.10.1

**The first v0.8.0 tag failed its own release, and this is the record of it.** The notice
`install.sh` gained in this version — that the manual gate does not travel with a skills
copy — prints after the summary line, and the CI step asserted the summary by POSITION
(`bash install.sh | tail -1 | grep -q 'Installed 6 skill'`). So the release run went red on
a step about installers while nothing was wrong with the installers, npm kept serving
0.7.0, and no artifact shipped under the tag. The assertion now reads the whole output and
has a second one requiring the notice, so the new behaviour is covered rather than
tolerated; the tag was re-cut at the fix, which is safe precisely because nothing had been
published under it. Run `32313338558`, step *Installers run*, exit 1.

That is the shape the umbrella's `B-78` is about — *a release was tagged, failed its gate
on one step, and nobody noticed*. It was noticed here in under two minutes because the
release was being watched, which is the only difference.


Released: `@ssheleg/sheleg-dev@0.7.0` (npm), tag `v0.7.0` at `6f66255`.

> **This heading has now been wrong twice.** It said `v0.5.0` while npm served `0.5.2`, and
> it said `v0.6.0` for the whole of v0.7.0's life on npm. A ledger describing an artifact
> nobody ships reads green for a version that no longer exists, which is worse than the
> absence it was created to fix. The third time is a guard rather than a note:
> `check_ledger_names_the_shipped_version` in `test/validate.py`.

CI: `validate` run `32293489020` at `6f66255` — the commit the tag names — →
**39 steps, 39 `success`**, including **28 of 28** negative self-tests. That run is what
makes the rows below shipped rather than local: the whole gate ran against the tagged tree.

Seven skills ship: `ad-tracking`, `crypto-payments`, `error-tracking`,
`frontend-performance`, `google-auth`, `google-signin`, `stripe-billing`.

| REQ | Requirement | Verified by | Result | Status |
|---|---|---|---|---|
| 001 | The structural validator passes on the shipped tree | `python3 test/validate.py` | `OK: sheleg-dev structurally valid (23 checks, 7 skill(s), v0.10.1)` — and the check count is now the length of the registry, so adding a check moves it. It used to be `10 + len(skill_dirs)`: adding a **skill** moved the number and adding a check did not, and four rows of this file read it as evidence that a guard had been added. `check_ledger_quotes_the_validator_verdict` compares this quoted string against the line the run prints, so it cannot drift again | **verified** |
| 002 | Every guard has been watched failing against a planted defect | CI run `32293489020` at `6f66255`, step-level conclusions of every `Negative self-test` step | **28 of 28 `success`**, 39 of 39 steps `success`, 0 failed steps in the run. This retires the *"CI has not seen any of this"* limitation that SD-01 through SD-04 each recorded separately: the four blocks below all ran in that one run, against the tagged tree | **verified** |
| 003 | Version is synchronised across every surface | read back from `package.json`, `.claude-plugin/marketplace.json`, `plugins/sheleg-dev/.claude-plugin/plugin.json`, the top `## vX.Y.Z` in `CHANGELOG.md` | all four → `0.7.0` | **verified** |
| 056 | `error-tracking` meets the Agent Skills standard and the house canon | `python3 audit_skill.py plugins/sheleg-dev/skills/error-tracking --house` (make-skill 0.23.0) | `0 GAP, 14 PASS` — description 943/970 chars, body 242 lines / ~2777 tokens against a 500/4750 working limit, every relative link resolves | **verified** |
| 057 | The skill's central claim is a measurement, not a recollection | `python3 -c "from sentry_sdk.scrubber import EventScrubber; e={'message':'postgresql://u:SUPERSECRET@h/db'}; EventScrubber().scrub_event(e); print('SUPERSECRET' in str(e))"` on `sentry-sdk` 2.19.2 | `True` — the default scrubber matches key names and does not inspect string values, so a credential inside a URL survives it. `dsn` and `database_url` are absent from the 32-entry default denylist | **verified** |
| 058 | The 403 the skill documents is an org policy, not an auth failure | `sentry project create sshlg/tg-boutique-bot:python --team sshlg`; `sentry api "/" --json`; `sentry org view sshlg --json` | `Your organization has disabled this feature for members.` with the caller holding `orgRole: owner` and a token carrying `project:admin`/`team:write` but no `org:write`; `allowMemberProjectCreation: false`. `POST /teams/sshlg/sshlg/projects/` fails identically | **verified** |
| 059 | The Sentry MCP is OAuth, so it belongs in an agent config rather than a shared gateway | `curl -si https://mcp.sentry.dev/mcp \| grep -i www-authenticate` | `401` carrying `www-authenticate: Bearer realm="OAuth", …, resource_metadata="https://mcp.sentry.dev/.well-known/oauth-protected-resource/mcp"` — the documented test for OAuth on this machine | **verified** |
| 060 | Every reference file is linked, and every link resolves | the bidirectional check in `test/validate.py` | three references, three links, no orphan and no dangling | **verified** |
| 061 | The skill's Heroku release guidance survives contact with Heroku | `heroku labs -a tg-boutique-bot`; `heroku config:get HEROKU_SLUG_COMMIT`; `heroku run -- printenv HEROKU_SLUG_COMMIT` | `runtime-dyno-metadata` was OFF, so `config.RELEASE` was `None` while Sentry held a release with a deploy — the drift the skill warns about, produced by following the skill. `config:get` prints nothing even when it works; enabling takes effect on the next release, not a restart. `references/releases.md` now names all three | **verified** |
| 062 | A production event arrives scrubbed | a deliberate exception carrying `postgresql://fakeuser:VERIFY_SCRUBBER_0000@fake.rds.amazonaws.com/fakedb`, sent from the production dyno, then read back from Sentry | stored as `postgresql://fakeuser:<redacted>@fake.rds.amazonaws.com:5432/fakedb` — password absent, host and user kept so the event stays debuggable | **verified** |
| 004 | A release cannot publish over a red suite | `grep -c workflow_call .github/workflows/validate.yml`; `grep -n` in `release.yml` | `workflow_call` 2; `uses: ./.github/workflows/validate.yml` at line 29, `needs: validate` at line 32. This is the repository where the failure was observed: v0.4.1 was tagged while its own validate run for that tag failed, and npm served it four minutes later | **verified** |
| 005 | Every reference a skill links resolves, and none is orphaned | walk each `SKILL.md` for `](references/…)` and each `references/*.md` for a mention | **0 unresolved, 0 orphans** across all seven skills; the count moved with `references/provider-concentration.md`, which the check requires to be linked **and** the link to resolve | **verified** |
| 006 | The installer installs every skill into a fresh HOME | `HOME=/tmp/fakehome-local node bin/sheleg-dev.js`, then list `$HOME/.claude/skills/` | seven directories: `ad-tracking crypto-payments error-tracking frontend-performance google-auth google-signin stripe-billing`. The roster is derived from `plugins/sheleg-dev/skills` on both sides now — the CI step named six skills and asserted the number four times, so a seventh broke it, the second release this file failed for a hand-written count | **verified** |
| 007 | A second run skips rather than re-writing | re-run the installer against the same HOME and count `^skip:` | `6` — one per skill, none re-installed | **verified** |
| 008 | Both workflows are parseable by the parser GitHub uses | `yaml.safe_load` over `validate.yml` and `release.yml` | both parse | **verified** |
| 009 | npm serves exactly the version this tree claims | `npm view @ssheleg/sheleg-dev version` | `0.7.0` | **verified** |
| 010 | The tag exists at the released version | `git tag --sort=-v:refname \| head -3`; `git cat-file -t v0.7.0`; `git log -1 --format=%H v0.7.0` | `v0.7.0 v0.6.0 v0.5.2` — newest tag matches, at `6f66255a5ad7ed3df9b2e915f00ef0b1e0a1c2e7`. **But `git cat-file -t v0.7.0` prints `commit`, not `tag`: v0.7.0 is LIGHTWEIGHT where v0.6.0 was annotated.** REQ-010 stated the annotation as a property at v0.6.0 and nothing enforced it, so the property was lost at the next release without anything going red. Filed as **B-98** — the fix is a retag, which is a push and belongs to whoever releases | **verified, with a regression named** |

## Shipped in v0.7.0 — rows SD-01 through SD-04

Four blocks of the cross-repository manifesto-conformance program, written 2026-08-19 and
**released as v0.7.0 the same day**. Until 2026-08-20 they sat under a heading reading
*"Unreleased — verified locally, not yet shipped"* and every row read
*verified locally · unreleased*, while npm served `0.7.0` and the tag existed — so the
ledger described a state the repository had left.

What makes them shipped, stated once rather than per row: **CI run `32293489020` at
`6f66255`, the commit the tag `v0.7.0` names, ran 39 steps and all 39 succeeded**,
including the 28 negative self-tests these blocks added. `npm view` returns `0.7.0`.

**What that run does not cover, named rather than implied.** Some rows below rest on a
reading of a document or a one-off script rather than on a gate step — **016, 017, 018,
022, 023, 026, 034, 035** and the `audit_skill.py` half of **046**. Nothing re-runs those;
they are shipped and unrepeatable, and a row that reads `verified` on that basis is
claiming a measurement was made, not that it is still being made.

Row **SD-01** of the cross-repository manifesto-conformance program, 2026-08-19,
requirements **M-44** (one authoritative home; references resolve) and **M-07** (a claim
points to an address another actor can resolve). Board rows: `docs/evidence/backlog.md`
B-79 through B-84.

| REQ | Requirement | Verified by | Result | Observed at | Status |
|---|---|---|---|---|---|
| 011 | `SECURITY.md` describes THIS pack, and every path it names exists here | `python3 test/validate.py` | `OK: sheleg-dev structurally valid (13 checks, 6 skill(s), v0.6.0)`, exit 0. The six dead references the audit cited — `SECURITY.md:10,11,17,35,54,56` of the old file — are gone; the document now names 29 path tokens and all 29 resolve | 2026-08-19 | **verified · v0.7.0** |
| 012 | Every command in *Verifying for yourself* runs, and prints what the document claims | each command run from the repo root, verbatim | `python3 test/validate.py` → 0; `git ls-files plugins \| wc -l` → `27`; `git ls-files plugins \| grep -v '.md$'` → 1 line, the plugin manifest; the installer I/O grep → `11` lines; the live-key grep → `1` line, the RSA placeholder; `npm pack --dry-run` → `total files: 33`. The old block's second and third commands exited 2 | 2026-08-19 | **verified · v0.7.0** |
| 013 | The guard refuses a recurrence, and has been watched doing it | three plants into `/tmp` copies, then `python3 test/validate.py` in each | all three refused with exit 1: a dead path (`SECURITY.md:58 names 'scripts/page_audit.py', which this repository has nowhere`), a citation past the end of a file (`cites install.sh:9001, but that file has 32 lines`), and a stale exemption (`FOREIGN_BY_DESIGN carries 'benchmarks.md' … but the document no longer names it`). It also refused the **real** defect before anything was fixed — 8 failures, the audit's 6 plus 2 it found itself | 2026-08-19 | **verified · v0.7.0** |
| 014 | The guard is bounded, not blanket — no false positive on the current tree | count the tokens it inspects and the exemptions it uses | 67 path tokens across the four self-describing documents, 10 of them `file:line` citations, 0 failures; 5 `FOREIGN_BY_DESIGN` entries and every one still matched by its document. The 41 reader-project paths inside the skill payload (`next.config.ts`, `src/lib/heleket.ts`, `web/auth.py`) are outside the corpus by design — board B-82 | 2026-08-19 | **verified · v0.7.0** |
| 015 | The two dead references in `.github/PULL_REQUEST_TEMPLATE.md` are gone | `python3 test/validate.py`; read the file | the evidence block is one command, `python3 test/validate.py`; the `cursor/rules/*.mdc` checklist item is replaced by the `references/` ↔ `SKILL.md` rule the validator actually enforces | 2026-08-19 | **verified · v0.7.0** |

**What is NOT verified in this block.** ~~The three new negative self-tests have not been
run by CI.~~ **Retired 2026-08-20:** CI run `32293489020` at `6f66255` ran all 28 as steps
and all 28 succeeded, so the step-level conclusions REQ-002 reads now exist for them.
~~Nothing here was released.~~ It shipped as v0.7.0.

Row **SD-02** of the same program, 2026-08-19, requirement **M-06** (a credential that
cannot reach production is stronger than a sentence saying not to use it there, because
the last control still works after context loss). Board rows: `docs/evidence/backlog.md`
B-85 through B-87.

| REQ | Requirement | Verified by | Result | Observed at | Status |
|---|---|---|---|---|---|
| 016 | The provider's real credential model is established from the document, not assumed | read `references/heleket-provider.md` §1, §3, §7, §15 | **Heleket offers no separate test credential.** One key per merchant (`:62`), which is *also* the webhook signing secret (`:126`); one host, `api.heleket.com` (`:60`, `:376`); no environment marker in the key, so the Stripe-style prefix read is unavailable; "test mode" is a toggle in merchant settings (`:1155`), a property of the **account** over the same key. The brief's imagined fix — assert the key's declared environment against the key itself — was therefore not buildable as written | 2026-08-19 | **verified · v0.7.0** |
| 017 | The boundary is built on what the provider actually exposes | read the shipped `assertHeleketEnv()` | it compares the declared `HELEKET_ENV` against the two **non-secret** discriminators Heleket does give: the merchant UUID pinned as `HELEKET_LIVE_MERCHANT_ID`, and a 12-hex SHA-256 prefix of the live key as `HELEKET_LIVE_KEY_FINGERPRINT`. Same shape as the house pattern at `plugins/sheleg-dev/skills/stripe-billing/references/price-integrity.md:62-64` — a declaration separate from the secret — with a different comparand because the key carries no mode | 2026-08-19 | **verified · v0.7.0** |
| 018 | Both mismatches are refused, and the logic has been run | the shipped snippet transliterated to JS with types stripped, control flow unchanged, driven over 11 cases | **11/11.** A live credential declared test is refused by UUID *and* by fingerprint alone (`HELEKET_ENV_TEST_HOLDS_LIVE_CREDENTIAL`); a test credential declared live is refused (`HELEKET_ENV_LIVE_HOLDS_TEST_CREDENTIAL`); unset refuses rather than defaults; an unpinned *test* run refuses because it cannot prove it is not live; `SKIP_BILLING=true` with `HELEKET_ENV=production` refuses; and the two correct configurations pass — a boundary that refuses everything is switched off within a day | 2026-08-19 | **verified · v0.7.0** |
| 019 | The control is a snippet and a check, not a paragraph | `python3 test/validate.py`; `npm test` | both exit **0**, `OK: sheleg-dev structurally valid (14 checks, 6 skill(s), v0.6.0)` — the count moved 13 → 14 with `check_credential_boundary()`, which requires that every copyable block assigning `HELEKET_API_KEY` also assigns `HELEKET_ENV`, that `assertHeleketEnv` exists to be copied, that both refusal codes are present, and that the residual exposure is written down | 2026-08-19 | **verified · v0.7.0** |
| 020 | The new guard has been watched failing, in both directions and on the original defect | three plants into `/tmp` copies, then `python3 test/validate.py` in each | all three refused with exit 1: the live-declared-test code renamed (`the boot assertion cannot refuse HELEKET_ENV_TEST_HOLDS_LIVE_CREDENTIAL`), the test-declared-live code renamed (`… HELEKET_ENV_LIVE_HOLDS_TEST_CREDENTIAL`), and the environment deleted from the Option B block (`heleket-provider.md:1362 — a copyable block sets HELEKET_API_KEY without HELEKET_ENV`). It also refused the **real** defect before anything was fixed: 6 failures on the unmodified tree, naming both credential-handover blocks at `:135` and `:1137` | 2026-08-19 | **verified · v0.7.0** |
| 021 | The twelve pre-existing negatives still refuse their plants | every `Negative self-test` step extracted from `validate.yml` and run as a process from the repo root | **15/15 refused.** The three new ones plus the twelve SD-01 left, none broken by edits to `test/validate.py` or `crypto-payments/SKILL.md` | 2026-08-19 | **verified · v0.7.0** |
| 022 | The new cross-references resolve | slugify every heading, then resolve every in-page and relative link in the two edited files | **0 broken** — 15 in-page links against 17 headings in `SKILL.md`, 27 against 37 in `heleket-provider.md`, and both relative links, including the new one to `stripe-billing/references/price-integrity.md` | 2026-08-19 | **verified · v0.7.0** |

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
- ~~**CI has not seen the three new negatives.**~~ **Retired 2026-08-20** by CI run
  `32293489020` at `6f66255`: 28 of 28 negative self-tests `success`, 39 of 39 steps
  `success`. The gap SD-01 opened and SD-02, SD-03 and SD-04 each re-recorded was one gap
  recorded four times, and one run closed all four.
- **`stripe-billing` is untouched and still has the same defect** (B-86), and the other three
  credential-holding skills were not looked at (B-87). Enforcing `CREDENTIAL_BOUNDARIES`
  over `stripe-billing` in this change would have turned the gate red for work this row did
  not do.
- **The reference this row grew is a size outlier** — 1696 lines / ~18.8k tokens against a
  next-largest reference of ~4.8k. `audit_skill.py` returns `0 GAP` and the 5000-token budget
  is a `SKILL.md` rule, so nothing is violated; it is filed as B-88 rather than left as an
  unmeasured consequence, and the fix is a split rather than a trim.
- ~~**Nothing was released**: no tag, no publish, no version bump.~~ **False from
  2026-08-19 21:31 onward**, and it stayed in this file for a day: it shipped as v0.7.0,
  tag `6f66255`, npm `0.7.0`. A sentence about the absence of a release has a shelf life of
  hours, and nothing here measured it — which is the whole reason
  `check_ledger_names_the_shipped_version` exists.

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
| 023 | The defect is what the audit said it was, and the pack shipped no gate of any kind | `git ls-tree -r --name-only 00285e7 plugins` | **27 files, 26 markdown and one manifest — no `hooks/`, no `hooks.json`, no permission list.** The two prose sites were `crypto-payments/SKILL.md:310` ("Never auto-refund from the webhook. Route holds and refunds to a queue a human can see") and `stripe-billing/references/webhook-events.md:170` ("route it to a human — evidence has a deadline"). SD-02's `assertHeleketEnv()` was the one real control and it runs inside the reader's application, so a shell that merely exports the live merchant credential never reaches it | 2026-08-19 | **verified · v0.7.0** |
| 024 | The gate refuses everything the row requires, and each refusal has been watched | `node test/moneygate_test.js` | **65 fixtures, exit 0** — 27 deny-plants, 25 allow-plants and 13 direct checks of the lexer, the environment reading and the category table. The deny-plants cover all eight categories: a live-shaped `sk_live_`/`rk_live_` key (three shapes, including inside `bash -c '…'`), `HELEKET_API_KEY` exported in a test-declaring run / with nothing declared / through `env(1)` / in a heredoc fed to `bash`, `stripe refunds create` (bare, quoted, via `npx`), a `…/v1/refunds` POST, `stripe payouts create`, `stripe transfers create`, a Heleket `…/v1/payout` POST, `stripe disputes close`, a `…/v1/disputes/…/close` POST, the `create_refund` MCP tool by name, `--live`, `--live-mode`, a command setting the gate's own switch, and `SKIP_BILLING=true` in production | 2026-08-19 | **verified · v0.7.0** |
| 025 | It does NOT refuse correct input — the direction that decides whether it stays switched on | same command; the allow-plants | **25 allow-plants, all allowed.** Every one is a command this repository or its readers actually run: `SECURITY.md:155`'s own sweep for `sk_live_[A-Za-z0-9]` verbatim; reading and grepping the two references that quote `sk_live_…`; a secret scanner given the bare prefix as its pattern; a `.env` heredoc fed to `cat`; a refund line inside a heredoc fed to `python3`; two whole-line comments; a bare `/v1/refunds` path in a grep and in a route-audit script; `HELEKET_API_KEY=` as an argument to grep; `echo --live`; `stripe refunds list`; the non-secret `HELEKET_LIVE_MERCHANT_ID` pin `assertHeleketEnv()` *requires* in a test run; a `sk_test_` key; `SKIP_BILLING=true` in development; a `Write` tool whose content is a live-shaped key; and an authorised refund in a production-declaring run, because a gate that cannot be passed is a gate that gets removed | 2026-08-19 | **verified · v0.7.0** |
| 026 | The fixtures can actually see a broken gate — they were mutation-tested | ten targeted mutations of `hooks/lib/moneygate.js`, `node test/moneygate_test.js` in each | **10/10 caught, after two rounds.** The first round caught 8: narrowing `LIVE_KEY` to the bare prefix and deleting the reader denylist both passed, because every prefix allow-plant was leaning on the denylist while every reader allow-plant was leaning on the key's shape — **two overlapping mechanisms, neither individually proven.** Three fixtures were added to isolate them (a non-reader scanner given the prefix; a reader given a full endpoint URL; a non-reader given a bare path) and all ten mutations then failed the suite | 2026-08-19 | **verified · v0.7.0** |
| 027 | The hook is a byte-mover, fails silent, and exits 0 on every path | five payload shapes driven through `plugins/sheleg-dev/hooks/money-gate.js` as a real process | **exit 0 in all five.** A refund payload → one JSON line, `permissionDecision: "deny"`, the reason naming `refunds create`; an ordinary `npm test` payload → empty stdout; garbage stdin → empty stdout **and empty stderr**; empty stdin → nothing; a payload with no `tool_input` → nothing. `node --check` passes on both files. The decision module `require`s nothing at all and the hook `require`s `path` plus the module — measured, and `child_process`, `fetch`, `http`, `fs`, `spawn`, `writeFile` return **no lines** across both | 2026-08-19 | **verified · v0.7.0** |
| 028 | The three umbrella invariants are enforced by the gate rather than by intention | `python3 test/validate.py`; `npm test` | both exit **0**, `OK: sheleg-dev structurally valid (15 checks, 6 skill(s), v0.6.0)` — the count moved 14 → 15 with `check_manual_gate()`, which requires a `PreToolUse` entry running `money-gate.js`, a `Bash` matcher, **no `if` key anywhere in the manifest**, the `require` of the pure module, a `catch` and a `process.exit(0)`, every category present in both module and fixtures, allow-plants at least half the deny-plants, `npm test` and CI both running the fixtures, and the two prose sites naming the mechanism | 2026-08-19 | **verified · v0.7.0** |
| 029 | The new guard has been watched failing, in eight ways | eight plants into `/tmp` copies, then the gate in each | **all eight refused.** Five against the shipped shape — the hook moved to `PostToolUse` ("a gate that can only report after the money moved"), an `if` filter reintroduced, the `require` renamed, `process.exit(0)` removed, the allow-plants deleted — and three against the decision module, which require the *fixtures* to go red: `LIVE_KEY` narrowed to the prefix, the heredoc rule inverted, and `allowedFor` letting a test-declaring run be authorised. **One escaped first**: the require check was satisfied by the hook's own doc comment, which names the module four times, so it read prose; it now reads the `require` expression | 2026-08-19 | **verified · v0.7.0** |
| 030 | The 15 pre-existing negatives still refuse their plants | every `Negative self-test` step extracted from `validate.yml` and run as a process from the repo root | **23/23 refused.** The eight new ones plus the fifteen SD-01 and SD-02 left, none broken by the edits to `test/validate.py`, `package.json`, `CONTRIBUTING.md`, `SECURITY.md`, `README.md` or the two skill documents | 2026-08-19 | **verified · v0.7.0** |
| 031 | The registration shape is the one Claude Code accepts | `claude plugin validate . --strict`; `claude plugin validate plugins/sheleg-dev --strict`; then two plants into a copy | both **`✔ Validation passed`**. And the validator genuinely reads the file: a truncated `hooks.json` → `Invalid JSON syntax … At runtime this breaks the entire plugin load`; a valid-JSON manifest declaring `NotAnEvent` → `hooks.NotAnEvent: Invalid key in record`. So `PreToolUse` + `matcher` + `command` + `statusMessage` + `timeout` as written are schema-valid, not merely plausible | 2026-08-19 | **verified · v0.7.0** |
| 032 | Nothing about the installers regressed, and the new notice does not break their contracts | the CI installer block run verbatim against `HOME=/tmp/fakehome-sd03` | six skills installed; second run `6` `^skip:` lines; `--force` `6` `^Installed` lines; `--wat` refused; `install.sh` last line still `Installed 6 skill(s). Restart your agent — skills load at session start.` The gate notice prints after the six install lines and matches neither grep | 2026-08-19 | **verified · v0.7.0** |
| 033 | `SECURITY.md`'s moved numbers are computed, not restated | each command in *Verifying for yourself* run from the repo root, verbatim | `git ls-files plugins` → **30** (27 + three gate files); `\| grep -v '.md$'` → **4** lines, the manifest and the three; the `require` grep → **2** lines, both in the hook, `0` in the decision module; the unreachable-API grep → **no output, exit 1**; the installer I/O grep → **11** lines, unchanged; the live-key sweep → **1** line, still the RSA placeholder at `adc-and-service-accounts.md:236`; `npm pack --dry-run` → `total files: 36`. Every key-shaped string in the new fixtures spells `PLACEHOLDER` in its body | 2026-08-19 | **verified · v0.7.0** |

**What is NOT verified in this SD-03 block.**

- ~~**The hook has never fired in a live session.**~~ **Two of the three claims closed
  2026-08-20.** In a live Claude Code session with the plugin enabled the hook fired twice
  and both times the tool call was refused, not merely reported: once on a command carrying
  a live-key shape, and once on a command exporting `SHELEG_DEV_LIVE_AUTHORISED` — the
  `self-authorisation` category, which is the one refusal that can never be authorised. So
  a plugin `PreToolUse` hook does fire on `Bash` when the plugin is enabled, and a `deny`
  decision does block the tool. **The residual is that nothing recorded either firing**: the
  observation is a session transcript, not an artifact, and B-92 stays open for that reason
  alone. The third claim — that a variable exported *inside* a tool call cannot reach the
  hook's environment — is untested still, and the `self-authorisation` refusal exists so the
  gate holds at the payload layer if it is wrong.
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
- ~~**CI has not seen any of this.**~~ **Retired 2026-08-20** by CI run `32293489020` —
  the eight negatives this block added and the gate-fixture step all ran and succeeded.
- ~~**Nothing was released**: no tag, no publish, no version bump.~~ **False from
  2026-08-19 21:31 onward**, and it stayed in this file for a day: it shipped as v0.7.0,
  tag `6f66255`, npm `0.7.0`. A sentence about the absence of a release has a shelf life of
  hours, and nothing here measured it — which is the whole reason
  `check_ledger_names_the_shipped_version` exists.

Row **SD-04** of the same program, 2026-08-19, requirements **M-29** (a test is stronger than
an instruction — `manifesto.md:200`) and **M-40** (evidence proves no more than it observed —
`:289`, "the one green dashboards routinely lose"). Board rows: `docs/evidence/backlog.md`
B-94 through B-97.

| REQ | Requirement | Verified by | Result | Observed at | Status |
|---|---|---|---|---|---|
| 034 | The defect is what the audit said it was: four money invariants, stated and unproven | `git show 90e9621:` over the two cited files | **all four stated, none tested.** `ad-tracking/SKILL.md:264` ("carry the SAME `event_id` / `transaction_id`, or both are counted"), `:268` ("**A purchase is not a browser event…**"), `stripe-billing/references/webhook-events.md:163` ("`amount_refunded` is **cumulative**"), `:183` ("**Never derive state from arrival order.**"). And the giveaway at `testing-and-local-dev.md:157` — a section titled *Mutation testing — the only proof that counts* whose method was the sentence "For every guard, delete it and re-run", closing at `:172` with "Skip it and you have a green build". No fixture file existed anywhere in the payload | 2026-08-19 | **verified · v0.7.0** |
| 035 | Real provider payloads ship, shaped the way the provider sends them | `ls plugins/sheleg-dev/skills/*/fixtures/*.json`; read each against the pack's own references | **12 payloads**, 9 Stripe event bodies and 3 Meta ones. The Stripe bodies carry the period on the invoice **line** (not the top-level field the reference warns returns `undefined`), the subscription id under `parent.subscription_details` as `references/webhook-events.md:97-108` describes, `amount_refunded` cumulative, minor units throughout, and `billing_reason` on every invoice. The Meta pair is the four `fbq` arguments and the CAPI request body; the third is the body a thank-you-page-sourced emitter produces, kept as the payload that must never exist | 2026-08-19 | **verified · v0.7.0** |
| 036 | The four named invariants each have a fixture, and each fails a wrong handler | `node assert-money-invariants.mjs`; `node assert-dedup-contract.mjs` | **12 + 6 = 18 assertions, both exit 0.** The four the row names: the proration `invoice.paid` (`proration-invoice-grants-nothing`), the duplicate `evt_` (`sequential-redelivery-grants-once` and `concurrent-redelivery-grants-once`), the two-step cumulative refund (`refund-total-is-cumulative`), the out-of-order pair (`out-of-order-pair-does-not-rewind-state`). Plus the ones the references demand and the row did not enumerate: the unpaid async session and its failure, the positive control that keeps a refuse-everything handler from passing it, the reconciliation re-grant, the conversion id read out of subscription metadata, the `event_name` half of the Meta contract, the browser event kept, and hashed identifiers | 2026-08-19 | **verified · v0.7.0** |
| 037 | Every assertion has been watched failing, against a handler with exactly one rule removed | `node assert-money-invariants.mjs --self-test`; the same for the ad-tracking pack | **both exit 0**, printing `12 assertions, each watched failing; 9 rules, each isolated by a fixture` and `6 assertions … 5 rules, each isolated`. The wrong handler is the reference handler with a named rule deleted — `fixtures/README.md` → *What each mutant deletes* shows the code each flag removes. The self-test fails if the measured break set differs from the declared one **in either direction**, so a mutant that stops breaking an assertion and an assertion that starts breaking under an extra rule are both failures | 2026-08-19 | **verified · v0.7.0** |
| 038 | The masking pairs are measured, not assumed — SD-03's lesson applied | the `invariant x mutant` matrix printed by `--self-test` | **two pairs found, both by the tool rather than by inspection, and both changed the design.** (1) *the event claim and the per-period grant marker*: a redelivery judged by the grant count alone is refused by either, so the pack's first version declared `breaks: ['cumulative-refund']` for a fixture that measured **nothing** — `--self-test` printed `no mutant breaks it`. Multi-rule mutants were added, the fixture now declares `claim+grant-marker`, and the claim's real isolator is the **concurrent** delivery (the marker reads before it writes; a read is a round trip) while the marker's is the **reconciliation** entry point, which has no event id. (2) *the claim and the refund compare-and-swap*: `duplicate-refund-claws-back-once` declares `claim+cumulative-refund` for the same reason, and the arithmetic is measured by the two-step pair, whose events carry different ids | 2026-08-19 | **verified · v0.7.0** |
| 039 | A third masking pair was found in ad-tracking and closed by moving the boundary | the same matrix, first run of the ad-tracking pack | **`keep-browser-event` was masking both id rules.** Reading the pixel side out of the same emitter meant deleting the browser event turned `pixel-and-capi-carry-one-event-id` and `pixel-and-capi-carry-one-event-name` red as well, so neither the id rule nor the name rule was proven alone — the matrix said so in the words `no fixture isolates shared-event-id`. Fixed by comparing the server's output against the **shipped fixture** rather than against the emitter's own pixel call: the browser contract is now held at a boundary the server does not control, which is also M-40's preference for evidence further from the component that produced the claim | 2026-08-19 | **verified · v0.7.0** |
| 040 | The fixtures cannot rot: the claim, the fixture and the pointer are checked in both directions | `python3 test/validate.py` | exit **0**, `OK: sheleg-dev structurally valid (16 checks, 6 skill(s), v0.6.0)` — the count moved 15 → 16 with `check_money_fixtures()`. It reads each `fixtures/manifest.json` (the single home, shipped to the reader) and requires: both skills ship a `fixtures/`, the manifest's assertion pack / reference handler / runbook exist, the manifest and the pack declare the **same** invariant ids, every fixture a row names exists and parses, every `*.json` beside the manifest is claimed by a row, every claiming document still carries its recorded phrase **and** names the invariant id **and** names a path under `fixtures/`, every `fixtures/…` token in the skill's markdown resolves, the runbook names every fixture and every invariant, the pack is findable from the skill's own markdown, and `npm test` plus CI both run the suite | 2026-08-19 | **verified · v0.7.0** |
| 041 | The new guard has been watched failing, in both directions the row asked for and three more | five plants into `/tmp` copies, then the gate in each | **all five refused.** A claimed invariant whose fixture is deleted (`manifest.json: refund-total-is-cumulative claims …/charge-refunded-remainder.json, which does not exist`); a fixture no invariant claims (`…/nobody-claims-me.json is claimed by no invariant`); a reference pointing at a fixture that is not there (`webhook-events.md:… points at fixtures/charge-refunded-renamed.json, which is not there`); a claim reworded away from its fixture (`no longer says '**Never derive state from arrival order.**'`); and an assertion neutered so it can no longer fail, which the *fixture suite* rejects rather than the validator. It also refused the **real** state before the pointers were written — the first run of the guard named the orphan `checkout-session-completed-paid.json`, which is why `paid-session-grants-once` exists | 2026-08-19 | **verified · v0.7.0** |
| 042 | `--self-test` can itself fail — the check one level up | `node test/fixtures_test.js` | exit **0**, `13 checks (both packs, both modes, 3 neutered-assertion plants)`. The three plants: the by-count-alone assertion replaced with `assert.ok(true)` (its `breaks` list then measures empty and the pack reports `no mutant breaks it`), the ad-tracking shared-id assertion compared against itself, and the `grant-marker` guard wired in unconditionally so the rule can no longer be removed. Each requires `--self-test` to exit non-zero. Without this, `--self-test` could be a print statement — the defect SD-03 caught when a `require` check turned out to be reading a doc comment | 2026-08-19 | **verified · v0.7.0** |
| 043 | The packs are safe to run: they read the fixtures beside them and nothing else | `grep -rnE` over the four `*.mjs` for network, spawn, write and env access | **no output, grep exits 1.** No `child_process`, no `fetch`, no `http`/`net`/`dns`/`tls` require, no `spawn`, no `execFile`, no `writeFileSync`/`appendFileSync`/`unlinkSync`, and **no `process.env.` read at all**. The only I/O is `readFileSync` of the JSON beside them. Asserted in `test/fixtures_test.js` by name, not just measured once, because a reader is being asked to execute these | 2026-08-19 | **verified · v0.7.0** |
| 044 | No credential, token or real id is anywhere in the payload | the `SECURITY.md` live-key sweep over `plugins`; the per-fixture shape sweep in both the validator and the suite | **1 line, unchanged** — still the RSA placeholder at `google-auth/references/adc-and-service-accounts.md:236`. Every id in the fixtures spells `PLACEHOLDER`; the one 64-hex string is the SHA-256 of `placeholder@example.invalid`, recomputed here; the IP is `203.0.113.10` from the documentation range. Four shapes are refused by name in two places (`sk_/rk_/pk_` live or test, `whsec_`, a PEM header, a Meta `EAA…` token) so a future fixture cannot quietly carry one | 2026-08-19 | **verified · v0.7.0** |
| 045 | The 23 pre-existing negatives still refuse their plants | every `Negative self-test` step extracted from `validate.yml` and run as a process from the repo root | **28/28 refused.** The five new ones plus the twenty-three SD-01, SD-02 and SD-03 left, none broken by the edits to `test/validate.py`, `package.json`, `README.md`, `SECURITY.md`, `CONTRIBUTING.md` or the five skill documents | 2026-08-19 | **verified · v0.7.0** |
| 046 | Nothing about the shipped artifact regressed | `claude plugin validate . --strict` and on the plugin; `audit_skill.py --house` on all six skills; both installers against fake HOMEs | both validations **`✔ Validation passed`**. Five skills `0 GAP, 14 PASS`; `crypto-payments` `1 GAP` on `BODY_HEADROOM` and **pre-existing** (`git diff HEAD` for that directory is empty in this change), filed as B-95. `stripe-billing/SKILL.md` is ~4747 tokens against a 4750 working limit — one token *lower* than before, because the routing row was reworded three characters shorter rather than grown; `ad-tracking/SKILL.md` moved 4643 → 4727. Both installers install six skills, the `fixtures/` directories travel (13 and 7 files), the packs run from the installed copy, the rerun still prints `6` `^skip:` lines and `install.sh`'s last line is unchanged | 2026-08-19 | **verified · v0.7.0** |
| 047 | `SECURITY.md`'s counted numbers were recomputed, and one of its claims was falsified | every command in *Verifying for yourself* run from the repo root, verbatim | `git ls-files plugins` → **50** (30 + 20 fixture files); `\| grep -v '.md$'` → **22**; `npm pack --dry-run` → `total files: 56`. And the sentence *"There is still no runtime code inside the six skills"* became **false** with this change — two skills now ship runnable `.mjs`. It is replaced by a statement of what that code does and by the grep that proves the boundary, rather than deleted | 2026-08-19 | **verified · v0.7.0** |

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
- ~~**CI has not seen any of this.**~~ **Retired 2026-08-20** by CI run `32293489020` —
  the five negatives this block added and the fixture-suite step all ran and succeeded.
- **`crypto-payments` ships no fixtures**, and it is the other skill whose subject is taking
  money. Its own invariants — under-payment, duplicate webhooks, rate drift — are the same
  class and were not in this row's scope. Not filed as a new row: it is the natural next
  step of B-94 rather than a separate defect, and its SKILL.md is over the working limit
  (B-95), so the pointers cannot be written until the split happens.
- ~~**Nothing was released**: no tag, no publish, no version bump.~~ **False from
  2026-08-19 21:31 onward**, and it stayed in this file for a day: it shipped as v0.7.0,
  tag `6f66255`, npm `0.7.0`. A sentence about the absence of a release has a shelf life of
  hours, and nothing here measured it — which is the whole reason
  `check_ledger_names_the_shipped_version` exists.

## Unreleased — verified locally, not yet shipped

Row **SD-05**, 2026-08-20. Not a manifesto-program row: a defect sweep over what the four
program rows left, starting from the one that mattered most — **the money-invariant
self-test was measuring break/no-break per INVARIANT while claiming it per ASSERTION.**
Board rows: `docs/evidence/backlog.md` B-84, B-86, B-90, B-92, B-93, B-95, B-98, B-99.

| REQ | Requirement | Verified by | Result | Observed at | Status |
|---|---|---|---|---|---|
| 048 | The headline defect is what it was measured to be | the shipped v0.7.0 pack, restored from `git show HEAD:…`, with three assertions replaced by `assert.ok(true)` | **`--self-test` exit 0**, printing `OK: 12 assertions, each watched failing; 9 rules, each isolated by a fixture`, and `node assert-money-invariants.mjs` exit 0 with it. The three: the `clawbacks.map` deepEqual, the `mirror.periodEnd` equality, and the `response.body` deepEqual. The cause is two lines — `runOne` returned on the first throw (`:281-289`) and the matrix compared one row per invariant (`:352-362`) — so an invariant went red as a unit and any assertion that was not the sole discriminator could be neutered undetected. Twelve invariants carried **45** `assert.` calls, and the verdict called them twelve assertions | 2026-08-20 | **verified locally · unreleased** |
| 049 | The same hole existed in the ad-tracking pack, in the assertion a reference advertises by name | the same neutering, applied to the PII guard | **`--self-test` exit 0** with `assert.ok(!JSON.stringify(userData).includes('@'))` replaced by `assert.ok(true)`. `references/meta-linkedin.md` names that assertion — *"refuses anything with an `@` in it"* — in the section about the one way a tracking integration breaches Meta's terms by accident. The `assert.match` above it discriminated the same mutant, so the invariant stayed red and nothing noticed | 2026-08-20 | **verified locally · unreleased** |
| 050 | The measurement is now per assertion, and the printed claim is what it measures | `node assert-money-invariants.mjs --self-test`; the same for the ad-tracking pack | **both exit 0.** Stripe: `12 invariants over 45 assertions — 37 watched failing ONE CALL SITE AT A TIME against 11 mutants; 8 declared unmutated and measured unbreakable; 9 rules, each isolated by a fixture`. Ad-tracking: `6 invariants over 12 assertions — 12 watched failing …; 0 declared unmutated`. The `assert` an invariant receives is a recorder: a failure is remembered rather than thrown, so the assertions after it still run, and each call site is identified by its line via `Error.captureStackTrace` | 2026-08-20 | **verified locally · unreleased** |
| 051 | The eight assertions no mutant can break are declared, not hidden — and four more became measurable rather than being declared away | the per-assertion matrix `--self-test` prints | **14 of 45 were broken by no mutant on the first measurement; six of those were reachable and are now measured.** `mirror.periodStart`/`periodEnd` and the four `conversion.*` field assertions were being pre-empted by a `TypeError` on the line above them — the run aborted before the assertion was reached, so no mutant had ever been watched breaking them. `|| {}` and `[conversion = {}]` make them fail instead of throw, and `grant-on-renewal` now breaks all six. The remaining **8** are `assert.unmutated.*`: two response envelopes, three `status`/`body` shape assertions, and three about conversions a session-sourced handler never emits — each with the reason at the call site | 2026-08-20 | **verified locally · unreleased** |
| 052 | The escape hatch is checked in both directions | the same run, plus a plant | **a discriminating assertion moved onto `assert.unmutated` is a failure**, not a silence: `refund-total-is-cumulative :197 is declared assert.unmutated and [cumulative-refund] breaks it`. Without that direction, `unmutated` would be the bypass the fix installed — an assertion parked there stops being counted as evidence and nothing would object | 2026-08-20 | **verified locally · unreleased** |
| 053 | The new plants have been watched refusing | `node test/fixtures_test.js` | exit **0**, `16 checks (both packs, both modes, 6 plants: neutered assertions, an unremovable rule, and a live discriminator parked in the unmutated escape hatch)`. Three plants are new and all three require a non-zero `--self-test`: the third-of-three `clawbacks.map` deepEqual neutered (`refund-total-is-cumulative :197 is broken by no mutant`), the second-of-two PII guard neutered (`identifiers-reach-the-server-hashed :152 is broken by no mutant`), and a live discriminator declared `unmutated`. Each was watched at exit **1** before being written into the suite | 2026-08-20 | **verified locally · unreleased** |
| 054 | The validator's check count counts checks | `python3 test/validate.py`; a plant that registers one more | `OK: sheleg-dev structurally valid (23 checks, 6 skill(s), v0.7.0)`. It was `checks = 10 + len(skill_dirs)` at `test/validate.py:1101` — so adding a **skill** moved the number and adding a check did not, and REQ-001, 011, 019, 028 and 040 all read that number as evidence that a guard had arrived. Every check is now registered in `CHECKS`; the plant appends one and the run goes red because the ledger's quoted verdict no longer matches | 2026-08-20 | **verified locally · unreleased** |
| 055 | The ledger describes the artifact that ships | `python3 test/validate.py`; `git describe --tags`; `npm view` | the shipped block was headed **v0.6.0** while `git describe --tags` printed **v0.7.0** and npm served `0.7.0`, and 37 rows read *verified locally · unreleased* with four blocks closing *"Nothing was released: no tag, no publish, no version bump."* `check_ledger_names_the_shipped_version` compares the heading against `git describe --tags` **and** against `package.json` — two comparands because git cannot look from a `/tmp` copy of a submodule checkout, and a plant has to be refused there too. `check_ledger_quotes_the_validator_verdict` compares REQ-001's quoted string against the printed line, scoped to the shipped block so the dated readings below it (13, 14, 15, 16 checks) are not rewritten to keep a checker quiet | 2026-08-20 | **verified locally · unreleased** |
| 056 | Every counted number in the two measuring documents is recomputed | `python3 test/validate.py`; `git ls-files plugins`; `npm pack --dry-run` | **seven numbers, all computed.** `SECURITY.md`: 52 files under `plugins/`, 30 markdown, 22 non-markdown, 22 references, 58 in the tarball — the four B-93 named were correct on the day they were written and three of them moved with this change. `docs/evals/stripe-billing.md` said `4994` tokens / `441` lines / `0 GAP, 13 PASS` against a measured 4747 / 409 / `0 GAP, 14 PASS`: three of four restated numbers wrong, in the document whose subject is measurement. The tarball count is derived from `package.json` → `files` rather than by shelling out, because `npm test` must run offline — **verified set-identical to `npm pack --dry-run --json`**, 56 paths at the time of the check and 58 after the split | 2026-08-20 | **verified locally · unreleased** |
| 057 | Both doors of the manual gate are required, and the copy channel gets the same gate | `python3 test/validate.py`; two plants | the `mcp__.*` half of `hooks/hooks.json:17` had **no guard**: deleting that entry left `validate.py`, `test/moneygate_test.js` and `test/fixtures_test.js` all at exit 0, while `hooks/lib/moneygate.js` does refuse `mcp__plugin_stripe_stripe__create_refund` by name. And `README.md:166`'s copy-channel snippet registered **one** matcher against the plugin's two, so a reader who followed the document could not refuse the `create_refund` tool the same README advertises at `:130`. Both are now checked — the second by matcher SET rather than by text — and both plants were watched at exit 1 | 2026-08-20 | **verified locally · unreleased** |
| 058 | `docs/` is inside the checked corpus, and every document in it is classified | `python3 test/validate.py`; a plant | `docs/AGENT_SYNC.md` named **six** paths this repository does not have (`agent_sync.py` plus five `references/*.md`, all the agent-sync skill's) and `docs/` was outside the corpus at `test/validate.py:399-404`. The two live documents joined it with explicit `FOREIGN_BY_DESIGN` entries; the three dated records are declared in `DATED_RECORDS` for the same reason `CHANGELOG.md` is excluded — a record has to be able to quote the dead path that was the defect. `check_docs_are_classified` requires every `docs/**/*.md` to be in exactly one list, and the plant drops an unclassified document in | 2026-08-20 | **verified locally · unreleased** |
| 059 | A document that SHIPS resolves against the tarball, not only against a clone | `python3 test/validate.py`; a plant | `SECURITY.md:143-144` sent a reader to `docs/evidence/verification.md` and `CONTRIBUTING.md`; `npm pack --dry-run` contains neither, and the existing path guard passed because it resolved against the clone. The paragraph now says where they live, and `NOT_IN_THE_TARBALL` enumerates the eleven clone-only paths the two shipped documents name — with the stale-exemption rule that applies to `FOREIGN_BY_DESIGN`. The sweep also found the `install.sh` table row describing a file the tarball does not carry | 2026-08-20 | **verified locally · unreleased** |
| 060 | The coordination config points at things that exist | `python3 test/validate.py`; two plants | `mergeLog.file` named `docs/MERGES.md`, which did not exist — a configured destination nothing could write to, in the file whose job is keeping two agents from overwriting each other — and `guardedFiles` claimed `docs/evidence/verification.md` while omitting `docs/evidence/backlog.md`, the board it cross-references by row id. The file now exists and the board is guarded; every path in the config is resolved, globs as globs | 2026-08-20 | **verified locally · unreleased** |
| 061 | The documents that describe the gate describe the whole gate | `python3 test/validate.py`; a plant | `CONTRIBUTING.md:74` called `npm test` two suites and it runs three — `test/fixtures_test.js`, 16 checks, was missing — and `.github/PULL_REQUEST_TEMPLATE.md:10` asked a contributor for `python3 test/validate.py` alone, one third of the gate. Both now name all three, derived from `package.json` → `scripts.test`, so a fourth suite fails the documents rather than passing them | 2026-08-20 | **verified locally · unreleased** |
| 062 | Both install channels say the gate does not travel with them | `HOME=/tmp/fakehome-notice bash install.sh`; `python3 test/validate.py` | `install.sh` — `rm -rf "$dest"` then `cp -R` per skill, the destructive channel — printed nothing about the hook while `bin/sheleg-dev.js:107-112` did. It now prints the same four-line notice, ending in `Nothing enforces this step.`, and the check requires both files to say `manual gate` and to name a document a reader can register it from. B-90 stays open: a printed reminder is a warning, and M-30 calls a warning weaker than a precondition — but printing in one channel and not the other was not a position | 2026-08-20 | **verified locally · unreleased** |
| 063 | The body budget is measured HERE, and every skill is inside it | `python3 test/validate.py`; `audit_skill.py --house` on all six | this repository's gate measured **no** body budget (`test/validate.py:170-185` was front matter only), so `crypto-payments/SKILL.md` sat at ~4894 tokens — `1 GAP` on `BODY_HEADROOM` — and was found by running another repository's auditor. `check_body_budget` reimplements both thresholds (5000/500 hard, 4750 house, `len(body)/3.9`) and `crypto-payments` was split rather than trimmed: `references/callback-route-hardening.md` and `references/testing-and-local-dev.md`, body **4894 → 4387** tokens, 439 → 376 lines. All six skills now `0 GAP, 14 PASS`. `stripe-billing` passes at ~4747 of 4750 and the failure message prints the distance, because a gate set below a value the tree already holds is a gate nobody can pass | 2026-08-20 | **verified locally · unreleased** |
| 064 | All 42 negatives refuse their plants, on a GREEN tree | every `Negative self-test` step extracted from `validate.yml` and run as a process | **42/42 refused, 0 broken steps.** Fourteen are new. Run twice on purpose: the first sweep happened while the tree was still red on the ledger heading, which makes every plant pass vacuously — a plant against a failing base measures nothing. Re-run after `python3 test/validate.py` reached exit 0 | 2026-08-20 | **verified locally · unreleased** |
| 065 | Nothing about the shipped artifact regressed | `npm test`; `claude plugin validate . --strict` and on the plugin; both installers against fake HOMEs; `npm pack --dry-run` | `npm test` exit **0** — `23 checks`, `65 fixtures`, `16 checks`. Both validations **`✔ Validation passed`**. `node bin/sheleg-dev.js` installs six skills into a fresh HOME, the rerun prints `6` `^skip:` lines, `install.sh`'s last install line is unchanged and the notice follows it; the two new `crypto-payments` references travel with the copy, and both assertion packs run from the installed copy (`45 assertions`, `37 watched failing`). `npm pack --dry-run` → `total files: 58` | 2026-08-20 | **verified locally · unreleased** |

**What is NOT verified in this SD-05 block.**

- **CI has not seen the fourteen new negatives, or the per-assertion self-test.** They were
  run locally as processes against real copies (REQ-064). Same gap the four blocks above
  recorded and one release closed; this one is a day old rather than four blocks deep, and
  it is named once here rather than repeated per row.
- **The eight `assert.unmutated` sites are not evidence, and the verdict says so.** Three of
  them state a rule this reference handler cannot break because it emits conversions on
  `invoice.paid` only — a reader whose handler reports from a checkout session WOULD be
  discriminated by them. So the honest reading is "unmeasured here", not "unnecessary", and
  the call sites say which.
- **Deletion is not neutering.** A plant that removes an assertion outright drops the call
  site from the census rather than leaving one no mutant breaks, and the count in the verdict
  line moves without failing. The claim is bounded to *"37 of the 45 assertions that RUN
  have been watched failing"*, which is what the line prints.
- **`git describe` cannot look from a `/tmp` copy** of a submodule checkout — `.git` is a
  gitlink file with a relative path. The version comparison against `package.json` is what
  refuses the plant locally; the tag comparison is what refuses it in CI, where `.git` is a
  real directory. Both were watched.
- **v0.7.0 is a lightweight tag** (`git cat-file -t v0.7.0` → `commit`), where v0.6.0 was
  annotated and REQ-010 stated the annotation as a property. Filed as **B-98**. The fix is a
  retag, which is a push, and this run neither tags nor pushes.
- **B-92's residual.** The hook has now been observed firing twice in a live session and
  refusing both calls, which closes two of that row's three claims. Nothing recorded either
  firing — the observation is a transcript, not an artifact — so the row stays open on that
  alone, and the third claim (a variable exported inside a tool call cannot reach the hook's
  environment) is still untested.
- **B-86's citation was stale and is now right, and nothing checks it.** The phrase
  *"something asserts they agree"* moved from `testing-and-local-dev.md:210` to `:246` when
  SD-04 grew the file. The board row and `test/validate.py`'s `CREDENTIAL_BOUNDARIES` comment
  are corrected; the skill payload's markdown is still outside the citation guard's corpus
  (board **B-82**), so the next drift will be found the same way this one was — by reading.
- **Nothing was released**: no tag, no publish, no version bump. Written knowing what
  happened to the last four copies of this sentence: it is true at this commit and has a
  shelf life of hours, and `check_ledger_names_the_shipped_version` is what notices when it
  expires.

Rows **066 through 070**, 2026-08-25. The cancel-flow save offer — Cursor's
*"Before you go… 50% off your next invoice"* — and the two ways it leaks money. Every
Stripe claim below was read from the OpenAPI spec at `2026-07-29.dahlia` or from a
documentation page, never recalled.

| REQ | Requirement | Verified by | Result | Observed at | Status |
|---|---|---|---|---|---|
| 066 | The offer on that page is `flow_data[subscription_cancel][retention]`, and it exists only per session | the Stripe OpenAPI spec (`info.version` → `2026-07-29.dahlia`, matching `docs.stripe.com/changelog` for latest); `docs.stripe.com/customer-management/portal-deep-links.md`; `.../cancellation-page.md` | `POST /v1/billing_portal/sessions` carries `flow_data.subscription_cancel.retention` (`retention_param`, required `["coupon_offer","type"]`, `type` enum `["coupon_offer"]`, `coupon_offer.coupon` required). The portal **configuration**'s `features.subscription_cancel` holds only `cancellation_reason`, `enabled`, `mode`, `proration_behavior` — **no `retention`** — so per-customer targeting exists on the session and nowhere else. The deep-links guide lists all four flow types and never mentions `retention`: it is in the spec and not in the page, which is why the spec was read | 2026-08-25 | **verified locally · unreleased** |
| 067 | A `duration=once` save offer can be taken every cycle, and Stripe cannot stop it | `docs.stripe.com/billing/subscriptions/coupons.md`; the spec's `coupon` schema | Stripe: *"the coupon is considered used after the invoice finalizes and is removed from the subscription's `discounts` array… a subscription may appear to have no discount even though a coupon was applied."* The `coupon` schema has `max_redemptions` — a total across **all** customers, shared with its promotion codes — `times_redeemed`, `redeem_by`, and no per-customer field of any kind. Stripe's own comparison marks *restrict to a specific customer*, *first purchase only* and *minimum spend* ❌ for coupons and ✓ for promotion codes, and `retention.coupon_offer` takes a **coupon**. Eligibility is therefore inexpressible in Stripe and has to be a row you own | 2026-08-25 | **verified locally · unreleased** |
| 068 | Flexible billing mode records a portal cancellation in a different field | `docs.stripe.com/billing/subscriptions/billing-mode/compare.md` → *Cancellations in the Customer Portal* | classic: `cancel_at_period_end: true`, `cancel_at` set to `current_period_end` and **following** it when it moves. Flexible: `cancel_at` set to the maximum `current_period_end` across items, `cancel_at_period_end` **false**, and `cancel_at` does not follow. `billing_mode` cannot be migrated back, so an established account holds both shapes at once and code reading the boolean is wrong for the customers who have paid longest | 2026-08-25 | **verified locally · unreleased** |
| 069 | Both defects are invariants with a mutant each, watched failing one assertion at a time | `node plugins/sheleg-dev/skills/stripe-billing/fixtures/assert-money-invariants.mjs --self-test`; `npm run test:all` | `OK: 14 invariants over 57 assertions — 43 watched failing ONE CALL SITE AT A TIME against 13 mutants; 14 declared unmutated and measured unbreakable; 11 rules, each isolated by a fixture`, and `PASS: all 42 guards provably reject their planted defect`. The first measurement of `retention-offer-is-consumed-once` reported **three assertions broken by no mutant** (`:302`, `:308`, `:311`) — the `retention-eligibility` mutant was gating only the ledger *reads*. Making it remove the whole ledger, the row included, turned all three into evidence and left the first-offer assertion as the declared positive control | 2026-08-25 | **verified locally · unreleased** |
| 070 | The split that made room for it, and every count that moved with it | `python3 test/validate.py` | `stripe-billing/SKILL.md` **4747 → 4683** tokens, **409 → 381** lines, against a 4750 working limit that had three tokens of headroom. Cancellation moved to `references/cancellation-and-retention.md`; three body code blocks with a second home in `references/subscription-lifecycle.md` (get-or-create, the seat update, the refund compare-and-swap) now live only there. `SECURITY.md` was restating **56** payload files (61), **34** markdown (35), **22** non-markdown (26), **25** references (26), **62** tarball files (67), and `SKILL.md`, one per skill` = **6** for seven skills. `package.json`'s npm description still began *"Six integration skills"* and omitted `error-tracking`, which has shipped since v0.9.0. The skill's own description sat at **967 of the 970 house working limit**, so the four new triggers (`cancel subscription`, `retention coupon`, `скидка при отмене`, and the cancel step in the opening sentence) were paid for rather than appended: `963` chars, `0 GAP, 14 PASS` under `audit_skill.py --house` (make-skill 0.23.1) | 2026-08-25 | **verified locally · unreleased** |


## What these checks do not cover

Named rather than left to be inferred, because a ledger that lists only its successes
reads as coverage it does not have.

- **The retention flow has not been walked against a live Stripe sandbox.** Rows 066–068
  are read from the OpenAPI spec and the documentation, which is stronger than
  recollection and weaker than a run. Two things neither source states: the order in
  which `customer.discount.created` and `customer.subscription.updated` arrive when the
  offer is redeemed, and whether redeeming abandons the cancellation entirely (no
  `cancel_at`, no `cancel_at_period_end`). `references/cancellation-and-retention.md`
  marks both as unverified and carries the `stripe listen` commands that answer them, so
  the gap is in the reader's hands rather than hidden.
- **Whether the integration advice is correct against the live vendors.** These seven
  skills describe Stripe, Heleket/BTCPay, Google Sign-In, Workload Identity, ad networks
  and web performance. Every row above measures the *artifact*: valid, linked, budgeted,
  released. Nothing here re-checks a vendor's current API against the page describing
  it, and vendor drift is this repository's largest untested exposure.
- **`--force` and the bad-argument path.** CI exercises both against a fake HOME; REQ-006
  and REQ-007 cover the fresh and rerun-skip paths locally and stop there.
- **The 42 negatives, one by one, on the shipped tree.** REQ-002 reads their step
  conclusions from CI run `32293489020`, which ran the 28 that existed at the tag. The 14
  added on 2026-08-20 were run locally as processes (SD-05, REQ-055) and have not yet been
  seen by CI — the same gap, honestly one release old rather than four blocks deep.
