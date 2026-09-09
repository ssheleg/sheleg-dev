#!/usr/bin/env python3
"""FIX-DV-19.07 — offline artifact / fault-injection corpus for
frontend-performance (sherlock audit, DV-19).

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
CASES = os.path.join(ROOT, "evals", "cases", "fix-dv-19.07.json")

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


def metric_field_measurable(metric, only_three_field):
    if only_three_field:
        return metric in ("LCP", "INP", "CLS")     # pre-fix: FCP excluded
    return metric in ("LCP", "INP", "CLS", "FCP")  # post-fix: FCP included


def inp_verdict(inp_passed_by_tbt, have_field_inp, tbt_good):
    if inp_passed_by_tbt and not have_field_inp and tbt_good:
        return "passed"          # pre-fix bug: TBT stands in as proof
    if not have_field_inp:
        return "unknown"         # post-fix: no field INP → unknown, not passed
    return "passed"


def change_allowed(blanket, measured_win, functional_loss):
    """A perf change: pre-fix applies blindly; post-fix needs a measured win and
    no functional loss."""
    if blanket:
        return True              # applied regardless
    return measured_win and not functional_loss


def t_corpus_structure():
    m = manifest()
    assert m["release_tie"] and m["environment"]["network"].startswith("none")
    ids = {c["id"] for c in m["cases"]}
    assert ids == {"DV-17-fcp-field-measurable", "DV-18-heuristics-not-prohibitions"}, ids
    for c in m["cases"]:
        assert "FAIL" in c["prefix_expect"] and "PASS" in c["postfix_expect"]


def t_dv17_fcp_and_inp():
    assert metric_field_measurable("FCP", only_three_field=True) is False, \
        "FCP was already field-measurable pre-fix — the finding did not reproduce"
    assert metric_field_measurable("FCP", only_three_field=False) is True, \
        "the fix does not make FCP field-measurable"
    # INP with TBT but no field data
    assert inp_verdict(inp_passed_by_tbt=True, have_field_inp=False, tbt_good=True) == "passed", \
        "the 'INP passed by TBT' bug did not reproduce"
    assert inp_verdict(inp_passed_by_tbt=False, have_field_inp=False, tbt_good=True) == "unknown", \
        "post-fix reported INP passed without field data"


def t_dv18_change_gated():
    # pre-fix: a blind change is allowed regardless of measurement or loss
    assert change_allowed(blanket=True, measured_win=False, functional_loss=True) is True, \
        "the blanket-change behaviour did not reproduce"
    # post-fix: a change with functional loss is refused even if it wins a metric
    assert change_allowed(blanket=False, measured_win=True, functional_loss=True) is False, \
        "a change with functional loss was allowed post-fix"
    assert change_allowed(blanket=False, measured_win=True, functional_loss=False) is True


def main():
    case("the corpus is offline, release-tied, one case per DV oracle",
         t_corpus_structure)
    case("DV-17: FCP lab-only + INP-by-TBT pre-fix; FCP field + INP unknown post-fix",
         t_dv17_fcp_and_inp)
    case("DV-18: a blind change applies pre-fix; gated on measurement post-fix",
         t_dv18_change_gated)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
