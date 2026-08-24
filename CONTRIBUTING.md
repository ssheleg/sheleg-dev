# Contributing

Thanks for taking the time. This repository ships **seven skills** — `stripe-billing`,
`crypto-payments`, `ad-tracking`, `google-signin`, `google-auth`,
`frontend-performance` and `error-tracking` — and they are almost entirely **knowledge**: twenty reference
files an agent reads on demand. That shapes what a good contribution looks like.

**Almost, not entirely.** Since 2026-08-19 the pack also ships a **manual gate** — a
`PreToolUse` hook under `plugins/sheleg-dev/hooks/` that refuses a refund, a payout,
closing a dispute, a live `sk_live_…` key, an export of `HELEKET_API_KEY` in a run
declaring `test`, an explicit `--live` flag, a command granting itself the gate's own
switch, and `SKIP_BILLING=true` in production. It exists because four of this pack's own
rules were sentences that stopped nothing. `README.md` → *The manual gate* is its single
home; the rules below about executable code apply to it and to `install.sh` /
`bin/sheleg-dev.js`, which are the only other things here that run.

## The one rule that matters

**A seam, not a summary.** Every one of these skills exists because a generated
integration gets one thing wrong in a way no screen shows: the webhook *is* the payment
and the redirect only proves a browser reached a URL; a purchase event fired from the
thank-you page cannot know the charge cleared; the same `event_id` missing on one side
counts the revenue twice. A reference file earns its place by naming a seam like that
and saying what happens when it is got wrong.

So a contribution is judged on three things:

- **It is checkable.** Name the API, the field, the status code, the header. "Handle
  webhooks properly" is not a contract; "a `checkout.session.completed` you have not
  verified with the signing secret is an unauthenticated POST from the internet" is.
- **It is dated where it can rot.** Provider APIs, consent regimes and browser defaults
  change. A claim about *what a provider does today* carries the date it was true.
- **It stays inside the boundary.** This layer answers *what it runs on*, never *what it
  should do*. Which tiers exist and what the paywall must accomplish belong to
  `super-ux`; how it looks to `sheleg-design`; the words on it to `copywriting`; the
  price itself is a business decision no skill makes. A PR that argues pricing strategy
  will be redirected, not merged.

## Where things go

| Change | File |
|---|---|
| Anything about one integration | that skill's `references/` — e.g. `plugins/sheleg-dev/skills/stripe-billing/references/webhook-events.md` |
| A new reference file | the skill's `references/`, **and** a link to it from that skill's `SKILL.md` |
| What a skill is *for*, or when it should be reached | that skill's `SKILL.md` front-matter `description` |
| A new skill | `plugins/sheleg-dev/skills/<name>/SKILL.md` — the directory name and the front-matter `name` must match |
| What the manual gate refuses | `plugins/sheleg-dev/hooks/lib/moneygate.js` (the decision), **and** a plant in each direction in `test/moneygate_test.js` |
| Anything user-visible | `README.md` and `CHANGELOG.md`, in the same PR |

**A reference nothing links to is never loaded.** Progressive disclosure means the agent
reads `SKILL.md` and follows only the links it finds there, so an unlinked file is dead
weight that still costs review. The validator enforces both directions: a `references/…`
link with no file behind it fails, and so does a reference file no `SKILL.md` mentions.

