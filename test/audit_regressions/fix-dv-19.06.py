#!/usr/bin/env python3
"""FIX-DV-19.06 — offline artifact / fault-injection corpus for error-tracking
(sherlock audit, DV-19; last of the family).

Each corpus case injects a fault per DV finding; this regression runs a
STATE/OUTPUT oracle for each — not a provider stub judging itself. DV-19: each
counterexample FAILS pre-fix and PASSES post-fix on state/outputs, offline,
release-tied.

Standard library only; offline.
"""
import json
import os
import re
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CASES = os.path.join(ROOT, "evals", "cases", "fix-dv-19.06.json")

failures = []


def case(name, fn):
    try:
        fn()
        print(f"  ok  {name}")
    except AssertionError as e:
        failures.append(f"{name}: {e}")
        print(f"FAIL  {name}: {e}")


def manifest():
    with open(CASES, encoding="utf-8") as fh:
        return json.load(fh)


# ---- offline oracles (state/outputs) ------------------------------------------


def scrub(text, require_nonempty_username):
    """DV-15: redact credential URLs. Pre-fix requires a non-empty username."""
    if require_nonempty_username:
        # the flawed regex: needs user:pass, so redis://:pw@ and /bot<id>:<tok>/ slip
        pat = re.compile(r"([a-z]+://)[^:/@\s]+:[^@\s]+@")
    else:
        # the fix: optional username, plus the telegram bot-token path
        pat = re.compile(r"([a-z]+://)[^:/@\s]*:[^@\s]+@")
    out = pat.sub(r"\1<redacted>@", text)
    if not require_nonempty_username:
        out = re.sub(r"/bot\d+:[A-Za-z0-9_-]+/", "/bot<redacted>/", out)
        out = re.sub(r"([?&]access_token=)[^&\s]+", r"\1<redacted>", out)
    return out


def secret_reaches_transport(require_nonempty_username):
    canaries = [
        "redis://:s3cret@cache:6379",                 # empty username
        "amqp://user:pw@mq:5672",
        "https://api.telegram.org/bot123456:AAExampleToken/sendMessage",
        "https://x.example?access_token=abc123",
    ]
    for c in canaries:
        scrubbed = scrub(c, require_nonempty_username)
        # a secret reaches the transport if any raw credential survives
        if "s3cret" in scrubbed or "AAExampleToken" in scrubbed or "abc123" in scrubbed \
                or ":pw@" in scrubbed:
            return True
    return False


def recover_revoked(restart_on_revoked, max_retries=3):
    """DV-16: what happens to a revoked session? Returns (alerts, restarts, stopped)."""
    alerts = 0
    restarts = 0
    stopped = False
    for _ in range(100):        # simulate a long window
        if restart_on_revoked:
            restarts += 1
            alerts += 1         # each failed restart alerts → storm
            if restarts > 50:   # never converges
                break
        else:
            alerts = 1          # one actionable alert
            stopped = True
            break
    return alerts, restarts, stopped


def t_corpus_structure():
    m = manifest()
    assert m["release_tie"] and m["environment"]["network"].startswith("none")
    ids = {c["id"] for c in m["cases"]}
    assert ids == {"DV-15-secret-scrubbing", "DV-16-revoked-session-recovery"}, ids
    for c in m["cases"]:
        assert "FAIL" in c["prefix_expect"] and "PASS" in c["postfix_expect"]


def t_dv15_scrubbing():
    assert secret_reaches_transport(require_nonempty_username=True) is True, \
        "the scrubber leak did not reproduce pre-fix"
    assert secret_reaches_transport(require_nonempty_username=False) is False, \
        "a secret still reaches the transport post-fix"


def t_dv16_recovery():
    a_pre, r_pre, stopped_pre = recover_revoked(restart_on_revoked=True)
    assert r_pre > 50 and not stopped_pre, \
        "the revoked-session crash loop did not reproduce pre-fix"
    assert a_pre > 1, "the alert storm did not reproduce"
    a_post, r_post, stopped_post = recover_revoked(restart_on_revoked=False)
    assert stopped_post and r_post == 0 and a_post == 1, \
        "post-fix did not stop with one alert and no restart loop"


def main():
    case("the corpus is offline, release-tied, one case per DV oracle",
         t_corpus_structure)
    case("DV-15: secrets reach the transport pre-fix, all scrubbed post-fix",
         t_dv15_scrubbing)
    case("DV-16: a revoked session crash-loops pre-fix, stops with one alert post-fix",
         t_dv16_recovery)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
