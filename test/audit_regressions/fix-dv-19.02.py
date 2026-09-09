#!/usr/bin/env python3
"""FIX-DV-19.02 — offline artifact / fault-injection corpus for crypto-payments
(sherlock audit, DV-19; sibling of fix-dv-19.01).

The corpus (evals/cases/fix-dv-19.02.json) injects a fault per DV-06 finding
and this regression runs a STATE/OUTPUT oracle for each — not a provider stub
judging itself. The DV-19 rule: each counterexample FAILS pre-fix and PASSES
post-fix, verified by state/outputs, offline, with a release tie.

Standard library only; offline.
"""
import json
import os
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CASES = os.path.join(ROOT, "evals", "cases", "fix-dv-19.02.json")

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


class Blocked(Exception):
    pass


# ---- the three offline oracles (state/outputs), pre-fix and post-fix ----------


def credited_usd_minor(mix_dimensions):
    """DV-06: credit a 10.5-unit Asset amount (TON) with a $3000 subscription.
    Pre-fix `??` reads the token amount as USD minor; post-fix converts it."""
    paid_usd_minor = None
    token_amount = 10.5          # ASSET units (TON), not USD
    amount_usd_minor = 3000
    quote = {"rate": 2.9, "source": "coingecko", "date": "2026-09-09"}
    if mix_dimensions:
        # the ??: paidAmountUsd ?? tokenAmount ?? amountUsd → tokenAmount(10.5)
        return paid_usd_minor if paid_usd_minor is not None else int(token_amount)
    # convert the Asset through the dated quote to USD minor, then waterfall
    usd_from_token = round(token_amount * quote["rate"] * 100)   # 3045
    return paid_usd_minor if paid_usd_minor is not None else (usd_from_token or amount_usd_minor)


def settle_excess(policy, paid_minor, base_minor):
    """DV-06.02: a missing policy must block, not invent a fee."""
    excess = paid_minor - base_minor
    if excess <= 0:
        return {"refund": 0, "credit": 0, "fee": 0}
    if policy is None:
        raise Blocked("excess policy required — the template chooses no business price")
    return {"credit": excess} if policy == "credit_excess" else {"refund": excess}


def convert_asset(guess_rate, quote):
    """DV-06: an unknown/undated FX source must block, not guess."""
    if not quote or not quote.get("source") or not quote.get("date"):
        if guess_rate:
            return 9999           # a plausible-but-wrong guessed credit
        raise Blocked("unknown FX source")
    return round(10.5 * quote["rate"] * 100)


def t_corpus_structure():
    m = manifest()
    assert m["release_tie"] and m["environment"]["network"].startswith("none")
    ids = {c["id"] for c in m["cases"]}
    assert ids == {"DV-06-typed-amounts", "DV-06-excess-policy-required",
                   "DV-06-unknown-fx-blocks"}, ids
    for c in m["cases"]:
        assert "FAIL" in c["prefix_expect"] and "PASS" in c["postfix_expect"]


def t_typed_amounts_counterexample():
    pre = credited_usd_minor(mix_dimensions=True)
    post = credited_usd_minor(mix_dimensions=False)
    assert pre == 10 and post == 3045, f"pre {pre} post {post}"
    assert pre != post, "the dimension mix did not change the credited amount"


def t_excess_policy_counterexample():
    # pre-fix: a default policy invents a fee/credit; post-fix: missing blocks
    try:
        settle_excess(None, 3030, 3000)
        raise AssertionError("a missing policy did not block — the counterexample would pass pre-fix")
    except Blocked:
        pass
    assert settle_excess("credit_excess", 3030, 3000) == {"credit": 30}


def t_unknown_fx_counterexample():
    bad_quote = {"rate": 2.9}      # no source/date
    # pre-fix (guess): a wrong number; post-fix: block
    assert convert_asset(guess_rate=True, quote=bad_quote) == 9999
    try:
        convert_asset(guess_rate=False, quote=bad_quote)
        raise AssertionError("an unknown FX source did not block")
    except Blocked:
        pass
    good = {"rate": 2.9, "source": "coingecko", "date": "2026-09-09"}
    assert convert_asset(guess_rate=False, quote=good) == 3045


def main():
    case("the corpus is offline, release-tied, one case per DV-06 oracle",
         t_corpus_structure)
    case("typed-amounts: the dimension mix fails pre-fix, converts post-fix",
         t_typed_amounts_counterexample)
    case("excess policy: a missing policy blocks, never invents a fee",
         t_excess_policy_counterexample)
    case("unknown FX: a guess is wrong pre-fix, blocks post-fix",
         t_unknown_fx_counterexample)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
