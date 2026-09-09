#!/usr/bin/env python3
"""FIX-DV-18.01 — optimization heuristics are conditional, not blanket
prohibitions (sherlock audit, DV-18).

The finding: "only hero+nav initial", "named imports only", "allow all loaded
CSP origins for the score", "footer headings → p", and "modern last-two
targets" were prescriptions without measurement or a support policy.

The fix under test (frontend-performance/SKILL.md):
* a MEASURE-first banner: check the trace+scenarios, the browser-support
  contract, the accessibility owner before any change;
* acceptance covers low-end/slow-network scenarios, keyboard+headings, the
  supported-browser matrix, no new unapproved CSP origin, several comparable
  measurements with no functional loss;
* CSP origins by functional necessity; headings by structure; lazy-load by
  the measured waterfall; browserslist by a user-support policy; named imports
  conditional.

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


def t_measure_first_banner():
    d = flat()
    assert "Before any of these changes: MEASURE, don't prescribe." in d
    for check in ("performance trace + the scenarios", "browser-support contract",
                  "accessibility owner"):
        assert check in d, f"the pre-change check '{check}' is missing"


def t_acceptance_covers_the_axes():
    d = flat()
    for req in ("low-end/slow-network scenarios", "keyboard + heading structure intact",
                "supported-browser matrix still served", "NO new unapproved CSP origin",
                "several comparable before/after measurements",
                "no\n functional loss".replace("\n ", " ")):
        assert req in d or req.replace("\n ", " ") in d, f"acceptance axis missing: {req}"


def t_lazy_load_by_waterfall():
    d = flat()
    assert "Code split by the MEASURED waterfall" in d
    assert "is a starting hypothesis, not a rule" in d
    assert "Only hero + nav in initial bundle." not in d, "the blanket lazy rule survived"


def t_browserslist_by_policy():
    d = flat()
    assert "Target the browsers your USERS run" in d
    assert "not a default \"last 2\"" in d
    assert "example only — replace with your measured support matrix" in d


def t_named_imports_conditional():
    d = flat()
    assert "it is a tree-shaking aid, not a ban" in d
    assert "Named imports only. No `import * as`." not in d, "the named-imports ban survived"


def t_csp_by_necessity():
    d = flat()
    assert "Approve origins by FUNCTIONAL NECESSITY, not for the score" in d
    assert "No new origin ships unapproved." in d
    assert "**Whitelist all loaded origins**" not in d, "the whitelist-all rule survived"


def t_headings_by_structure():
    d = flat()
    assert "Heading hierarchy follows STRUCTURE, decided with the accessibility owner" in d
    assert "Accessibility is the owner here, not the score." in d


def main():
    case("the measure-first banner names the three pre-change checks",
         t_measure_first_banner)
    case("acceptance covers the required axes", t_acceptance_covers_the_axes)
    case("lazy-load follows the measured waterfall, not a blanket rule",
         t_lazy_load_by_waterfall)
    case("browserslist follows a user-support policy", t_browserslist_by_policy)
    case("named imports are conditional, not a ban", t_named_imports_conditional)
    case("CSP origins by functional necessity, not for the score", t_csp_by_necessity)
    case("headings by structure with the accessibility owner", t_headings_by_structure)
    if failures:
        print(f"\n{len(failures)} failure(s)")
        return 1
    print("\nall green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
