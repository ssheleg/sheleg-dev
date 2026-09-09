#!/usr/bin/env python3
"""COPIED from `seo-aeo-audit/test/negatives.py`, 2026-08-24, which was copied from
`task-pipeline`'s. Four things differ from the original: the step floor (43, not 412), the property-check floor (0 -- this repository
has none yet), the lock name, and the success marker is matched case-insensitively --
this repository prints `OK:` like the original, but the insensitivity is kept so the
three copies stay one file rather than three dialects. Everything else is the same file, because
two implementations of one runner is the defect this family keeps finding in its own
history.

It exists because of the other half of that lesson. This repository had 42 negative self-tests in its
workflow and no way to run any of them locally, which is the ALL-26 shape: a plant
that cannot RUN dies before its landing assert, and the failure reads as a broken
guard. The runner decides that centrally -- `differs_from_repo` reports BROKEN when a
planted defect changed nothing -- so no step needed rewriting.

The original docstring follows.

Run the CI negative self-tests locally. Exit 0 = every guard provably fails.

`test/validate.py` proves the repo is well-formed. This proves the *validator* is
not a decoration: each check is fed a planted defect and must reject it. A green
result from a check nobody has watched fail is worth nothing — the same law the
skill's own `references/audit.md` applies to every gate in a run.

The tests live in `.github/workflows/validate.yml` and are read from there, never
duplicated here: a second copy of a corruption is a second thing to drift.

    python3 test/negatives.py            # run them all
    python3 test/negatives.py --list     # just show what would run
    python3 test/negatives.py -k ladder  # only tests whose name matches

Zero dependencies, same as the validator.
"""
# shared-mechanism: negatives.py — 3 copies in this family, kept as one file
#   rather than 3 dialects. The umbrella's gate computes which module-level
#   constants actually differ between the copies and refuses a difference this line
#   does not name: on 2026-08-24 an undeclared success-vocabulary constant made a
#   ported runner report twenty healthy guards as broken, and nothing could see it.
# diverges: MIN_EXPECTED, MIN_PROPS, SUCCESS_MARKERS
import concurrent.futures
import tempfile
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW = os.path.join(ROOT, ".github/workflows/validate.yml")
MARKER = "Negative self-test"
PROP_MARKER = "Property check"
MIN_PROPS = 0
# A format change that silently matched nothing would report "0 failures" and look
# like success. Refuse to be that quiet.
#
# Raise this when guards are added. It sat at 20 while the workflow carried 34,
# which is the floor doing half its job: it would have caught a total collapse and
# not the loss of a third of the suite. Set it to the real count, and treat a
# mismatch as a finding rather than as noise to be lowered away.
MIN_EXPECTED = 47

# The success vocabulary, DECLARED rather than assumed, and this constant is the
# whole lesson of porting this runner three times in one afternoon. Copying it
# verbatim was right -- one implementation of one idea -- and each copy then met a
# repository that says "this plant behaved" in different words:
#
#   task-pipeline   `OK:`
#   seo-aeo-audit   `ok:`            (same word, other case -- 2 steps misread)
#   sheleg-dev      `OK:` AND `rejected, as it must be`   (20 steps misread)
#
# Twenty healthy guards reported as guards that do not fire, on the first local run,
# because a shared mechanism carried an unstated assumption across a repository
# boundary. That is ALL-44's shape -- nine repositories, overlapping doctrine, aligned
# by whoever happens to look -- caught here by the mechanism itself the moment it
# crossed. The remedy is not a fourth hardcoded marker: it is that the convention is
# a declaration a reader can see and a port can adjust.
SUCCESS_MARKERS = ("OK:", "SKIP:", "REJECTED, AS IT MUST BE")


