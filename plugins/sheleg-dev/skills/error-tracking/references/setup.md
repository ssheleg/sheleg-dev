# Sentry setup — install, auth, projects, DSN, MCP

Read when adding Sentry to a project for the first time, or when a CLI call is
refused and you need to tell a policy problem from an auth problem.

## Contents

- [Install](#install)
- [Authenticate](#authenticate)
- [Token taxonomy — which kind can do what](#token-taxonomy--which-kind-can-do-what)
- [Find what already exists](#find-what-already-exists)
- [Create a project](#create-a-project)
- [Get the DSN and wire it in](#get-the-dsn-and-wire-it-in)
- [Declare the MCP server](#declare-the-mcp-server)
- [SDK options for a backend service](#sdk-options-for-a-backend-service)

All commands below were executed on 2026-08-24 against `sentry` 0.43.0 and
`sentry-sdk` 2.19.2. Where a version matters, it is named.

## Install

```bash
brew install getsentry/tools/sentry     # macOS, preferred: no piping a remote script to a shell
curl https://cli.sentry.dev/install -fsS | bash   # the documented alternative
```

Then check for a shadow — two prefixes, and the older copy usually wins:

```bash
which -a sentry | while read p; do printf '%-34s %s\n' "$p" "$("$p" --version 2>&1 | head -1)"; done
```

Remove the stale copy rather than reordering `PATH`. Credentials live in
`~/.sentry/`, not beside the binary, so this does not log you out.

## Authenticate

```bash
sentry auth                    # OAuth device flow: prints a URL and a code
sentry auth --token <TOKEN>    # non-interactive, for CI
sentry auth status             # who, which token, when it expires
sentry auth logout
```

`sentry auth` writes to `~/.sentry/cli.db`. Override with `SENTRY_CONFIG_DIR`.
`SENTRY_URL` points at self-hosted instances.

**The device-flow token expires.** `auth status` prints the expiry — one
observed token had three days left. A CI job depending on it fails on a
Wednesday for no visible reason; CI wants a token, not the device flow.

## Token taxonomy — which kind can do what

| Kind | Created in | Scopes | Use it for |
|---|---|---|---|
| **OAuth device flow** (`sentry auth`) | the CLI | fixed by the flow; measured: `event:read`, `event:write`, `member:read`, `org:read`, `project:admin`, `project:read`, `project:write`, `team:read`, `team:write` — **no `org:write`/`org:admin`** | interactive work at a desk |
| **Organization Token** | Settings → Developer Settings → Organization Tokens | limited, not customizable | CI. Sentry's own recommendation for it |
| **Internal Integration** | the integration platform | customizable, **full API access** | org-level automation, including creating projects |
| **Personal Token** | Account → Personal Tokens | chosen at creation, never editable after | a one-off at a desk. Explicitly discouraged for CI |

Print the scopes a token actually carries, rather than inferring them from how
it was made:

```bash
sentry api "/" --json          # {"auth": {"scopes": [...]}, "user": {...}}
```

## Create a project

```bash
sentry project create <org>/<name>:<platform> --team <team> --dry-run
sentry project create <org>/<name>:<platform> --team <team> --json
```

`--dry-run` prints the resolved org, team, slug and platform without creating
anything. Use it: the org must be in the argument or the command refuses.

### When it returns 403

```
Your organization has disabled this feature for members.
This is an org-level policy setting, not an auth issue.
```

The message is accurate and easy to disbelieve, because it appears **even for an
org owner**. The policy is evaluated against the token's scopes, not the human's
role, so an owner acting through a device-flow token is treated as a member.

```bash
sentry org view <org> --json | grep -E 'allowMemberProjectCreation|allowMemberInvite'
```

`allowMemberProjectCreation: false` is the cause. `POST /teams/{org}/{team}/projects/`
fails identically — the error names it as an alternative, but it is the same
policy underneath.

Resolutions, cheapest first:

1. Create the project once in the web UI. One browser action, then everything
   else is scriptable forever.
2. Flip the org setting. Also a browser action, and it loosens a policy that
   exists for a reason — decide deliberately.
3. Issue an Internal Integration token and `sentry auth --token` with it. The
   only route that makes project creation itself scriptable.

## Get the DSN and wire it in

```bash
sentry project view <org>/<project> --json \
  | python3 -c "import json,sys; print(json.load(sys.stdin)[0]['dsn'])"
```

The response is a **list**, hence the `[0]`. The DSN is the app's ingest
address; put it wherever that host keeps configuration:

```bash
heroku config:set SENTRY_DSN='https://…@o….ingest.sentry.io/…' -a <app>
fly secrets set SENTRY_DSN='…'
gh secret set SENTRY_DSN --body '…'        # only if CI itself reports errors
```

A DSN is write-only ingest, not an API credential — see the table in `SKILL.md`.
Treat it as configuration, not as a secret to be guarded like a token, and still
do not commit it.

## Declare the MCP server

```bash
curl -si https://mcp.sentry.dev/mcp | grep -i www-authenticate
```

A `401` whose `www-authenticate` carries `resource_metadata=` means OAuth, which
means **the agent's own config, never a shared MCP gateway** — an OAuth upstream
names itself as the resource at its own address, so a client pointed at a
gateway must reject the mismatch and the flow cannot complete.

```bash
claude mcp add --transport http sentry https://mcp.sentry.dev/mcp/<org>/<project>
```

Scoping is optional and narrows what the server sees:
`…/mcp`, `…/mcp/<org>`, `…/mcp/<org>/<project>`. Narrow it.

Everything the MCP does, the CLI also does. A machine without it loses no
capability, so never let a procedure depend on it.

## SDK options for a backend service

```python
sentry_sdk.init(
    dsn=SENTRY_DSN,
    environment=ENVIRONMENT,             # "production" | "staging" | "local"
    release=RELEASE,                     # MUST equal the version you create in Sentry
    event_scrubber=EventScrubber(        # see references/scrubbing.md
        denylist=DEFAULT_DENYLIST + ["dsn", "database_url", "auth_key"],
        recursive=True,
    ),
    before_send=scrub_values,
    send_default_pii=False,              # excludes headers, IPs, and similar
    traces_sample_rate=0.0,              # tracing off unless someone reads the spans
)
```

Notes that decide behaviour:

- `environment` defaults to `"production"`. A local run that forgets to set it
  pollutes the production feed with a developer's laptop.
- `release` defaults to `None` and the SDK's auto-detection is not reliable
  enough to depend on. Set it.
- `traces_sample_rate` defaults to `None`; tracing is off unless it or
  `traces_sampler` is set. Turning it on costs quota — do it when someone is
  going to read the result, not by default.
- `profiles_sample_rate` is the current profiling option and is not deprecated.
- `send_default_pii=False` (the default) keeps integrations from attaching
  request headers and IP addresses. It does **not** scrub your own payloads;
  that is the scrubber's job.
