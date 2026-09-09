#!/usr/bin/env python3
"""FIX-DV-13.01 — consent claims scoped: provider policy vs business choice vs
jurisdiction (sherlock audit, DV-13).

The finding: Basic mode was described as "No conversion modeling" (Google
applies a general model), the certified-CMP requirement was declared for all
Google ad products (official scope: publisher products), and "always
Advanced", "65–70%" and "no banner needed" outside the EEA were presented as
universal.

The fix under test (ad-tracking SKILL.md + references/consent-mode.md):
* Basic = general modeling, Advanced = advertiser-specific;
* the certified CMP is scoped to AdSense/Ad Manager/AdMob, a recommendation
  on the advertiser side;
* mode choice = three questions (provider policy / business choice /
  jurisdiction); percentages are dated, scoped, unmeasured-until-your-traffic;
* "no banner needed" replaced by a recorded business choice + jurisdiction
  note.

Standard library only.
"""
import os
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SKILL = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "ad-tracking", "SKILL.md")
REF = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "ad-tracking",
                   "references", "consent-mode.md")

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


def t_basic_has_general_modeling():
    d = flat(REF)
    assert "**General** modeling only" in d
    assert '"no modeling" was never true' in d
    assert "**Advertiser-specific** modeling" in d
    assert "| **Basic** | No — tags blocked until consent granted | No | No |" not in d, \
        "the wrong Basic row survived"


def t_cmp_scope():
    d = flat(REF)
    assert "scoped to Google's **publisher** products — AdSense, Ad Manager, AdMob" in d
    assert "Google's recommendation, not a stated requirement" in d
    assert "no longer sufficient on its own for Google's ad products" not in d, \
        "the all-products CMP claim survived"


def t_three_questions_not_one_default():
    d = flat(REF)
    assert "three separate questions, not one default" in d
    for q in ("*Provider policy:*", "*Business choice:*", "*Jurisdiction:*"):
        assert q in d, f"{q} missing"
    assert "**Always prefer Advanced mode**" not in d, "the universal default survived"
    assert "Basic is the conservative answer" in d


def t_percentage_is_dated_and_scoped():
    d = flat(REF)
    assert "dated, campaign-specific case studies" in d
    assert "your recovery is unknown until measured on your traffic" in d
    assert "an unmeasured percentage is not a promise" in d
    s = flat(SKILL)
    assert "yours is unknown until measured" in s
    assert "roughly two thirds of the otherwise lost data" not in s, \
        "the universal two-thirds claim survived in SKILL.md"


def t_no_banner_claim_scoped():
    d = flat(REF)
    assert "(no banner needed)" not in d, "the universal no-banner verdict survived"
    assert "a recorded BUSINESS choice, not legal" in d
    assert "jurisdiction question" in d


def main():
    case("Basic carries general modeling; Advanced advertiser-specific",
         t_basic_has_general_modeling)
    case("the certified-CMP requirement is publisher-scoped", t_cmp_scope)
    case("mode choice is three questions; the universal default is gone",
         t_three_questions_not_one_default)
    case("the percentage is dated, scoped and unmeasured-until-yours",
         t_percentage_is_dated_and_scoped)
    case("the no-banner verdict is a recorded choice + jurisdiction note",
         t_no_banner_claim_scoped)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
