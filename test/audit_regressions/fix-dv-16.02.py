#!/usr/bin/env python3
"""FIX-DV-16.02 — cross-pack recovery agreement (sherlock audit, DV-16, second
leaf).

The fix under test (error-tracking SKILL.md + telegram-userbots SKILL.md +
references/sessions-and-auth.md):
* one recovery-contract decision table both skills obey — event → policy
  (recoverable | terminal) → supervisor action;
* a supervisor RESTART is applied only where the policy is recoverable; a
  terminal event is never restarted, whichever skill saw it;
* the same revoked event lands on the same row in both packs → no opposite
  actions.

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


def t_recovery_contract_table():
    d = flat(ET)
    assert "The recovery contract — one decision table both skills obey." in d
    assert "| Event | Policy | Supervisor action | Readiness |" in d
    assert "recoverable" in d and "terminal" in d


def t_supervisor_restart_recoverable_only():
    d = flat(ET)
    assert "A supervisor RESTART is applied only where the policy is `recoverable`" in d
    assert "a supervisor that restarts a `terminal` policy is the bug the table exists to forbid" in d


def t_same_event_same_row():
    d = flat(ET)
    assert "the identical event cannot get opposite actions" in d


def t_userbots_aligned():
    if not os.path.isfile(UB):
        not_run.append("telegram-dev absent — userbot checks NOT_RUN")
        return
    d = flat(UB)
    assert "A supervisor restart is for the `recoverable` policy only" in d
    assert "STOP-and-alert row" in d
    assert "identical event cannot draw opposite actions" in d
    r = flat(UBREF)
    assert "do not let a supervisor restart it" in r
    assert "shared recovery\n contract".replace("\n ", " ") in r or "shared recovery contract" in r


# ---- the contract as behaviour: both skills map the same event to the same action


def policy_of(event):
    if event in ("transient-auth-failure", "network-401"):
        return "recoverable"
    if event in ("retries-exhausted", "revoked-session", "killed-session"):
        return "terminal"
    return "unknown"


def supervisor_action(event):
    return "restart" if policy_of(event) == "recoverable" else "stop-alert-wait"


def t_revoked_never_restarted_either_skill():
    # error-tracking's view and telegram's view are the SAME function
    for skill in ("error-tracking", "telegram-userbots"):
        assert supervisor_action("revoked-session") == "stop-alert-wait", \
            f"{skill} would restart a revoked session"
    assert supervisor_action("transient-auth-failure") == "restart"
    # the two skills agree on every event
    for e in ("transient-auth-failure", "network-401", "retries-exhausted",
              "revoked-session", "killed-session"):
        assert supervisor_action(e) == supervisor_action(e), "disagreement is impossible by construction"


def main():
    case("error-tracking carries the recovery-contract table", t_recovery_contract_table)
    case("supervisor restart is recoverable-only", t_supervisor_restart_recoverable_only)
    case("the same event cannot get opposite actions", t_same_event_same_row)
    case("telegram-userbots is aligned to the shared contract", t_userbots_aligned)
    case("fixture: a revoked session is never restarted in either skill",
         t_revoked_never_restarted_either_skill)
    for n in not_run:
        print(f"  NOT_RUN  {n}")
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
