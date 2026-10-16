#!/usr/bin/env python3
"""Frontend performance is tested in WebKit (Safari) first; Lighthouse and CDP
traces are the stated Chromium exception (family release 2026-10-16, R14).

A page measured only by Lighthouse was measured only in Chrome. The skill keeps
Lighthouse, PageSpeed Insights, CrUX and CDP traces — they are Chromium by
definition — and names them as the stated Chromium exception, with the WebKit
route first. Mutations that drop each point are refused, so the check is
watched saying no. Text integrity only: no claim that a model follows it.

Standard library only.
"""
import os
import re
import sys

sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SKILL = os.path.join(ROOT, "plugins", "sheleg-dev", "skills", "frontend-performance")
HEADING = "## Test browser — WebKit (Safari) first"

checks = 0
failures = []


def case(name, fn):
    global checks
    try:
        fn()
        checks += 1
        print(f"  ok  {name}")
    except (AssertionError, IndexError, ValueError) as e:
        failures.append(f"{name}: {e!r}")
        print(f"FAIL  {name}: {e!r}")


def read(rel):
    with open(os.path.join(SKILL, rel), encoding="utf-8") as fh:
        return fh.read()


def flat(text):
    return " ".join(text.split())


def engine_contract(text):
    section = flat(text.split(HEADING, 1)[1].split("\n## ", 1)[0])
    for needle in ("safaridriver", "Playwright", "`webkit`", "--browser webkit",
                   "npx playwright install webkit", "Safari Web Inspector",
                   "open -a Safari", "WebKit/Safari backend",
                   "stated Chromium exception", "say which and why", "Chrome Dev",
                   "temporary profile", "close every process",
                   "checked only in Chromium", "Lighthouse", "CDP trace",
                   "chrome-devtools MCP", "Chromium by definition"):
        assert needle in section, f"test-browser section no longer states {needle!r}"


def t_section():
    engine_contract(read("SKILL.md"))


def t_workflow_measure_and_validate():
    wf = read("SKILL.md").split("## Audit Workflow", 1)[1].split("\n## ", 1)[0]
    lines = {l.split("**")[1]: l for l in wf.splitlines() if l[:1].isdigit()}
    for step in ("Measure", "Validate"):
        assert "WebKit" in lines[step], f"workflow step {step} has no WebKit run"


def t_degradation_names_webkit_channels():
    deg = flat(read("SKILL.md").split("## Degradation", 1)[1])
    item = deg.split("**No browser channel**", 1)[1].split("**No network**", 1)[0]
    assert "safaridriver" in item and "Playwright `webkit`" in item


def t_contrast_check_webkit_first():
    ref = flat(read("references/accessibility-perf.md"))
    block = ref.split("### Checking Contrast", 1)[1].split("###", 1)[0]
    assert block.index("Safari Web Inspector") < block.index("Chrome DevTools")
    assert "Chromium" in block


def t_dropped_points_are_refused():
    text = read("SKILL.md")
    engine_contract(text)
    for token in ("safaridriver", "open -a Safari", "stated Chromium exception",
                  "temporary profile", "close every process",
                  "checked only in Chromium", "Chrome Dev", "Chromium by definition"):
        pattern = r"\s+".join(map(re.escape, token.split()))
        try:
            engine_contract(re.sub(pattern, "REMOVED", text))
        except AssertionError:
            continue
        raise AssertionError(f"dropping {token!r} was not refused")
    try:
        engine_contract(text.replace(HEADING, "## Something else"))
    except IndexError:
        return
    raise AssertionError("a missing section was not refused")


case("SKILL.md carries the WebKit-first test-browser section", t_section)
case("Measure and Validate steps run WebKit too", t_workflow_measure_and_validate)
case("Degradation names the WebKit channels", t_degradation_names_webkit_channels)
case("contrast check names Safari Web Inspector first", t_contrast_check_webkit_first)
case("dropping any point is refused", t_dropped_points_are_refused)

if failures:
    print(f"\n{len(failures)} failure(s), {checks} passed")
    sys.exit(1)
print(f"\nall green ({checks} checks)")
