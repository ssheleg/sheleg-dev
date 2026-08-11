# Subscription lifecycle — code for each stage

**Load this when** implementing checkout, the verify fallback, renewal grants,
seat or plan changes, cancellation, or refund clawback. Every snippet is the
shape that survived production; the reasoning for each is in `SKILL.md`.

## Contents

- [Data model](#data-model)
- [Creating the checkout session](#creating-the-checkout-session)
- [The verify fallback](#the-verify-fallback)
- [Granting on renewal](#granting-on-renewal)
- [Seat and quantity changes](#seat-and-quantity-changes)
- [Plan changes](#plan-changes)
- [Trials](#trials)
- [Cancellation and reactivation](#cancellation-and-reactivation)
- [The customer portal](#the-customer-portal)
- [Refund clawback](#refund-clawback)
- [Reconciliation job](#reconciliation-job)
- [Non-Stripe subscriptions](#non-stripe-subscriptions)

## Data model

The minimum that makes every later question answerable:

| Column | Note |
|---|---|
| `stripeSubscriptionId` | **unique** — this constraint is your idempotency |
| `stripeSubscriptionItemId` | needed for every quantity update and usage report |
| `stripePriceId`, `stripeProductId` | what they are on, denormalised for queries |
| `status` | your own enum, mapped from Stripe's — never Stripe's string raw |
| `currentPeriodStart`, `currentPeriodEnd` | from the **item**, not the subscription |
| `cancelAtPeriodEnd` | drives the UI; distinct from `status` |
| `quantity` | seats; 1 for flat plans |
| `pricingType` | `flat` \| `tiered` \| `metered` — decides which paths apply |
| `lastGrantedPeriodStart` | the double-grant guard |
| `paymentSource` | `stripe` \| something else; the reconciliation job reads it |

Map status once, in one function, and log the unknown case rather than
defaulting silently:

```ts
const MAP: Record<string, Status> = {
  active: "active", trialing: "trialing", past_due: "past_due",
  unpaid: "unpaid", canceled: "canceled", incomplete: "incomplete",
  incomplete_expired: "canceled", paused: "canceled",
};
export function mapStatus(s: string): Status {
  const m = MAP[s];
  if (!m) log.warn("unknown Stripe subscription status", { s });
  return m ?? "incomplete";
}
```

## Creating the checkout session

```ts
const metadata = { userId, productId, quantity: String(quantity) };

const session = await stripe.checkout.sessions.create({
  customer: customerId,
  mode: "subscription",
  line_items: [{ price: priceId, quantity }],
  // Do NOT pass payment_method_types — Stripe picks eligible methods from
  // Dashboard settings, and hardcoding ['card'] costs conversion.
  metadata,
  subscription_data: { metadata },
  success_url: `${origin}/onboarding?session_id={CHECKOUT_SESSION_ID}`,
  cancel_url: `${origin}/pricing`,
});
```

Before that call, in order:

1. authenticate, and check the account is in a state allowed to transact
   (blocked, deletion-scheduled and delinquent accounts should not reach Stripe);
2. rate-limit per user — this endpoint creates objects in someone else's system;
3. validate `productId` against an allowlist; reject anything else with 400;
4. clamp quantity server-side (`Math.floor`, min 1, a hard max);
5. refuse a duplicate: an active subscription to the same product answers 409
   with the existing id, not a second checkout;
6. validate any caller-supplied `successUrl`/`cancelUrl` against your own
   origin, and fall back to the default on mismatch.

## The verify fallback

The success page calls this; it is also how local development works at all.

```ts
const s = await stripe.checkout.sessions.retrieve(sessionId);

if (s.metadata?.userId !== callerId) return json({ error: "not yours" }, 403);
if (s.status !== "complete")          return json({ error: "not complete" }, 400);
if (s.payment_status === "unpaid")    return json({ error: "not paid" }, 402);

const existing = await db.subscription.findUnique({ where: { stripeSubscriptionId } });
if (existing) return json({ subscription: existing, created: false });

try {
  const created = await grantExactlyAsTheWebhookWould();
  return json({ subscription: created, created: true });
} catch (err) {
  if (isUniqueViolation(err)) {                    // the webhook won the race
    return json({ subscription: await reread(), created: false });
  }
  throw err;
}
```

The ownership check is the security-critical line: without it, any authenticated
user who learns a `cs_…` id claims someone else's purchase. Rate-limit it too —
it costs an API call per request.

While the race is open, render a "confirming your payment" state. Sending the
user back to the plan chooser shows a paywall to somebody who just paid.

## Granting on renewal

```ts
if (invoice.billing_reason !== "subscription_cycle") return;   // see webhook-events.md

await db.$transaction(async (tx) => {
  const sub = await tx.subscription.findUnique({ where: { id }, select: { lastGrantedPeriodStart: true } });
  if (sub?.lastGrantedPeriodStart && sub.lastGrantedPeriodStart >= periodStart) return;  // replay

  await tx.subscription.update({ where: { id }, data: { lastGrantedPeriodStart: periodStart } });
  await tx.wallet.update({ where: { userId }, data: { credit: { increment: allowance } } });
  await tx.auditLog.create({ data: { userId, action: "grant", amount: allowance,
    source: "subscription-renewal", metadata: { invoiceId: invoice.id } } });
});
```

Marker and grant in **one** transaction. Two statements outside a transaction is
the same bug as read-then-write, one level up.

## Seat and quantity changes

```ts
const item = (await stripe.subscriptions.retrieve(subId)).items.data[0];

try {
  await stripe.subscriptions.update(subId, {
    items: [{ id: item.id, quantity: newQuantity }],
    proration_behavior: "always_invoice",
    payment_behavior: "error_if_incomplete",     // upgrades only
  });
} catch (err) {
  if (err.type === "StripeCardError" || err.code === "invoice_payment_intent_requires_action") {
    return json({ error: "payment failed", code: "payment_failed" }, 402);
  }
  throw err;
}

try {
  await db.subscription.update({ where: { id }, data: { quantity: newQuantity } });
} catch (dbErr) {
  await stripe.subscriptions.update(subId, {                  // compensating revert
    items: [{ id: item.id, quantity: oldQuantity }],
    proration_behavior: "none",                               // do not re-bill the revert
  }).catch((e) => log.error("CRITICAL: revert failed, Stripe and DB disagree", { subId, e }));
  throw dbErr;
}
```

- **Downgrades** need no `payment_behavior`; they produce a credit.
- **Reducing below what is in use** is a business decision, not an API call.
  Answer 409 with the list of things that must be released first, and let the
  user choose which — picking for them deletes the wrong one.
- **`preview` before charging.** A separate read-only action that quotes the
  prorated amount (`stripe.invoices.createPreview`) turns "why was I charged
  $17.43" into a number the user already agreed to.
- Do not add seats to a subscription flagged `cancel_at_period_end` — reactivate
  first, or the seats vanish at period end.

## Plan changes

Same shape as a quantity change, with `items: [{ id: item.id, price: newPriceId }]`.
Two extra decisions:

- **Immediate or at period end.** Immediate is `proration_behavior:
  "always_invoice"`. At period end is a subscription schedule, not an update —
  the difference is whether the customer is charged today.
- **What happens to the current period's allowance.** Grant the difference
  pro-rata for the remaining time, and write the marker so the next renewal does
  not grant twice. Granting the full new allowance on an upgrade is a free month
  for anyone who upgrades on the last day.

## Trials

`subscription_data: { trial_period_days: N }` on the session. A trialing
subscription has `status: "trialing"` — entitlement logic must treat it as
active or trials do not work, and `mapStatus` must not collapse it into
`active` or you cannot tell them apart in reporting.

`customer.subscription.trial_will_end` fires three days out. When the trial
converts, `invoice.paid` arrives with `billing_reason: "subscription_cycle"`.

## Cancellation and reactivation

```ts
await stripe.subscriptions.update(subId, { cancel_at_period_end: true });
// local: cancelAtPeriodEnd = true, status stays "active"
```

If the local write fails after Stripe succeeded, say so honestly ("submitted,
syncing shortly") and let reconciliation fix it. Reverting Stripe here would
un-cancel a subscription the user asked to end.

Reactivation is `cancel_at_period_end: false`, and is only meaningful while the
period is still running. Past that, it is a new subscription.

Immediate cancellation (`stripe.subscriptions.cancel`) is for refunds and abuse.
Everything it must clean up belongs in the
`customer.subscription.deleted` handler, not next to the API call.

## The customer portal

```ts
const portal = await stripe.billingPortal.sessions.create({
  customer: customerId,
  return_url: `${origin}/billing?portal_return=true`,
});
```

The portal is a second writer with no CSRF token and no notion of your database.
Everything a user does there reaches you as a webhook, later. Two consequences:
the billing page must refresh from the webhook-updated row on return, and any
invariant you enforce in your own UI (seat minimums, plan eligibility) must be
configured in the portal too, or it can be violated there.

Users with no `stripeCustomerId` get a 400 with a plain message, not a crash.

## Refund clawback

```ts
const totalRefunded = charge.amount_refunded / 100;
const increment = totalRefunded - stored.refundedTotal;
if (increment <= 0) return;

const { count } = await db.purchase.updateMany({
  where: { id: stored.id, refundedTotal: stored.refundedTotal },
  data:  { refundedTotal: totalRefunded },
});
if (count === 0) return;                       // concurrent delivery won

try {
  await clawBack(stored.userId, increment);    // idempotent, keyed on charge id + total
} catch (err) {
  await db.purchase.update({ where: { id: stored.id },
    data: { refundedTotal: stored.refundedTotal } });   // put the marker back
  throw err;
}
```

Clamp the deduction at zero. A user who already spent the credit goes to a
negative balance or to a collections decision — pick one deliberately and log
which. Silently deducting into negative is how a support ticket becomes a
dispute.

If you pay referral or affiliate commission on purchases, reverse it
proportionally, computing the target from the **original** commission rather
than the current balance — otherwise partial refunds compound.

## Reconciliation job

```ts
for await (const sub of stripe.subscriptions.list({ customer, status: "all", limit: 100 })) {
  // create / update / grant-if-period-advanced — sequential on purpose:
  // each iteration opens a transaction and may call an external API.
}
for (const local of localRows) {
  if (local.status === "canceled") continue;
  if (seenInStripe.has(local.stripeSubscriptionId)) continue;
  if (isNonStripeBacked(local)) continue;         // ← the guard that matters
  await cancelLocally(local);
}
```

Run it nightly per active customer, and expose it as a "Sync now" button. Any
grant it performs must reuse the webhook's idempotency marker.

## Non-Stripe subscriptions

Comped accounts, manual invoices, crypto and app-store purchases all end up in
the same table. Give them a `paymentSource` and synthetic ids with a recognisable
prefix, and make every Stripe-facing path skip them explicitly:

```ts
const isDev     = (id: string) => id.startsWith("dev_sub_");
const isNonStripe = (row) => row.paymentSource !== "stripe" || row.stripeSubscriptionId.startsWith("bal_sub_");
```

The reconciliation job is where this bites: without the guard it finds rows
Stripe has never heard of and cancels every one of them.
