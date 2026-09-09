#!/usr/bin/env python3
"""FIX-EV-01.22 — the outcome corpus for stripe-billing (sherlock audit,
parent FIX-EV-01; depends on the family harness of FIX-EV-01.01).

The corpus (evals/cases/stripe-billing.json) is anchored to the audit's own
findings: a greenfield first release must carry happy + adversarial +
failure/retry trials and an empty corpus closes no gate (AS-06); an
order-sensitivity rubric must fail a swapped confirm/charge while passing
swapped reads, negative example kept beside it (AS-07); boundary n=1/n=3
statistics carry no zero-width intervals (AS-08, a no-op case — the skill
reports, redesigns nothing); a regrade of an old trace is labelled and a
mutated candidate must flip the gate (AS-10); plus negative routing — judged
on ARTIFACTS through the family's outcome-case contract, so stripe-billing can
no longer pass an eval by its name being picked.

Checked here, stdlib only.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
CASES = os.path.join(ROOT, "evals", "cases", "stripe-billing.json")
HARNESS = os.path.expanduser("~/DATA/sshlg-skills/test/outcome_harness.py")

failures = []
not_run = []


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


def t_cases_are_structurally_valid():
    m = manifest()
    ids = [c["id"] for c in m["cases"]]
    assert len(ids) == len(set(ids)) and len(ids) >= 5
    for c in m["cases"]:
        assert c["schema_version"] == "outcome-case/1"
        assert c["skill"] == "stripe-billing"
        assert c["environment"]["case_digest"] == \
            hashlib.sha256(c["prompt"]["text"].encode()).hexdigest(), \
            f"{c['id']}: case_digest does not pin the frozen prompt"
        assert c["checks"]["outcome"], \
            f"{c['id']}: no outcome checks — the name-picking eval again"


def t_positive_pins_the_kill_window():
    c = next(x for x in manifest()["cases"] if "webhook-idempotency" in x["id"])
    p = c["prompt"]["text"]
    assert "ONE transaction (or an outbox)" in p, "the DV-01 remedy is not pinned"
    assert "SIGKILL between the marker INSERT and the effect" in p, \
        "the kill-between-steps scenario is not pinned"


def t_negative_refuses_to_load():
    neg = next(c for c in manifest()["cases"] if "negative" in c["id"])
    assert "stripe-billing" in neg["checks"]["load_trace"]["expect_not_loaded"]


def t_grant_refund_and_hostile():
    m = manifest()
    gr = next(c for c in m["cases"] if "both-periods" in c["id"])
    assert "February→January" in gr["prompt"]["text"], "the DV-02 fixture is not pinned"
    assert "does not by itself lock the row" in gr["prompt"]["text"]
    rf = next(c for c in m["cases"] if "refund-cas" in c["id"])
    assert "compare-and-swap" in rf["prompt"]["text"], "the DV-04 remedy is not pinned"
    assert "must not overwrite a newer total" in rf["prompt"]["text"]
    ho = next(c for c in m["cases"] if "hostile" in c["id"])
    assert "always_invoice" in ho["prompt"]["text"] and "proration_behavior:none" in ho["prompt"]["text"]
    assert any((o.get("expect") or "") == "release" for o in ho["checks"]["outcome"])


def t_live_gated_and_manifest_rules():
    m = manifest()
    live = next(c for c in m["cases"] if "live" in c["id"])
    cmd = live["checks"]["tool"][0]["command"]
    assert "STRIPE_TEST_SECRET_KEY" in cmd, \
        "the live case has no credential probe — it cannot NOT_RUN"
    assert "never a PASS and never an invented result" in live["prompt"]["text"]
    flat = " ".join(json.dumps(m, ensure_ascii=False).split())
    for needle in ("actual output oracle", "raw result", "with/without-skill",
                   "NOT_RUN, never PASS", "FAIL on the pre-fix output", "grader convenience"):
        assert needle in flat, f"the manifest no longer records {needle!r}"


def t_family_harness_validates_each_case_where_present():
    if not os.path.isfile(HARNESS):
        not_run.append("family harness absent — case validation NOT_RUN (never PASS)")
        return
    for c in manifest()["cases"]:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(c, fh)
            path = fh.name
        try:
            r = subprocess.run([sys.executable, HARNESS, path],
                               capture_output=True, text=True, timeout=60)
            assert r.returncode == 0, \
                f"{c['id']} rejected by the family harness:\n{r.stdout}"
        finally:
            os.unlink(path)


def main():
    case("every case is structurally valid, none is name-picking",
         t_cases_are_structurally_valid)
    case("the positive pins the DV-01 kill window", t_positive_pins_the_kill_window)
    case("the negative case refuses to load the skill", t_negative_refuses_to_load)
    case("the DV-02 grant, DV-04 refund-CAS and DV-19 hostile cases are pinned",
         t_grant_refund_and_hostile)
    case("the live case is credential-gated; manifest rules recorded",
         t_live_gated_and_manifest_rules)
    case("the family harness validates each case (where present)",
         t_family_harness_validates_each_case_where_present)
    for n in not_run:
        print(f"  NOT_RUN  {n}")
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
