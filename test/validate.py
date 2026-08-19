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
  * every path the SELF-DESCRIBING documents name exists here, and a `file:line`
    citation in one of them does not point past the end of that file. SECURITY.md
    was a copy of a sibling skill's and named six things this repository has never
    had, in the npm tarball -- a security document inviting the reader to verify,
    with commands that exit 2.
  * every SKILL.md body inside the Agent Skills budget AND inside the house working
    limit. Measured HERE: until 2026-08-20 this gate checked front matter only, and a
    skill past the working limit was found by running another repository's auditor.
  * every counted number in the two measuring documents recomputed rather than restated.
    All four in SECURITY.md were correct on the day they were written, which is the point.
  * the ledger's shipped heading naming what `git describe --tags` prints, and REQ-001's
    quoted verdict equal to the line this file prints. Both were wrong for a day.
  * CI runs this file. A validator that CI stopped calling is decoration.

**The verdict line counts the registry, not a guess.** It was `10 + len(skill_dirs)`, so
adding a skill moved the number and adding a check did not -- and five rows of
`docs/evidence/verification.md` read it as evidence a guard had arrived.

Exit code 0 = green. Anything else = a fail with a reason on stderr.
"""

import fnmatch
import glob
import json
import subprocess
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILURES = []


def fail(msg):
    FAILURES.append(msg)


# Every check this file makes is REGISTERED here, and the verdict line counts the registry.
# Until 2026-08-20 the count was `10 + len(skill_dirs)`, so adding a skill moved the number
# and adding a check did not — and four rows of `docs/evidence/verification.md` read that
# number as evidence that a guard had been added. A count that answers a different question
# from the one it is quoted for is worse than no count.
CHECKS = []


def check(fn):
    """Register a check. `len(CHECKS)` is the number the verdict line prints."""
    CHECKS.append(fn)
    return fn


def verdict_line():
    """The exact line a green run prints. Quoted in the ledger, and checked there."""
    return (f"OK: sheleg-dev structurally valid ({len(CHECKS)} checks, "
            f"{len(skill_dirs)} skill(s), v{version})")


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


@check
def check_one_version_four_files():
    """package.json, plugin.json, marketplace.json and the top CHANGELOG entry agree."""
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


@check
def check_changelog_heads_this_version():
    """The top `## vX.Y.Z` is this version, and no version is documented twice."""
    changelog = os.path.join(ROOT, "CHANGELOG.md")
    if not os.path.exists(changelog):
        fail("missing CHANGELOG.md")
        return
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

def _skill_front_matter(name):
    """The front-matter block and full text of one SKILL.md, or (None, None)."""
    spath = os.path.join(SKILL_ROOT, name, "SKILL.md")
    if not os.path.exists(spath):
        return None, None
    return front_matter(spath)


@check
def check_skill_front_matter():
    """Front matter inside the Agent Skills limits, and `name` equal to the directory."""
    for name in skill_dirs:
        block, _text = _skill_front_matter(name)
        if block is None and _text is None:
            fail(f"{name}: no SKILL.md")
            continue
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


@check
def check_references_resolve_both_ways():
    """No link to a missing reference, and no reference nobody links."""
    for name in skill_dirs:
        _block, text = _skill_front_matter(name)
        if text is None:
            continue
        rdir = os.path.join(SKILL_ROOT, name, "references")
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


@check
def check_no_stray_skill_or_build_artifacts():
    """No SKILL.md outside plugins/*/skills/*/, and no build artifacts in the shipped tree."""
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, "plugins")):
        if "__pycache__" in dirnames or any(f.endswith(".pyc") for f in filenames):
            fail(f"build artifacts inside plugins/ at {os.path.relpath(dirpath, ROOT)}")
        if "SKILL.md" in filenames:
            rel = os.path.relpath(dirpath, ROOT).replace(os.sep, "/")
            if not re.fullmatch(r"plugins/[^/]+/skills/[^/]+", rel):
                fail(f"stray SKILL.md at {rel}/SKILL.md -- only plugins/*/skills/*/ may hold one")


# ------------------------------------------------------------------- CI


@check
def check_ci_runs_the_validator():
    """CI runs this file. A validator that CI stopped calling is decoration."""
    wf = os.path.join(ROOT, ".github", "workflows", "validate.yml")
    if not os.path.exists(wf):
        fail("missing .github/workflows/validate.yml")
        return
    with open(wf, encoding="utf-8") as fh:
        ci = fh.read()
    # Match the ENTRY POINT, not any mention. The negative self-tests below run
    # `python3 /tmp/<copy>/test/validate.py`, so a substring search for
    # "test/validate.py" stays satisfied after the real step is deleted -- which
    # is a guard that cannot fail. Require a step that runs it at the repo root.
    if not re.search(r"^\s*run:\s*python3\s+test/validate\.py\s*$", ci, re.M):
        fail("validate.yml has no `run: python3 test/validate.py` step -- the gate stopped being a gate")

# ---------------------------------------------------------------- verdict


@check
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


def _disclose_routing(msg):
    """A check that could not run, said out loud rather than counted as a pass."""
    print(f"  unlooked: {msg}")


@check
def check_contributing_routes_to_files_that_exist():
    """The *Where things go* table sends a contributor somewhere; it had better be here.

    B-47: this table routed contributions to `benchmarks.md`, `growth-plays.md`,
    `myths.md`, `algorithm-updates.md`, `aeo-geo.md` and `scripts/page_audit.py`. All six
    belong to `seo-aeo-audit`; `git ls-files` here matched none. A whole document had been
    copied from a sibling and never adapted, and a sweep found **eleven** absent names
    where the board row had spotted six.

    **Only this table, and that is the point.** A general "every path in the file must
    exist" check cannot tell a path being USED from a path being DISCUSSED — the rewritten
    document names three of `seo-aeo-audit`'s files on purpose, to send a reader who wants
    them to the right repository, and the umbrella's `skills.json` for the same reason.
    Flagging those is standing instruction #7, which this family has recorded three times.
    The table is unambiguous: it is a list of places to put work in THIS repository.
    """
    path = os.path.join(ROOT, "CONTRIBUTING.md")
    if not os.path.isfile(path):
        fail("CONTRIBUTING.md is missing")
        return
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    match = re.search(r"^## Where things go\n(.*?)(?=^## )", text, re.S | re.M)
    if not match:
        fail("CONTRIBUTING.md: no `## Where things go` section — it is the one place that "
             "tells a contributor where work belongs, and B-47 is what happens when it "
             "describes another repository")
        return
    # TABLE ROWS ONLY, not the whole section. The first draft of this guard read
    # everything up to the next heading and immediately flagged the paragraph directly
    # below the table — the one that names three `seo-aeo-audit` files to send a reader
    # to the right repository. It caught its own author demonstrating #7 one paragraph
    # after writing about it.
    rows = [ln for ln in match.group(1).splitlines() if ln.lstrip().startswith("|")]
    cited = re.findall(r"`([A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:md|py|json|sh|yml))`", "\n".join(rows))
    if not cited:
        fail("CONTRIBUTING.md: the `Where things go` table names no file — an empty "
             "corpus makes this guard pass everything")
        return
    # A bare filename in this table is generic on purpose — "that skill's `SKILL.md`"
    # means one of six, not a file at the root. So a name resolves if the exact path
    # exists OR the basename exists anywhere here. `SKILL.md` passes; `benchmarks.md`,
    # the defect this guard was written for, still does not.
    present = set()
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules")]
        for fn in filenames:
            present.add(fn)
    for rel in dict.fromkeys(cited):
        if os.path.exists(os.path.join(ROOT, rel)) or os.path.basename(rel) in present:
            continue
        fail(f"CONTRIBUTING.md: `Where things go` sends contributions to {rel!r}, "
             f"which this repository has nowhere (B-47)")



# ------------------------------------------------- self-describing documents

# The documents whose SUBJECT is this repository. An outside reader meets the pack
# through these: `README.md` and `SECURITY.md` ship in the npm tarball (`package.json`
# -> `files`), `CONTRIBUTING.md` and the PR template greet a contributor on GitHub. A
# path named in one of them is a claim about what is IN this repository, so it has to
# resolve.
#
# `CHANGELOG.md` ships too and is deliberately NOT in this list, said out loud rather than
# left to be inferred: a history entry has to be able to name the dead path it removed,
# verbatim, or the record of the fix becomes unwritable. The B-47 and B-79 entries each
# quote half a dozen files that were never here, on purpose.
SELF_DESCRIBING_DOCS = (
    "README.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
    # `docs/` joined the corpus on 2026-08-20. Until then it was outside it, and
    # `docs/AGENT_SYNC.md` named six paths this repository does not have -- five
    # `references/*.md` and `agent_sync.py`, all of them the agent-sync skill's -- in a
    # document whose whole subject is how to coordinate work HERE.
    "docs/AGENT_SYNC.md",
    "docs/evals/stripe-billing.md",
)

# The other documents under `docs/`, and why they are NOT in the corpus. Same argument as
# `CHANGELOG.md` above, and it is the reason the exclusion is a list rather than a habit: a
# dated record has to be able to name the dead path it removed, verbatim, or the record of
# the fix becomes unwritable. `docs/evidence/verification.md` quotes `scripts/page_audit.py`
# and `benchmarks.md` because those were the defect; `backlog.md` quotes `manifesto.md` and
# `audit_skill.py`, which are another repository's tools.
#
# `check_docs_are_classified` is what keeps this honest: every markdown file under `docs/`
# must be in exactly one of the two lists, so a new live document cannot arrive unchecked
# and cannot be parked here without saying so.
DATED_RECORDS = {
    "docs/evidence/verification.md":
        "one row per shipped requirement, dated. Its rows quote the dead paths and the "
        "stale counts that WERE the defect, at the commit they were read",
    "docs/evidence/backlog.md":
        "the board. Its rows cite another repository's tools (`manifesto.md`, "
        "`audit_skill.py`) and the reader-project paths a finding was measured over",
    "docs/MERGES.md":
        "the agent-sync merge log, appended by the tool rather than written by hand "
        "(`.claude/agent-sync.json` -> `mergeLog.file`)",
}

# A path that belongs to another repository ON PURPOSE, declared one document at a time
# with the reason. This is the narrow answer to standing instruction #7 -- a check cannot
# tell a path being USED from a path being DISCUSSED, so the discussion is enumerated
# instead of guessed. Scoped to a single document each: the same name leaking into a
# different document is still a failure, which is how B-79 was found.
FOREIGN_BY_DESIGN = {
    ("CONTRIBUTING.md", "benchmarks.md"):
        "signpost: sends a contributor looking for it to seo-aeo-audit (B-47)",
    ("CONTRIBUTING.md", "growth-plays.md"):
        "signpost: sends a contributor looking for it to seo-aeo-audit (B-47)",
    ("CONTRIBUTING.md", "scripts/page_audit.py"):
        "signpost: sends a contributor looking for it to seo-aeo-audit (B-47)",
    ("CONTRIBUTING.md", "skills.json"):
        "the umbrella's catalogue in ssheleg/sshlg-skills, which re-pins this member",
    ("CONTRIBUTING.md", "agent_sync.py"):
        "ships with the agent-sync skill, which CONTRIBUTING names alongside it",
    ("README.md", ".claude/settings.json"):
        "the READER's settings file, where the manual gate is registered when the pack was "
        "installed by copy rather than as a plugin. It is the one path this repository must "
        "name and must never write -- SD-03",
    # `docs/AGENT_SYNC.md` is GENERATED -- its first line says so and names the generator.
    # A repo-local reword is overwritten by the next `agent_sync.py setup`, which is why
    # board B-83 puts the fix upstream and this list carries the names meanwhile.
    ("docs/AGENT_SYNC.md", "agent_sync.py"):
        "the generator of this very file; it ships with the agent-sync skill (B-83)",
    ("docs/AGENT_SYNC.md", "references/two-sources.md"):
        "agent-sync's own doctrine, which the line above points at by name (B-83)",
    ("docs/AGENT_SYNC.md", "references/lease-protocol.md"):
        "agent-sync's own doctrine (B-83)",
    ("docs/AGENT_SYNC.md", "references/branching.md"):
        "agent-sync's own doctrine (B-83)",
    ("docs/AGENT_SYNC.md", "references/roadmap.md"):
        "agent-sync's own doctrine (B-83)",
    ("docs/AGENT_SYNC.md", "references/pipeline-binding.md"):
        "agent-sync's own doctrine (B-83)",
    ("docs/evals/stripe-billing.md", "audit_skill.py"):
        "make-skill's house auditor, in ssheleg/make-skill. Named because the GAP/PASS pair "
        "beside it is that script's counter and this gate cannot recompute it",
    ("docs/evals/stripe-billing.md", "settings.json"):
        "the READER's Claude Code settings, read to establish the neighbour set rather "
        "than assumed -- the same file README.md must name and never write",
}

# A path a document that SHIPS IN THE TARBALL names, which the tarball does not contain.
# Declared one document at a time, with where a reader who only has the tarball can get it.
#
# The defect, measured 2026-08-20: `SECURITY.md:143-144` sent a reader to
# `docs/evidence/verification.md` and `CONTRIBUTING.md`. Both resolve in a clone and
# `npm pack --dry-run` lists neither, so the path guard passed while the one document an
# outside reader consults *precisely because they will not read the code* pointed at two
# files they do not have. The existing guard could not see it: it resolves against the
# clone, which is the wrong filesystem for a document that ships.
NOT_IN_THE_TARBALL = {
    ("README.md", "install.sh"):
        "the shell installer is clone-only: `files` ships `bin/` and `plugins/`, not the "
        "root script. README names it as an alternative to `npx`, from the repository",
    ("README.md", "marketplace.json"):
        "the marketplace manifest is how a plugin channel finds the pack; it is read from "
        "the GitHub repository, never from the npm tarball",
    ("README.md", "test/validate.py"):
        "the gate, named as the thing that compares the copy-channel snippet against the "
        "plugin manifest. Clone-only, like the rest of `test/`",
    ("README.md", "test/moneygate_test.js"):
        "the gate's own suite. A tarball reader is pointed at the repository for it, and "
        "`SECURITY.md` -> *Verifying for yourself* opens with the `git clone`",
    ("README.md", "test/fixtures_test.js"):
        "the money-fixture suite, same as above",
    ("SECURITY.md", "test/validate.py"):
        "the gate. Named before the clone block as the thing that refuses a dead path, and "
        "run inside it -- the block's first line is `git clone`",
    ("SECURITY.md", "test/moneygate_test.js"):
        "run inside *Verifying for yourself*, after the `git clone`",
    ("SECURITY.md", "test/fixtures_test.js"):
        "run inside *Verifying for yourself*, after the `git clone`",
    ("SECURITY.md", "install.sh"):
        "clone-only, and the table row now says so: the tarball ships `bin/sheleg-dev.js`, "
        "not the shell installer",
    ("SECURITY.md", "docs/evidence/verification.md"):
        "the ledger, named as repository-only in the sentence itself -- this is the "
        "2026-08-20 defect, fixed by saying where it is rather than by shipping it",
    ("SECURITY.md", "CONTRIBUTING.md"):
        "the contributor guide, named as repository-only in the sentence itself",
}

_PATH_TOKEN = re.compile(
    r"^(?:[A-Za-z0-9_.*-]+/)*[A-Za-z0-9_.*-]+"
    r"\.(?:md|mdc|py|js|json|sh|yml|yaml|ts|tsx|txt)$"
)


def _named_paths(text):
    """Every path-shaped token a reader could try, with its line number.

    Two sources, because the defect hides in the second one. Inline code spans are the
    obvious half; the other half is fenced blocks, and B-79's worst reference -- a
    "verify for yourself" command that cannot run -- was a fenced line, not a span. A
    guard reading only backticks would have passed the document it exists to catch.

    Tokenised on whitespace so a span holding a command (`agent_sync.py setup`) is read
    as its parts. URLs, flags and `~/`-rooted paths are somebody else's filesystem.
    """
    fenced = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        spans = [line] if fenced else [m.group(1) for m in re.finditer(r"`([^`\n]+)`", line)]
        for span in spans:
            for raw in span.split():
                tok = raw.strip("(),;:'\"<>[]|").lstrip("$")
                if "://" in tok or tok.startswith(("-", "~", "@", "/")):
                    continue
                # `path:236` and `path:21-22` are this family's evidence convention, and
                # M-07 is about an address another actor can RESOLVE. So the suffix is
                # split off and checked rather than making the whole token unreadable --
                # which is also how an `…/abbreviated/path.md:12` would evade the guard
                # entirely, so do not write one.
                ref = re.search(r":(\d+)(?:-\d+)?$", tok)
                if ref:
                    tok = tok[: ref.start()]
                if _PATH_TOKEN.match(tok):
                    yield lineno, tok, int(ref.group(1)) if ref else None


def _tarball_paths():
    """Every path `npm pack` would put in the tarball, from `package.json` -> `files`.

    Reimplemented rather than shelled out to `npm pack --dry-run`, because `npm test` has to
    work offline and without npm on PATH. `files` here is six entries, two of them
    directories, and npm always adds `package.json` -- so the expansion is a walk.

    Verified against npm on 2026-08-20: **56 paths, set-identical** to
    `npm pack --dry-run --json`. That command stays in `SECURITY.md` ->
    *Verifying for yourself* as the cross-check a reader can run.
    """
    entries = (pkg or {}).get("files") or []
    out = {"package.json"}
    for entry in entries:
        base = os.path.join(ROOT, entry)
        if os.path.isdir(base):
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames[:] = [d for d in dirnames if d not in ("__pycache__", "node_modules")]
                for fn in filenames:
                    if fn.endswith(".pyc") or fn == ".DS_Store":
                        continue
                    rel = os.path.relpath(os.path.join(dirpath, fn), ROOT)
                    out.add(rel.replace(os.sep, "/"))
        elif os.path.isfile(base):
            out.add(entry)
    return out


def _in_tarball(tok, tarball, tarball_basenames):
    """Same resolution rules as `_resolves_here`, against the tarball instead of the clone.

    Exact path, directory prefix, glob, or a bare basename -- the last one deliberately, for
    the same reason `_resolves_here` has it: `SKILL.md` in a table means one of six.
    """
    rel = tok[2:] if tok.startswith("./") else tok
    if rel in tarball:
        return True
    if any(t == rel or t.startswith(rel.rstrip("/") + "/") for t in tarball):
        return True
    if "*" in rel and any(fnmatch.fnmatch(t, rel) for t in tarball):
        return True
    return os.path.basename(rel) in tarball_basenames


def _resolves_here(tok, basenames):
    """Exact path, glob, or a bare name that exists somewhere in the tree.

    The basename fallback is deliberate and inherited from the B-47 guard: `SKILL.md`
    means one of six, not a file at the root. It is also the reason this guard is not a
    substitute for reading -- it answers "is there such a file at all", which is the
    question a dead cross-repo copy fails.
    """
    rel = tok[2:] if tok.startswith("./") else tok
    if os.path.exists(os.path.join(ROOT, rel)):
        return True
    if glob.glob(os.path.join(ROOT, rel)):
        return True
    return os.path.basename(rel) in basenames


@check
def check_self_describing_docs_resolve():
    """Every path these four documents name must exist here (B-79).

    B-79, 2026-08-19: `SECURITY.md` was a wholesale copy of `seo-aeo-audit`'s. It
    described "one small Python script", `scripts/page_audit.py`, a `commands/` and a
    `cursor/rules/` directory, and `references/threats-and-defense.md` -- none of which
    this repository has ever had -- and closed with a *Verifying for yourself* block whose
    second command (`python3 test/test_page_audit.py`) exits 2 and whose third greps a
    path under a skill directory named `sheleg-dev` that does not exist. It shipped in the
    npm tarball, so the pack was telling an outside reader to verify its safety with
    commands that cannot run. Six dead references in the one document a reader consults
    precisely because they will not read the code.

    B-47 fixed the same disease in one table of `CONTRIBUTING.md` and deliberately went no
    wider. This is the widening it was waiting for, and it is bounded twice rather than
    once: by the corpus (documents ABOUT this repository -- a skill reference naming the
    reader's `next.config.ts` or `src/lib/heleket.ts` is describing their project, not
    claiming a file here, and 41 such names would have been false positives) and by
    `FOREIGN_BY_DESIGN`, which enumerates the cross-repo signposts one document at a time.

    An exemption that stops matching anything is itself a failure -- otherwise the list
    silently widens into a blanket as the documents move underneath it.
    """
    basenames = set()
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules", "graphify-out")]
        basenames.update(filenames)

    tarball = _tarball_paths()
    tarball_basenames = {os.path.basename(t) for t in tarball}

    used = set()
    used_tarball = set()
    for doc in SELF_DESCRIBING_DOCS:
        path = os.path.join(ROOT, doc)
        if not os.path.isfile(path):
            fail(f"{doc} is missing -- it is one of the documents an outside reader meets "
                 "the pack through")
            continue
        ships = _in_tarball(doc, tarball, set())
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        for lineno, tok, ref in _named_paths(text):
            if (doc, tok) in FOREIGN_BY_DESIGN:
                used.add((doc, tok))
                continue
            if not _resolves_here(tok, basenames):
                fail(f"{doc}:{lineno} names {tok!r}, which this repository has nowhere "
                     "(B-79). Either the path is wrong or the claim is another "
                     "repository's -- if it is deliberately foreign, declare it in "
                     "FOREIGN_BY_DESIGN with a reason")
                continue
            # Resolving in the clone is the wrong question for a document that SHIPS. The
            # tarball is a different filesystem and it is the only one a reader who reached
            # this pack through npm has.
            if ships and not _in_tarball(tok, tarball, tarball_basenames):
                if (doc, tok) in NOT_IN_THE_TARBALL:
                    used_tarball.add((doc, tok))
                else:
                    fail(f"{doc}:{lineno} names {tok!r}, which resolves in a clone and is "
                         "NOT in the published tarball -- and this document ships. A reader "
                         "who has only the tarball cannot reach it. Either put it in "
                         "`package.json` -> `files`, say in the sentence where it lives, or "
                         "declare it in NOT_IN_THE_TARBALL with a reason")
                    continue
            # A `file:line` whose line is past the end of the file is a pointer that
            # resolves to nothing, which is the same defect one level down.
            target = os.path.join(ROOT, tok[2:] if tok.startswith("./") else tok)
            if ref and os.path.isfile(target):
                with open(target, encoding="utf-8", errors="replace") as fh:
                    total = sum(1 for _ in fh)
                if ref > total:
                    fail(f"{doc}:{lineno} cites {tok}:{ref}, but that file has {total} "
                         "lines -- the address resolves to nothing (B-79)")

    for key, reason in FOREIGN_BY_DESIGN.items():
        if key not in used:
            fail(f"FOREIGN_BY_DESIGN carries {key[1]!r} for {key[0]} ({reason}) but the "
                 "document no longer names it -- a stale exemption is a hole waiting for "
                 "the next copied paragraph")
    for key, reason in NOT_IN_THE_TARBALL.items():
        if key not in used_tarball:
            fail(f"NOT_IN_THE_TARBALL carries {key[1]!r} for {key[0]} ({reason}) but that "
                 "document no longer names it, or the path now ships -- either way the "
                 "exemption is a hole")



# ------------------------------------------------ credential boundaries (M-06)

# Manifesto M-06: *a credential that cannot reach production is stronger than a sentence
# saying not to use it there, because the last control still works after context loss.*
#
# A reference document that hands the reader a provider secret is the moment that control
# is either installed or lost. So: a document may not set a live credential in a copyable
# block without setting the environment that credential is declared to belong to, and it
# must ship the boot assertion that refuses the two mismatches -- plus, where the provider
# offers no test credential at all, the exposure that remains, named.
#
# Table-driven so a second provider is a row, not a second shape (M-44). It carries ONE
# row today, and that is a measurement rather than an oversight: `stripe-billing`
# prescribes the same control at `references/price-integrity.md:62-64` and asks for it at
# `references/testing-and-local-dev.md:246` ("something asserts they agree") while
# shipping no assertion to copy. Filed as board **B-85**, not enforced here, because a
# guard added in the same breath as the defect it would flag turns the gate red for work
# this row did not do.
CREDENTIAL_BOUNDARIES = {
    "crypto-payments/references/heleket-provider.md": {
        # the env var that IS the secret
        "secret": "HELEKET_API_KEY",
        # the separate declaration of which environment it belongs to. Separate on
        # purpose: price-integrity.md:62-64 -- "one variable that does both cannot be
        # checked for consistency; two can."
        "declared_env": "HELEKET_ENV",
        # the boot assertion that compares them
        "assertion": "assertHeleketEnv",
        # both directions must be refusable, by code rather than by sentence: a code
        # survives a rewording, and an operator can grep their logs for it
        "codes": (
            "HELEKET_ENV_TEST_HOLDS_LIVE_CREDENTIAL",
            "HELEKET_ENV_LIVE_HOLDS_TEST_CREDENTIAL",
        ),
        # the provider offers no separate test credential, so the residual risk is
        # written down rather than left silent
        "exposure": "### Residual exposure",
    },
}

_ASSIGNS = re.compile(r"^\s*(?:export\s+)?%s\s*=")


def _fenced_blocks(text):
    """Yield (first_line_number, block_text) for every fenced block.

    Blocks, not lines, because the invariant is about what a reader COPIES. A `.env`
    snippet handing over a key is copied whole; whether the environment is declared
    beside it is a property of the block, not of the file.
    """
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("```"):
            start = i + 1
            j = i + 1
            while j < len(lines) and not lines[j].lstrip().startswith("```"):
                j += 1
            yield start + 1, "\n".join(lines[start:j])
            i = j + 1
        else:
            i += 1


@check
def check_docs_are_classified():
    """Every markdown file under `docs/` is either checked or declared a dated record.

    `docs/` was outside the corpus until 2026-08-20, and `docs/AGENT_SYNC.md` spent that
    time naming six paths this repository does not have. Widening the corpus closes those
    six; this check is what stops the next document arriving outside it. A file in NEITHER
    list is unclassified -- which is how `docs/` got out of the corpus the first time -- and
    a file in BOTH is a contradiction rather than a belt-and-braces.
    """
    root = os.path.join(ROOT, "docs")
    if not os.path.isdir(root):
        fail("docs/ is missing -- AGENT_SYNC.md, the evals record and the two evidence "
             "documents all live there")
        return
    found = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules")]
        for fn in filenames:
            if fn.endswith(".md"):
                rel = os.path.relpath(os.path.join(dirpath, fn), ROOT)
                found.add(rel.replace(os.sep, "/"))
    if not found:
        fail("docs/ holds no markdown -- an empty corpus makes this check pass everything")
        return
    checked = set(SELF_DESCRIBING_DOCS)
    for rel in sorted(found):
        in_corpus = rel in checked
        in_records = rel in DATED_RECORDS
        if in_corpus and in_records:
            fail(f"{rel} is both in SELF_DESCRIBING_DOCS and in DATED_RECORDS -- one of the "
                 "two is wrong, and the pair reads as coverage either way")
        elif not in_corpus and not in_records:
            fail(f"{rel} is in neither SELF_DESCRIBING_DOCS nor DATED_RECORDS. Every "
                 "document under docs/ is one or the other: a live document whose paths "
                 "must resolve, or a dated record that has to be able to quote a dead one. "
                 "Unclassified is how docs/ sat outside the corpus until 2026-08-20")
    for rel in sorted(DATED_RECORDS):
        if rel not in found:
            fail(f"DATED_RECORDS carries {rel!r}, which is not under docs/ -- a stale "
                 "exemption is a hole")


@check
def check_credential_boundary():
    """A copyable block that sets a live credential must declare its environment.

    The defect, measured 2026-08-19 (manifesto program row SD-02): `crypto-payments`
    had no test/live credential boundary of any kind. `HELEKET_API_KEY` was the only
    credential, it is *also* the webhook signing secret
    (`heleket-provider.md:126`), and the document's own local-development path handed
    the reader that key with no environment beside it (`:1146`) while telling them to
    flip "Test mode" in the merchant dashboard (`:1155`) -- an account-level toggle,
    not a credential. So a dev or agent run held the production credential, and the
    document never said so.

    Four requirements, each one a thing that was actually missing:

      1. every block that ASSIGNS the secret also assigns the declared environment --
         the `:1146` defect, and the only part of this check that reads position
         rather than presence;
      2. the boot assertion exists to be copied, so the control is a snippet and not
         a paragraph;
      3. both mismatches are refusable by a stable code -- a live credential declared
         test, and a test credential declared live. One direction is half a boundary:
         the second is how a staging merchant's key reaches production and settles
         real money to a wallet nobody reconciles;
      4. where the provider offers no test credential at all, the exposure is named.
         Heleket does not offer one -- one key per merchant, no sandbox host, "test
         mode" a dashboard toggle over the same key. An unavoidable risk that is
         written down is a different object from one that is silent.
    """
    for rel, spec in CREDENTIAL_BOUNDARIES.items():
        path = os.path.join(SKILL_ROOT, rel)
        if not os.path.isfile(path):
            fail(f"credential boundary: {rel} is missing -- it is the document that hands "
                 f"the reader {spec['secret']}")
            continue
        with open(path, encoding="utf-8") as fh:
            text = fh.read()

        assign_secret = re.compile(_ASSIGNS.pattern % re.escape(spec["secret"]), re.M)
        assign_env = re.compile(_ASSIGNS.pattern % re.escape(spec["declared_env"]), re.M)

        blocks = 0
        for lineno, block in _fenced_blocks(text):
            if not assign_secret.search(block):
                continue
            blocks += 1
            if not assign_env.search(block):
                fail(f"{rel}:{lineno} — a copyable block sets {spec['secret']} without "
                     f"{spec['declared_env']}. A credential handed over with no declared "
                     "environment is the M-06 defect: the run holds production and nothing "
                     "can tell. Set both in the same block")
        if not blocks:
            fail(f"{rel}: no block assigns {spec['secret']} — this guard's corpus is empty, "
                 "which makes it pass everything. Either the document stopped handing the "
                 "credential over, or the assignment shape changed and this check went blind")

        if spec["assertion"] not in text:
            fail(f"{rel}: no {spec['assertion']}() to copy. M-06 is that prose is the "
                 "weakest control surface — a boundary the reader has to re-derive is a "
                 "sentence, not a control")
        for code in spec["codes"]:
            if code not in text:
                fail(f"{rel}: the boot assertion cannot refuse {code} — a boundary that "
                     "refuses one direction only lets the other one through")
        if spec["exposure"] not in text:
            fail(f"{rel}: no {spec['exposure']!r} section. This provider issues one "
                 "credential per merchant and no test key, so a residual risk remains "
                 "after the assertion; unwritten, it reads as absent")



# The manual gate. Each entry is a category the hook must be able to refuse AND a fixture
# file must be able to demonstrate — a list, because a gate whose categories drift out of
# the fixtures is a gate nobody has watched refuse them.
MANUAL_GATE_CATEGORIES = (
    "live-key",             # sk_live_ / rk_live_ reaching a shell
    "credential",           # a provider credential with no test variant, in a test run
    "refund",               # money movement, and not undoable
    "payout",               # money out
    "dispute",              # closing a dispute accepts the loss
    "live-flag",            # an explicit request for production access
    "self-authorisation",   # granting yourself the gate's own switch
    "skip-billing",         # the free-money path, in production
)

# The prose this pack shipped for four releases, and the sites that had to stop being only
# prose. `manifesto.md:200` — "a precondition is stronger than a warning."
MANUAL_GATE_PROSE = {
    "crypto-payments/SKILL.md": "Never auto-refund from the webhook",
    "stripe-billing/references/webhook-events.md": "route it to a human",
}

GATE_HOOKS = "plugins/sheleg-dev/hooks"


def _has_key(node, key):
    """Is `key` anywhere in this JSON tree?"""
    if isinstance(node, dict):
        return key in node or any(_has_key(v, key) for v in node.values())
    if isinstance(node, list):
        return any(_has_key(v, key) for v in node)
    return False


@check
def check_manual_gate():
    """The four manual-gate categories must be refusable, not merely described.

    The defect, measured 2026-08-19 (manifesto program row SD-03, requirement **M-30**):
    all four categories `manifesto.md:204` names -- ambiguity, external publication,
    irreversible action, money movement, production access, destructive operations,
    changes of scope -- were named in this pack's prose and stopped nothing. The plugin
    shipped no hooks, no permission list and no gate, so
    `crypto-payments/SKILL.md:309-310` ("Never auto-refund from the webhook. Route holds
    and refunds to a queue a human can see") and
    `stripe-billing/references/webhook-events.md:169-170` ("route it to a human --
    evidence has a deadline") were advice to a reader who could ignore them and an agent
    that never saw them.

    Seven requirements, each one a way this could quietly stop being a gate:

      1. the hook is SHIPPED -- `hooks/hooks.json` plus the two scripts, inside
         `plugins/`, which is what npm packs and what the plugin channel loads;
      2. it fires at `PreToolUse`, the only event that can still prevent something.
         `manifesto.md:200`: a precondition is stronger than a warning;
      3. it carries **no `if` filter**. The Claude Code reference calls that filter
         best-effort and says it FAILS OPEN on a command it cannot parse, so a gate
         resting on it ships with a documented bypass -- and `Bash(stripe refunds*)` is
         exactly the shape a `bash -c '...'` wrapper defeats;
      4. the deciding is in a pure module the hook requires, not in the hook. Enforced by
         name so the split cannot be quietly collapsed;
      5. the hook fails silent -- a `catch` and `process.exit(0)`. A guard that throws
         breaks every turn in every session, including sessions of packs that never asked
         for this one;
      6. every category is refusable AND fixtured. A category present in the module and
         absent from the fixtures is a refusal nobody has watched;
      7. **both directions are fixtured.** The audit rated a guard nobody has watched
         failing as no evidence; the converse is that a guard which refuses correct input
         gets switched off, and then the pack is back to prose. So the fixture file must
         carry allow-plants as well as deny-plants.

    And the prose sites are required to name the mechanism, because the two documents are
    where a reader looks for it.
    """
    hooks_rel = f"{GATE_HOOKS}/hooks.json"
    hooks_path = os.path.join(ROOT, hooks_rel)
    if not os.path.isfile(hooks_path):
        fail(f"manual gate: {hooks_rel} is missing -- M-30's categories are prose again, and "
             "prose stops nothing")
        return
    try:
        with open(hooks_path, encoding="utf-8") as fh:
            hooks = json.load(fh)
    except json.JSONDecodeError as exc:
        fail(f"{hooks_rel}: invalid JSON -- {exc}")
        return

    pre = (hooks.get("hooks") or {}).get("PreToolUse") or []
    if not pre:
        fail(f"{hooks_rel}: no PreToolUse entry. A gate at PostToolUse is a report about a "
             "refund that already cleared -- manifesto.md:200, a precondition is stronger "
             "than a warning")
    commands = [
        h.get("command", "")
        for entry in pre
        for h in (entry.get("hooks") or [])
    ]
    if not any("money-gate.js" in c for c in commands):
        fail(f"{hooks_rel}: no PreToolUse hook runs money-gate.js")
    if not any("Bash" in (entry.get("matcher") or "") for entry in pre):
        fail(f"{hooks_rel}: no PreToolUse entry matches Bash -- a shell is where a live key "
             "gets exported and where the CLI runs")
    # The OTHER half, and it had no guard at all until 2026-08-20. Measured that day:
    # deleting the `mcp__.*` entry from hooks.json left this validator, the gate fixtures
    # and the money fixtures all at exit 0, while `lib/moneygate.js` does refuse
    # `mcp__plugin_stripe_stripe__create_refund` by name. A rule the module enforces and
    # the manifest no longer routes to it is a refusal that never gets asked for -- and the
    # Stripe MCP server ships `create_refund` as a tool, so the shell is not the only door.
    if not any(re.search(r"mcp__", entry.get("matcher") or "") for entry in pre):
        fail(f"{hooks_rel}: no PreToolUse entry matches an `mcp__…` tool name. "
             f"{GATE_HOOKS}/lib/moneygate.js decides non-Bash tools from the NAME "
             "(MONEY_TOOL), so `create_refund` on an MCP server is refusable -- but only if "
             "the manifest routes those calls to it. A refund does not care which door it "
             "came through")
    if _has_key(hooks, "if"):
        fail(f"{hooks_rel}: a hook entry declares `if`. The reference calls that filter "
             "best-effort and FAILS OPEN on a command it cannot parse, so a guard resting "
             "on it ships with a bypass. Match broadly and decide in the module")

    hook_rel = f"{GATE_HOOKS}/money-gate.js"
    lib_rel = f"{GATE_HOOKS}/lib/moneygate.js"
    hook_path = os.path.join(ROOT, hook_rel)
    lib_path = os.path.join(ROOT, lib_rel)
    for rel, path in ((hook_rel, hook_path), (lib_rel, lib_path)):
        if not os.path.isfile(path):
            fail(f"manual gate: {rel} is missing")
            return

    with open(hook_path, encoding="utf-8") as fh:
        hook_src = fh.read()
    with open(lib_path, encoding="utf-8") as fh:
        lib_src = fh.read()

    # The REQUIRE, not any mention. A substring search for "moneygate.js" is satisfied by
    # this hook's own doc comment, which names the module four times -- so the plant that
    # renames the require passed and this check was reading prose. Watched, 2026-08-19.
    if not re.search(r"require\([^)]*['\"]moneygate\.js['\"]", hook_src):
        fail(f"{hook_rel}: does not require {lib_rel}. The invariant is that a guard decides "
             "in a pure module and the hook only moves bytes -- a decision inlined here "
             "cannot be fixtured without a session")
    if "catch" not in hook_src or "process.exit(0)" not in hook_src:
        fail(f"{hook_rel}: must catch everything and exit 0. A hook that throws breaks every "
             "turn in every session, including sessions of packs that never asked for this one")
    if "permissionDecision" not in hook_src or "deny" not in hook_src:
        fail(f"{hook_rel}: emits no PreToolUse deny decision -- it cannot refuse anything")

    test_rel = "test/moneygate_test.js"
    test_path = os.path.join(ROOT, test_rel)
    if not os.path.isfile(test_path):
        fail(f"manual gate: {test_rel} is missing -- a guard nobody has watched failing is "
             "not evidence that it works")
        return
    with open(test_path, encoding="utf-8") as fh:
        test_src = fh.read()

    for category in MANUAL_GATE_CATEGORIES:
        if f"'{category}'" not in lib_src:
            fail(f"{lib_rel}: nothing refuses the {category!r} category -- M-30 names money "
                 "movement, irreversible action, production access and destructive "
                 "operations, and a missing one is the one that gets used")
        if f"'{category}'" not in test_src:
            fail(f"{test_rel}: no fixture names the {category!r} category. A refusal nobody "
                 "has watched is indistinguishable from a refusal that does not happen")

    refusals = test_src.count("\nrefuses(")
    allowances = test_src.count("\nallows(")
    if refusals < len(MANUAL_GATE_CATEGORIES):
        fail(f"{test_rel}: {refusals} deny-plants for {len(MANUAL_GATE_CATEGORIES)} categories")
    if allowances < refusals // 2:
        fail(f"{test_rel}: {allowances} allow-plants against {refusals} deny-plants. Both "
             "directions matter: a guard that refuses correct input gets switched off, and "
             "this repository's own references quote sk_live_ and hand over a .env heredoc")

    # The suite must actually run it. `npm test` is the gate CONTRIBUTING names.
    if pkg and "moneygate_test.js" not in (pkg.get("scripts") or {}).get("test", ""):
        fail("package.json: `npm test` does not run test/moneygate_test.js -- a fixture file "
             "nothing runs is a file that rots green")
    ci_path = os.path.join(ROOT, ".github", "workflows", "validate.yml")
    if os.path.isfile(ci_path):
        with open(ci_path, encoding="utf-8") as fh:
            if "moneygate_test.js" not in fh.read():
                fail("validate.yml: CI never runs test/moneygate_test.js")

    for rel, phrase in MANUAL_GATE_PROSE.items():
        path = os.path.join(SKILL_ROOT, rel)
        if not os.path.isfile(path):
            fail(f"manual gate: {rel} is missing -- it is one of the two documents whose "
                 "prose this gate exists to back")
            continue
        with open(path, encoding="utf-8") as fh:
            body = fh.read()
        if phrase not in body:
            fail(f"{rel}: no longer says {phrase!r}. Either the rule moved and this check went "
                 "blind, or the rule was dropped while the gate enforcing it stayed")
        if "money-gate" not in body:
            fail(f"{rel}: states the rule and never names the mechanism that enforces it. "
                 "M-30 is that a precondition beats a warning; a reader who cannot find the "
                 "precondition has only the warning")



@check
def check_copy_channel_snippet_matches_the_plugin():
    """The gate README hands a copy-channel reader must be the gate the plugin ships.

    The defect, measured 2026-08-20: `README.md` -> *The manual gate* carries a
    `~/.claude/settings.json` snippet for the install channels that carry no hook, and it
    registered **one** matcher (`Bash`) against the plugin's two. So a reader who followed
    the document to the letter could not refuse the `create_refund` tool the same README
    advertises seventeen lines earlier -- a weaker gate handed out by the document that
    exists because the channel has none.

    Compared by MATCHER SET, not by text: the snippet is formatted for reading and the
    manifest for a loader, and requiring them to be byte-equal would fail on whitespace and
    teach the next person to delete the check.
    """
    hooks_path = os.path.join(ROOT, GATE_HOOKS, "hooks.json")
    readme_path = os.path.join(ROOT, "README.md")
    if not (os.path.isfile(hooks_path) and os.path.isfile(readme_path)):
        fail("copy-channel snippet: hooks.json or README.md is missing")
        return
    try:
        with open(hooks_path, encoding="utf-8") as fh:
            hooks = json.load(fh)
    except json.JSONDecodeError as exc:
        fail(f"{GATE_HOOKS}/hooks.json: invalid JSON -- {exc}")
        return
    shipped = {
        (entry.get("matcher") or "")
        for entry in ((hooks.get("hooks") or {}).get("PreToolUse") or [])
    }

    with open(readme_path, encoding="utf-8") as fh:
        readme = fh.read()
    snippets = []
    for lineno, block in _fenced_blocks(readme):
        if "PreToolUse" not in block:
            continue
        try:
            snippets.append((lineno, json.loads(block)))
        except json.JSONDecodeError as exc:
            fail(f"README.md:{lineno} -- the copy-channel gate snippet is not valid JSON "
                 f"({exc}). A reader pastes this into their settings; it has to parse")
    if not snippets:
        fail("README.md: no fenced block declares a `PreToolUse` hook -- the copy install "
             "channels ship no gate and this snippet is the only thing that gives them one. "
             "An empty corpus makes this check pass everything")
        return
    for lineno, snippet in snippets:
        offered = {
            (entry.get("matcher") or "")
            for entry in ((snippet.get("hooks") or {}).get("PreToolUse") or [])
        }
        missing = shipped - offered
        if missing:
            fail(f"README.md:{lineno} -- the copy-channel snippet registers "
                 f"{sorted(offered)} and the plugin registers {sorted(shipped)}: a reader "
                 f"who follows this document cannot refuse {sorted(missing)}. The snippet "
                 "must be the same gate, not a weaker one")
        if _has_key(snippet, "if"):
            fail(f"README.md:{lineno} -- the copy-channel snippet declares `if`. The "
                 "reference calls that filter best-effort and FAILS OPEN, and the plugin "
                 "deliberately carries none")


# ---------------------------------------------- money fixtures (M-40, M-29)

# Manifesto M-29: *a test is stronger than an instruction.* M-40: evidence *proves no more
# than it observed*, and the property green dashboards routinely lose.
#
# The defect, measured 2026-08-19 (program row SD-04): this pack already KNEW the four
# invariants that cost real money -- the webhook is the payment and the redirect only
# proves a browser, one `event_id` on both sides or the revenue counts twice, a refund
# total that arrives cumulative, and delivery that is not ordered -- and shipped every one
# of them as prose that delegated enforcement to the reader. The giveaway was in the
# testing reference itself: *"For every guard, delete it and re-run."* An instruction to
# perform the mutation testing, in the document whose subject is proving a money defect
# would be caught.
#
# `fixtures/` is the answer, and this check is what stops it rotting. Two directions, both
# of which have been watched failing:
#
#   * a claimed invariant with no fixture -- the paragraph still states the rule and the
#     file that proved it is gone;
#   * a fixture nobody claims, or a document pointing at a fixture that does not exist --
#     the same M-07 defect B-79 fixed in the self-describing documents, one layer in. This
#     is the bounded widening B-82 asked for: the corpus is the documents a manifest NAMES,
#     and the tokens are the ones under `fixtures/`, so a skill reference naming the
#     reader's `src/lib/stripe.ts` is still none of its business.
#
# The mapping lives in each `fixtures/manifest.json` -- one home, shipped to the reader,
# machine-readable -- rather than in a table here, so there is nothing to drift.

FIXTURE_SKILLS = ("stripe-billing", "ad-tracking")
FIXTURE_TEST = "test/fixtures_test.js"

_ID_IN_PACK = re.compile(r"^\s+id: '([a-z0-9][a-z0-9-]*)',", re.M)
_RULES_BLOCK = re.compile(r"RULES = Object\.freeze\(\[(.*?)\]\)", re.S)
_FIXTURE_TOKEN = re.compile(r"fixtures/([A-Za-z0-9._-]+)")


def _squash(text):
    """Markdown wraps; a phrase does not stop being present because a newline fell in it."""
    return " ".join(text.split())


@check
def check_money_fixtures():
    """Every money invariant these skills state has a fixture, and every fixture a claim.

    Nine requirements, each one a way this could quietly stop being a test:

      1. both skills that state a money invariant SHIP a `fixtures/` directory. Named, so
         deleting one is a failure rather than a smaller check;
      2. the manifest parses, names itself correctly, and its assertion pack, reference
         handler and runbook all exist -- a manifest pointing at a missing pack is the
         B-79 defect with a different extension;
      3. the manifest and the assertion pack declare the SAME invariant ids. A row with no
         assertion is a claim; an assertion with no row is unfindable;
      4. every fixture a row names exists and is valid JSON. This is the "claimed invariant
         with no fixture" direction;
      5. every `*.json` beside the manifest is claimed by some row. This is the "fixture
         nobody claims" direction -- an orphan is a file that rots without going red;
      6. every claiming document still carries its phrase, names the invariant id, and
         names a path under `fixtures/`. A reworded paragraph fails here rather than
         drifting away from the fixture that proves it;
      7. every `fixtures/...` token in a claiming document resolves inside that skill;
      8. the runbook names every fixture and every invariant -- the completeness check the
         per-section pointers cannot give, because a pointer only proves one direction;
      9. `npm test` and CI both run the suite. A fixture file nothing runs rots green.

    Placeholder discipline is checked too: nothing key-shaped may appear in a payload whose
    whole purpose is to be copied into somebody else's repository.
    """
    for skill in FIXTURE_SKILLS:
        fdir = os.path.join(SKILL_ROOT, skill, "fixtures")
        rel = f"{skill}/fixtures"
        if not os.path.isdir(fdir):
            fail(f"money fixtures: {rel}/ is missing -- the invariants it proves are back to "
                 "prose, and manifesto.md:200 is that a test is stronger than an instruction")
            continue

        manifest_rel = f"{rel}/manifest.json"
        manifest_path = os.path.join(fdir, "manifest.json")
        if not os.path.isfile(manifest_path):
            fail(f"{manifest_rel} is missing -- it is the single home of the invariant-to-"
                 "fixture-to-document mapping, and without it neither direction is checkable")
            continue
        try:
            with open(manifest_path, encoding="utf-8") as fh:
                manifest = json.load(fh)
        except json.JSONDecodeError as exc:
            fail(f"{manifest_rel}: invalid JSON -- {exc}")
            continue

        if manifest.get("skill") != skill:
            fail(f"{manifest_rel}: declares skill {manifest.get('skill')!r}, but it sits in "
                 f"{skill!r}")

        pack_name = manifest.get("assertionPack")
        handler_name = manifest.get("referenceHandler")
        runbook_name = manifest.get("runbook")
        missing_part = False
        for label, name in (("assertionPack", pack_name),
                            ("referenceHandler", handler_name),
                            ("runbook", runbook_name)):
            if not name or not os.path.isfile(os.path.join(fdir, name)):
                fail(f"{manifest_rel}: {label} names {name!r}, which is not in {rel}/")
                missing_part = True
        if missing_part:
            continue

        with open(os.path.join(fdir, pack_name), encoding="utf-8") as fh:
            pack_src = fh.read()
        with open(os.path.join(fdir, handler_name), encoding="utf-8") as fh:
            handler_src = fh.read()
        with open(os.path.join(fdir, runbook_name), encoding="utf-8") as fh:
            runbook_src = fh.read()

        rows = manifest.get("invariants") or []
        if not rows:
            fail(f"{manifest_rel}: no invariants -- an empty manifest passes every other rule "
                 "in this check, which is exactly why this one is here")
            continue

        declared = [row.get("id") for row in rows]
        in_pack = _ID_IN_PACK.findall(pack_src)
        for only_manifest in sorted(set(declared) - set(in_pack)):
            fail(f"{manifest_rel}: claims invariant {only_manifest!r}, and "
                 f"{rel}/{pack_name} asserts nothing by that name -- a claim, not a test")
        for only_pack in sorted(set(in_pack) - set(declared)):
            fail(f"{rel}/{pack_name}: asserts {only_pack!r}, which {manifest_rel} does not "
                 "claim -- an assertion no document points at is one a reader never finds")

        rules_block = _RULES_BLOCK.search(handler_src)
        rules = set(re.findall(r"'([a-z0-9][a-z0-9-]*)'", rules_block.group(1))) if rules_block else set()
        if not rules:
            fail(f"{rel}/{handler_name}: no RULES list -- the mutants the pack deletes are "
                 "what makes each assertion evidence")

        on_disk = {f for f in os.listdir(fdir) if f.endswith(".json") and f != "manifest.json"}
        claimed = set()

        for row in rows:
            rid = row.get("id")
            isolates = row.get("isolates")
            if isolates is not None and rules and isolates not in rules:
                fail(f"{manifest_rel}: {rid} says it isolates {isolates!r}, which is not a rule "
                     f"{handler_name} can remove")
            row_fixtures = row.get("fixtures") or []
            if not row_fixtures:
                fail(f"{manifest_rel}: {rid} names no fixture -- the invariant is claimed and "
                     "nothing observes it (M-40: evidence proves no more than it observed)")
            for name in row_fixtures:
                path = os.path.join(fdir, name)
                if not os.path.isfile(path):
                    fail(f"{manifest_rel}: {rid} claims {rel}/{name}, which does not exist")
                    continue
                claimed.add(name)
                try:
                    with open(path, encoding="utf-8") as fh:
                        json.load(fh)
                except json.JSONDecodeError as exc:
                    fail(f"{rel}/{name}: invalid JSON -- {exc}. A reader is told to feed this "
                         "to their handler")

            for claim in row.get("claimedBy") or []:
                doc = claim.get("document")
                phrase = claim.get("phrase") or ""
                doc_path = os.path.join(SKILL_ROOT, skill, doc or "")
                if not doc or not os.path.isfile(doc_path):
                    fail(f"{manifest_rel}: {rid} says {doc!r} claims it, and {skill} has no "
                         "such document")
                    continue
                with open(doc_path, encoding="utf-8") as fh:
                    body = fh.read()
                flat = _squash(body)
                if _squash(phrase) not in flat:
                    fail(f"{skill}/{doc}: no longer says {phrase!r}, which {manifest_rel} "
                         f"records as the claim {rid} proves. Either the rule moved and this "
                         "check went blind, or it was dropped while its fixture stayed")
                if rid not in body:
                    fail(f"{skill}/{doc}: states the rule and never names {rid} -- M-29 is "
                         "that a test beats an instruction, and a reader who cannot find the "
                         "test has only the instruction")
                if not _FIXTURE_TOKEN.search(body):
                    fail(f"{skill}/{doc}: names no path under fixtures/ -- the pointer from "
                         "the claim to the thing that proves it is missing")

        for orphan in sorted(on_disk - claimed):
            fail(f"{rel}/{orphan} is claimed by no invariant in {manifest_rel} -- a fixture "
                 "nothing points at is a file that rots without ever going red")

        # The runbook is the completeness check: a per-section pointer proves one direction,
        # and only a list of every fixture and every invariant proves the other.
        for name in sorted(on_disk):
            if name not in runbook_src:
                fail(f"{rel}/{runbook_name}: never names {name} -- the map a reader copies "
                     "the directory with is incomplete")
        for rid in declared:
            if rid and rid not in runbook_src:
                fail(f"{rel}/{runbook_name}: never names the invariant {rid!r}")

        # The entry point has to be findable from the skill's own markdown.
        reachable = False
        for dirpath, _dirnames, filenames in os.walk(os.path.join(SKILL_ROOT, skill)):
            if os.path.basename(dirpath) == "fixtures":
                continue
            for name in filenames:
                if not name.endswith(".md"):
                    continue
                with open(os.path.join(dirpath, name), encoding="utf-8") as fh:
                    if pack_name in fh.read():
                        reachable = True
        if not reachable:
            fail(f"{skill}: no SKILL.md or reference names {pack_name} -- a suite the reader "
                 "cannot find is prose again")

        # Every `fixtures/...` token in the skill's markdown must resolve. The reverse
        # pointer, and the reason a renamed fixture cannot leave a dead address behind.
        for dirpath, _dirnames, filenames in os.walk(os.path.join(SKILL_ROOT, skill)):
            for name in sorted(filenames):
                if not name.endswith(".md"):
                    continue
                doc_rel = os.path.relpath(os.path.join(dirpath, name), os.path.join(SKILL_ROOT, skill))
                with open(os.path.join(dirpath, name), encoding="utf-8") as fh:
                    text = fh.read()
                for lineno, line in enumerate(text.splitlines(), 1):
                    for token in set(_FIXTURE_TOKEN.findall(line)):
                        if not os.path.exists(os.path.join(fdir, token)):
                            fail(f"{skill}/{doc_rel}:{lineno} points at fixtures/{token}, "
                                 "which is not there (B-79's defect, one layer in)")

        # A payload whose purpose is to be copied must carry nothing key-shaped.
        for name in sorted(on_disk):
            with open(os.path.join(fdir, name), encoding="utf-8") as fh:
                blob = fh.read()
            for shape in (r"\b(sk|rk|pk)_(live|test)_[A-Za-z0-9]{8,}", r"\bwhsec_[A-Za-z0-9]{8,}",
                          r"BEGIN [A-Z ]*PRIVATE KEY", r"\bEAA[A-Za-z0-9]{20,}"):
                if re.search(shape, blob):
                    fail(f"{rel}/{name}: carries something key-shaped ({shape}). These files "
                         "are copied into other people's repositories -- placeholders only")

    if pkg and "fixtures_test.js" not in (pkg.get("scripts") or {}).get("test", ""):
        fail(f"package.json: `npm test` does not run {FIXTURE_TEST} -- the fixtures would "
             "prove nothing about this repository's own gate")
    ci_path = os.path.join(ROOT, ".github", "workflows", "validate.yml")
    if os.path.isfile(ci_path):
        with open(ci_path, encoding="utf-8") as fh:
            if "fixtures_test.js" not in fh.read():
                fail(f"validate.yml: CI never runs {FIXTURE_TEST}")
    if not os.path.isfile(os.path.join(ROOT, FIXTURE_TEST)):
        fail(f"{FIXTURE_TEST} is missing -- it is what runs both assertion packs in both "
             "modes, and a pack nobody runs is a pack nobody has watched fail")



# ------------------------------------------------------------- the body budget
#
# The Agent Skills hard budget and the house working limit, in the numbers
# `make-skill`'s `audit_skill.py` uses: 5000 tokens / 500 lines is the spec, 4750 tokens is
# the house limit that leaves room for the next section, and the estimator is
# `len(body) / 3.9`. Reimplemented here rather than shelled out, because `audit_skill.py`
# lives in another repository and this gate must run from a bare clone -- and because the
# whole point is that THIS repo's gate measures it, not that another one might.
BODY_MAX_TOKENS = 5000
BODY_MAX_LINES = 500
BODY_TARGET_TOKENS = 4750
CHARS_PER_TOKEN = 3.9


def _body_of(path):
    """A SKILL.md with its front matter removed -- what the host loads at level 2."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = re.match(r"^---\n.*?\n---\n", text, re.S)
    return text[m.end():] if m else text


@check
def check_body_budget():
    """Every SKILL.md body is inside the budget AND inside the house working limit.

    The defect, measured 2026-08-20: this repository's gate checked front matter and
    nothing else, so `crypto-payments/SKILL.md` sat at ~4894 tokens -- past the 4750
    working limit, `1 GAP` under `audit_skill.py --house` -- and was found by running
    ANOTHER repository's auditor. A budget enforced only by a tool that ships elsewhere is
    enforced by whoever remembers to run it, which is board B-95's whole history.

    Both thresholds, and they say different things. Over 5000 tokens or 500 lines the host
    truncates and nothing errors. Over 4750 the file still loads and the NEXT section
    breaks it -- so the working limit is where a split is still cheap. The house answer at
    that point is a split, never a trim: `crypto-payments` shed
    `references/callback-route-hardening.md` and `references/testing-and-local-dev.md`
    rather than losing a paragraph.

    `stripe-billing` passes at ~4747 of 4750, which is three tokens of headroom and is
    stated here rather than discovered: this check is deliberately not set below any value
    the tree already holds, and the measured numbers print on every failure so the next
    person sees the distance rather than a verdict.
    """
    for name in skill_dirs:
        path = os.path.join(SKILL_ROOT, name, "SKILL.md")
        if not os.path.isfile(path):
            continue  # check_skill_front_matter owns the missing case
        body = _body_of(path)
        lines = body.count("\n") + 1
        est = int(len(body) / CHARS_PER_TOKEN)
        if lines >= BODY_MAX_LINES:
            fail(f"{name}/SKILL.md: body is {lines} lines, the budget is < {BODY_MAX_LINES} "
                 "-- move detail into references/")
        if est >= BODY_MAX_TOKENS:
            fail(f"{name}/SKILL.md: body is ~{est} tokens ({len(body)} chars / "
                 f"{CHARS_PER_TOKEN}), the budget is < {BODY_MAX_TOKENS}. Over this the host "
                 "truncates silently, which is worse than an error")
        elif est >= BODY_TARGET_TOKENS:
            fail(f"{name}/SKILL.md: body is ~{est} tokens, inside the {BODY_MAX_TOKENS} "
                 f"budget and past the {BODY_TARGET_TOKENS} house working limit "
                 f"({BODY_TARGET_TOKENS - est} of headroom). The next section breaches it, "
                 "and the answer then is a split into references/, not a trim")


# ------------------------------------------- the numbers documents restate (B-84, B-93)
#
# A counted number in a document is a claim about the tree, and a literal nobody
# recomputes is the claim rotting quietly. Both defects were measured on 2026-08-20:
# `SECURITY.md` carried four counts that were correct that day and checked by nothing, and
# `docs/evals/stripe-billing.md` carried four that were three-quarters wrong.
#
# Table-driven, so a fifth number is a row rather than a second shape. Each row's pattern
# must match EXACTLY ONCE: a sentence that moved takes the check blind with it, and that is
# a failure rather than a pass.

def _payload_files():
    """Every file under `plugins/` -- the shipped skill payload.

    `os.walk`, not `git ls-files`, so the gate runs from an export with no `.git`. Measured
    equal on 2026-08-20: both return 52. `SECURITY.md` -> *Verifying for yourself* hands the
    reader the git command, which is the cross-check.
    """
    out = []
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, "plugins")):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", "node_modules")]
        for fn in filenames:
            if fn.endswith(".pyc") or fn == ".DS_Store":
                continue
            out.append(os.path.relpath(os.path.join(dirpath, fn), ROOT).replace(os.sep, "/"))
    return out