# ---- FIX-DV-20.01: explicit stages, so an environment failure is never read as a
# guard bypass. A negative self-test passes through four stages IN ORDER:
#
#     fixture_setup -> mutation_verified -> validator_ran -> assertion
#
# A failure BEFORE the validator ran (a failed `cp -R .`, a full disk / ENOSPC, a
# timeout) is a TEST_ERROR: the environment could not stage the test, so NOTHING is
# known about the guard. A GAP -- the validator accepting a planted defect, the only
# real guard-bypass finding -- is reported ONLY when the validator actually RAN
# against a verified-different mutant and still passed. The runner used to print 40
# such TEST_ERRORs as "the guard does not actually fire" on a full disk; this is why.
STAGES = ("fixture_setup", "mutation_verified", "validator_ran", "assertion")

# Substrings that mark an OS resource failure rather than a guard verdict, matched
# case-insensitively against the step's combined output.
ENV_ERROR_SIGNS = (
    "no space left on device",
    "cannot allocate memory",
    "too many open files",
    "resource temporarily unavailable",
    "input/output error",
    "disk quota exceeded",
)


def has_env_error(text):
    low = (text or "").lower()
    return any(sign in low for sign in ENV_ERROR_SIGNS)


def classify_stages(*, timed_out, env_error, skipped, setup_ok, mutant_differs,
                    guard_fired):
    """Map the observed stage signals to one status. The order is the whole point:
    a resource failure or a failed setup wins over any read of the validator, so a
    full disk can never be classified as a guard that did not fire.

        TEST_ERROR  the environment could not stage or run the test (failed cp,
                    ENOSPC, timeout) -- NEVER a guard-bypass finding.
        SKIP        the probe declared it could not run and changed nothing.
        BROKEN      the mutant was identical to the repo: nothing was planted.
        GAP         the validator RAN against a real mutant and accepted it -- the
                    only genuine "the guard does not fire" result.
        PASS        the validator ran and rejected the mutant.
    """
    if timed_out or env_error:
        return "TEST_ERROR"
    if not setup_ok:
        return "TEST_ERROR"             # fixture_setup failed before anything ran
    if skipped:
        return "SKIP"
    if not mutant_differs:
        return "BROKEN"                 # mutation_verified failed: nothing planted
    return "PASS" if guard_fired else "GAP"   # validator_ran -> assertion


def preflight_disk(min_free_mb=200):
    """Refuse to run on a filesystem too full to stage a repo copy. Returns a
    reason string when space is short, else None. A full disk otherwise
    manufactures dozens of false guard-bypass findings (FIX-DV-20.01)."""
    try:
        free = shutil.disk_usage(tempfile.gettempdir()).free
    except OSError as e:
        return f"could not stat the scratch filesystem {tempfile.gettempdir()!r}: {e}"
    if free < min_free_mb * 1024 * 1024:
        return (f"only {free // (1024 * 1024)} MB free on {tempfile.gettempdir()} -- "
                f"need {min_free_mb} MB to stage the repo copies; refusing to run "
                f"rather than report guards as broken")
    return None


def parse_steps(path):
    """(name, script) per `- name: … / run: |` step. Deliberately not PyYAML —
    the validator ships dependency-free and so does this."""
    steps, name, body, indent = [], None, None, None
    for line in open(path, encoding="utf-8").read().splitlines():
        m = re.match(r"^\s*- name:\s*(.+?)\s*$", line)
        if m:
            if name is not None and body is not None:
                steps.append((name, "\n".join(body)))
            name, body, indent = m.group(1), None, None
            continue
        if name is not None and body is None and re.match(r"^\s*run:\s*\|\s*$", line):
            body = []
            continue
        if body is not None:
            if line.strip() == "":
                body.append("")
                continue
            cur = len(line) - len(line.lstrip())
            if indent is None:
                indent = cur
            if cur < indent:                      # dedent ends the block
                steps.append((name, "\n".join(body)))
                name, body, indent = None, None, None
                continue
            body.append(line[indent:])
    if name is not None and body is not None:
        steps.append((name, "\n".join(body)))
    return steps


