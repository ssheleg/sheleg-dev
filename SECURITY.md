# Security

`sheleg-dev` is seven skills about the layer a product reaches once it has users.
Five of them touch other people's money or identity — Stripe billing, crypto
payments, ad and conversion tracking, Google sign-in, server-side Google auth —
the sixth is front-end performance and the seventh is error tracking. Money is the
reason this document
has to be exact about the pack itself.

Everything below is checkable from a clone, and the commands at the end are the
checks. **If one of them does not run, that is a defect in this document** —
please report it as one. Until this rewrite the file was a wholesale copy of a
sibling skill's, published in the npm tarball: it described a Python auditor this
repository has never had, and closed with a "verify for yourself" block whose
second and third commands exited 2. `test/validate.py` now refuses any path these
documents name that does not exist here.

## What ships, and what of it executes

`git ls-files plugins` returns **56 files: 34 markdown, one plugin manifest, three
files of the manual gate, and 18 files of money fixtures.** Two of the seven skills now
ship code you can run — the assertion packs under `fixtures/` — and that is a change
from every release before v0.7.0, so it is stated here rather than left to be noticed.
They run only when you invoke them, read only the JSON fixtures beside them, and open
no socket; the greps below prove all three.

| Component | Count | Runtime behavior |
|---|---|---|
| `SKILL.md`, one per skill | 6 | Text. Read by the agent, executes nothing. |
| `references/` files, loaded on demand | 25 | Text. Same. |
| `plugins/sheleg-dev/.claude-plugin/plugin.json` | 1 | Manifest read by Claude Code. |
| `plugins/sheleg-dev/hooks/hooks.json` | 1 | Hook manifest read by Claude Code. Declares one `PreToolUse` hook and no `if` filter. |
| `plugins/sheleg-dev/hooks/money-gate.js` | 1 | Runs on a tool call, when the plugin is enabled. Requires `path` and its own decision module — nothing else. Reads stdin, writes one JSON line, exits 0 on every path. |
| `plugins/sheleg-dev/hooks/lib/moneygate.js` | 1 | Pure. Payload and environment in, verdict out. No `require` at all, no filesystem, no clock. |
| `bin/sheleg-dev.js` — the npm installer | 1 | Runs only when you invoke it. Node built-ins only: `fs`, `path`, `os`. |
| `install.sh` — the shell installer | 1 | **Not in the tarball** — `files` ships `bin/` and `plugins/`, so this one reaches you only through a clone. Runs when you invoke it. Coreutils only: `cd`, `pwd`, `dirname`, `basename`, `mkdir`, `rm`, `cp`, `echo`. It is the destructive channel: `rm -rf` per skill, then `cp -R`. |
| `plugins/sheleg-dev/skills/*/fixtures/*.json` — webhook payloads | 12 | Data. Placeholder ids only; no key, token, signing secret or real customer id. |
| `plugins/sheleg-dev/skills/*/fixtures/*.mjs` — the assertion packs and their reference implementations | 4 | Runs only when you invoke it. Reads the JSON beside it with `readFileSync` and nothing else: no `child_process`, no `fetch`, no write, no `process.env`. |
| `plugins/sheleg-dev/skills/*/fixtures/manifest.json` and its `README.md` | 4 | Text. The invariant-to-fixture-to-document map, which `test/validate.py` reads. |

The published tarball is `bin/` and `plugins/` plus `README.md`, `CHANGELOG.md`,
`SECURITY.md`, `LICENSE` and `package.json` — 62 files, listed by
`npm pack --dry-run`. `install.sh`, `test/`, `docs/` and `CONTRIBUTING.md` are **not**
in it; `test/validate.py` now refuses a path these shipped documents name that the
tarball does not carry, because resolving in a clone is the wrong question for a
document that ships.

**The gate can refuse a command and can never run one.** `money-gate.js` requires
`path` and the decision module; the decision module requires nothing. There is no
`child_process`, no `fetch`, no `http`, no `fs` on either path — so the strongest
thing it can do to your session is print a denial, and the strongest thing a bug
in it can do is print nothing. It reads `process.env` for one variable pair
(`SHELEG_DEV_LIVE_AUTHORISED`, `SHELEG_DEV_MONEY_GATE`) and the environment
declaration a run already carries, and it never writes to any file. `README.md` →
*The manual gate* is its single home.

