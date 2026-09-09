#!/usr/bin/env python3
"""FIX-DV-08.01 — ADC precedence was written in reverse (sherlock audit, DV-08).

The finding: both the SKILL.md body and the reference said attached service
account → local ADC → env var, but Google resolves env var → local ADC →
attached service account. A config change made against the wrong lever does
nothing.

The fix under test: both places corrected from one canonical order (env
FIRST), and the doctrine says to print the ACTUALLY-resolved principal/source
(without the secret) before configuring. The resolver is run over three fake
sources in an isolated env.

Standard library only.
"""
import os
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GA = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "google-auth")

failures = []


def case(name, fn):
    try:
        fn()
        print(f"  ok  {name}")
    except AssertionError as e:
        failures.append(f"{name}: {e}")
        print(f"FAIL  {name}: {e}")


def t_both_places_have_the_canonical_order():
    ref = " ".join(open(os.path.join(GA, "references", "adc-and-service-accounts.md"),
                        encoding="utf-8").read().split())
    # env var appears BEFORE the attached account in the ordered list
    i_env = ref.find("`GOOGLE_APPLICATION_CREDENTIALS` — env var pointing")
    i_attached = ref.find("**Attached service account** — via GCP metadata server "
                          "(Compute Engine, Cloud Run, GKE, etc.) ")
    # find within the ADC Search Order list specifically
    order = ref[ref.find("## ADC Search Order"):]
    assert order.find("`GOOGLE_APPLICATION_CREDENTIALS`") < order.find("**Attached service account**"), \
        "the reference still lists the attached account before the env var"
    assert "env var FIRST" in ref and "The old text here had it reversed" in ref
    assert "print the ACTUALLY-resolved principal and source" in ref

    sk = " ".join(open(os.path.join(GA, "SKILL.md"), encoding="utf-8").read().split())
    assert "env var FIRST — this line was reversed" in sk
    order_sk = sk[sk.find("ADC search order"):]
    assert order_sk.find("`GOOGLE_APPLICATION_CREDENTIALS`") < order_sk.find("attached service account"), \
        "the SKILL.md one-liner still lists the attached account first"
    assert "attached service account → `gcloud auth application-default login` file → `GOOGLE_APPLICATION_CREDENTIALS`" not in sk, \
        "the reversed one-liner survived"


# ---------------- the resolver, run over three fake sources


def resolve_adc(env, local_adc_present, attached_present, principals):
    """Google's actual precedence: env var, then local ADC, then attached.
    Returns (source, principal) — the source that WON and its account, never a
    secret."""
    if env.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return "env", principals["env"]
    if local_adc_present:
        return "local", principals["local"]
    if attached_present:
        return "attached", principals["attached"]
    return "none", None


PRINCIPALS = {"env": "env-sa@proj.iam", "local": "user@example.com",
              "attached": "vm-sa@proj.iam"}


def t_env_wins_when_all_three_present():
    src, who = resolve_adc({"GOOGLE_APPLICATION_CREDENTIALS": "/k.json"},
                           local_adc_present=True, attached_present=True,
                           principals=PRINCIPALS)
    assert src == "env" and who == "env-sa@proj.iam", \
        f"env did not win the precedence: {src}"


def t_local_wins_over_attached():
    src, _ = resolve_adc({}, local_adc_present=True, attached_present=True,
                         principals=PRINCIPALS)
    assert src == "local", "local ADC did not beat the attached account"


def t_attached_is_last():
    src, _ = resolve_adc({}, local_adc_present=False, attached_present=True,
                         principals=PRINCIPALS)
    assert src == "attached", "attached account not used when it is the only source"
    assert resolve_adc({}, False, False, PRINCIPALS)[0] == "none"


def t_report_names_the_resolved_source_not_a_secret():
    src, who = resolve_adc({"GOOGLE_APPLICATION_CREDENTIALS": "/k.json"},
                           True, True, PRINCIPALS)
    report = f"resolved via {src}: {who}"
    assert "/k.json" not in report, "the report leaked the credential path/secret"
    assert "env" in report and "env-sa@proj.iam" in report


def main():
    case("both places carry the canonical order (env first)",
         t_both_places_have_the_canonical_order)
    case("env wins when all three sources are present",
         t_env_wins_when_all_three_present)
    case("local ADC wins over the attached account", t_local_wins_over_attached)
    case("the attached account is last", t_attached_is_last)
    case("the report names the resolved source, not a secret",
         t_report_names_the_resolved_source_not_a_secret)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
