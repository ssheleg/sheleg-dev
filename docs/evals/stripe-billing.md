# Evaluations — `stripe-billing`

Not shipped with the package (`files` in `package.json` covers `bin`, `plugins`,
and the repo meta only). This is the measurement record for the skill: what the
baseline gets wrong, and what a run with the skill has to get right.

## Baseline

The usual baseline for a new skill is "run the task with no skill and record the
failures". This skill had a stronger one available: **the defect record of a
live subscription integration built by agents without it** — a Next.js SaaS on
Stripe Billing, with seats, metered usage, refunds and referral commission.

Every rule in `SKILL.md` traces to a defect that reached production there, or to
a guard added after one did. The eight that shaped the skill:

| # | Baseline failure | Rule it produced |
|---|---|---|
| B1 | Renewal grants fired on proration invoices — a seat change gave away a month of product | `billing_reason` table |
| B2 | Read-then-write idempotency: two deliveries 40 ms apart both credited | claim-first, `INSERT` on a primary key |
| B3 | A handler that failed left the event marked processed; the retry did nothing | release the claim on failure |
| B4 | Client built with no retry policy; a dropped connection surfaced as "could not start payment" | `maxNetworkRetries`, never a hand-rolled loop |
| B5 | `amount_refunded` read as an increment | cumulative total, compare-and-swap |
| B6 | A pricing page carried its own constants and advertised $300/yr for a $250 plan, for months | one home per fact; conformance job |
| B7 | Seat quantity written to Stripe, then a failed local write left the two disagreeing | Stripe first, compensating revert with `proration_behavior: none` |
| B8 | Two concurrent requests created two Stripe customers for one user | conditional update + orphan delete |

B6 is the one that argues for the skill's existence: it failed no request, threw
no error and passed every test, because checkout sends a price id and Stripe
holds the amount. Only customers ever saw it.

## Coexistence

Measured against the **installed** set on the authoring machine, not a guess:
`stripe@claude-plugins-official` 0.5.1 was enabled, providing `stripe-docs`,
`stripe-best-practices`, `stripe-apps`, `stripe-projects`, `stripe-directory`,
`connect-recommend`, `upgrade-stripe`.

The nearest neighbour is `stripe-best-practices`, whose trigger is broad ("any
Stripe integration"). It answers *which Stripe primitive to use*; this skill
answers *what happens on your side of the boundary*. The description carries an
explicit "Not for …" clause naming it, and the body defers to it by name on
three decisions (usage-based billing, tax, Connect) and states that it wins any
disagreement.

## Eval cases

Each is a prompt to run against a scratch repository, with and without the
skill. Pass = the listed behaviour appears without being asked for.

1. **"Add Stripe subscription checkout to this Next.js app."**
   Pass: metadata on both the session and `subscription_data`; no
   `payment_method_types`; return URLs validated against the origin; webhook
   verified on the raw body; the webhook path exempted from CSRF by exact match.

2. **"Handle subscription renewals."**
   Pass: `billing_reason` is branched on, `subscription_update` does not grant,
   and the period is read from `items.data[0]`, not the subscription.

3. **"Make the webhook idempotent."**
   Pass: a claim written before the work, released on failure; duplicates
   answered 200; a store failure answered 5xx rather than treated as new.

4. **"Users can add and remove seats."**
   Pass: `proration_behavior` chosen deliberately; `error_if_incomplete` on the
   upgrade; Stripe written before the database, with a revert on local failure.

5. **"Handle refunds."**
   Pass: `amount_refunded` treated as cumulative; compare-and-swap on the stored
   total; the subscription-invoice path handled as well as the payment-intent
   one.

6. **"Show the plan prices on the marketing page."**
   Pass: the number is read from the one module the checkout path uses; no
   second constant is introduced.

**Status: NOT RUN as an A/B measurement.** The cases are written against
recorded production failures rather than against a simulated no-skill run, and
none of them has been executed as a scored eval. Recording that plainly is
cheaper than a pass nobody earned; the next person to touch this skill should
run them before claiming the skill improves anything.

## Verified at authoring time

- Body budget: ~4747 tokens by the house heuristic, 409 lines of body — both
  recomputed by `test/validate.py` (`check_evals_numbers_are_computed`), because the
  three numbers this line used to carry were measured once and restated afterwards:
  `4994` tokens, `441` lines and `0 GAP, 13 PASS` against a tree that measured 4747,
  409 and `0 GAP, 14 PASS`. Three of four wrong, in the document whose subject is
  measurement.
- The `GAP/PASS` pair is a **dated reading, not a computed one**: `audit_skill.py --house`
  printed `0 GAP, 14 PASS` for this skill on 2026-08-20, and that script ships with
  `make-skill` in another repository. There is no tokeniser in this repository's
  toolchain either, which is why the cl100k count is gone rather than restated — a
  number nothing here can recompute is a claim, and this file already learned that.
- Official material read from `docs.stripe.com/agents`, `/skills`, `/mcp` and
  the CLI's own `--help` on 2026-08-11, against Stripe CLI 1.45.2.
- Neighbour set read from
  `~/.claude/plugins/cache/claude-plugins-official/stripe/0.5.1` and from
  `enabledPlugins` in `settings.json`, not assumed.
