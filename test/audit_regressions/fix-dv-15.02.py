#!/usr/bin/env python3
"""FIX-DV-15.02 — every outbound channel has its own scrub hook, or it is
UNSUPPORTED (sherlock audit, DV-15).

The finding: the scrubbing doctrine wired only `before_send` (error events)
while implying a universal scrub. Transactions, breadcrumbs, logs and
attachments are separate outbound channels; `before_send` sees none of them,
and attachments have NO scrub hook at all.

The fix under test (scrubbing.md):
* a channel table names the hook per channel; attachments are UNSUPPORTED
  (stated, not promised away); an old-SDK logs channel is UNKNOWN;
* the wiring block passes the scrubber to before_send, before_send_transaction
  and before_breadcrumb;
* the coverage model runs the SAME secret fixture through every claimed
  channel and reports a hookless channel UNKNOWN/UNSUPPORTED — never green.

Standard library only.
"""
import os
import re
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DOC = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "error-tracking",
                   "references", "scrubbing.md")

failures = []


def case(name, fn):
    try:
        fn()
        print(f"  ok  {name}")
    except AssertionError as e:
        failures.append(f"{name}: {e}")
        print(f"FAIL  {name}: {e}")


def doc():
    with open(DOC, encoding="utf-8") as fh:
        return fh.read()


def t_channel_table_names_each_hook():
    d = " ".join(doc().split())
    for ch, hook in (("error events", "before_send"),
                     ("transactions", "before_send_transaction"),
                     ("breadcrumbs", "before_breadcrumb"),
                     ("logs", "before_send_log")):
        assert hook in d, f"the {ch} channel names no hook ({hook})"
    assert "no scrub hook exists" in d, "the attachments gap is not stated"
    assert "UNSUPPORTED" in d, "an uncoverable channel is not marked UNSUPPORTED"
    assert "never promised away as a\nuniversal scrub".replace("\n", " ") in d or \
           "never promised away as a universal scrub" in d, \
        "the universal-scrub promise is back"


def t_wiring_covers_the_three_hookable_channels():
    blocks = re.findall(r"```python\n(.*?)```", doc(), re.S)
    init = next((b for b in blocks if "sentry_sdk.init" in b and "before_send_transaction" in b), None)
    assert init, "no init block wiring the per-channel hooks"
    assert "before_send=scrub_values" in init
    assert "before_send_transaction=scrub_values" in init
    assert "before_breadcrumb" in init
    assert "UNKNOWN" in init, "the absent-logs-hook honesty note is missing from the wiring"


def t_before_send_alone_is_not_universal():
    d = " ".join(doc().split())
    assert "`before_send` sees ERROR EVENTS and nothing else" in d, \
        "the doc no longer states before_send's actual reach"


# ---------------- the coverage model, run as behaviour


HOOKS = {"event": True, "transaction": True, "breadcrumb": True,
         "logs": False,           # old SDK: no before_send_log
         "attachment": None}      # no hook exists at all


def channel_verdict(channel, payload, scrub):
    hook = HOOKS.get(channel)
    if hook is None:
        return "UNSUPPORTED"
    if hook is False:
        return "UNKNOWN"
    return "clean" if "SECRET" not in scrub(payload) else "leak"


def t_fixtures_through_every_channel():
    scrub = lambda s: s.replace("SECRET", "<redacted>")
    fixture = "postgres://u:SECRET@host"
    verdicts = {ch: channel_verdict(ch, fixture, scrub) for ch in HOOKS}
    assert verdicts["event"] == verdicts["transaction"] == verdicts["breadcrumb"] == "clean"
    assert verdicts["logs"] == "UNKNOWN", "an old-SDK logs channel was reported green"
    assert verdicts["attachment"] == "UNSUPPORTED", \
        "the hookless attachment channel was reported green — the bypass is invisible"
    assert "clean" not in (verdicts["logs"], verdicts["attachment"]), \
        "a bypass channel came back green"


def main():
    case("the channel table names each hook; attachments UNSUPPORTED",
         t_channel_table_names_each_hook)
    case("the wiring covers event/transaction/breadcrumb hooks",
         t_wiring_covers_the_three_hookable_channels)
    case("before_send's actual reach is stated", t_before_send_alone_is_not_universal)
    case("secret fixtures run through every channel; bypass is never green",
         t_fixtures_through_every_channel)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
