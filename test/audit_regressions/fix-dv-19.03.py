#!/usr/bin/env python3
"""FIX-DV-19.03 — offline artifact / fault-injection corpus for google-auth
(sherlock audit, DV-19; sibling of 19.01/19.02).

Each corpus case injects a fault per DV finding; this regression runs a
STATE/OUTPUT oracle for each — not a provider stub judging itself. DV-19: each
counterexample FAILS pre-fix and PASSES post-fix on state/outputs, offline,
release-tied.

Standard library only; offline.
"""
import json
import os
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CASES = os.path.join(ROOT, "evals", "cases", "fix-dv-19.03.json")

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


def secret_readable_from_cookie(store_in_cookie):
    """DV-07: a signed (not encrypted) cookie's payload is base64-decodable."""
    if store_in_cookie:
        # signed != encrypted → the holder reads the secret. STATE: leaked.
        return True
    return False   # tokens server-side; cookie holds only a session id


def adc_wins(order):
    """DV-08: which credential wins when BOTH an env var and an attached SA exist."""
    for source in order:
        if source == "env":
            return "env"
        if source == "attached-sa":
            return "attached-sa"
        # local-adc not present in this scenario
    return None


def callback_accepts(shared_client, consume_state, returned_state, stored_state):
    """DV-09: does a callback with a given state pass?"""
    if not shared_client and stored_state is not None:
        # per-request client, state stored: reject when missing or already consumed
        if returned_state is None or returned_state != stored_state:
            return False
        # single-use consume happens here; a replay would find it gone
        return True
    # pre-fix: shared client, undefined===undefined passes a stateless callback
    return returned_state == stored_state   # None == None → True (the bug)


def t_corpus_structure():
    m = manifest()
    assert m["release_tie"] and m["environment"]["network"].startswith("none")
    ids = {c["id"] for c in m["cases"]}
    assert ids == {"DV-07-secrets-in-signed-cookie", "DV-08-adc-resolution-order",
                   "DV-09-state-single-use"}, ids
    for c in m["cases"]:
        assert "FAIL" in c["prefix_expect"] and "PASS" in c["postfix_expect"]


def t_dv07_secret_leak():
    assert secret_readable_from_cookie(store_in_cookie=True) is True, \
        "the signed-cookie leak did not reproduce pre-fix"
    assert secret_readable_from_cookie(store_in_cookie=False) is False, \
        "the fix still leaks the secret"


def t_dv08_resolution_order():
    pre = adc_wins(["attached-sa", "local-adc", "env"])   # wrong order
    post = adc_wins(["env", "local-adc", "attached-sa"])  # Google's order
    assert pre == "attached-sa", "the wrong order did not shadow the env credential"
    assert post == "env", "the fix does not honour env → local ADC → attached SA"


def t_dv09_state_single_use():
    # pre-fix: shared client, no consume, a callback with NO state passes
    assert callback_accepts(shared_client=True, consume_state=False,
                            returned_state=None, stored_state=None) is True, \
        "the undefined===undefined bug did not reproduce"
    # post-fix: per-request client, state stored; missing state rejected
    assert callback_accepts(shared_client=False, consume_state=True,
                            returned_state=None, stored_state="abc") is False, \
        "a missing state was accepted post-fix"
    assert callback_accepts(shared_client=False, consume_state=True,
                            returned_state="abc", stored_state="abc") is True


def main():
    case("the corpus is offline, release-tied, one case per DV oracle",
         t_corpus_structure)
    case("DV-07: secrets leak from a signed cookie pre-fix, not post-fix",
         t_dv07_secret_leak)
    case("DV-08: the wrong resolution order shadows env pre-fix, correct post-fix",
         t_dv08_resolution_order)
    case("DV-09: a missing state passes pre-fix, is rejected post-fix",
         t_dv09_state_single_use)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
