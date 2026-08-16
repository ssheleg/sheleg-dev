#!/usr/bin/env python3
"""Structural validator for sheleg-dev.

House rules, each one written because it can actually break:

  * one version, four files -- package.json, plugin.json, marketplace.json and
    the top CHANGELOG entry. A plugin whose manifest disagrees with its package
    installs fine and reports the wrong version forever.
  * SKILL.md front matter inside the Agent Skills limits, and `name` equal to
    the directory. Over-long front matter does not error -- it is silently
    truncated by the host, which is worse.
  * references/ and SKILL.md agree in BOTH directions: no link to a missing
    file, no file nobody links. The source this skill came from shipped a
    reference.md that nothing referenced.
  * no stray SKILL.md outside plugins/*/skills/*/, no build artifacts in the
    shipped tree.
  * CI runs this file. A validator that CI stopped calling is decoration.

Exit code 0 = green. Anything else = a fail with a reason on stderr.
"""

import json
import subprocess
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILURES = []


def fail(msg):
    FAILURES.append(msg)


def load_json(rel):
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        fail(f"missing {rel}")
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        fail(f"{rel}: invalid JSON -- {exc}")
        return None


def front_matter(path):
    """Return the raw front-matter block of a markdown file, or None."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None, text
    return m.group(1), text


def scalar(block, key):
    """Read one front-matter scalar without a YAML dependency.

    Handles both `key: value` and the folded `key: >-` form used for long
    descriptions, which is the only multi-line shape this repo ships.
    """
    m = re.search(rf"^{re.escape(key)}:\s*(.*)$", block, re.M)
    if not m:
        return None
    head = m.group(1).strip()
    if head not in (">-", ">", "|", "|-"):
        return head
    lines = []
    started = False
    for line in block.splitlines():
        if re.match(rf"^{re.escape(key)}:", line):
            started = True
            continue
        if not started:
            continue
        if line.startswith((" ", "\t")):
            lines.append(line.strip())
        elif line.strip() == "":
            lines.append("")
        else:
            break
    return " ".join(x for x in lines if x)


# ---------------------------------------------------------------- versions

pkg = load_json("package.json")
plugin = load_json("plugins/sheleg-dev/.claude-plugin/plugin.json")
market = load_json(".claude-plugin/marketplace.json")

version = pkg.get("version") if pkg else None
if not version:
    fail("package.json: missing version")

if plugin and plugin.get("version") != version:
    fail(f"version drift: plugin.json={plugin.get('version')!r} package.json={version!r}")

if market:
    plugins = market.get("plugins") or []
    if not plugins:
        fail("marketplace.json: plugins[] empty")
    for entry in plugins:
        if entry.get("version") != version:
            fail(
                f"version drift: marketplace.json {entry.get('name')!r}="
                f"{entry.get('version')!r} package.json={version!r}"
            )
        src = entry.get("source", "")
        if not os.path.isdir(os.path.join(ROOT, src.lstrip("./"))):
            fail(f"marketplace.json: source {src!r} does not exist")

changelog = os.path.join(ROOT, "CHANGELOG.md")
if not os.path.exists(changelog):
    fail("missing CHANGELOG.md")
else:
    with open(changelog, encoding="utf-8") as fh:
        text = fh.read()
    headings = re.findall(r"^## \[?v?(\d+\.\d+\.\d+)\]?", text, re.M)
    if not headings:
        fail("CHANGELOG.md: no version heading found")
    elif headings[0] != version:
        fail(f"version mismatch: CHANGELOG=v{headings[0]} package.json={version!r}")
    for dup in sorted({v for v in headings if headings.count(v) > 1}):
        fail(f"CHANGELOG.md: v{dup} documented twice -- the release notes would truncate")

# ------------------------------------------------------------------ skills

SKILL_ROOT = os.path.join(ROOT, "plugins", "sheleg-dev", "skills")
if not os.path.isdir(SKILL_ROOT):
    fail("missing plugins/sheleg-dev/skills/")
    skill_dirs = []
else:
    skill_dirs = sorted(
        d for d in os.listdir(SKILL_ROOT) if os.path.isdir(os.path.join(SKILL_ROOT, d))
    )
    if not skill_dirs:
        fail("plugins/sheleg-dev/skills/ has no skills")

for name in skill_dirs:
    sdir = os.path.join(SKILL_ROOT, name)
    spath = os.path.join(sdir, "SKILL.md")
    if not os.path.exists(spath):
        fail(f"{name}: no SKILL.md")
        continue

    block, text = front_matter(spath)
    if block is None:
        fail(f"{name}/SKILL.md: no front matter")
        continue

    fm_name = scalar(block, "name")
    fm_desc = scalar(block, "description")

    if fm_name != name:
        fail(f"{name}/SKILL.md: front-matter name {fm_name!r} != directory {name!r}")
    if not fm_name or len(fm_name) > 64:
        fail(f"{name}/SKILL.md: name must be 1-64 chars, got {len(fm_name or '')}")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", fm_name or ""):
        fail(f"{name}/SKILL.md: name {fm_name!r} must be lowercase [a-z0-9-]")
    if not fm_desc:
        fail(f"{name}/SKILL.md: description is required")
    elif len(fm_desc) > 1024:
        fail(
            f"{name}/SKILL.md: description is {len(fm_desc)} chars, limit 1024 "
            "-- hosts truncate silently, so this never surfaces at runtime"
        )
    if fm_desc and re.search(r"<[a-zA-Z/]", fm_desc):
        fail(f"{name}/SKILL.md: description must not contain angle-bracket tags")

    # references: both directions
    rdir = os.path.join(sdir, "references")
    on_disk = set()
    if os.path.isdir(rdir):
        on_disk = {f for f in os.listdir(rdir) if f.endswith(".md")}
    linked = set(re.findall(r"references/([A-Za-z0-9._-]+\.md)", text))

    for missing in sorted(linked - on_disk):
        fail(f"{name}/SKILL.md links references/{missing}, which does not exist")
    for orphan in sorted(on_disk - linked):
        fail(
            f"{name}/references/{orphan} exists but SKILL.md never links it "
            "-- an unreferenced reference is a file nobody loads"
        )

# --------------------------------------------------------------- hygiene

for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, "plugins")):
    if "__pycache__" in dirnames or any(f.endswith(".pyc") for f in filenames):
        fail(f"build artifacts inside plugins/ at {os.path.relpath(dirpath, ROOT)}")
    if "SKILL.md" in filenames:
        rel = os.path.relpath(dirpath, ROOT).replace(os.sep, "/")
        if not re.fullmatch(r"plugins/[^/]+/skills/[^/]+", rel):
            fail(f"stray SKILL.md at {rel}/SKILL.md -- only plugins/*/skills/*/ may hold one")

# ------------------------------------------------------------------- CI

wf = os.path.join(ROOT, ".github", "workflows", "validate.yml")
if not os.path.exists(wf):
    fail("missing .github/workflows/validate.yml")
else:
    with open(wf, encoding="utf-8") as fh:
        ci = fh.read()
    # Match the ENTRY POINT, not any mention. The negative self-tests below run
    # `python3 /tmp/<copy>/test/validate.py`, so a substring search for
    # "test/validate.py" stays satisfied after the real step is deleted -- which
    # is a guard that cannot fail. Require a step that runs it at the repo root.
    if not re.search(r"^\s*run:\s*python3\s+test/validate\.py\s*$", ci, re.M):
        fail("validate.yml has no `run: python3 test/validate.py` step -- the gate stopped being a gate")

# ---------------------------------------------------------------- verdict


def check_release_gates_on_validate():
    """A release must not publish over a red `validate`.

    On 2026-08-12 this repository tagged v0.4.1 while its own `validate` run for that
    exact tag FAILED, and npm served 0.4.1 four minutes later. The two are separate
    workflows, so nothing connected them: `release.yml` ran the structural validator and
    never the negative self-tests, which are steps in `validate.yml`.

    The fix is a `workflow_call` — the release calls the real suite rather than a copy of
    it — and this guard is what keeps the call there. A dependency nobody checks is a
    dependency somebody removes.
    """
    wf = os.path.join(ROOT, ".github/workflows")
    rel, val = os.path.join(wf, "release.yml"), os.path.join(wf, "validate.yml")
    if not (os.path.isfile(rel) and os.path.isfile(val)):
        return
    v = open(val, encoding="utf-8").read()
    r = open(rel, encoding="utf-8").read()
    if not re.search(r"^\s*workflow_call:\s*$", v, re.M):
        fail(".github/workflows/validate.yml: no `workflow_call:` trigger — the release "
             "workflow cannot run this suite, and a publish would go out over whatever "
             "subset it runs itself")
    if not re.search(r"^\s*uses:\s*\./\.github/workflows/validate\.yml\s*$", r, re.M):
        fail(".github/workflows/release.yml: does not call ./.github/workflows/validate.yml "
             "— a red validate would not stop a publish. This repository tagged v0.4.1 with "
             "a failing validate run and npm served it")
    if not re.search(r"^\s*needs:\s*(?:\[[^\]]*\bvalidate\b[^\]]*\]|validate)\s*$", r, re.M):
        fail(".github/workflows/release.yml: no job declares `needs: validate` — calling "
             "the suite without depending on it lets the release run beside it rather "
             "than after it")


check_release_gates_on_validate()

def _disclose_routing(msg):
    """A check that could not run, said out loud rather than counted as a pass."""
    print(f"  unlooked: {msg}")


def check_routed_triggers_still_advertised():
    """The family's routing hook fires on words this description has to keep.

    B-54, 2026-08-16: `sheleg-design` 1.37.0 shipped green on its own gate having dropped
    a phrase from its description that was a live trigger in the umbrella's
    `lib/triggers.js`. This repository has no way to know that table exists, and it
    releases BEFORE the umbrella re-pins, so the umbrella found out minutes after the tag.
    A hook firing on a promise nobody made is the defect; a patch release was the cost.

    **The table is not copied here.** The umbrella's own checker is asked, reading the
    module the hook itself calls, so there is no duplicate to drift. When no umbrella sits
    above this checkout — the ordinary state of a standalone clone, and of CI — this
    discloses instead of passing, because a check that cannot look must never read as one
    that looked.
    """
    script = os.path.join(str(ROOT), "..", "..", "test", "advertised_check.js")
    if not os.path.isfile(script):
        _disclose_routing("routed triggers — no sshlg-skills umbrella above this checkout")
        return
    try:
        proc = subprocess.run(["node", script, "--member", "sheleg-dev", "--root", str(ROOT)],
                              capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        _disclose_routing(f"routed triggers — could not run the umbrella's checker ({exc})")
        return
    if proc.returncode == 1:
        fail((proc.stdout + proc.stderr).strip())
    elif proc.returncode != 0:
        _disclose_routing(f"routed triggers — {(proc.stderr or 'the checker could not look').strip()}")


check_routed_triggers_still_advertised()


if FAILURES:
    print(f"FAIL: {len(FAILURES)} problem(s)", file=sys.stderr)
    for f in FAILURES:
        print(f"  - {f}", file=sys.stderr)
    sys.exit(1)

checks = 6 + len(skill_dirs)
print(f"OK: sheleg-dev structurally valid ({checks} checks, {len(skill_dirs)} skill(s), v{version})")