There is no shared reference directory and no auditor script. If you are looking for
`benchmarks.md`, `growth-plays.md` or `scripts/page_audit.py`, you want
[`seo-aeo-audit`](https://github.com/ssheleg/seo-aeo-audit) — this file described that
repository's layout for a while, and a contributor following it was told to put work in
files this repository has never had.

## Setup

No dependencies. Python 3.9+ is all you need.

```bash
git clone https://github.com/ssheleg/sheleg-dev && cd sheleg-dev
```

## Before you open a PR

One command:

```bash
npm test          # python3 test/validate.py, then node test/moneygate_test.js,
                  # then node test/fixtures_test.js
```

**Three suites, not two.** This line said two until 2026-08-20, and the missing one was
`test/fixtures_test.js` — the 16 checks that run both money-assertion packs in both modes
and plant six neutered assertions. `test/validate.py` now derives the list from
`package.json` → `scripts.test`, so a fourth suite fails this paragraph rather than
passing it.

It checks the four-way version sync (`package.json`, the plugin manifest, the
marketplace manifest and the top `CHANGELOG.md` heading — one number, four files, and a
plugin whose manifest disagrees with its package installs a lie); that no version is
documented twice, because the release workflow reads the first matching section and
would ship the wrong notes; that every skill's front matter is legal under the Agent
Skills standard (name matches its directory, 1–64 characters, lowercase `[a-z0-9-]`,
description present and free of angle-bracket tags); that every `references/…` link
resolves and every reference is linked; that no build artifact and no stray `SKILL.md`
has appeared outside `plugins/*/skills/*/`; that every path named by the documents whose
subject is this repository — `README.md`, `SECURITY.md`, this file and the PR template —
exists here, and that a `file:line` citation in one of them does not point past the end
of the file; that the release workflow still gates on this validator rather than
merely mentioning it; and that the **manual gate** is shipped in a working shape — a
`PreToolUse` entry running `money-gate.js`, no `if` filter on it (the reference calls that
filter best-effort and says it fails open), the deciding in a required pure module, a
`catch` and an `exit 0` in the hook, every refusal category present in both the module and
the fixtures, allow-plants as well as deny-plants, and the two prose sites naming the
mechanism instead of only the rule.

`node test/moneygate_test.js` is the gate's own suite: 65 fixtures over the pure decision
module with no `HOME`, plus the real hook run as a process, because *fails silent* and
*exit 0* are properties of the script rather than of the module.

`node test/fixtures_test.js` is the money fixtures: 13 checks over the two assertion packs
under `plugins/sheleg-dev/skills/*/fixtures/`, run as processes from their own directories
the way a reader who copied them would. It runs each pack twice — once against its
reference implementation, once with `--self-test`, which deletes one rule at a time and
requires every assertion to go red — and then plants three neutered assertions and requires
`--self-test` to notice. **An assertion nobody has watched failing is the thing this row
existed to remove**, so a check that cannot fail is a failure here.

It also asks the family umbrella whether this repository still advertises every word the
routing hook fires on. That check needs an `sshlg-skills` checkout above this one and
**discloses instead of passing** when there is none, so a standalone clone prints an
`unlooked:` line rather than a false green.

CI runs the same validator plus **forty-two** negative self-tests, each of which plants
a real defect — a version drift, an over-long description, a front-matter name that stops
matching its directory, a dangling reference link, a reference nobody links, a stray
`SKILL.md`, a release that stops gating on validate, the validator dropped from CI, a
routing table sending work to a file we do not have, a shipped document naming a path we
do not have, a `file:line` citation past the end of that file, an exemption left
behind after the document stopped naming the path, a credential boundary that stops
refusing a live key declared test, the same boundary refusing only that one direction,
a copyable block handing over a credential with no declared environment, a manual gate
moved to `PostToolUse` where it can only report, an `if` filter reintroduced onto it, the
decision inlined into the hook, a hook that stops exiting 0, the false-positive plants
deleted, a live-key rule narrowed to the bare prefix, a heredoc body read as an
invocation, a test-declaring run that can buy its way past the gate, a claimed money
invariant whose fixture is gone, a fixture no invariant claims, a reference pointing at a
fixture that is not there, a claim reworded away from the fixture that proves it, and an
assertion that can no longer fail — and requires the gate to reject it. A guard nobody has
watched fail is not a guard.

**Both directions, always.** Three of those plants break the gate's *decision
module* and require its own fixtures to go red, because a guard that refuses correct input
gets switched off and then there is no guard. Two of them were written after the first
attempt went **uncaught**: every `sk_live_` allow-plant was leaning on the reader denylist
while every reader allow-plant was leaning on the key's shape, so neither mechanism was
individually proven. If you add a rule, add the innocent shape closest to it.

### The family catalogue moves with the release

`sshlg-skills` — the launcher that installs and updates the whole ssheleg family — pins every
member's version in its own `skills.json`. **A release that does not bump that pin is invisible.**
`npx sshlg-skills list` keeps reporting the previous version, `update` keeps installing it, and
anyone comparing their install against `list` is told the wrong number with nothing to reveal it.

So a release is not finished at `npm publish`:

```bash
# in ssheleg/sshlg-skills
#   1. bump this member's "version" in skills.json
#   2. bump the launcher's own version, changelog, tag
npm publish --access public
npx --yes sshlg-skills@latest list   # the new number must appear here
```

## Coordinating with other agents

`docs/AGENT_SYNC.md` describes how coordination is wired in this repository and
what it does **not** guarantee. It is generated from `.claude/agent-sync.json`:
read it before editing a file that config guards, and regenerate it with
`agent_sync.py setup` in the same change that alters the config. That script
ships with the `agent-sync` skill, not with this repository.

## Style

- US spelling. A mixed standard has already cost one broken anchor here.
- Plain sentences over hedged ones. Say what is known and what is not.
- Cross-reference by path, never by an invented anchor — and check the path exists. Every
  file name in this document was checked against `git ls-files` when it was written,
  because the previous version cited eleven that were not here.
- Conventional commits (`feat:`, `fix:`, `docs:`), one concern per PR.
- Behavior changes update `README.md` and `CHANGELOG.md` in the same PR.

## Reporting problems

Bugs and ideas: [open an issue](https://github.com/ssheleg/sheleg-dev/issues).
For a wrong or outdated claim, please include what the correct claim is and what
backs it — that turns a report into a merge.

Security issues: see [SECURITY.md](SECURITY.md); please do not open a public
issue for those.

## License

By contributing you agree that your contributions are licensed under the
[MIT License](LICENSE).
