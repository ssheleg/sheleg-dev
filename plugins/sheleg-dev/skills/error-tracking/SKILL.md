---
name: error-tracking
description: >-
  Use when wiring error tracking into a product — adding Sentry to a service, deciding what a
  DSN is and where it may live, keeping secrets out of events before they reach a third party,
  tying releases to commits so a stack trace names the change that caused it, or judging whether
  a green health check means anything. Covers the Sentry SDK options that matter for a backend,
  the two different tools both called sentry, the auth-token taxonomy and which kind can create
  a project, and the MCP server with the config channel it belongs in. Triggers - "add Sentry",
  "set up error tracking", "SENTRY_DSN", "sentry-cli", "sentry mcp", "scrub secrets from
  errors", "release tracking", "suspect commits", "why is Sentry empty", "подключить Sentry",
  "трекинг ошибок", "секреты в Sentry", "релизы в Sentry", "наблюдаемость". NOT for judging an
  agent's trajectory (agent-evals), triaging tickets in a tracker (triage-issue), or choosing an
  uptime vendor.
license: MIT
metadata:
  version: 0.9.1
---

# error-tracking — Sentry wired so it does not leak, and so a stack trace names a commit

Adding Sentry is four lines of SDK setup, which is why it is usually done badly.
The four failures below were all observed, on this machine, in one session, by an
agent working without this skill.

| Observed failure | What it cost |
|---|---|
| Called "get a DSN" a manual human step needing an account | The account existed and the CLI was already authenticated. Error tracking sat switched off for no reason |
| Wrote a `before_send` scrubber without knowing `EventScrubber` exists and runs by default | Could not say which layer covered what, so could not say whether the code was redundant or load-bearing |
| Did not know the MCP is OAuth | Would have declared it in the machine's shared gateway, where an OAuth flow cannot complete |
| Would have set a DSN and stopped | Every issue lands on a release with no commits; suspect-commit attribution never works |

## The one that actually leaks

**Sentry's built-in scrubber matches KEY NAMES. It does not look inside string
values.** A credential embedded in a URL — inside a message, an exception value,
a breadcrumb — passes through untouched.

Measured against `sentry-sdk` 2.19.2 on 2026-08-24:

```python
from sentry_sdk.scrubber import EventScrubber
event = {"message": "could not connect to postgresql://u:SUPERSECRET@host/db"}
EventScrubber().scrub_event(event)
assert "SUPERSECRET" in str(event)   # passes — it was NOT scrubbed
```

`EventScrubber` is on by default, its denylist holds 32 keys (`password`,
`token`, `api_key`, `auth`, `secret`, `authorization`, …), and **`dsn` and
`database_url` are not among them.**

So a service that already writes a database URL to its log — a common enough
mistake — starts forwarding that same password to a third party the moment
Sentry is added, with a wider blast radius than the log had.

**Two layers, always:**

```python
from sentry_sdk.scrubber import DEFAULT_DENYLIST, EventScrubber

sentry_sdk.init(
    dsn=..., environment=..., release=...,
    event_scrubber=EventScrubber(                 # layer 1 — keys
        denylist=DEFAULT_DENYLIST + ["dsn", "database_url", "auth_key"],
        recursive=True,
    ),
    before_send=scrub_values,                     # layer 2 — values
    send_default_pii=False,
)
```

Layer 2 is a regex over URL credentials. Write a test that asserts **layer 1
alone still leaks** — if that test ever goes red, Sentry started scrubbing
values and layer 2 may be redundant, which is a thing to learn from a red test
rather than never. Both layers, the regex and that test: `references/scrubbing.md`.

## A DSN is not an auth token

They are different objects and conflating them produces both paranoia and
carelessness in the wrong places.

| | DSN | Auth token |
|---|---|---|
| Direction | write-only ingest | full API |
| Lives in | the built artifact, client-side included | CI secrets, a developer's keychain |
| If it leaks | someone can send you junk events; rate-limit and rotate | someone can read your issues and change your org |
| Needed to | report an error | create a project, read issues, cut a release |

A DSN in a repository is untidy. An auth token in a repository is an incident.
**Neither the CLI nor the MCP removes the need for a DSN** — they operate Sentry,
they do not instrument your app. What they remove is the manual step of getting
one.

## Setting it up without a human in the loop

Before calling any of this a manual step, check — the answer is often that it is
already done:

```bash
sentry auth status          # already authenticated? (credentials in ~/.sentry)
sentry org list --json      # which orgs this token can see
sentry project list --json  # what already exists
```

To fetch a DSN for an existing project, which is what the app needs:

```bash
sentry project view <org>/<project> --json | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['dsn'])"
```

Full procedure — install, auth, project creation, wiring the DSN into a host's
config, and the MCP declaration: read `references/setup.md` when you are adding
Sentry to a project for the first time.

### The 403 that looks like an auth problem and is not

`sentry project create` can fail with:

```
Your organization has disabled this feature for members.
```

even when **you are the owner of that organization**. Measured 2026-08-24. The
cause is an org policy, `allowMemberProjectCreation: false`, evaluated against
the token's scopes rather than the human's role — and the OAuth device-flow
token that `sentry auth` stores carries `project:admin` and `team:write` but
**no `org:write` or `org:admin`**. The team-scoped endpoint
(`POST /teams/{org}/{team}/projects/`) fails identically; it is the same policy.

Check before assuming a bug:

```bash
sentry org view <org> --json | grep allowMemberProjectCreation
sentry api "/" --json                     # prints the token's actual scopes
```

Three ways out, in the order worth trying: create the project once in the web
UI; flip the org setting; or issue an **Internal Integration token**, which is
the only token type Sentry documents as granting the org-level API access that
programmatic project creation needs. Organization Tokens are the CI
recommendation but cannot do org-level operations, and personal tokens are
explicitly discouraged for CI. Table with the trade-offs: `references/setup.md`.

## Two different tools are called sentry

Confusing them wastes a debugging round, because commands from one silently do
not exist in the other.

| | `sentry` | `sentry-cli` |
|---|---|---|
| From | `cli.sentry.dev`, `brew install getsentry/tools/sentry` | `github.com/getsentry/sentry-cli` |
| Shape | agent-oriented; `issue explain`, `issue plan`, `api` like `gh api` | build-oriented; source maps, debug files |
| Auth | `sentry auth` — OAuth device flow, stored in `~/.sentry/` | `SENTRY_AUTH_TOKEN` |
| Both do | `release create / set-commits / finalize / deploy`, `project`, `org` | |

Either can run the release commands. Pick one per repository and say which in
the README, or two people will wire two halves.

**Check for a shadow before trusting a version.** Both install into different
prefixes; `~/.local/bin` typically precedes `/opt/homebrew/bin`, so an older
copy wins silently:

```bash
which -a sentry | while read p; do printf '%-34s %s\n' "$p" "$("$p" --version 2>&1 | head -1)"; done
```

Observed here: 0.38.0 shadowing 0.43.0. Credentials live in `~/.sentry/`, not
beside the binary, so removing the stale copy does not log you out.

## The MCP is OAuth, which decides where it is declared

`https://mcp.sentry.dev/mcp` answers an unauthenticated request with:

```
401  www-authenticate: Bearer realm="OAuth", …, resource_metadata="https://mcp.sentry.dev/.well-known/oauth-protected-resource/mcp"
```

That `www-authenticate` header carrying `resource_metadata` **is** the test for
OAuth. An OAuth upstream declares itself as the resource at its own address, so
a client pointed at a local gateway must reject the mismatch and the flow never
starts. **OAuth MCP servers therefore belong in the agent's own config, never
behind a shared MCP gateway.** Run the curl before choosing a channel; a static
token upstream goes to the gateway, an OAuth one does not.

```bash
claude mcp add --transport http sentry https://mcp.sentry.dev/mcp/<org>/<project>
```

The MCP is for reading and triaging from inside a session. It is an accelerator:
everything it does, the CLI also does, and a machine without it loses no
capability.

## Releases, or the stack trace names nothing

A release in Sentry is only useful if its version string is **identical** to
what the SDK reports as `release`. When they drift, issues attach to a release
with no commits and suspect-commit attribution silently does nothing — which
reads as "Sentry is not very good" rather than as a wiring bug.

Pick one source for the version and use it on both sides. On Heroku that is the
slug commit:

```python
RELEASE = os.getenv("HEROKU_SLUG_COMMIT") or os.getenv("RELEASE")
```

```bash
VERSION="$(git rev-parse HEAD)"          # the same value
sentry release create   "<org>/$VERSION" --project <project> --finalize
sentry release set-commits "<org>/$VERSION" --auto
sentry release deploy   "<org>/$VERSION" production
```

**Release bookkeeping is non-fatal.** A deploy that reached production must not
be reported as failed because a release call did not land. Guard each command so
it logs and continues; the deploy-script shape is in `references/releases.md`,
which also covers what `--auto` needs from your repository integration.

## A process that is up is not a service that works

Observed 2026-08-24: a bot token was rotated, and for ten minutes the platform
reported the dyno `up` with a clean log while the API returned `401` to every
call and no user was served. Nothing in the system could tell the difference.

**Liveness must assert the thing the service exists to do**, not that a process
exists. For anything holding a long-lived authenticated connection, check the
credential periodically and exit non-zero when it fails — a crash loop is
visible, a silent zombie is not. Sentry helps only if something raises; a
connection that stopped working without raising produces no event at all. Cron
monitors (`sentry monitor`) cover the shape where a job stops running.

## Degradation

- **Not Claude Code** (Cursor, Codex, skills CLI, the API container): no MCP, no
  `/command`. Everything here is CLI and SDK, both of which work anywhere with a
  shell — except the API container, which has no network and no package install,
  so treat this skill as Claude Code and Cursor only for the setup half.
- **`sentry` CLI absent**: say so once, then use the REST API directly with a
  token (`curl https://sentry.io/api/0/…`), or the web UI for the one-off. Do
  not loop on the missing binary.
- **MCP absent**: no capability is lost — read issues with `sentry issue list`.
- **Not authenticated, or a scope is missing**: interactive auth is a human
  step. State the exact command once, name what is blocked, and continue with
  everything that does not need it.

## Verify, do not assume

```bash
sentry auth status                                   # authenticated, and as whom
sentry api "/" --json                                # the token's real scopes
sentry project view <org>/<project> --json           # the DSN, and that it exists
sentry release list <org>/<project> --limit 3        # releases arriving at all
python3 -c "import sentry_sdk; print(sentry_sdk.VERSION)"
```

Two claims worth re-measuring rather than trusting from this page, because both
are version-dependent: the default denylist contents, and whether the SDK has
started scrubbing values. `references/scrubbing.md` carries the command for
each.