def copy_dir_of(script):
    """The scratch copy a step makes, so we can tell a real defect from a no-op."""
    m = re.search(r"cp -R \. (\S+)", script)
    return m.group(1) if m else None


def differs_from_repo(path):
    r = subprocess.run(
        ["diff", "-rq", "--exclude=.git", "--exclude=node_modules", "--exclude=graphify-out", path, ROOT],
        capture_output=True, text=True,
    )
    return bool(r.stdout.strip()) or bool(r.stderr.strip())


def sweep(paths):
    for p in paths:
        if p and p.startswith("/tmp/"):
            shutil.rmtree(p, ignore_errors=True)


def main(argv):
    args = argv[1:]
    only = None
    if "-k" in args:
        only = args[args.index("-k") + 1].lower()
    listing = "--list" in args

    if not os.path.isfile(WORKFLOW):
        print(f"FAIL: no workflow at {WORKFLOW}")
        return 2

    _STEPS = parse_steps(WORKFLOW)          # parsed once; both filters read the same list

    # Every step copies the repo to a FIXED `/tmp` name. In CI that is correct — one
    # runner per job, no neighbours. On a developer machine two suite runs share those
    # paths and overwrite each other mid-copy: four runs over an unchanged tree once
    # returned four different answers (1, 2, 3 and 4 guards "not firing"), and the cause
    # was never the tree. Board row B-075.
    #
    # The first fix rewrote every `/tmp/...` in the script text to a per-run name, and it
    # broke two plants whose PAYLOAD IS THE WORKFLOW TEXT — they search the copied
    # workflow for a literal path in order to duplicate it. A mechanical rewrite cannot
    # tell a path being used from a path being discussed, which is the umbrella's standing
    # instruction #7, met for the second time in two days.
    #
    # So the paths stay exactly as CI has them, and the runs are serialised instead. An
    # exclusive lock for the duration of the suite: the second run waits rather than
    # corrupting the first, and says so instead of producing a number nobody can trust.
    _LOCK_PATH = os.path.join(tempfile.gettempdir(), "sd-negatives.lock")
    _lock = open(_LOCK_PATH, "w")
    try:
        import fcntl
        try:
            fcntl.flock(_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            print("another run of this suite holds the scratch paths — waiting for it.\n"
                  "  (every step copies the repo to a fixed /tmp name, so two runs at once\n"
                  "   overwrite each other and both report about a tree neither one saw)")
            fcntl.flock(_lock, fcntl.LOCK_EX)
    except ImportError:
        # No flock (Windows): say what is not guaranteed rather than implying it is.
        print("note: no file locking available here — do not run two suites at once")

    tests = [(n, s) for n, s in _STEPS if MARKER in n]
    if len(tests) < MIN_EXPECTED:
        print(f"FAIL: found only {len(tests)} negative self-tests in the workflow "
              f"(expected at least {MIN_EXPECTED}). The parser or the workflow "
              f"format changed — a run that quietly tests nothing is the failure "
              f"this check exists to prevent.")
        return 2
    if only:
        tests = [(n, s) for n, s in tests if only in n.lower()]
        # The bail moved below the property filter: `-k property` matched no negative
        # self-test and errored out while the checks it named were sitting right there,
        # unrun. A selector that refuses the thing it selected is worse than no selector.
        if not tests and not [1 for _n, _ in _STEPS if PROP_MARKER in _n and only in _n.lower()]:
            print(f"FAIL: no negative self-test or property check matches {only!r}")
            return 2

    label = lambda n: n.replace(MARKER, "").strip().strip("()")
    _plabel = lambda n: n.replace(PROP_MARKER, "").strip().strip("()")
    if listing:
        for n, _ in tests:
            print(" ", label(n))
        # A listing that omits a whole category of test teaches that the category does
        # not exist. They run; they are listed.
        for n, _ in [(n, s) for n, s in _STEPS if PROP_MARKER in n
                     and (not only or only.lower() in n.lower())]:
            print("  [property]", _plabel(n))
        print(f"\n{len(tests)} negative self-tests")
        return 0

    # A leftover copy from an interrupted run would make the next one lie.
    sweep([copy_dir_of(s) for _, s in tests])

    # Every test does `cp -R .` — from the CURRENT WORKING DIRECTORY. Run with cwd=ROOT
    # that is the live tree, so editing a file mid-run hands some tests a half-written
    # copy and the suite reports on a state the repo was never in. It happened twice in
    # one session, and board row B-023 predicted both.
    #
    # So the suite copies ROOT once into a snapshot and runs every test with cwd there.
    # Editing while it runs is now harmless.
    # FIX-DV-20.01 resource preflight: a filesystem too full to stage the repo copies
    # would otherwise turn every step into a false guard-bypass finding. Refuse first.
    _short = preflight_disk()
    if _short:
        print(f"TEST_ERROR: {_short}")
        return 3
    _snap = tempfile.mkdtemp(prefix="tp-negatives-snap-")
    try:
        _base = os.path.join(_snap, "repo")
        shutil.copytree(ROOT, _base, ignore=shutil.ignore_patterns(
            "node_modules", "graphify-out", ".git"), symlinks=True)
        # `.git` is skipped for speed and restored for the two tests that commit a plant.
        #
        # **Ask git where the repository is; do not parse the pointer.** `.git` has three shapes
        # and this repository is consumed in all of them: a directory in a normal clone, a FILE
        # holding `gitdir: …/.git/modules/skills/task-pipeline` in the **submodule** checkout the
        # `sshlg-skills` umbrella ships (which is how most work on this pack happens), and a FILE
        # pointing at a per-worktree directory in a **linked worktree** — which `build.md` itself
        # tells every run to work in.
        #
        # Handling only the directory meant both git-dependent guards ran against a tree with no
        # repository, reported `fatal: not a git repository`, and were counted as *did not fire*:
        # exit 1 with two guards silently disarmed, while CI — which clones normally — stayed
        # green and said nothing. Measured 2026-08-15. Handling the pointer by hand fixed the
        # submodule and left the worktree broken in the identical way, because a per-worktree
        # directory holds HEAD and index while `objects`, `refs` and `config` live wherever its
        # `commondir` points.
        #
        # So BOTH are needed, and asking for only the common one is the trap the first fix fell
        # into: from a worktree on `feature`, a copy of the common dir alone reports
        # `git branch --show-current` = the main checkout's branch and a `git log` missing every
        # commit the worktree made. The common dir is copied first and the per-worktree dir
        # overlaid on top, which is exactly what git resolves at runtime.
        #
        # The result is COPIED rather than pointed at, for two reasons that both bite: a plant
        # that commits would otherwise move the real branch, and a submodule's config carries
        # `core.worktree` aimed back at the live checkout, which would make every git command
        # inside the snapshot operate on the tree the snapshot exists to protect. So the copy is
        # made, that one key is stripped, and `commondir` is dropped because the copy is now
        # self-contained and a dangling pointer is worse than none.
        _git_dst = os.path.join(_base, ".git")

        def _git_path(_flag):
            try:
                _r = subprocess.run(["git", "rev-parse", _flag],
                                    cwd=ROOT, capture_output=True, text=True)
            except OSError:
                return None         # no git on PATH: the two git guards will say so themselves
            if _r.returncode != 0 or not _r.stdout.strip():
                return None
            return os.path.normpath(os.path.join(ROOT, _r.stdout.strip()))

        _common = _git_path("--git-common-dir")
        _priv = _git_path("--git-dir")
        if _common and os.path.isdir(_common):
            shutil.copytree(_common, _git_dst, symlinks=True)
            if _priv and os.path.isdir(_priv) and os.path.realpath(_priv) != os.path.realpath(_common):
                # A linked worktree: HEAD, index, logs and the rest of the per-worktree state
                # win over the main checkout's copies of the same names.
                shutil.copytree(_priv, _git_dst, symlinks=True, dirs_exist_ok=True)
                for _stale in ("commondir", "gitdir"):
                    _p = os.path.join(_git_dst, _stale)
                    if os.path.exists(_p):
                        os.remove(_p)
            _cfg = os.path.join(_git_dst, "config")
            if os.path.isfile(_cfg):
                with open(_cfg, encoding="utf-8") as _fh:
                    _kept = [ln for ln in _fh if not re.match(r"\s*worktree\s*=", ln)]
                with open(_cfg, "w", encoding="utf-8") as _fh:
                    _fh.writelines(_kept)

        # Property checks assert that something IS printed, so the validator passes inside
        # them and they cannot join the suite above. They still have to run somewhere the
        # author can see: a step that lives only in CI is a step the local gate is blind to,
        # and that is exactly how this runner shipped green while CI failed on a string this
        # very file had renamed.
        props = [(n, s) for n, s in _STEPS if PROP_MARKER in n]
        # Same floor, same reason as MIN_EXPECTED above, one level up: rename the sole
        # property step and this list empties, the runner skips it in silence and still
        # exits 0 — which is the failure property checks were added to close.
        if len(props) < MIN_PROPS:
            print(f"FAIL: found only {len(props)} property checks in the workflow "
                  f"(expected at least {MIN_PROPS}). A category that quietly empties is "
                  f"a category nobody notices is gone.")
            return 2
        if only:
            props = [(n, s) for n, s in props if only.lower() in n.lower()]

        # 187 tests x (copy + validate) is thirteen minutes serially, long enough that the
        # suite gets backgrounded and stops being run before a commit — board row B-021.
        # They are independent and each owns a distinct scratch name, so they run in
        # parallel. Collisions only happen between two SUITE runs, which is a different row.
        _WORKERS = min(8, (os.cpu_count() or 4))

        failed, broken, prop_failed, errored = [], [], [], []
        print(f"running {len(tests)} negative self-tests"
              + (f" + {len(props)} property checks\n" if props else "\n"))
        _TIMEOUT = int(os.environ.get("SD_NEG_TIMEOUT", "600"))
        def _run_one(name_script):
            name, script = name_script
            cdir = copy_dir_of(script)
            sweep([cdir])
            try:
                r = subprocess.run(["bash", "-c", script], cwd=_base,
                                   capture_output=True, text=True, timeout=_TIMEOUT)
                return name, script, cdir, r.stdout, r.stderr, r.returncode, False
            except subprocess.TimeoutExpired as e:
                _dec = lambda b: b if isinstance(b, str) else (b or b"").decode(errors="replace")
                # A timeout is fixture_setup/validator_ran never completing -- an
                # environment fact, classified as TEST_ERROR, not a guard verdict.
                return name, script, cdir, _dec(e.stdout), _dec(e.stderr), None, True

        with concurrent.futures.ThreadPoolExecutor(max_workers=_WORKERS) as _ex:
            _results = list(_ex.map(_run_one, tests))
        for name, script, cdir, _stdout, _stderr, _rc, _timed_out in _results:
            # The success vocabulary is declared, not assumed (see SUCCESS_MARKERS): a
            # runner reads what the repository prints, it does not impose a convention.
            _out = _stdout.upper()
            guard_fired = _rc == 0 and any(_k in _out for _k in SUCCESS_MARKERS)
            # A probe that DECLARED a skip changed nothing on purpose -- its own status.
            skipped = _rc == 0 and "SKIP:" in _stdout

            # FIX-DV-20.01: compute the stages EXPLICITLY, then classify. An environment
            # failure (failed cp, ENOSPC, timeout) is a TEST_ERROR -- it is not, and can
            # never be, "the guard does not fire", because the guard never ran.
            env_error = has_env_error(_stdout + _stderr)
            # fixture_setup: a step that declares a scratch copy must actually have it.
            setup_ok = (cdir is None) or os.path.isdir(cdir)
            # mutation_verified: the scratch differs from the repo (nothing to verify
            # when a step plants in place and declares no scratch copy).
            mutant_differs = (cdir is None) or (os.path.isdir(cdir) and differs_from_repo(cdir))
            status = classify_stages(timed_out=_timed_out, env_error=env_error,
                                     skipped=skipped, setup_ok=setup_ok,
                                     mutant_differs=mutant_differs, guard_fired=guard_fired)
            bucket = {"GAP": failed, "BROKEN": broken, "TEST_ERROR": errored}.get(status)
            # GAP is displayed FAIL for continuity with the historical guard-bypass line.
            _disp = "FAIL" if status == "GAP" else status
            print(f"  {_disp:<11}{label(name)}")
            if bucket is not None:
                bucket.append((label(name), _stdout[-500:], _stderr[-500:]))
            sweep([cdir])

        for name, script in props:
            cdir = copy_dir_of(script)
            sweep([cdir])
            r = subprocess.run(["bash", "-c", script], cwd=_base, capture_output=True, text=True)
            ok = r.returncode == 0 and any(_k in r.stdout.upper() for _k in SUCCESS_MARKERS)
            print(f"  {'PASS' if ok else 'FAIL':<7}[property] " + _plabel(name))
            if not ok:
                prop_failed.append((_plabel(name), r.stdout[-500:], r.stderr[-500:]))
            sweep([cdir])

        print()
        for title, rows, why in (
            ("BROKEN — the planted defect changed nothing, so the test proves nothing", broken,
             "fix the corruption in .github/workflows/validate.yml"),
            ("FAIL — the validator accepted a planted defect", failed,
             "the guard does not actually fire"),
            ("TEST_ERROR — the environment could not run the test (NOT a guard verdict)", errored,
             "a failed copy, a full disk (ENOSPC) or a timeout — free resources and re-run; nothing is known about the guard"),
            ("FAIL — a property the run must print was not printed", prop_failed,
             "nothing was planted here: the check asserts an output, and the output is gone"),
        ):
            if rows:
                print(f"{title}:")
                for n, out, err in rows:
                    print(f"\n  * {n} — {why}")
                    for line in (out + err).strip().splitlines()[-6:]:
                        print("      " + line)
                print()


        # An environment failure with NO real guard-bypass is its own outcome: the suite
        # could not measure the guards, so it neither passes nor reports them as broken.
        if errored and not (failed or broken or prop_failed):
            print(f"TEST_ERROR: {len(errored)} test(s) could not run (environment) -- free "
                  f"resources and re-run. Zero guard-bypass findings: a full disk or a "
                  f"timeout is not a guard that failed to fire.")
            return 3
        if failed or broken or prop_failed or errored:
            print(f"FAIL: {len(failed)} guard(s) did not fire, {len(broken)} test(s) broken"
                  + (f", {len(prop_failed)} property check(s) silent" if prop_failed else "")
                  + (f", {len(errored)} test(s) could not run (environment)" if errored else ""))
            return 1
        # "all 0 guards ... provably reject" is a pass over an empty set, which is the
        # shape this repository calls a refused measurement. Say what actually ran.
        _parts = ([f"all {len(tests)} guards provably reject their planted defect"] if tests else [])
        _parts += ([f"{len(props)} property check(s) printed what they assert"] if props else [])
        print("PASS: " + " · ".join(_parts) if _parts else
              "PASS: nothing ran — no test matched, which is not a result")
        return 0
    finally:
        # FIX-DV-20.01: the snapshot and any scratch copies are removed on EVERY
        # exit path, including an early return or an exception mid-run.
        shutil.rmtree(_snap, ignore_errors=True)
        sweep([copy_dir_of(s) for _, s in tests])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
