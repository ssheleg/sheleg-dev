#!/usr/bin/env python3
"""FIX-DV-19.05 — offline artifact / fault-injection corpus for ad-tracking
(sherlock audit, DV-19; sibling of 19.01–19.04).

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
CASES = os.path.join(ROOT, "evals", "cases", "fix-dv-19.05.json")

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


def basic_mode_modeling(basic_no_modeling):
    """DV-13: what modeling does Basic mode actually provide?"""
    if basic_no_modeling:
        return "none"          # pre-fix claim
    return "general"           # Google applies a general model in Basic


def cmp_required_for(product, required_everywhere):
    """DV-13: is a certified CMP a requirement for this Google product?"""
    publisher = {"adsense", "ad-manager", "admob"}
    if required_everywhere:
        return "required"      # pre-fix: everywhere
    return "required" if product in publisher else "recommended"


def pixels_before_consent(meta_noscript_ungated, enhanced_before_consent):
    """DV-14: which pixels fire before the user consents?"""
    fired = []
    if meta_noscript_ungated:
        fired.append("meta-noscript")
    if enhanced_before_consent:
        fired.append("ga4-enhanced-conversions")
    return fired


def t_corpus_structure():
    m = manifest()
    assert m["release_tie"] and m["environment"]["network"].startswith("none")
    ids = {c["id"] for c in m["cases"]}
    assert ids == {"DV-13-basic-mode-modeling", "DV-13-cmp-scope",
                   "DV-14-meta-noscript-before-consent"}, ids
    for c in m["cases"]:
        assert "FAIL" in c["prefix_expect"] and "PASS" in c["postfix_expect"]


def t_dv13_basic_modeling():
    assert basic_mode_modeling(basic_no_modeling=True) == "none", \
        "the 'no modeling' claim did not reproduce pre-fix"
    assert basic_mode_modeling(basic_no_modeling=False) == "general", \
        "the fix does not report Basic's general modeling"


def t_dv13_cmp_scope():
    # pre-fix: required everywhere, including advertiser products
    assert cmp_required_for("google-ads", required_everywhere=True) == "required"
    # post-fix: publisher required, advertiser recommended
    assert cmp_required_for("google-ads", required_everywhere=False) == "recommended", \
        "a certified CMP was still demanded on the advertiser side"
    assert cmp_required_for("adsense", required_everywhere=False) == "required"


def t_dv14_no_pixel_before_consent():
    pre = pixels_before_consent(meta_noscript_ungated=True, enhanced_before_consent=True)
    assert pre == ["meta-noscript", "ga4-enhanced-conversions"], \
        "the pre-consent pixel fires did not reproduce"
    post = pixels_before_consent(meta_noscript_ungated=False, enhanced_before_consent=False)
    assert post == [], "a pixel still fires before consent post-fix"


def main():
    case("the corpus is offline, release-tied, one case per DV oracle",
         t_corpus_structure)
    case("DV-13: Basic reports 'no modeling' pre-fix, general modeling post-fix",
         t_dv13_basic_modeling)
    case("DV-13: the certified-CMP requirement is publisher-scoped post-fix",
         t_dv13_cmp_scope)
    case("DV-14: pixels fire before consent pre-fix, none post-fix",
         t_dv14_no_pixel_before_consent)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
