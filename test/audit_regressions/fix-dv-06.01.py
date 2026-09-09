#!/usr/bin/env python3
"""FIX-DV-06.01 — typed amounts: no implicit unit conversion (sherlock audit,
DV-06).

The finding: the credit waterfall chained paidAmountUsd ?? tokenAmount ??
amountUsd — Money, an Asset amount (described as plan units while the Heleket
reference defines it as invoice base+buffer) and Money again — with no
dimensional contract; `??` across dimensions is an implicit conversion.

The fix under test (crypto-payments SKILL.md + references/heleket-provider.md):
* four dimensions named — Money minor, Asset network/amount, Entitlement
  units, dated FX quote;
* tokenAmount is an ASSET amount (base+buffer), not plan units — in both
  files;
* conversion only via a dated quote from a known source; unknown source
  BLOCKS; the audit row names the quote;
* the rule run as behaviour: USD minor never adds to crypto decimals.

Standard library only.
"""
import os
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SKILL = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "crypto-payments",
                     "SKILL.md")
REF = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "crypto-payments",
                   "references", "heleket-provider.md")

failures = []


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


def t_four_dimensions_named():
    d = flat(SKILL)
    for dim in ("**Money** (currency + minor units", "**Asset** (network + token",
                "**Entitlement** (plan units)", "**dated FX quote**"):
        assert dim in d, f"dimension {dim} missing"
    assert "they never mix implicitly" in d


def t_token_amount_is_asset_both_files():
    d = flat(SKILL)
    assert "`tokenAmount` is an **Asset amount**" in d
    assert "NOT plan units" in d
    assert "what the plan says this purchase grants" not in d, \
        "the wrong tokenAmount description survived"
    r = flat(REF)
    assert "ASSET amount (invoice token)" in r
    assert "never added to USD fields without a dated FX quote" in r


def t_unknown_quote_blocks():
    d = flat(SKILL)
    assert "dated quote from a known source" in d
    assert "**blocks** the conversion rather than guessing" in d
    assert "naming the source AND the quote used" in d
    assert "toUsdMinor(payment.tokenAmount, quote)" in d, \
        "the waterfall still chains dimensions with ??"


# ---- behaviour


class Blocked(Exception):
    pass


def to_usd_minor(asset_amount, quote):
    if not quote or not quote.get("source") or not quote.get("date"):
        raise Blocked("unknown or undated FX source")
    return round(asset_amount * quote["rate"] * 100)


def credit_usd_minor(payment, quote=None):
    candidates = [payment.get("paidAmountUsdMinor")]
    if payment.get("tokenAmount") is not None:
        candidates.append(to_usd_minor(payment["tokenAmount"], quote))
    candidates.append(payment.get("amountUsdMinor"))
    return next(v for v in candidates if v is not None)


def t_usd_minor_never_adds_to_crypto():
    # the naive ?? would credit 0.031 (a TON amount) as 0.031 USD minor
    payment = {"paidAmountUsdMinor": None, "tokenAmount": 10.5,
               "amountUsdMinor": 3000}
    quote = {"rate": 2.9, "source": "coingecko", "date": "2026-09-09"}
    assert credit_usd_minor(payment, quote) == 3045, \
        "the Asset amount did not convert through the quote"
    try:
        credit_usd_minor(payment, {"rate": 2.9})     # sourceless quote
        assert False, "an unknown FX source did not block the conversion"
    except Blocked:
        pass


def t_money_paths_need_no_quote():
    assert credit_usd_minor({"paidAmountUsdMinor": 2999}) == 2999
    assert credit_usd_minor({"amountUsdMinor": 3000}) == 3000


def main():
    case("the four dimensions are named and never mix implicitly",
         t_four_dimensions_named)
    case("tokenAmount is an Asset amount in both files",
         t_token_amount_is_asset_both_files)
    case("an unknown FX source blocks; the audit row names the quote",
         t_unknown_quote_blocks)
    case("fixture: USD minor never adds to crypto decimals; blocked without a source",
         t_usd_minor_never_adds_to_crypto)
    case("fixture: pure Money paths need no quote", t_money_paths_need_no_quote)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
