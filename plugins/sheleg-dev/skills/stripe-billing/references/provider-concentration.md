# Depending on one provider

**Load this when** revenue is growing, when a second market is being opened, when
involuntary churn needs separating from voluntary, or when someone asks what
happens if the payment account is limited.

Everything in `SKILL.md` assumes Stripe is the payment system. That is a
reasonable default and it is also a concentration: the account that runs the
charges can be limited or closed, and when it is, there is no second route unless
one was built before it was needed. The seam that makes a second route possible
costs almost nothing while there is one provider, and becomes a migration once
there are two.

## Contents

- [Keep the seam, not the second provider](#keep-the-seam-not-the-second-provider)
- [Three ways this costs money at volume](#three-ways-this-costs-money-at-volume)
- [Automatic card updates, and what they do not tell you](#automatic-card-updates-and-what-they-do-not-tell-you)
- [Involuntary is not voluntary](#involuntary-is-not-voluntary)
- [Checklist](#checklist)

## Keep the seam, not the second provider

Running two providers from day one is two webhook surfaces, two reconciliations,
two test matrices and two sets of tax obligations, for a problem most products
never have. Adding the second one later is cheap **if** three things were true
from the start, and expensive if they were not.

- **The entitlement is yours and the charge is theirs.** Your own row, keyed to
  your own user id, with the provider's ids as fields on it rather than as its
  primary key. `SKILL.md` → **Reconciliation** already assumes this: its loop
  excludes "rows that were never Stripe's" — comped, manual and other-provider
  plans with synthetic ids. That exclusion is this seam, half-built.
- **The customer identity is yours too.** Email or user id, resolved before
  checkout, so a second provider can be added without re-identifying the base.
  A provider's customer id as your only handle on a person is the migration
  nobody budgets for.
- **The reconciliation job is the external check.** It is the one number in the
  system that is not telemetry: charges that succeeded, reported by the party
  that processed them. Everything else you know about revenue is inference from
  your own instrumentation.

What this is **not**: an argument for an abstraction layer over payments. A
generic `PaymentProvider` interface written against one provider encodes that
provider's model and has to be rewritten for the second one anyway. The seam is
in the data — whose id owns what — not in the code shape.

## Three ways this costs money at volume

None of these looks like a payments problem from inside the app.

| What happens | Why it is invisible | Where to look |
|---|---|---|
| Approval rates differ by country, and some markets are not served at all | An unserved market is obvious. A market with a poor approval rate is not: a declined charge and a customer who changed their mind produce the same empty result in the funnel | Decline codes grouped by country, measured against **attempts** rather than against successes |
| Renewals fail on cards that expired, were reissued, or were blocked | The subscription ends and nobody decided to end it, so it lands in churn beside voluntary cancellations | `invoice.payment_failed` and the dunning path, kept separate from the `customer.subscription.deleted` that came from your own UI |
| A replaced card silently keeps working, or silently does not | See the next section: the mechanism exists, its coverage varies by country, and Stripe states you cannot tell which cards it covers | `payment_method.automatically_updated` and `payment_method.updated` |

The measurement that makes the first row actionable is the denominator. Approval
rate is successes over *attempts*, and a dashboard that reports successes over
successes reports 100% in every market.

## Automatic card updates, and what they do not tell you

Stripe works with the card networks and **automatically** attempts to update
saved card details when a customer's card is replaced, so a saved payment method
can keep working after an expiry or a reissue. There is nothing to switch on.

Two limits, both stated by Stripe and both load-bearing:

- Support is **wide in the United States** across American Express, Visa,
  Mastercard and Discover issued there, and **varies by country** elsewhere,
  because it needs the issuer to participate.
- It is **not possible to identify which cards support it**. So you cannot
  compute how much of your subscription base is protected, and any plan that
  assumes the mechanism will catch a reissue is a plan with an unmeasurable
  branch.

What to do rather than assume:

- Listen for **`payment_method.automatically_updated`** for network-driven
  changes and **`payment_method.updated`** for API-driven ones.
- Both carry the card's new expiration and last four. Write them to your own
  records from the event, or the billing page keeps showing digits the customer
  no longer has, and a support ticket follows a change that actually succeeded.
- A card update that includes a new **number** changes the payment method's
  `fingerprint`. If anything in your system keys off the fingerprint — dedup of
  saved cards, fraud rules, "you already used this card" — that identity moves
  under it.

## Involuntary is not voluntary

Stripe owns the retry schedule and the terminal state (`SKILL.md` →
**Renewal**, **Cancellation**). What it cannot own is the difference between a
subscription that ended because someone chose to leave and one that ended because
a bank reissued a number.

Keep them apart in your own data, because everything downstream reads it:

| | Voluntary | Involuntary |
|---|---|---|
| Arrives as | your own cancel route, or `cancel_at_period_end` | `invoice.payment_failed` → dunning → terminal |
| The customer's intent | stated | never expressed |
| The right message | confirm, and say what happens to their data | tell them a payment failed and how to fix it |
| The wrong message | — | a farewell email, which spends the relationship on a recoverable failure |
| Counts as churn | yes | yes, and reporting it in the same number hides a fixable revenue leak |

A single `canceled` status for both is the shape this failure takes. Record the
cause, not just the outcome.

## Checklist

- [ ] Entitlement rows keyed to your user id, provider ids as fields
- [ ] Customer identity (email or user id) resolved before checkout
- [ ] Reconciliation job running, and its result compared against your own numbers
- [ ] Decline codes grouped by country, measured against attempts
- [ ] `payment_method.automatically_updated` and `payment_method.updated` handled,
      and the stored last-four and expiry written from them
- [ ] Anything keyed on `fingerprint` reviewed for the case where it changes
- [ ] Involuntary and voluntary cancellation distinguishable in your own data
- [ ] No farewell email on the involuntary path
