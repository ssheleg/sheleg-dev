#!/usr/bin/env python3
"""FIX-DV-13.02 — Basic and Advanced are two technical contracts (sherlock
audit, DV-13, second leaf).

The fix under test (references/consent-mode.md):
* each mode carries its own complete wiring example and its own pre-consent
  behaviour (Advanced: cookieless pings, no cookies; Basic: zero requests);
* the mixed waterfall is named as the defect to test for;
* the contracts run as behaviour on fixtures — no mixed waterfall passes.

Standard library only.
"""
import os
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DOC = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "ad-tracking",
                   "references", "consent-mode.md")

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


def t_two_contracts():
    d = flat()
    assert "Two different technical contracts — never one snippet with a policy flag." in d
    assert "ADVANCED contract: denied defaults set synchronously" in d
    assert "BASIC contract: NO tag bytes reach the page before consent" in d
    assert "physically block `<script>` tags until consent granted" not in d, \
        "the one-liner survived instead of a complete contract"


def t_pre_consent_behaviour_named():
    d = flat()
    assert "cookieless pings go out, no cookies are written" in d
    assert "zero requests to Google — nothing loads, nothing pings" in d


def t_mixed_waterfall_is_the_defect():
    d = flat()
    assert "The mixed waterfall is the defect to test for" in d
    assert "a page failing both assertions is running the mix" in d


# ---- the contracts as behaviour


def pre_consent(page):
    """page: {loads_gtag_eagerly, defaults_denied_before_load, config_waits}.
    Returns the observable pre-consent behaviour."""
    if page["loads_gtag_eagerly"] and page["defaults_denied_before_load"] \
            and not page["config_waits"]:
        return {"requests": "cookieless-pings", "cookies": False}       # Advanced
    if not page["loads_gtag_eagerly"]:
        return {"requests": "none", "cookies": False}                   # Basic
    return {"requests": "mixed", "cookies": None}                        # the defect


def t_each_mode_preserves_its_behaviour():
    adv = pre_consent({"loads_gtag_eagerly": True,
                       "defaults_denied_before_load": True, "config_waits": False})
    assert adv == {"requests": "cookieless-pings", "cookies": False}
    basic = pre_consent({"loads_gtag_eagerly": False,
                         "defaults_denied_before_load": False, "config_waits": True})
    assert basic == {"requests": "none", "cookies": False}


def t_mixed_waterfall_detected():
    mix = pre_consent({"loads_gtag_eagerly": True,
                       "defaults_denied_before_load": False, "config_waits": True})
    assert mix["requests"] == "mixed", \
        "the eager-load + gated-config mix passed as a mode"


def main():
    case("two complete contracts, no policy-flag one-liner", t_two_contracts)
    case("each mode names its pre-consent behaviour", t_pre_consent_behaviour_named)
    case("the mixed waterfall is named as the defect", t_mixed_waterfall_is_the_defect)
    case("fixture: each mode preserves its pre-consent behaviour",
         t_each_mode_preserves_its_behaviour)
    case("fixture: the mixed waterfall is detected", t_mixed_waterfall_detected)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
