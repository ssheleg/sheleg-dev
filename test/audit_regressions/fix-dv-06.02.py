#!/usr/bin/env python3
"""FIX-DV-06.02 — the excess policy is a required enum, not a template default
(sherlock audit, DV-06, second leaf).

The finding: the buffer template preselected the business outcome (credit the
full invoice) — a business price baked into a code sample.

The fix under test (references/heleket-provider.md):
* the enum refund_excess / credit_excess / buffer_fee is REQUIRED and the
  template preselects none;
* a missing policy blocks and asks — it never invents a fee;
* each variant carries a unit-safe (USD minor) example;
* the rule run as behaviour.

Standard library only.
"""
import os
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DOC = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "crypto-payments",
                   "references", "heleket-provider.md")

failures = []


def case(name, fn):
    try:
        fn()
        print(f"  ok  {name}")
    except AssertionError as e:
        failures.append(f"{name}: {e}")
        print(f"FAIL  {name}: {e}")


def flat():
    with open(DOC, encoding="utf-8") as fh:
        return " ".join(fh.read().split())


def t_enum_required_no_default():
    d = flat()
    assert "'refund_excess' | 'credit_excess' | 'buffer_fee'" in d
    assert "required business policy, not a template default" in d
    assert "The template carries the enum and no preselected price" in d
    assert "credit the **full invoice amount** (not the base) to the user's balance" not in d, \
        "the preselected business outcome survived"


def t_missing_policy_never_invents_a_fee():
    d = flat()
    assert "A missing policy BLOCKS" in d and "invoice creation and asks" in d
    assert "never silently invents a fee" in d


def t_unit_safe_examples_per_variant():
    d = flat()
    assert "3030¢ against a 3000¢ subscription → 30¢ goes BACK" in d, \
        "the refund_excess example is not unit-safe"
    assert "lands as 30¢ of BALANCE" in d
    assert 'appears as "buffer fee: 30¢" on the invoice BEFORE payment' in d
    assert "the buffer never mixes with Asset amounts" in d


# ---- behaviour


class PolicyMissing(Exception):
    pass


def settle_excess(policy, paid_minor, base_minor):
    excess = paid_minor - base_minor
    if excess <= 0:
        return {"refund": 0, "credit": 0, "fee": 0}
    if policy == "refund_excess":
        return {"refund": excess, "credit": 0, "fee": 0}
    if policy == "credit_excess":
        return {"refund": 0, "credit": excess, "fee": 0}
    if policy == "buffer_fee":
        return {"refund": 0, "credit": 0, "fee": excess}
    raise PolicyMissing("excess policy is required — the template does not choose")


def t_each_variant_settles():
    assert settle_excess("refund_excess", 3030, 3000) == {"refund": 30, "credit": 0, "fee": 0}
    assert settle_excess("credit_excess", 3030, 3000) == {"refund": 0, "credit": 30, "fee": 0}
    assert settle_excess("buffer_fee", 3030, 3000) == {"refund": 0, "credit": 0, "fee": 30}


def t_missing_policy_blocks():
    try:
        settle_excess(None, 3030, 3000)
        assert False, "a missing policy invented an outcome"
    except PolicyMissing:
        pass
    # no excess → nothing to decide, any policy state settles zero
    assert settle_excess(None, 3000, 3000) == {"refund": 0, "credit": 0, "fee": 0}


def main():
    case("the enum is required and the template preselects nothing",
         t_enum_required_no_default)
    case("a missing policy blocks, never invents a fee",
         t_missing_policy_never_invents_a_fee)
    case("each variant carries a unit-safe example", t_unit_safe_examples_per_variant)
    case("fixture: each variant settles its own way", t_each_variant_settles)
    case("fixture: a missing policy blocks; zero excess needs no decision",
         t_missing_policy_blocks)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
