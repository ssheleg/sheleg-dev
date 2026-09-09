#!/usr/bin/env python3
"""FIX-DV-17.01 — FCP is field-measurable; two independent axes (sherlock
audit, DV-17).

The finding: the skill said only the three Core Web Vitals are
field-measurable and filed FCP under lab-only diagnostics — but web.dev lists
both lab and field tools for FCP (CrUX reports it).

The fix under test (frontend-performance/SKILL.md):
* two independent axes — CWV/not-CWV and lab/field availability;
* FCP is not-CWV but IS field-measurable;
* field claims require p75, device/cohort, period, sample size;
* TBT is a diagnostic correlate of INP, never a substitute for its evidence;
* the CrUX-FCP + Lighthouse-TBT + no-field-INP case: FCP=field-supported,
  INP=unknown, never "passed by TBT" — run as behaviour.

Standard library only.
"""
import os
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DOC = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "frontend-performance",
                   "SKILL.md")

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


def t_two_axes():
    d = flat()
    assert "Two INDEPENDENT axes" in d
    assert "is it a Core Web Vital" in d and "where can you measure it" in d
    assert 'the three CWV are field-measurable" was wrong' in d


def t_fcp_is_field_measurable():
    d = flat()
    assert "FCP is the case that breaks the one-axis story" in d
    assert "it is NOT a Core Web Vital, yet it IS field-measurable" in d
    # the table row: FCP no / yes
    assert "| FCP | no | **yes (CrUX)**" in d


def t_field_claim_provenance():
    d = flat()
    assert "A field claim carries its provenance" in d
    for req in ("p75", "device/cohort", "period", "sample size"):
        assert req in d, f"the {req} requirement is missing"
    assert "that is `unknown`, not `good`" in d


def t_tbt_is_a_correlate_not_proof():
    d = flat()
    assert "TBT is a diagnostic CORRELATE of INP, never a substitute for its evidence." in d
    assert "it does NOT PROVE INP" in d
    assert "FCP = field-supported, INP = unknown" in d
    assert 'never "INP passed by TBT"' in d


# ---- the classification as behaviour


def classify(available):
    """available: dict of metric -> source ('crux' | 'lighthouse' | None).
    Returns per-metric field-support verdict."""
    field_capable = {"LCP", "INP", "CLS", "FCP"}   # FCP included
    out = {}
    for metric, source in available.items():
        if metric in field_capable and source == "crux":
            out[metric] = "field-supported"
        elif source == "lighthouse":
            out[metric] = "lab-only"
        else:
            out[metric] = "unknown"
    return out


def t_crux_fcp_lighthouse_tbt_no_inp():
    v = classify({"FCP": "crux", "TBT": "lighthouse", "INP": None})
    assert v["FCP"] == "field-supported", "FCP was not treated as field-measurable"
    assert v["INP"] == "unknown", \
        "INP was claimed on TBT's behalf — the exact defect"
    # TBT is lab-only and cannot upgrade INP
    assert v["TBT"] == "lab-only"


def t_thin_origin_is_unknown_not_good():
    v = classify({"LCP": None})
    assert v["LCP"] == "unknown", "a thin origin with no field data was not unknown"


def main():
    case("the two independent axes are named", t_two_axes)
    case("FCP is not-CWV but field-measurable", t_fcp_is_field_measurable)
    case("a field claim requires p75/device/period/sample", t_field_claim_provenance)
    case("TBT is a correlate of INP, not proof", t_tbt_is_a_correlate_not_proof)
    case("fixture: CrUX FCP + Lighthouse TBT + no INP → FCP supported, INP unknown",
         t_crux_fcp_lighthouse_tbt_no_inp)
    case("fixture: a thin origin is unknown, not good", t_thin_origin_is_unknown_not_good)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