**There are no npm lifecycle scripts.** `package.json` declares exactly one
script, `test`. Installing this package, or reaching it through `npx`, runs
nothing but the CLI you typed.

## What the installers read and write

Both do one thing: copy the seven skill directories out of the package into
`~/.claude/skills/<name>`.

- **Read:** only files inside the package.
- **Write:** only `~/.claude/skills/` — seven directories, named for the seven skills.
  Nothing else on the filesystem, nothing outside `$HOME`.
- **Network: none.** Neither file opens a socket or resolves a hostname.
  `bin/sheleg-dev.js` requires `fs`, `path` and `os` and nothing else — no
  `child_process`, no `fetch`, no `http` — so it spawns no process at all;
  `install.sh` runs only the coreutils named above. The grep below prints the
  whole surface of both files in eleven lines.
- **No telemetry, no analytics, no phone-home.** Nothing here has anywhere to
  send anything.

**One destructive difference between the two installers.** `bin/sheleg-dev.js`
skips a skill that is already installed and says so, unless you pass `--force`
(`bin/sheleg-dev.js:45-46`). `install.sh` does not ask: for each of the seven names
it runs `rm -rf` on the destination and re-copies, every time
(`install.sh:21-22`). If you have hand-edited an installed skill, the shell
installer deletes your edits and the node installer does not.

## Credentials

**This pack handles payment credentials as a subject and never as a value.** It
reads no credential, stores none, transmits none, logs none. It is markdown; it
could not.

What it contains is credential *names*, inside example code you adapt —
`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `HELEKET_API_KEY`,
`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`. No real key ships. The grep below
searches the whole skill payload for live-key shapes and returns exactly one line
— a `-----BEGIN RSA PRIVATE KEY-----\n...` placeholder inside a service-account
JSON example, at
`plugins/sheleg-dev/skills/google-auth/references/adc-and-service-accounts.md:236`.
The pack's own position on live keys, that one in a repository is an incident
rather than a lint warning, is at
`plugins/sheleg-dev/skills/stripe-billing/references/stripe-agent-toolchain.md:156`.

`.env` and `.env.*` are gitignored here, `.env.example` excepted.

## What the advice can lead an agent to run

The pack executes nothing — but it tells an agent what to run, and some of those
commands move real credentials. Every one is a vendor's own tool, invoked by you
or by an agent you approved:

- `stripe login` and `stripe agent setup` — browser consent, then a written CLI
  profile. The reference marks the login a human step:
  `plugins/sheleg-dev/skills/stripe-billing/references/stripe-agent-toolchain.md:36-37`
- `stripe listen`, `stripe trigger`, `stripe logs tail` — use the profile the CLI
  already holds:
  `plugins/sheleg-dev/skills/stripe-billing/references/testing-and-local-dev.md:24-51`
- `gcloud auth application-default login` — mints a local credential file:
  `plugins/sheleg-dev/skills/google-auth/references/adc-and-service-accounts.md:50-57`
- `gcloud iam workload-identity-pools create-cred-config` — writes a
  credential-configuration file:
  `plugins/sheleg-dev/skills/google-auth/references/workload-identity.md:127`
- `claude mcp add --transport http stripe https://mcp.stripe.com/` — OAuth
  consent to **Stripe's own MCP server**, which can make live calls against your
  account:
  `plugins/sheleg-dev/skills/stripe-billing/references/stripe-agent-toolchain.md:106-107`

The last is the one to weigh. This pack *points at* Stripe's MCP server and does
not install, proxy or wrap it; if you connect it, that account access is between
you and Stripe. The same file states the key hygiene the pack expects — restricted
`rk_` keys, one per service, minimum permissions, a secrets vault in preference to
environment variables, never in source and never in logs:
`plugins/sheleg-dev/skills/stripe-billing/references/stripe-agent-toolchain.md:144-158`.

## What this pack never does

