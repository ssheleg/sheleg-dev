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
  * CI runs this file. A validator that CI stopped calling is decoration.

Exit code 0 = green. Anything else = a fail with a reason on stderr.
"""

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


check_contributing_routes_to_files_that_exist()


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
)

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

    used = set()
    for doc in SELF_DESCRIBING_DOCS:
        path = os.path.join(ROOT, doc)
        if not os.path.isfile(path):
            fail(f"{doc} is missing -- it is one of the documents an outside reader meets "
                 "the pack through")
            continue
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


check_self_describing_docs_resolve()


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
# `references/testing-and-local-dev.md:210` ("something asserts they agree") while
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


check_credential_boundary()


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


check_manual_gate()


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

checks = 9 + len(skill_dirs)
print(f"OK: sheleg-dev structurally valid ({checks} checks, {len(skill_dirs)} skill(s), v{version})")
