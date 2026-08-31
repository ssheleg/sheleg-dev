# Evaluation results

**Status: executed 2026-08-31 against two models; method and limits below.**

CI still proves only that the files are shaped correctly and that the validator
catches a planted invalid trigger class. The rows below are model runs executed
from an agent harness, not from an interactive user session — the Method section
states exactly what was and was not reproduced.

| Date | Version | Model | Trigger pass rate (train / validation) | Scenario lines passed | Installed alongside | Notes |
|---|---|---|---|---|---|---|
| 2026-08-31 | 0.11.1 (release tree) | haiku (Claude Code Agent-tool alias) | 23/24 (95.8%) / 15/18 (83.3%) — 3 runs per query | — | full ssheleg family + foreign packs (machine roster) | misses: q10 once (r1 → stripe-billing), q13 all three runs (→ frontend-performance) |
| 2026-08-31 | 0.11.1 (release tree) | sonnet (Claude Code Agent-tool alias) | 23/24 (95.8%) / 16/18 (88.9%) — 3 runs per query | 23/24 (s01 3/4; s02–s06 4/4) | full ssheleg family + foreign packs (machine roster) | misses: q02 once (r3 → task-pipeline), q13 twice (→ frontend-performance) |

## Method (2026-08-31 run)

- **Trigger cases**: each of the 14 queries was posed verbatim to a FRESH
  subagent (Claude Code Agent tool, general-purpose, models `haiku` and
  `sonnet`), three times per query per model, per this file's protocol. The
  prompt was the query plus the seven pack skill names-with-descriptions
  (extracted from the SKILL.md frontmatters) and the instruction to answer with
  one skill name or "none". A positive query scores a hit only when the
  intended skill is named; a negative query scores a hit when NO pack skill is
  named — several probes named a correct foreign router instead of "none"
  (q10 → copywriting, q11 → telegram-bots, q12 → task-pipeline), which counts
  as a hit for the negative class and is itself the routing the family map
  intends.
- **Not a clean-room install**: the harness machine carries the full ssheleg
  family and foreign packs, and several sonnet probes answered from that
  installed roster without reading the provided list. Coexistence changed
  routing exactly as the README warns: one q02 run sent an implementation
  request to `task-pipeline` instead of `crypto-payments`.
- **Known false trigger**: "Explain what LCP means" (q13, informational) pulled
  `frontend-performance` in 3/3 haiku and 2/3 sonnet runs. The boundary
  "informational question, not an optimisation task" does not hold in either
  model's routing; recorded here rather than tuned away, since q13 sits in the
  validation split.
- **Scenarios**: each scenario's query was handed to a fresh sonnet subagent
  with the named skill file(s) loaded, asked for an implementation design
  (no full code). Each expected_behavior line was scored against that design by
  the coordinating agent. This scores stated design intent, not code produced
  in a live interactive run — a full interactive reproduction is not available
  from this harness. Failing line: s01 "Tests renewal, refund and out-of-order
  delivery paths" — the design tested renewal and duplicate delivery but named
  no refund-path test.
- Raw per-run answers are in the wave-3 run report; this table is the durable
  summary.