- It never charges, refunds, rotates or revokes anything. It has no code that could
  — and since 2026-08-19 it ships a hook whose whole purpose is to stop an *agent*
  from doing so unasked. `README.md` → *The manual gate*.
- It never asks for a key, and has nowhere to send one.
- It does not choose your payment processor. Licensing, AML programme and
  sanctions exposure are a business and compliance decision, and `README.md` says
  so where a reader meets the crypto skill.

## Where the real risk is

Not the bytes — the advice. These seven skills describe Stripe, Heleket and BTCPay,
Google Sign-In, Workload Identity Federation, four ad platforms and browser
defaults, and every one of those changes. **A claim here that a provider has since
changed is a security defect in this pack**, not merely a stale doc, and it is the
exposure the verification ledger names as the largest one this repository does not
test. **Neither that ledger nor the contributor guide is in this tarball** —
`docs/evidence/verification.md` and `CONTRIBUTING.md` live in the git repository at
<https://github.com/ssheleg/sheleg-dev>, and until 2026-08-20 this paragraph named
both as if you had them. The guide requires a claim about what a provider does
*today* to carry the date it was true. If you find one that has rotted, report it
with what the correct claim is and what backs it.

## Reporting a problem

Open an issue: <https://github.com/ssheleg/sheleg-dev/issues>. **For a security
problem, do not put the details in a public issue** — open one saying you have
found something, and a private channel will be arranged.

## Verifying for yourself

```bash
git clone https://github.com/ssheleg/sheleg-dev && cd sheleg-dev

# The whole gate: version sync across four manifests, front matter inside the
# Agent Skills limits, references resolving both directions, and every path the
# self-describing documents name -- this file included.
python3 test/validate.py

# The shipped payload: 56 files.
git ls-files plugins

# 22 lines: the plugin manifest, the three files of the manual gate, and the 18
# files of money fixtures. Everything else in the payload is markdown.
git ls-files plugins | grep -v '\.md$'

# Every require the gate makes: two lines, both in the hook -- `path`, and its own
# decision module. The decision module makes none.
grep -nE "\brequire\(" plugins/sheleg-dev/hooks/money-gate.js plugins/sheleg-dev/hooks/lib/moneygate.js

# What it cannot reach: NO OUTPUT, and grep exits 1 because it matched nothing.
grep -nE "child_process|\bfetch\(|require\('(http|https|net|fs|dns|tls)'\)|spawn\(|execFile|writeFile|appendFile|unlink" \
  plugins/sheleg-dev/hooks/money-gate.js plugins/sheleg-dev/hooks/lib/moneygate.js

# Both directions of the gate, watched: every refusal and every false-positive
# plant. The command prints its own count -- this document does not restate it.
node test/moneygate_test.js

# The money fixtures: both assertion packs against their reference implementation, both
# --self-test runs (per ASSERTION, not per invariant), and the plants that neuter one.
# The command prints its own count.
node test/fixtures_test.js

# What the assertion packs cannot reach: NO OUTPUT, and grep exits 1 because it
# matched nothing. `readFileSync` of the fixtures beside them is their whole I/O.
grep -rnE "child_process|\bfetch\(|require\('(http|https|net|dns|tls)'\)|spawn\(|execFile|writeFileSync|appendFileSync|unlinkSync|process\.env\." \
  plugins/sheleg-dev/skills/*/fixtures/*.mjs

# The entire I/O surface of the only two executable files: eleven lines. Three
# built-in requires, the copy/mkdir/remove calls, homedir, and install.sh's
# rm -rf + cp -R. No process, no socket, no network.
grep -nE "require|child_process|exec|spawn|fetch|socket|rm -rf|cp -R|copyFileSync|mkdirSync|rmSync|homedir" bin/sheleg-dev.js install.sh

# Live-key shapes across the skill payload: one line, and it is a placeholder.
grep -rnE "sk_live_[A-Za-z0-9]|rk_live_[A-Za-z0-9]|whsec_[A-Za-z0-9]{8}|BEGIN [A-Z ]*PRIVATE KEY" plugins

# What npm publishes, and nothing else: 62 files.
npm pack --dry-run
```