@check
def check_security_counts_are_computed():
    """Every counted number in SECURITY.md is recomputed here, not restated there.

    Board **B-93**, open since 2026-08-19: *"`SECURITY.md` states counted numbers and
    nothing recomputes them."* All four were correct on the day they were written, which is
    the point -- the same four were correct at v0.6.0 too, and then a release moved three of
    them. This change moved all four again (the `crypto-payments` split added two files), so
    the row closes with the numbers under a check rather than under a habit.
    """
    path = os.path.join(ROOT, "SECURITY.md")
    if not os.path.isfile(path):
        fail("SECURITY.md is missing")
        return
    with open(path, encoding="utf-8") as fh:
        text = fh.read()

    payload = _payload_files()
    markdown = [f for f in payload if f.endswith(".md")]
    tarball = _tarball_paths()
    references = [f for f in payload if "/references/" in f and f.endswith(".md")]

    rows = (
        (r"`git ls-files plugins` returns \*\*(\d+) files", len(payload),
         "files under plugins/"),
        (r"returns \*\*\d+ files: (\d+) markdown", len(markdown), "markdown files"),
        (r"# The shipped payload: (\d+) files\.", len(payload), "files under plugins/"),
        (r"# (\d+) lines: the plugin manifest", len(payload) - len(markdown),
         "non-markdown files under plugins/"),
        (r"\| `references/` files, loaded on demand \| (\d+) \|", len(references),
         "reference documents"),
        (r"(\d+) files, listed by\s+`npm pack --dry-run`", len(tarball),
         "files in the published tarball"),
        (r"# What npm publishes, and nothing else: (\d+) files\.", len(tarball),
         "files in the published tarball"),
    )
    for pattern, computed, what in rows:
        found = re.findall(pattern, text)
        if len(found) != 1:
            fail(f"SECURITY.md: the sentence matching {pattern!r} appears {len(found)} "
                 "times, expected exactly once -- the number moved or the sentence did, and "
                 "either way this check went blind (B-93)")
            continue
        if int(found[0]) != computed:
            fail(f"SECURITY.md states {found[0]} {what}; counting them here gives "
                 f"{computed} (B-93)")


