#!/usr/bin/env python3
"""FIX-DV-20.01 — an environment error is a TEST_ERROR, never a proven validation gap
(sherlock audit, DV-20).

The finding: `npm run test:all` had the base suites PASS but the negative
self-tests reported 40 FAILures with `cp: No space left on device`, while the
runner printed "the validator accepted a planted defect" / "the guard does not
actually fire" — turning a full disk into a proven guard bypass.

The fix under test (test/negatives.py):
* explicit stages fixture_setup → mutation_verified → validator_ran →
  assertion, classified by classify_stages();
* a failed cp / ENOSPC / timeout is TEST_ERROR, with ZERO guard-bypass (GAP)
  findings; a GAP is reported ONLY when the validator RAN against a verified
  mutant and accepted it;
* a resource preflight refuses to run on a too-full filesystem;
* cleanup runs in a finally.

This is offline: it drives the pure classifier and preflight directly, and
re-runs a full simulated 40-step batch before/after resources. Standard library
only.
"""
import importlib.util
import os
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
NEG = os.path.join(ROOT, "test", "negatives.py")

failures = []


def case(name, fn):
    try:
        fn()
        print(f"  ok  {name}")
    except AssertionError as e:
        failures.append(f"{name}: {e}")
        print(f"FAIL  {name}: {e}")


def load_neg():
    spec = importlib.util.spec_from_file_location("negatives_dv2001", NEG)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def t_stages_declared_in_order():
    neg = load_neg()
    assert neg.STAGES == ("fixture_setup", "mutation_verified", "validator_ran",
                          "assertion"), neg.STAGES


def t_env_error_is_test_error_not_gap():
    neg = load_neg()
    c = neg.classify_stages
    # ENOSPC while the guard 'looks' like it didn't fire: still TEST_ERROR
    assert c(timed_out=False, env_error=True, skipped=False, setup_ok=False,
             mutant_differs=False, guard_fired=False) == "TEST_ERROR"
    # failed cp: no scratch dir -> setup_ok False -> TEST_ERROR
    assert c(timed_out=False, env_error=False, skipped=False, setup_ok=False,
             mutant_differs=True, guard_fired=False) == "TEST_ERROR"
    # timeout -> TEST_ERROR
    assert c(timed_out=True, env_error=False, skipped=False, setup_ok=True,
             mutant_differs=True, guard_fired=False) == "TEST_ERROR"
    assert neg.has_env_error("cp: /tmp/x: No space left on device") is True
    assert neg.has_env_error("everything is fine") is False


def t_gap_only_when_validator_accepted_a_real_mutant():
    neg = load_neg()
    c = neg.classify_stages
    # the only genuine guard bypass: setup ok, mutant differs, validator ran & accepted
    assert c(timed_out=False, env_error=False, skipped=False, setup_ok=True,
             mutant_differs=True, guard_fired=False) == "GAP"
    # validator rejected the mutant -> PASS
    assert c(timed_out=False, env_error=False, skipped=False, setup_ok=True,
             mutant_differs=True, guard_fired=True) == "PASS"
    # nothing planted -> BROKEN, never GAP
    assert c(timed_out=False, env_error=False, skipped=False, setup_ok=True,
             mutant_differs=False, guard_fired=False) == "BROKEN"
    # a declared skip -> SKIP
    assert c(timed_out=False, env_error=False, skipped=True, setup_ok=True,
             mutant_differs=False, guard_fired=False) == "SKIP"


def t_preflight_refuses_a_full_disk():
    neg = load_neg()
    # an impossible free requirement stands in for a full disk
    assert neg.preflight_disk(min_free_mb=10 ** 12), "preflight did not refuse a full disk"
    assert neg.preflight_disk(min_free_mb=0) is None, "preflight refused a healthy disk"


def _batch_status(neg, *, env_error):
    """A full 40-step negative suite: each step plants a real, verified mutant.
    With env_error every step is a resource failure; without it, the classifier
    reads the actual guard verdict (here: 38 fire=PASS, 2 genuinely bypass=GAP)."""
    out = []
    for i in range(40):
        guard_fired = i not in (7, 23)     # two genuine guard bypasses
        out.append(neg.classify_stages(
            timed_out=False, env_error=env_error, skipped=False,
            setup_ok=not env_error, mutant_differs=True, guard_fired=guard_fired))
    return out


def t_full_suite_before_and_after_resources():
    neg = load_neg()
    # BEFORE resources (ENOSPC on every step): all TEST_ERROR, ZERO guard-bypass
    pre = _batch_status(neg, env_error=True)
    assert pre.count("TEST_ERROR") == 40, pre.count("TEST_ERROR")
    assert pre.count("GAP") == 0, f"{pre.count('GAP')} false guard-bypass findings under ENOSPC"
    # AFTER resources (re-run the FULL suite): the real verdict surfaces
    post = _batch_status(neg, env_error=False)
    assert post.count("TEST_ERROR") == 0, "a TEST_ERROR survived once resources returned"
    assert post.count("GAP") == 2, post.count("GAP")
    assert post.count("PASS") == 38, post.count("PASS")


def t_finally_cleanup_present():
    with open(NEG, encoding="utf-8") as fh:
        src = fh.read()
    assert "    finally:" in src, "no finally-cleanup in the runner"
    assert "shutil.rmtree(_snap, ignore_errors=True)" in src
    # the preflight is called before the snapshot is even created
    assert "_short = preflight_disk()" in src


def main():
    case("the four stages are declared in order", t_stages_declared_in_order)
    case("a failed cp / ENOSPC / timeout is TEST_ERROR, not a guard bypass",
         t_env_error_is_test_error_not_gap)
    case("GAP is reported only when the validator accepted a real mutant",
         t_gap_only_when_validator_accepted_a_real_mutant)
    case("the resource preflight refuses a full disk", t_preflight_refuses_a_full_disk)
    case("the full suite: zero GAPs under ENOSPC, real verdict after resources",
         t_full_suite_before_and_after_resources)
    case("cleanup runs in a finally; preflight runs before the snapshot",
         t_finally_cleanup_present)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
