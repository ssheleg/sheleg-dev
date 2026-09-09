#!/usr/bin/env python3
"""FIX-DV-02.02 — monotonic mirror and bounded serialization retry (sherlock
audit; on FIX-DV-02.01's keyed grant ledger).

The contract under test: the subscription mirror (state) lives apart from the
grant ledger (history) and moves forward only; a serialization conflict
retries inside the same claim, bounded; past the bound the route answers 5xx
with the claim released so the redelivery lands the renewal — a conflict may
delay a grant, never lose it.

Proved via the shipped pack as a process, plus the doctrine phrases.
Standard library only.
"""
import os
import subprocess
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FIXTURES = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "stripe-billing", "fixtures")
DOC = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "stripe-billing",
                   "references", "webhook-events.md")

failures = []


def case(name, fn):
    try:
        fn()
        print(f"  ok  {name}")
    except AssertionError as e:
        failures.append(f"{name}: {e}")
        print(f"FAIL  {name}: {e}")


def t_doctrine_states_mirror_and_retry():
    flat = " ".join(open(DOC, encoding="utf-8").read().split())
    for needle in ("The mirror is state; the ledger is history",
                   "the mirror moves FORWARD only",
                   "never rewinds a confirmed period",
                   "retries inside the same claim, bounded",
                   "a conflict may delay a grant, never lose it",
                   "a swallowed conflict answered 200 is a renewal that silently never happened"):
        assert needle in flat, f"the doctrine no longer states {needle!r}"


def t_pack_proves_both_invariants():
    r = subprocess.run(["node", "assert-money-invariants.mjs"], cwd=FIXTURES,
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, f"the pack fails:\n{(r.stderr or r.stdout)[-400:]}"
    for inv in ("serialization-conflict-does-not-lose-the-renewal",
                "exhausted-retries-answer-5xx-and-the-redelivery-lands",
                "out-of-order-pair-does-not-rewind-state"):
        assert f"pass {inv}" in r.stdout, f"the pack no longer asserts {inv}"


def t_self_test_watches_the_new_rule_fail():
    st = subprocess.run(["node", "assert-money-invariants.mjs", "--self-test"], cwd=FIXTURES,
                        capture_output=True, text=True, timeout=600)
    assert st.returncode == 0, f"--self-test fails:\n{(st.stderr or st.stdout)[-300:]}"
    assert "tx-retry-bounded" in st.stdout, "the self-test never exercised tx-retry-bounded"


def main():
    case("the doctrine states the mirror/ledger split and the bounded retry",
         t_doctrine_states_mirror_and_retry)
    case("the pack proves conflict-delay, exhausted-5xx and no-rewind",
         t_pack_proves_both_invariants)
    case("the self-test watches tx-retry-bounded fail", t_self_test_watches_the_new_rule_fail)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