@check
def check_evals_numbers_are_computed():
    """`docs/evals/stripe-billing.md` quotes this skill's body budget; recompute it.

    Measured 2026-08-20: the record said `4994` tokens, `441` lines and `0 GAP, 13 PASS`
    against a tree measuring 4747, 409 and `0 GAP, 14 PASS`. Three of four restated numbers
    were wrong, in the one document whose subject is measurement.

    The `GAP/PASS` pair is NOT checked here and says so in the document instead: it is
    `audit_skill.py`'s counter, that script lives in another repository, and a number this
    gate cannot recompute is carried as a dated reading rather than as a claim.
    """
    rel = "docs/evals/stripe-billing.md"
    path = os.path.join(ROOT, rel)
    skill = os.path.join(SKILL_ROOT, "stripe-billing", "SKILL.md")
    if not (os.path.isfile(path) and os.path.isfile(skill)):
        fail(f"{rel} or stripe-billing/SKILL.md is missing")
        return
    body = _body_of(skill)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    rows = (
        (r"~(\d+) tokens by the house heuristic", int(len(body) / CHARS_PER_TOKEN),
         "estimated body tokens"),
        (r"(\d+) lines of body", body.count("\n") + 1, "body lines"),
    )
    for pattern, computed, what in rows:
        found = re.findall(pattern, text)
        if len(found) != 1:
            fail(f"{rel}: the sentence matching {pattern!r} appears {len(found)} times, "
                 "expected exactly once")
            continue
        if int(found[0]) != computed:
            fail(f"{rel} states {found[0]} {what}; measuring stripe-billing/SKILL.md here "
                 f"gives {computed}")


