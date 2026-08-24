# Keeping secrets out of Sentry events

Read before switching Sentry on in any service that has ever handled a
credential — which is every service with a database.

## Contents

- [The measurement](#the-measurement)
- [What each layer covers](#what-each-layer-covers)
- [Layer 1 — keys, by the SDK](#layer-1--keys-by-the-sdk)
- [Layer 2 — values, by you](#layer-2--values-by-you)
- [The test that guards the boundary](#the-test-that-guards-the-boundary)
- [Re-measuring after an SDK upgrade](#re-measuring-after-an-sdk-upgrade)

## The measurement

`sentry-sdk` 2.19.2, run on 2026-08-24:

```python
from sentry_sdk.scrubber import EventScrubber

LEAK = "postgresql://u4fc:SUPERSECRETPW@host.rds.amazonaws.com:5432/db"
event = {
    "message": f"could not connect to {LEAK}",
    "exception": {"values": [{"value": f"FATAL: auth failed for {LEAK}"}]},
    "extra": {"password": "caught", "database_url": LEAK},
}
EventScrubber().scrub_event(event)

# extra.password      -> AnnotatedValue           (scrubbed: key is on the denylist)
# extra.database_url  -> untouched                (key is NOT on the denylist)
# message             -> untouched                (values are never inspected)
# exception value     -> untouched
assert "SUPERSECRETPW" in str(event)
```

Two facts follow, and neither is a criticism of Sentry — they are the boundary
of what that layer claims to do:

1. The default denylist holds **32 keys**, and **`dsn` and `database_url` are
   not among them**. Present: `password`, `passwd`, `secret`, `api_key`,
   `apikey`, `auth`, `credentials`, `token`, `session`, `authorization`, and
   similar.
2. The scrubber matches **key names**. A credential that lives inside a string
   value — a connection URL in a log line that became a message, an exception
   from a driver that echoes the DSN — is not seen at all.

Fact 2 is the one that bites. A service that prints a database URL anywhere near
an error is common; adding Sentry to it forwards that password to a third party
on every exception, with a wider reach than the log had.

## What each layer covers

| | Matches on | Catches | Misses |
|---|---|---|---|
| `EventScrubber` (SDK, default on) | key names, against a denylist | `extra.password`, `request.headers.authorization` | anything inside a string value; keys not on the list |
| `before_send` (yours) | the shape of the value | `postgres://u:pw@host` wherever it appears | keys whose value is not URL-shaped |

They are complementary, not alternatives. Run both.

## Layer 1 — keys, by the SDK

```python
from sentry_sdk.scrubber import DEFAULT_DENYLIST, EventScrubber

EXTRA_DENYLIST = ["dsn", "database_url", "bot_token", "api_hash", "auth_key", "session"]

sentry_sdk.init(
    ...,
    event_scrubber=EventScrubber(
        denylist=DEFAULT_DENYLIST + EXTRA_DENYLIST,
        recursive=True,     # off by default; nested payloads otherwise escape
    ),
)
```

`recursive=False` is the default. Any structure deeper than one level — a
config dict inside `extra`, a nested exception context — is not walked. Turn it
on unless you have measured the cost on a payload you actually send.

Add to `EXTRA_DENYLIST` every key your own code uses for a secret. The default
list knows Sentry's world, not your variable names.

## Layer 2 — values, by you

Match the shape, not a list of known names — a newly added secret is then
covered by default instead of leaking until someone updates a list.

```python
import re

_URL_CREDENTIALS = re.compile(r"(?P<scheme>[a-zA-Z][a-zA-Z0-9+.-]*://)(?P<user>[^:/@\s]+):(?P<pw>[^@/\s]+)@")
_REDACTED = "<redacted>"

def scrub_text(value):
    if not isinstance(value, str):
        return value
    return _URL_CREDENTIALS.sub(rf"\g<scheme>\g<user>:{_REDACTED}@", value)

def scrub_values(event, _hint=None):
    def walk(node):
        if isinstance(node, dict):
            return {k: walk(v) for k, v in node.items()}
        if isinstance(node, (list, tuple)):
            return type(node)(walk(v) for v in node)
        return scrub_text(node)
    try:
        return walk(event)
    except Exception:
        # Returning None DROPS the event. A scrubber bug must not silently
        # switch error tracking off.
        return {"message": "event dropped by scrubber", "level": "error"}
```

Three properties that matter:

- **Keep the user and host.** A fully redacted URL is useless for debugging.
  Redact the password only.
- **Scheme-agnostic.** `amqps://`, `redis://`, `mongodb+srv://` leak the same way.
- **Never return `None`.** In `before_send` that discards the event. A bug in
  the scrubber then reads as "Sentry is quiet", which is indistinguishable from
  "nothing is broken".

## The test that guards the boundary

The important assertion is the one that says **the SDK layer alone still leaks**.
It documents why layer 2 exists, and it goes red the day that stops being true —
which is exactly when you want to be told.

```python
def test_the_sdk_scrubber_alone_would_leak_it():
    """If this fails, the SDK started scrubbing values and layer 2 may be
    redundant. Check before deleting it."""
    from sentry_sdk.scrubber import EventScrubber
    event = {"message": f"could not connect to {LEAK}"}
    EventScrubber().scrub_event(event)
    assert "SUPERSECRETPW" in str(event)

def test_our_layer_catches_what_the_sdk_misses():
    assert "SUPERSECRETPW" not in str(scrub_values({"message": f"…{LEAK}"}))

def test_extra_denylist_names_what_the_default_omits():
    from sentry_sdk.scrubber import DEFAULT_DENYLIST
    for key in ("dsn", "database_url"):
        assert key not in DEFAULT_DENYLIST, f"{key} is covered now; drop it from EXTRA_DENYLIST"
        assert key in EXTRA_DENYLIST
```

The third one keeps the extra list honest: when Sentry adds a key to its
default, the test tells you to stop carrying it yourself.

**Never put a real credential in a fixture.** Use an obviously fake value of the
same shape. A test that asserts a password is scrubbed, while carrying that
password in the repository, has moved the leak rather than closed it.

## Re-measuring after an SDK upgrade

Both facts on this page are version-dependent. After any `sentry-sdk` bump:

```bash
python3 -c "
from sentry_sdk.scrubber import DEFAULT_DENYLIST as D
print(len(D), 'keys'); print([k for k in ('dsn','database_url') if k in D], 'now covered by default')
"
python3 -m pytest -k scrubber        # the boundary tests above
```

If `dsn` or `database_url` appear in the default list, drop them from
`EXTRA_DENYLIST`. If the value test goes red, layer 2's job changed — read what
the SDK now does before removing it.
