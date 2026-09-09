#!/usr/bin/env python3
"""FIX-DV-16.01 — typed health states; a revoked session stops work until
fresh auth (sherlock audit, DV-16).

The finding: error-tracking prescribed "exit non-zero, a crash loop is
visible" for ANY credential failure, while telegram-userbots forbids a restart
loop for a dead session — the two skills gave opposite actions.

The fix under test (error-tracking SKILL.md + telegram-userbots SKILL.md +
references/sessions-and-auth.md):
* three states — liveness / readiness / degraded_auth — named in both skills;
* a live process with a dead credential is live-but-NOT-ready;
* degraded_auth splits transient (bounded retry / restart legitimate) from
  terminal/revoked (stop, alert, wait for fresh auth, no restart loop);
* the state machine run as behaviour — a revoked session is not ready and
  retries do not log in forever.

The telegram-dev checkout may be absent → those doc checks NOT_RUN.
Standard library only.
"""
import os
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
ET = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "error-tracking", "SKILL.md")
UB = os.path.expanduser(
    "~/DATA/telegram-dev/plugins/telegram-dev/skills/telegram-userbots/SKILL.md")
UBREF = os.path.expanduser(
    "~/DATA/telegram-dev/plugins/telegram-dev/skills/telegram-userbots/references/sessions-and-auth.md")

failures = []
not_run = []


def case(name, fn):
    try:
        fn()
        print(f"  ok  {name}")
    except AssertionError as e:
        failures.append(f"{name}: {e}")
        print(f"FAIL  {name}: {e}")


def flat(path):
    with open(path, encoding="utf-8") as fh:
        return " ".join(fh.read().split())


def t_three_states_in_error_tracking():
    d = flat(ET)
    assert "Three health states" in d
    for s in ("*Liveness*", "*Readiness*", "*degraded_auth*"):
        assert s in d, f"{s} missing"
    assert "live but NOT ready" in d
    assert "the same rule `telegram-userbots` states" in d


def t_transient_vs_terminal():
    d = flat(ET)
    assert "**transient**" in d and "**terminal / revoked**" in d
    assert 'this is where "exit non-zero, a crash loop is visible" is right' in d
    assert "wait for FRESH auth" in d
    assert "retries exhausted against the same auth error is terminal" in d
    assert "exit non-zero when it fails — a crash loop is visible, a silent zombie is not" not in d, \
        "the universal crash-loop prescription survived"


def t_userbots_aligned():
    if not os.path.isfile(UB):
        not_run.append("telegram-dev absent — userbot doc checks NOT_RUN")
        return
    d = flat(UB)
    assert "terminal / revoked" in d
    assert "NOT READY" in d
    assert "three-state contract" in d
    r = flat(UBREF)
    assert "TERMINAL auth state" in r
    assert 'transient `401` a fresh CONNECT fixes' in r


# ---- the state machine as behaviour


def health(proc):
    """proc: {loop_running, auth_error, retries_left, error_kind} → states."""
    live = proc["loop_running"]
    if not proc.get("auth_error"):
        return {"live": live, "ready": live, "degraded_auth": None, "action": "serve"}
    kind = proc["error_kind"]
    if kind == "terminal":
        return {"live": live, "ready": False, "degraded_auth": "terminal",
                "action": "alert-and-wait-for-fresh-auth"}
    # transient
    if proc["retries_left"] > 0:
        return {"live": live, "ready": False, "degraded_auth": "transient",
                "action": "retry-backoff"}
    return {"live": live, "ready": False, "degraded_auth": "terminal",
            "action": "alert-and-wait-for-fresh-auth"}


def t_revoked_is_live_but_not_ready():
    h = health({"loop_running": True, "auth_error": True, "error_kind": "terminal",
                "retries_left": 0})
    assert h["live"] is True and h["ready"] is False, \
        "a revoked session reported ready"
    assert h["action"] == "alert-and-wait-for-fresh-auth"


def t_retries_do_not_login_forever():
    # a transient error that never clears escalates to terminal, not infinite retry
    steps, proc = 0, {"loop_running": True, "auth_error": True,
                      "error_kind": "transient", "retries_left": 3}
    while health(proc)["action"] == "retry-backoff":
        proc["retries_left"] -= 1
        steps += 1
        assert steps <= 3, "the retry loop never terminates — infinite login"
    assert health(proc)["degraded_auth"] == "terminal"


def main():
    case("error-tracking names the three states", t_three_states_in_error_tracking)
    case("transient vs terminal split; the universal crash-loop is gone",
         t_transient_vs_terminal)
    case("telegram-userbots is aligned to the same contract", t_userbots_aligned)
    case("fixture: a revoked session is live but NOT ready",
         t_revoked_is_live_but_not_ready)
    case("fixture: bounded retries escalate to terminal, never login forever",
         t_retries_do_not_login_forever)
    for n in not_run:
        print(f"  NOT_RUN  {n}")
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