# ----------------------------------------------- the ledger describes what ships


@check
def check_ledger_names_the_shipped_version():
    """The ledger's shipped block names the version that actually shipped.

    The defect, measured 2026-08-20: `docs/evidence/verification.md:18` headed its shipped
    block `## Shipped state — v0.6.0` while `v0.7.0` was tagged and on npm. The file's own
    opening paragraph says a row is verified once watched passing on the SHIPPED artifact,
    so a heading naming a superseded version makes every row below it a claim about
    something else. It had happened before: the same heading said `v0.5.0` while npm served
    `0.5.2`, and the block that records that is three lines under the one that repeated it.

    Two comparands, because one of them is not always available. `git describe --tags` is
    the authority and is what the release actually cut; `package.json` -> `version` is what
    this tree claims and is readable from an export with no git. Where git cannot look --
    a `/tmp` copy of a submodule checkout, for instance -- the version comparison still
    fires, so a plant is still refused.
    """
    rel = "docs/evidence/verification.md"
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        fail(f"{rel} is missing -- it is the ledger, and its absence read as zero exposure "
             "once already")
        return
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    headings = re.findall(r"^## Shipped state — v(\S+)\s*$", text, re.M)
    if len(headings) != 1:
        fail(f"{rel}: found {len(headings)} `## Shipped state — vX.Y.Z` headings, expected "
             "exactly one. One block describes the shipped artifact; a second is two "
             "answers to the same question")
        return
    named = headings[0]
    if version and named != version:
        fail(f"{rel}: the shipped block is headed v{named} and this tree declares "
             f"v{version}. The rows below it claim to be measured against the shipped "
             "artifact, so the heading has to name it -- move the block and re-measure, or "
             "the ledger describes something nobody ships")
    proc = None
    try:
        proc = subprocess.run(["git", "-C", ROOT, "describe", "--tags", "--abbrev=0"],
                              capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        _disclose_routing(f"shipped version — could not ask git ({exc})")
    if proc is None or proc.returncode != 0:
        if proc is not None:
            _disclose_routing("shipped version — git cannot look here, so the heading was "
                              "compared against package.json only")
        return
    tag = proc.stdout.strip().lstrip("v")
    if tag and named != tag:
        fail(f"{rel}: the shipped block is headed v{named} and `git describe --tags` prints "
             f"v{tag} -- the ledger describes an artifact nobody ships")


@check
def check_ledger_quotes_the_validator_verdict():
    """The verdict this validator prints is the one the shipped block quotes.

    REQ-001 quotes the line as its evidence. On 2026-08-20 it read
    `(12 checks, 6 skill(s), v0.6.0)` while the tree printed `16 checks … v0.7.0`, and the
    board row that noticed said `13` -- itself two releases stale. Three numbers for one
    measurement, none of them connected to the thing measured.

    **Only the shipped block.** The unreleased blocks below it quote 13, 14, 15 and 16
    checks, and each was true at the commit its row was measured at. Rewriting a dated
    reading to keep a checker quiet is the failure this file exists to prevent.
    """
    rel = "docs/evidence/verification.md"
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        return  # the check above owns the missing case
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r"^## Shipped state — .*?(?=^## )", text, re.S | re.M)
    if not m:
        fail(f"{rel}: no `## Shipped state` section to read REQ-001 out of")
        return
    quoted = re.findall(r"`(OK: sheleg-dev structurally valid \([^`]*\))`", m.group(0))
    if len(quoted) != 1:
        fail(f"{rel}: the shipped block quotes the validator verdict {len(quoted)} times, "
             "expected exactly once (REQ-001). An empty corpus makes this check pass "
             "everything")
        return
    if quoted[0] != verdict_line():
        fail(f"{rel}: REQ-001 quotes {quoted[0]!r}; this run prints {verdict_line()!r}. "
             "The row's evidence is the line, so the line has to be the one that comes out")


