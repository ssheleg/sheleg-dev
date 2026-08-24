# Releases, deploys, and health that means something

Read when wiring Sentry into a deploy script, when issues show no suspect
commits, or when a service reports healthy while serving nobody.

## Contents

- [The version contract](#the-version-contract)
- [The four release commands](#the-four-release-commands)
- [In a deploy script, non-fatally](#in-a-deploy-script-non-fatally)
- [What set-commits --auto needs](#what-set-commits---auto-needs)
- [Health that means something](#health-that-means-something)
- [Cron monitors](#cron-monitors)

## The version contract

**The version string you create in Sentry and the one the SDK reports as
`release` must be byte-identical.** When they differ, every issue attaches to a
release that has no commits, suspect-commit attribution silently does nothing,
and "which change broke this" stays unanswerable. Nothing errors. It reads as
Sentry being unhelpful.

Pick one source and use it on both sides.

| Platform | The value | Read in the app as |
|---|---|---|
| Heroku | slug commit | `os.getenv("HEROKU_SLUG_COMMIT")` |
| Vercel | commit SHA | `os.getenv("VERCEL_GIT_COMMIT_SHA")` |
| GitHub Actions | `github.sha` | `os.getenv("GITHUB_SHA")` |
| Anywhere | `git rev-parse HEAD` | inject it at build time |

```python
RELEASE = os.getenv("HEROKU_SLUG_COMMIT") or os.getenv("RELEASE")
sentry_sdk.init(dsn=..., release=RELEASE, environment=...)
```

```bash
VERSION="$(git rev-parse HEAD)"    # the same string, on the other side
```

`sentry release propose-version` will invent one, which is convenient and
exactly the thing that drifts. Prefer an explicit value both sides can derive.

## The four release commands

```bash
sentry release create      "<org>/$VERSION" --project <project> --finalize
sentry release set-commits "<org>/$VERSION" --auto
sentry release deploy      "<org>/$VERSION" <environment>
sentry release list        "<org>/<project>" --limit 5
```

- `--finalize` marks it released now. Omit it when you create the release
  before the code is live and call `sentry release finalize` afterwards.
- `set-commits --auto` derives the commit range from the previous release.
  `--local` uses local git history instead when the repository is not linked.
- `deploy` records environment and timing, which is what "released 4 minutes
  before the first error" in the UI is built from.

## In a deploy script, non-fatally

Release bookkeeping records what happened; it does not make it happen. A deploy
that reached production must never be reported as failed because a bookkeeping
call did not land.

```bash
notify_sentry() {
  local version org_project
  version="$(git rev-parse HEAD)"
  org_project="${SENTRY_ORG:?}/${SENTRY_PROJECT:?}"

  command -v sentry >/dev/null || { log "sentry CLI absent — skipping"; return 0; }
  sentry auth status >/dev/null 2>&1 || { log "sentry not authenticated — skipping"; return 0; }

  sentry release create "${SENTRY_ORG}/${version}" \
      --project "${SENTRY_PROJECT}" --finalize >/dev/null 2>&1 \
    || { log "could not create the release — continuing"; return 0; }
  sentry release set-commits "${SENTRY_ORG}/${version}" --auto >/dev/null 2>&1 \
    || log "could not attach commits (repository linked in Sentry?) — continuing"
  sentry release deploy "${SENTRY_ORG}/${version}" production >/dev/null 2>&1 \
    || log "could not mark the deploy — continuing"
  log "Sentry: release ${version:0:8} recorded for ${org_project}"
}
notify_sentry
```

Under `set -euo pipefail` every branch must return 0 explicitly, or the guard
you wrote becomes the thing that fails the deploy. Test it with the project
deliberately absent:

```bash
bash -c 'set -euo pipefail; . ./deploy.sh --source-only; notify_sentry; echo "exit $?"'
```

Order matters: record the release **after** the code is live, or the first
errors from the new build arrive before the release exists and attach to the
previous one.

## What set-commits --auto needs

`--auto` asks Sentry to resolve commits itself, which requires the repository to
be linked through a source-control integration (GitHub, GitLab, Bitbucket) in
the org's settings. Without it the call fails and the release still exists —
useful, minus attribution.

```bash
sentry repo list <org>              # what is linked
sentry release set-commits "<org>/$VERSION" --local   # fallback: local git history
```

`--local` needs the deploy to run from a real checkout with history, not a
shallow clone. CI defaults to `fetch-depth: 1`; set it to `0` when using
`--local`.

## Health that means something

Observed 2026-08-24: a credential was rotated, and for ten minutes the platform
reported the process `up` with a clean log while the upstream API returned `401`
to every call. No user was served. Nothing in the system could tell the
difference between that and working.

**Sentry sees exceptions. It does not see a connection that quietly stopped
working**, because nothing raises. Two different failures, two different checks:

| Failure | Caught by |
|---|---|
| Code raises | Sentry, automatically |
| Credential revoked, connection idle | a periodic check that asserts authorization |
| Process died | the platform's own supervisor |
| Job stopped running | a cron monitor |

For a worker holding a long-lived authenticated connection:

```python
async def assert_still_authorized(client):
    """Exit non-zero rather than idle in a state that serves nobody.
    A crash loop is visible; a silent zombie is not."""
    try:
        await client.get_me()
    except AuthError:
        logger.error("Credential no longer valid — exiting so the platform restarts us")
        sys.exit(1)
```

The rule generalises: **liveness asserts the thing the service exists to do.**
Anything weaker reports a process, and a process is not a service.

## Cron monitors

For work that is supposed to happen on a schedule, absence is the failure and
absence raises nothing.

```bash
sentry monitor list
```

Wrap the job so Sentry is told it started and finished; a missed check-in then
becomes an alert. This is the only shape here that catches "it stopped running"
rather than "it ran and threw".
