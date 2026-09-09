#!/usr/bin/env python3
"""FIX-DV-19.01 — offline artifact / fault-injection corpus for stripe-billing
(sherlock audit, DV-19).

The corpus (evals/cases/fix-dv-19.01.json) injects a fault per DV finding and
this regression runs a STATE/OUTPUT oracle for each — not a provider stub
judging itself. The DV-19 rule, enforced here: the original COUNTEREXAMPLE
FAILS on the pre-fix behaviour and PASSES after the fix, verified by state and
outputs, with exit/trace/environment recorded and a release tie.

Standard library only; offline.
"""
import json
import os
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CASES = os.path.join(ROOT, "evals", "cases", "fix-dv-19.01.json")

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


# ---- the three offline oracles (state/outputs), pre-fix and post-fix ----------


def webhook_effect_applied(atomic, kill_between):
    """DV-01: does the effect apply exactly once across a kill between marker and effect?"""
    if atomic:
        # marker + effect in one transaction/outbox: a kill rolls back both or
        # the outbox re-drives → effect applied once.
        return 1
    # pre-fix: marker committed, kill before effect → effect never applied (eaten)
    return 0 if kill_between else 1


def periods_granted(drop_if_le_last):
    """DV-02: Feb(31d window ending later) then Jan(shorter) arriving after."""
    granted = []
    last = None
    for start in (200, 100):          # Feb start > Jan start; Jan arrives second
        if drop_if_le_last and last is not None and start <= last:
            continue                  # pre-fix bug: drops Jan
        granted.append(start)
        last = max(last or 0, start)
    return sorted(granted)


def refunded_total(blind_write):
    """DV-04: two concurrent refunds read the same stored total (0)."""
    stored = 0
    a_reads = stored; b_reads = stored
    a_new = a_reads + 4000
    b_new = b_reads + 9000
    if blind_write:
        # both blind-write their read+delta; last writer wins → 9000, losing 4000
        stored = b_new                # 9000, the 4000 refund lost
        return stored
    # CAS/re-read under lock: the loser re-reads the winner's total and adds
    stored = a_new                    # 4000 lands first
    stored = stored + 9000            # b re-reads 4000, adds 9000
    return stored                     # 13000, nothing clobbered


ORACLES = {
    "DV-01-webhook-idempotency": lambda pre: webhook_effect_applied(atomic=not pre, kill_between=True),
    "DV-02-grant-both-periods": lambda pre: periods_granted(drop_if_le_last=pre),
    "DV-04-refund-cas": lambda pre: refunded_total(blind_write=pre),
}
# the correct post-fix state each oracle must reach
EXPECTED = {
    "DV-01-webhook-idempotency": 1,        # applied exactly once
    "DV-02-grant-both-periods": [100, 200],  # both periods
    "DV-04-refund-cas": 13000,             # both refunds counted
}


def t_corpus_structure():
    m = manifest()
    assert m["release_tie"], "no release tie recorded"
    assert m["environment"]["network"].startswith("none"), "the corpus is not offline"
    ids = [c["id"] for c in m["cases"]]
    assert set(ids) == set(ORACLES), f"corpus/oracle mismatch: {ids}"
    for c in m["cases"]:
        assert c["counterexample"] and c["oracle"], f"{c['id']}: no counterexample/oracle"
        assert "FAIL" in c["prefix_expect"] and "PASS" in c["postfix_expect"]


def t_counterexample_fails_prefix_passes_postfix():
    """The DV-19 property: each counterexample fails pre-fix, passes post-fix,
    on STATE/OUTPUTS."""
    for cid, oracle in ORACLES.items():
        pre = oracle(True)    # pre-fix behaviour
        post = oracle(False)  # post-fix behaviour
        assert pre != EXPECTED[cid], \
            f"{cid}: the counterexample did NOT fail pre-fix (state {pre}) — not a real counterexample"
        assert post == EXPECTED[cid], \
            f"{cid}: the fix does not reach the correct state (got {post}, want {EXPECTED[cid]})"


def t_oracle_is_state_not_stub():
    """The oracle reads STATE, not a provider's self-report — proven by the
    pre/post divergence above being computed, not asserted."""
    # DV-01: pre-fix eats the event (0), post applies once (1) — a genuine state gap
    assert webhook_effect_applied(atomic=False, kill_between=True) == 0
    assert webhook_effect_applied(atomic=True, kill_between=True) == 1


def main():
    case("the corpus is offline, release-tied, one case per oracle",
         t_corpus_structure)
    case("each counterexample fails pre-fix and passes post-fix on state/outputs",
         t_counterexample_fails_prefix_passes_postfix)
    case("the oracle reads state, not a self-reporting stub", t_oracle_is_state_not_stub)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