# ------------------------------------------------- coordination and the gate line


@check
def check_agent_sync_config_paths_resolve():
    """Every path in `.claude/agent-sync.json` resolves.

    Measured 2026-08-20: `mergeLog.file` pointed at `docs/MERGES.md`, which did not exist —
    a configured destination nothing could write to, in the file whose whole job is keeping
    two agents from overwriting each other. And `guardedFiles` listed
    `docs/evidence/verification.md` while omitting `docs/evidence/backlog.md`, so the ledger
    was claimed and the board it cross-references was not.

    Globs are resolved as globs: `plugins/*/.claude-plugin/plugin.json` is a pattern on
    purpose, and a pattern that matches nothing is as dead as a missing file.
    """
    rel = ".claude/agent-sync.json"
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        fail(f"{rel} is missing -- coordination is on in this repository "
             "(docs/AGENT_SYNC.md), and the config is what turns it on")
        return
    try:
        with open(path, encoding="utf-8") as fh:
            cfg = json.load(fh)
    except json.JSONDecodeError as exc:
        fail(f"{rel}: invalid JSON -- {exc}")
        return

    seen = []

    def walk(node, where):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{where}.{k}" if where else k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{where}[{i}]")
        elif isinstance(node, str) and _PATH_TOKEN.match(node):
            seen.append((where, node))

    walk(cfg, "")
    if not seen:
        fail(f"{rel}: names no path at all -- an empty corpus makes this check pass "
             "everything, and `guardedFiles` is the reason the file exists")
        return
    for where, tok in seen:
        if "*" in tok:
            if not glob.glob(os.path.join(ROOT, tok)):
                fail(f"{rel}: {where} = {tok!r} matches nothing here -- a guarded-file "
                     "pattern that matches nothing guards nothing")
        elif not os.path.exists(os.path.join(ROOT, tok)):
            fail(f"{rel}: {where} = {tok!r} does not exist. A coordination config pointing "
                 "at a file nobody created is a lease over nothing")

    guarded = set(cfg.get("guardedFiles") or [])
    for required in ("docs/evidence/verification.md", "docs/evidence/backlog.md"):
        if required not in guarded:
            fail(f"{rel}: guardedFiles omits {required!r}. The two evidence documents are "
                 "edited by every run and cross-reference each other by row id; claiming "
                 "one and not the other is how two agents renumber the same board")


