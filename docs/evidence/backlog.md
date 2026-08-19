# Board — sheleg-dev

The work-list between runs. Seeded 2026-08-19 by row **SD-01** of the cross-repository
manifesto-conformance program, which needed somewhere in *this* repository to file what it
found and did not close. Until then the only evidence file here was
`docs/evidence/verification.md`, so a deferred item had nowhere to survive a session —
the same absence `sshlg-skills` row B-30 measured about the ledger.

Priority is computed, not asserted: **`(impact × confidence) / effort`**. `impact` 1–5 on
what it costs an outside reader to be told something untrue here; `confidence` 1.0
confirmed defect · 0.7 measured but scoped · 0.4 single observation · 0.2 hypothesis;
`effort` 1–5 in engineering days including the release.

Status: `open` · `in progress` · `done` · `dropped (why)`.

| id | Priority | Item | Why it matters | Source | Status |
|---|---|---|---|---|---|
| B-79 | 5.0 | `SECURITY.md` was a wholesale copy of `seo-aeo-audit`'s, with six references this repository has nowhere | It ships in the npm tarball (`package.json` → `files`), so a reader deciding whether to trust a pack about payment credentials was told to verify it with two commands that exit 2. Manifesto M-44 (one authoritative home, references resolve) and M-07 (a claim points to an address another actor can resolve) | manifesto program row SD-01, 2026-08-19; audit evidence `SECURITY.md:10,11,17,35,54,56` | done — rewritten against measured facts; `test/validate.py` refuses a recurrence |
| B-80 | 4.0 | The PR template asked for output from `python3 test/test_page_audit.py` and named `cursor/rules/*.mdc` | Same copy, same disease, one layer out: every contributor was asked for evidence from a command that cannot run, and told to respect a directory this repository has never had. Found by the B-79 guard on its first run, not by the audit | B-79 guard, first run 2026-08-19 | done — one gate command, and the checklist item now names a rule this repo has |
| B-81 | 2.0 | `CONTRIBUTING.md` named `agent_sync.py` with no owner | A reader told to "regenerate it with `agent_sync.py setup`" cannot find the script: it ships with the `agent-sync` skill, not here. An M-07 pointer with no address — smaller than B-79 and the same shape | B-79 guard, first run 2026-08-19 | done — the sentence now names the owning skill; declared in `FOREIGN_BY_DESIGN` |
| B-82 | 1.4 | The B-79 guard does not read the 26 markdown files of the skill payload | Its corpus is the four documents *about* this repository. Inside a skill reference, 41 backticked paths name the **reader's** project (`next.config.ts`, `src/lib/heleket.ts`, `web/auth.py`) and must not resolve here — so widening needs a second rule (a repo-internal prefix such as `plugins/`, `test/`, `bin/`, `scripts/`), not a wider corpus. Until it exists, a dead `plugins/…` path inside a `SKILL.md` is caught only by the existing `references/` check | SD-01 measurement 2026-08-19: 55 non-resolving path tokens across 35 tracked markdown files, 41 of them legitimate reader-project paths | open |
| B-83 | 1.0 | `docs/AGENT_SYNC.md` names five `references/*.md` files that live in the `agent-sync` skill | Generated from `.claude/agent-sync.json`, so a fix belongs upstream in the generator, not in the file. Low impact — the paragraph says "full doctrine ships with the skill" one line earlier — but it is the same class as B-81 and a reader cannot resolve them | SD-01 measurement 2026-08-19, `docs/AGENT_SYNC.md:89-91` | open |
| B-84 | 0.9 | `docs/evidence/verification.md` REQ-001 quotes `12 checks`; the tree now prints `13` | The row measures **shipped v0.6.0** and was true of it, so it is not wrong — but nothing connects the quoted string to the validator's current output, and the same drift is what REQ-001 exists to catch one level up. The next release must re-measure it | SD-01, 2026-08-19 | open — re-measure at the next release |

## How this file is used

A run reads it before starting and quotes the open count. Anything a run finds and does not
close gets an id here with a computed priority, or it did not happen. A row that leaves
without either a `done` or a stated reason is what this file exists to prevent.
