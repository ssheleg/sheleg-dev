# Stripe's own agent toolchain

**Load this when** starting a Stripe integration from nothing, or when the
agent is about to guess an API shape, a parameter name or a current best
practice. Stripe ships tooling built for agents; using it is faster and more
accurate than recalling the API from training data.

*Read from `docs.stripe.com/agents`, `/skills`, `/mcp` and the CLI's own
`--help` on 2026-08-11, against Stripe CLI 1.45.2 and the Claude Code plugin
`stripe@claude-plugins-official` 0.5.1; the plugin re-read at 0.6.1 on
2026-08-25. Re-check before quoting a version.*

## Contents

- [The four pieces](#the-four-pieces)
- [CLI](#cli)
- [Getting keys without an account](#getting-keys-without-an-account)
- [Skills and plugins](#skills-and-plugins)
- [MCP server](#mcp-server)
- [Plain-text documentation](#plain-text-documentation)
- [Key handling for agents](#key-handling-for-agents)
- [When none of it is available](#when-none-of-it-is-available)

## The four pieces

| Piece | What it gives an agent | Entry point |
|---|---|---|
| **CLI** | resource discovery, webhook forwarding, event triggers, logs, sandboxes | `npm install -g @stripe/cli` |
| **Skills / plugin** | Stripe's own instructions: product choice, billing, tax, security, Connect | `stripe agent setup` |
| **MCP server** | live calls against the account, doc search, an implementation planner | `https://mcp.stripe.com` |
| **Plain-text docs** | any page as Markdown | append `.md` to a `docs.stripe.com` URL |

## CLI

```bash
npm install -g @stripe/cli          # v1.43.3+ for `stripe docs`
stripe login                        # browser consent — a human step
stripe agent setup                  # detects Claude Code / Codex / Cursor, installs plugins
stripe agent setup --status --json  # read-only: what is already installed
```

Discovery commands worth knowing before writing any call — they answer from the
installed CLI rather than from memory:

```bash
stripe --map                        # the whole command tree
stripe resources                    # every API resource
stripe <resource> --help            # operations and common parameters
stripe help <resource> <operation>  # the full parameter list
stripe docs                         # read docs.stripe.com in the terminal
```

Development loop:

```bash
stripe listen --forward-to localhost:3000/api/billing/webhook
stripe trigger checkout.session.completed
stripe logs tail                    # watch API requests, including 403s from a restricted key
```

## Getting keys without an account

```bash
stripe sandbox create --from-git    # resolves the email from git config
stripe sandbox create --email you@example.com
```

Provisions a sandbox through a proof-of-work challenge — **no browser, no
signup** — and writes the test keys into the current CLI profile, so subsequent
commands work immediately. Falls back to browser login on server errors. If a
key is already configured, the same command opens the sandbox management page
instead.

This is the honest answer to "I want to try the integration before I have an
account", and it is far better than inventing placeholder ids.

## Skills and plugins

`stripe agent setup` installs the official plugin for each detected harness. The
per-harness commands, if you prefer them explicit:

```bash
claude plugin install stripe@claude-plugins-official   # Claude Code
codex plugin add stripe@openai-curated                 # Codex
# Cursor: run /add-plugin stripe inside the agent
npx skills add https://docs.stripe.com                 # any other agent — manual, no auto-update
```

Manually installed skills do not auto-update: `npx skills update -y`.

The machine-readable index is
`https://docs.stripe.com/.well-known/skills/index.json`; individual files sit
under `https://docs.stripe.com/.well-known/skills/<filepath>`. Seven skills at
the time of writing: `stripe-best-practices`, `stripe-docs`, `stripe-apps`,
`stripe-projects`, `stripe-directory`, `connect-recommend`, `upgrade-stripe`.

**Division of labour with this skill.** `stripe-best-practices` decides *which
Stripe primitive* and states Stripe's own rules (product catalogue modelling,
tax, dynamic payment methods, Metronome for new usage-based billing, key
hygiene). `stripe-docs` looks things up. This skill covers what happens on
*your* side of the boundary — reconciling Stripe's state into your database.
When they disagree about anything Stripe-side, Stripe's skill wins.

What Stripe's own skills do **not** cover, measured over plugin 0.6.1 on
2026-08-25: a grep for `retention`, `coupon` and `churn` across all eight returns
nothing about cancellation deflection. The save offer is this skill's ground by
absence, not by preference — see
[`cancellation-and-retention.md`](cancellation-and-retention.md).

## MCP server

```bash
claude mcp add --transport http stripe https://mcp.stripe.com/
claude /mcp                         # OAuth consent — a human step
```

Other clients take `{"url": "https://mcp.stripe.com"}` (Cursor `~/.cursor/mcp.json`,
VS Code `.vscode/mcp.json` with `"type": "http"`). Clients without OAuth may
send a **restricted** key as `Authorization: Bearer rk_…`; connected-account
calls add a `Stripe-Account: acct_…` header.

Tools worth reaching for by name:

| Tool | Use |
|---|---|
| `stripe_implementation_planner` | a tailored integration plan before any code |
| `search_stripe_documentation` | current docs, in preference to a web search |
| `stripe_api_search` / `stripe_api_details` | find a method, then read its exact parameters |
| `stripe_api_read` / `stripe_api_write` | call the API without a per-endpoint tool |
| `create_refund`, `get_stripe_account_info`, `stripe_report` | the dedicated ones |

Two cautions from Stripe's own page, both worth honouring: **enable human
confirmation for tool calls**, and be careful combining this server with other
MCP servers — tool output is untrusted input and prompt injection is the
documented risk. OAuth sessions are listed and revocable in Dashboard user
settings; administrators can revoke other users' sessions and enable or disable
MCP access per environment.

## Plain-text documentation

Append `.md` to any documentation URL:

```
https://docs.stripe.com/billing/subscriptions/webhooks.md
https://docs.stripe.com/api/subscriptions/update.md
```

Cheaper and cleaner than fetching the rendered page, and it is the same content
`stripe docs` reads in the terminal.

## Key handling for agents

Stripe's security reference is blunt about this, and it applies doubly to code
an agent writes:

- Prefer **restricted keys** (`rk_`) over secret keys (`sk_`), one per service,
  minimum permissions. Migrate by watching `stripe logs tail` and adding
  permissions until the 403s stop.
- Keys live in a **secrets vault** where the platform has one (AWS Secrets
  Manager, GCP Secret Manager, Azure Key Vault); environment variables are the
  fallback, not the goal. On Vercel, mark them sensitive.
- Never in source, never in logs, never in error messages, never in client-side
  code. `sk_live_…` or `rk_live_…` in a repository is an incident, not a lint
  warning — a pre-commit hook for `sk_`/`rk_` is cheap.
- Separate keys per environment, and rotate when someone with access leaves.

## When none of it is available

The toolchain is an accelerator, not a dependency. With no CLI, no MCP and no
network:

- write the integration from the invariants in `SKILL.md` — they are the part
  that does not change between API versions;
- pin the API version the installed SDK ships with, and say in a comment that
  it was not verified against the changelog;
- use the SDK's own type definitions as the parameter reference (they are
  generated from the same spec the docs are);
- state plainly which facts could not be verified, rather than asserting a
  parameter name you recall. A wrong parameter fails loudly; a wrong *default*
  bills someone.