@check
def check_gate_commands_agree():
    """`npm test` runs three suites, and the documents that name the gate name all three.

    Measured 2026-08-20: `CONTRIBUTING.md:74` described the gate as two suites — the
    fixture suite, 16 checks, was missing — and `.github/PULL_REQUEST_TEMPLATE.md:10` asked
    a contributor for the output of `python3 test/validate.py` alone, one third of the gate.
    A contributor who supplied exactly what was asked for supplied evidence for a third of
    it, and the reviewer had no way to notice.

    Derived from `package.json` -> `scripts.test`, so adding a fourth suite fails these two
    documents rather than passing them.
    """
    script = ((pkg or {}).get("scripts") or {}).get("test", "")
    suites = re.findall(r"(test/[A-Za-z0-9_.-]+\.(?:py|js|mjs))", script)
    if not suites:
        fail("package.json: `scripts.test` names no suite -- an empty corpus makes this "
             "check pass everything")
        return
    for rel, needle in (("CONTRIBUTING.md", "npm test"),
                        (".github/PULL_REQUEST_TEMPLATE.md", "npm test")):
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            fail(f"{rel} is missing")
            continue
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        blocks = [b for _ln, b in _fenced_blocks(text) if needle in b]
        if not blocks:
            fail(f"{rel}: no fenced block runs `{needle}` -- it is the gate, and a document "
                 "that describes the gate without naming it sends a contributor somewhere "
                 "else")
            continue
        joined = "\n".join(blocks)
        for suite in suites:
            if suite not in joined:
                fail(f"{rel}: the `{needle}` block does not name {suite}, which "
                     f"`package.json` -> `scripts.test` runs. The gate is "
                     f"{len(suites)} suites; a document naming fewer asks for evidence "
                     "about part of it")


