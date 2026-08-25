# Cancellation, and the offer that deflects it

**Load this when** implementing cancel or reactivation, or building the "before
you go — 50% off your next invoice" card at the cancel step.

*Every parameter path, enum and required-field claim below is read from the
Stripe OpenAPI spec at API version `2026-07-29.dahlia` (the latest, confirmed
against `docs.stripe.com/changelog`) and from `docs.stripe.com` on 2026-08-25.
The two facts the documentation does not answer are marked as such, with the
commands that answer them.*

## Contents

- [Cancellation](#cancellation)
- [`cancel_at_period_end` is not the flag it used to be](#cancel_at_period_end-is-not-the-flag-it-used-to-be)
- [The save offer: two channels, one of which cannot say no](#the-save-offer-two-channels-one-of-which-cannot-say-no)
- [A coupon cannot say "once per customer"](#a-coupon-cannot-say-once-per-customer)
- [The trap: a `duration=once` discount deletes itself](#the-trap-a-durationonce-discount-deletes-itself)
- [Nobody tells you the customer stayed](#nobody-tells-you-the-customer-stayed)
- [Applying it yourself: `discounts` is a replacement, not an append](#applying-it-yourself-discounts-is-a-replacement-not-an-append)
- [Reading a discount now costs one more hop](#reading-a-discount-now-costs-one-more-hop)
- [Where the flow is simply not available](#where-the-flow-is-simply-not-available)
- [A save is not a renewal, and it is not a churn event either](#a-save-is-not-a-renewal-and-it-is-not-a-churn-event-either)
- [The test matrix](#the-test-matrix)

## Cancellation

```ts
await stripe.subscriptions.update(subId, { cancel_at_period_end: true });
// local: cancelAtPeriodEnd = true, status stays "active"
```

- **At period end is the default.** The user keeps what they paid for; `status`
  stays `active` and a separate flag drives the UI.
- **Do the teardown in `customer.subscription.deleted`**, never beside the API
  call, so one path serves your UI, the portal and dunning alike.
- **The portal is a second writer.** Everything a user does there reaches you
  only as a webhook; a billing page that assumes otherwise goes stale in a week.
- On `invoice.payment_failed`, mark `past_due` and notify — do not cancel.
  Stripe's dunning decides the retries and the terminal state; cancelling early
  cancels customers whose next attempt would have cleared.
- **Reactivation** is `cancel_at_period_end: false`, and is only meaningful while
  the period is still running. Past that it is a new subscription.
- If the local write fails after Stripe succeeded, say so honestly ("submitted,
  syncing shortly") and let reconciliation fix it. Reverting Stripe here would
  un-cancel a subscription the user asked to end.
- Immediate cancellation (`stripe.subscriptions.cancel`) is for refunds and
  abuse, and everything it must clean up still belongs in the
  `customer.subscription.deleted` handler.

## `cancel_at_period_end` is not the flag it used to be

Under **flexible** `billing_mode`, a cancellation scheduled *from the customer
portal* does not set `cancel_at_period_end` at all:

| | **classic** | **flexible** |
|---|---|---|
| `cancel_at_period_end` | `true` | **`false`** |
| `cancel_at` | the `current_period_end` timestamp, and it **follows** `current_period_end` when that moves | the maximum `current_period_end` across all items, and it does **not** follow |

So a billing page whose banner reads `if (sub.cancelAtPeriodEnd)` shows
"active, renews on the 2nd" to a customer who cancelled ten seconds ago, on a
subscription Stripe will end. Nothing errors, and the customer's next move is a
support ticket or a dispute.

**Derive the flag, in one function, from both fields:**

```ts
export function cancellationScheduled(sub: Stripe.Subscription): number | null {
  if (sub.cancel_at) return sub.cancel_at;                 // flexible, and classic too
  if (sub.cancel_at_period_end) return sub.items.data      // classic, cancel_at unset
    .reduce((max, i) => Math.max(max, i.current_period_end), 0) || null;
  return null;
}
```

Store the timestamp, not the boolean. `cancel_at` under classic mode moves when
the period moves; under flexible mode it does not — a stored boolean cannot
express either, and a stored timestamp refreshed from every
`customer.subscription.updated` expresses both.

Since `billing_mode` cannot be changed after creation, an account that has been
selling for a while holds **both kinds of row at once**. Code that handles only
the mode you create today is correct for new customers and wrong for the ones
who have been paying longest.

## The save offer: two channels, one of which cannot say no

Stripe's cancel page can carry a coupon card — headline, the amount saved, the
terms, and a **Redeem discount** button. It is configured in two places, and the
difference is not cosmetic.

| | **Dashboard "Retention Coupon"** | **`flow_data` retention** |
|---|---|---|
| Where | Settings → customer portal → Cancellations | the API call that mints the portal session |
| Who gets it | **every customer who reaches the cancel page** | whoever your server decided to offer it to |
| Per-customer targeting | impossible | the whole point |
| In code review, in a test, in git | no | yes |
| Turning it off during an incident | a human in the Dashboard | a deploy, or a feature flag |

The API path, with the exact parameter names (`flow_data_subscription_cancel_param`
→ `retention_param` → `coupon_offer_param` in the spec):

```ts
const session = await stripe.billingPortal.sessions.create({
  customer: customerId,
  return_url: `${origin}/billing`,                    // the "not now" exit, always live
  flow_data: {
    type: "subscription_cancel",
    subscription_cancel: {
      subscription: subId,
      ...(offer && {
        retention: {
          type: "coupon_offer",                       // the only value the enum takes
          coupon_offer: { coupon: offer.couponId },
        },
      }),
    },
    after_completion: {
      type: "redirect",
      redirect: { return_url: `${origin}/billing/cancelled` },
    },
  },
});
```

`retention` requires **both** `type` and `coupon_offer` — the spec marks the pair
required, so a call carrying only `type: "coupon_offer"` is rejected rather than
silently offering nothing.

**There is no `retention` field on the portal *configuration*.** The
configuration's `features.subscription_cancel` holds exactly four keys —
`enabled`, `mode` (`at_period_end` | `immediately`), `proration_behavior`
(`none` | `create_prorations` | `always_invoice`) and `cancellation_reason`. That
asymmetry is the whole design: **a targeted offer exists only on the session, so
eligibility is code you own, on your side of the boundary, or it does not exist.**

`after_completion.type` is one of `redirect`, `hosted_confirmation` or
`portal_homepage`. Send a cancellation somewhere that can say what happens next;
the default hosted page cannot tell the customer what they still have access to.

## A coupon cannot say "once per customer"

`retention.coupon_offer` takes a **coupon** id. Stripe's own comparison of the
two discount primitives:

| | **Coupon** | **Promotion code** |
|---|---|---|
| Restrict to a specific customer | ❌ | ✓ |
| First purchase only | ❌ | ✓ |
| Minimum spend | ❌ | ✓ |
| Deactivate without deleting | ❌ delete only | ✓ `active: false` |

None of the three restrictions you want on a save offer can be expressed by the
object the offer accepts. And `max_redemptions` is **not** a per-customer cap:
it is a total across all customers, shared with every promotion code on the same
coupon, so as a guard it is both wrong and a race — the fiftieth and
fifty-first cancelling customers both pass a read of `times_redeemed`.

Two consequences, and neither is optional:

1. **Eligibility is a decision your server makes before it mints the session.**
   Not a Stripe setting, not a coupon field.
2. **A coupon cannot be deactivated.** Deleting it prevents new applications and
   leaves every existing discount in place — which is the right behaviour, and
   means an over-generous `forever` coupon cannot be recalled from the customers
   who took it. Choose `duration` as if it were permanent for whoever redeems.

## The trap: a `duration=once` discount deletes itself

Straight from the coupon documentation:

> When a subscription uses a coupon with `duration=once`, the coupon is
> considered used after the invoice finalizes and is removed from the
> subscription's `discounts` array. […] This means a subscription may appear to
> have no discount even though a coupon was applied.

So the obvious eligibility check is the expensive one:

```ts
// WRONG. After the discounted invoice finalizes this is empty again.
const alreadyDiscounted = sub.discounts.length > 0;
```

A monthly subscriber cancels, takes 50% off, pays the discounted invoice — and
the array is clean. Next month they open the cancel flow again and your server,
reading Stripe, offers 50% off again. **The customer now rides half price
forever, one cancel-flow visit at a time, and every renewal looks ordinary in
the logs.** At $200/month that is $1,200 a year per customer who works it out,
and the flow's own copy — "You can still cancel at any time" — teaches them.

The guard is a row of your own, written when the discount arrives and never read
back from Stripe:

```ts
// retention_offers: (customerId, offerId) unique
type RetentionOffer = {
  customerId: string;
  offerId: string;              // yours: "cancel-50-once", not the coupon id
  couponId: string;             // what was actually offered, for the audit trail
  offeredAt: Date;
  redeemedAt: Date | null;      // set from customer.discount.created
  subscriptionId: string;
};

const COOLDOWN_DAYS = 365;

export async function offerFor(customerId: string, sub: Stripe.Subscription) {
  const history = await db.retentionOffer.findMany({ where: { customerId } });

  if (history.some((o) => o.redeemedAt)) {
    const last = Math.max(...history.filter((o) => o.redeemedAt)
      .map((o) => o.redeemedAt!.getTime()));
    if (Date.now() - last < COOLDOWN_DAYS * 86_400_000) return null;   // took one already
  }
  if (history.filter((o) => !o.redeemedAt).length >= 2) return null;   // declined twice
  if (sub.discounts.length > 0) return null;        // already discounted RIGHT NOW
  if (sub.status !== "active") return null;         // never discount out of dunning
  if (!(await isProfitableAtHalfPrice(sub))) return null;

  return { offerId: "cancel-50-once", couponId: process.env.STRIPE_RETENTION_COUPON! };
}
```

Four properties of that function, each of which is a defect if dropped:

- **The ledger is the source of truth, Stripe is the second opinion.** `discounts`
  answers "is there a discount right now", which is a different question from
  "has this person been given one".
- **A cooldown, not a lifetime ban.** A customer who took a save two years ago is
  a different risk from one who took it last month, and a lifetime ban makes the
  offer useless as a retention instrument.
- **Declining counts.** Someone walking the cancel flow repeatedly without
  redeeming is measuring you.
- **`status !== "active"` excludes dunning.** A customer whose card is failing is
  an involuntary-churn problem; discounting them halves the revenue you were
  already not collecting. Keep the two churn kinds apart —
  [`provider-concentration.md`](provider-concentration.md).

Write the row **before** the session is created, with `redeemedAt: null`. A
session minted and never recorded is an offer you cannot count, and the count is
the only thing that stops the loop.

## Nobody tells you the customer stayed

There is **no** portal event for a completed flow. The spec's webhook catalogue
holds `billing_portal.session.created` and the two
`billing_portal.configuration.*` events, and nothing else — no
`billing_portal.session.completed`, no per-flow outcome. What you get:

| Signal | Means |
|---|---|
| `customer.discount.created` | a Discount object now exists — this is the redemption |
| `customer.subscription.updated` | the subscription changed; `event.data.previous_attributes.discounts` says whether the discount is what changed |
| `customer.subscription.deleted` | the teardown, when they cancelled immediately |
| *nothing arriving at all* | the customer closed the tab |

**Absence of a cancellation is not a save.** A funnel that infers "retained"
from "no `customer.subscription.deleted` within an hour" counts every abandoned
tab as a win, and the number it produces is the one somebody will use to justify
widening the discount. Record the save from `customer.discount.created`, matched
to the open row in your ledger:

```ts
case "customer.discount.created": {
  const discount = event.data.object as Stripe.Discount;
  const couponId = typeof discount.source?.coupon === "string"
    ? discount.source.coupon
    : discount.source?.coupon?.id;                    // see the next section
  if (!couponId || !discount.customer || !discount.subscription) break;

  const { count } = await db.retentionOffer.updateMany({
    where: { customerId: idOf(discount.customer), couponId, redeemedAt: null },
    data: { redeemedAt: new Date() },
  });
  if (count === 0) {                                  // a discount we never offered
    log.warn("discount applied with no open retention offer", { couponId });
  }
  break;
}
```

That `count === 0` branch is the one worth keeping: it fires when a coupon is
applied by support, by the Dashboard, or by a Dashboard-configured retention
coupon nobody told the code about. Silently swallowing it is how a discount
programme becomes untraceable.

## Applying it yourself: `discounts` is a replacement, not an append

The hosted flow is the only way to get Stripe's cancel page. Any other offer —
pause, downgrade, service credit, a human — means you own the screen and apply
the coupon yourself. Three rules, and the first one destroys revenue:

**`discounts` on an update is the complete new list.** From the documentation:
"When updating `discounts`, you need to pass in any previously set `coupon`,
`promotion_code` or `discount` you want to keep on the subscription." So:

```ts
const fresh = await stripe.subscriptions.retrieve(subId, { expand: ["discounts"] });

await stripe.subscriptions.update(subId, {
  discounts: [
    ...fresh.discounts.map((d) => ({ discount: typeof d === "string" ? d : d.id })),
    { coupon: offer.couponId },                       // the save, added to what exists
  ],
});
```

Read it fresh inside the same request. A list you loaded when the page rendered
can be missing a discount sales negotiated since, and passing the stale list
**deletes** it — a 30%-off enterprise agreement replaced by a one-month 50%,
with no error and no invoice until the next cycle. `discounts: ""` clears them
all, which is a deliberate action and never a default.

- **Up to 20 discounts** stack on a subscription or item, and **order matters**
  when `amount_off` and `percent_off` mix: 20% then $5 off is not $5 off then 20%.
- **Adding a discount creates no invoice and no proration.** "The new discounts
  are applied the next time the subscription creates an invoice" — which is
  exactly why the honest copy is *"50% off your next invoice"* and why a card
  promising money back today is a lie the API will not tell.
- **Quote the number from Stripe.** `stripe.invoices.createPreview` returns what
  the next invoice will actually be. A percentage multiplied in your own code is
  a second home for a price — [`price-integrity.md`](price-integrity.md) — and
  the discrepancy surfaces on the customer's card statement, not in your tests.

## Reading a discount now costs one more hop

Three shapes moved, and all three fail as `undefined` rather than as an error —
so a save card renders "% off" with nothing in front of it:

| Reading | Then | Now | Moved in |
|---|---|---|---|
| the coupon behind a discount | `discount.coupon` | `discount.source.coupon`, with `discount.source.type === "coupon"` | `2025-09-30.clover` |
| the coupon behind a promotion code | `promotion_code.coupon` | `promotion_code.promotion.coupon`, with `promotion.type === "coupon"` | `2025-09-30.clover` |
| a subscription's discount | `subscription.discount` | `subscription.discounts[]`, and it needs `expand: ["discounts"]` | the `discounts` array |

`Discount` objects cannot be fetched by id — `expand` is the only way to read
one — and both new wrapper objects carry a `type` enum whose only current value
is `"coupon"`. Switch on it rather than assuming it: that enum exists because
something else is coming.

## Where the flow is simply not available

Each of these makes the cancel page — and therefore the offer — disappear for
some of your customers. The button either 400s or the page renders without the
action, and a cancel flow that dead-ends is worse than one that never existed.

- **A subscription with a subscription schedule attached can be neither updated
  nor cancelled in the portal.** If you implement downgrade-at-period-end with
  schedules — the standard way — you have removed your own cancel page from
  every customer who downgraded. Check for a schedule before offering the portal
  route, and keep an owned cancel path for those subscriptions.
- **Multiple products, usage-based prices, `collection_method: send_invoice`, or
  an unsupported payment method:** cancel works, *update* does not.
- **Modifying a `trialing` subscription ends the trial and invoices immediately.**
  Never route a trialing customer into a flow that can update.
- **A portal session expires 5 minutes after creation if unused**, and an hour
  after the last activity. Mint it in the request that redirects; a session id
  put in an email is dead on arrival.
- **The portal cannot be displayed in an iframe.** A modal cancel flow has to be
  a redirect or your own screen.

## A save is not a renewal, and it is not a churn event either

- **MRR** falls by the discount for as long as it runs. A discounted month is
  real revenue at a lower amount, not a deferred full month.
- **Churn** must not count the save. But the offer's *acceptance rate* is a
  number worth having on its own, and it comes from your ledger — Stripe cannot
  tell you about an offer it never saw the customer decline.
- `cancellation_details.feedback` is the customer's reason, one of
  `too_expensive`, `missing_features`, `switched_service`, `unused`,
  `customer_service`, `low_quality`, `too_complex`, `other` — configured per
  portal configuration and readable on the subscription and in Sigma. It is the
  input to *which* offer to make: `too_expensive` is a discount, `missing_features`
  is not.
- `cancellation_details.reason` is why the subscription ended, one of
  `cancellation_requested`, `payment_failed`, `payment_disputed`,
  `canceled_by_retention_policy`. **The last one is Stripe's test-data retention
  policy deleting old sandbox data, not your retention offer** — the names
  collide and the meanings do not.

## The test matrix

Shipped, and runnable now. `fixtures/` carries both invariants this file states,
each with the mutant that makes it fail:

| Invariant | Mutant | What the mutant ships |
|---|---|---|
| `retention-offer-is-consumed-once` | `retention-eligibility` | no ledger at all — eligibility read from `subscription.discounts`, so the offer returns every cycle and a save cannot be told from a support discount |
| `scheduled-cancellation-survives-billing-mode` | `cancellation-timestamp` | `cancel_at_period_end` alone, which reads as "renews" on every flexible-mode cancellation |

```bash
node fixtures/assert-money-invariants.mjs              # both, against the reference handler
node fixtures/assert-money-invariants.mjs --self-test  # watch each assertion go red on its own
```

Beyond that, two things the documentation does not state and a sandbox does —
run them before shipping a live offer, and record what you saw:

```bash
stripe listen --forward-to localhost:3000/api/billing/webhook
# then walk the flow: does redeeming emit customer.discount.created BEFORE
# customer.subscription.updated, and does the cancellation get abandoned
# entirely (no cancel_at, no cancel_at_period_end)?
stripe subscriptions retrieve sub_... --expand discounts
```

- [ ] cancel from the portal, classic and flexible `billing_mode`; the stored
      cancellation timestamp is right in **both**
- [ ] redeem the offer; the ledger row gets `redeemedAt` and the subscription is
      **not** flagged for cancellation
- [ ] pay the discounted invoice, then re-enter the flow: **no second offer**
- [ ] a subscription carrying a negotiated discount: the save is added, the
      negotiated one survives
- [ ] a subscription with a schedule attached: the flow is refused with a real
      message, not a Stripe 400
- [ ] `past_due`: no offer
- [ ] a coupon applied from the Dashboard: the `count === 0` warning fires