@check
def check_install_channels_name_the_gate():
    """Both destructive install channels say the gate does not travel with them.

    `bin/sheleg-dev.js` prints the notice; `install.sh` printed nothing, and it is the more
    dangerous of the two — `rm -rf "$dest"` per skill, then `cp -R`. Board **B-90** is that
    a printed reminder is a warning and M-30 calls a warning weaker than a precondition;
    that argument is about whether printing is ENOUGH, and it does not make printing in one
    channel and not the other coherent. A reader who installs by shell gets the six skills
    and no hint that the refusals README advertises are not there.
    """
    for rel in ("bin/sheleg-dev.js", "install.sh"):
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            fail(f"{rel} is missing -- it is one of the two install channels")
            continue
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        if "manual gate" not in text:
            fail(f"{rel}: never says `manual gate`. This channel copies skills and carries "
                 "no hook, so the one honest thing it can do is say so -- "
                 "`plugins/sheleg-dev/hooks/` travels with the PLUGIN")
        if "README.md" not in text:
            fail(f"{rel}: names no document a reader can register the gate from. A notice "
                 "with no next step is how an operator learns to ignore notices")


@check
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



# ---------------------------------------------------------------- verdict

for _fn in CHECKS:
    _fn()

if FAILURES:
    print(f"FAIL: {len(FAILURES)} problem(s)", file=sys.stderr)
    for f in FAILURES:
        print(f"  - {f}", file=sys.stderr)
    sys.exit(1)

print(verdict_line())
