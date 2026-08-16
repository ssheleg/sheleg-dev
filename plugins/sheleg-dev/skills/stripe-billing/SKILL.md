---
name: stripe-billing
description: >-
  Use when connecting a product to Stripe, or auditing a live integration:
  checkout sessions, subscriptions and renewals, seats, proration, refunds, the
  portal, and the webhook that turns a payment into an entitlement in the
  application's own database. Covers Stripe's agent toolchain (CLI, MCP,
  skills), the pinned API version and SDK retries, product-to-price resolution
  across test and live, the get-or-create customer race, metadata written
  twice, claim-first webhook idempotency, what invoice billing_reason decides,
  cumulative refund totals, write ordering across two systems with compensating
  reverts, reconciliation, and price drift only customers see. Triggers - "add
  Stripe", "Stripe checkout", "subscription billing", "webhook signature",
  "invoice.paid", "proration", "seats", "refund", "подключить Stripe", "оплата
  подпиской", "вебхук Stripe", "биллинг". Not for choosing between Stripe
  products (stripe-best-practices) or reading Stripe docs (stripe-docs).
license: MIT
---

# Stripe billing

Stripe holds the money. Your database holds the entitlement. **Every serious
billing defect is one fact living in two systems that stopped agreeing** — a
price, a quantity, a period, a refunded total.

Stripe's API is not where integrations fail. Failures happen at the seam: the
callback that arrived twice, the renewal that granted a month of product for a
$0.40 proration invoice, the upgrade that charged the card and then failed to
write the row.

This skill is that seam. For **which** Stripe primitive to use (Checkout vs
PaymentIntents, Connect, Tax, usage-based billing) the official
`stripe-best-practices` skill is the authority and wins any disagreement; for
lookups, `stripe-docs`. Examples are TypeScript; the rules are
language-neutral.

Deep material, loaded on demand:

| Read | When |
|---|---|
| [`references/stripe-agent-toolchain.md`](references/stripe-agent-toolchain.md) | starting from nothing, or about to guess an API shape — CLI, MCP tools, skills index, key handling |
| [`references/webhook-events.md`](references/webhook-events.md) | writing or reviewing the handler — event catalogue, payload shapes, ordering, failure semantics |
| [`references/subscription-lifecycle.md`](references/subscription-lifecycle.md) | implementing checkout, verify, renewal, seats, plan change, trials, cancellation, clawback |
| [`references/price-integrity.md`](references/price-integrity.md) | pricing lives in more than one file, or an advertised price must be proved against Stripe |
| [`references/testing-and-local-dev.md`](references/testing-and-local-dev.md) | local webhooks, fixtures, mocks, and a suite that would actually catch a money defect |
| [`references/provider-concentration.md`](references/provider-concentration.md) | growing revenue, opening a second market, separating involuntary churn, or asking what happens if the payment account is limited |

---

## Start with Stripe's own tooling

Stripe ships its own MCP server, CLI and agent skills; the API moves monthly, so
**reach for them first**. This skill owns the seams they do not: which signal is
the payment, what the redirect proves, and where money gets counted twice. Commands
in `references/stripe-agent-toolchain.md`.

## The two ledgers

```
   browser                  your server                    Stripe
      │  choose plan ──────────►│
      │                         │  create checkout session ──►│
      │◄──────── url ───────────│◄──── session + hosted page ─│
      │  pays on Stripe's page ─┼────────────────────────────►│
      │◄─ redirect (proves nothing) ────────────────────────  │
      │                         │◄──── webhook (at-least-once)│
      │                         │  write entitlement          │
      │                         │◄──── webhook (again, later) │
                                 └── nightly: reconcile ─────►│
```

Amounts, tax, invoices, dunning and payment methods are **Stripe's**. Who may
use what, how many seats and what credit was granted are **yours**. The link
between them is ids, and nothing else.

**One home per fact.** Copy an amount out of Stripe into your code and you own
the drift — silently, because checkout sends a price id and Stripe holds the
number. A wrong amount never fails a request; it is only ever shown to
customers. See [`references/price-integrity.md`](references/price-integrity.md).

---

## The client

```ts
let client: Stripe | null = null;

export function getStripe(): Stripe {
  if (!client) {
    const key = process.env.STRIPE_SECRET_KEY;
    if (!key) throw new Error("STRIPE_SECRET_KEY is not set");
    client = new Stripe(key, { apiVersion: "2026-07-29.dahlia", maxNetworkRetries: 2 });
  }
  return client;
}
```

- **Lazy, not module-level.** A `new Stripe(...)` at import time crashes every
  build step that imports the module without a key.
- **Pin `apiVersion`.** Unpinned, response shapes change on Stripe's schedule
  rather than yours. Upgrades are a task (`stripe:upgrade-stripe`), not a
  deploy-day surprise.
- **`maxNetworkRetries`, never a hand-rolled loop.** The SDK generates an
  idempotency key per request, which is the only thing that makes retrying a
  *write* safe. A loop around `subscriptions.create` buys two subscriptions for
  one intent. For deliberate retries, pass your own stable `{ idempotencyKey }`.

---

## Products, prices, two modes

Checkout takes a **price**; your code should speak **product**. Prices are
replaced when you reprice; products are stable.

- **One Product per plan a customer can choose.** Several Prices on one Product
  only for variants of the same plan (monthly vs annual, per currency). Tiers
  sharing a Product make every invoice line read the same name and destroy the
  product-id → plan mapping the rest of your code depends on.
- **Pin price ids in configuration, keep `prices.list({ active: true })` as the
  fallback.** After a reprice a product has two active prices, in an order
  nobody promised.
- **Validation allowlists need ids from both modes.** Your database holds rows
  written in test and rows written in live; a webhook checking "do we sell this"
  against only the current mode rejects real history.
- **`resource_missing` almost always means mode mismatch.** Catch it and say so,
  naming the mode and the key prefix — raw, it reads as "product deleted".

---

## Get-or-create customer is a race

Two tabs, two requests, two customers, and the second silently owns the
subscription the first is charging.

```ts
const customer = await stripe.customers.create({ email, metadata: { userId } });

const { count } = await db.user.updateMany({          // write only if nobody did
  where: { id: userId, stripeCustomerId: null },
  data: { stripeCustomerId: customer.id },
});

if (count === 0) {                                    // lost the race
  await stripe.customers.del(customer.id).catch(log); // delete the orphan
  return (await db.user.findUnique({ where: { id: userId } }))!.stripeCustomerId!;
}
return customer.id;
```

Before creating, retrieve the stored id and treat `resource_missing` or
`deleted: true` as "create a new one" — the normal state after a key rotation.

---

## Checkout session

```ts
const metadata = { userId, productId, quantity: String(qty) };

await stripe.checkout.sessions.create({
  customer: customerId,
  mode: "subscription",
  line_items: [{ price: priceId, quantity: qty }],
  // Never pass payment_method_types — Stripe picks eligible methods from
  // Dashboard settings; hardcoding ['card'] locks out methods that convert.
  metadata,                                 // reaches checkout.session.completed
  subscription_data: { metadata },          // reaches EVERY later subscription event
  success_url: `${origin}/after?session_id={CHECKOUT_SESSION_ID}`,
  cancel_url: `${origin}/plans`,
});
```

1. **Write metadata twice.** Session metadata does not propagate to the
   subscription. Renewal invoices and every `customer.subscription.*` event
   carry the subscription — a year later the session is gone and the only
   `userId` you have is the one in `subscription_data.metadata`.
2. **Validate caller-supplied return URLs against your own origin.** An endpoint
   that passes a body-supplied `successUrl` through is an open redirect wearing
   a payment flow.
3. **Guard duplicates before the money moves**, not after: an active
   subscription to the same product answers 409 with the existing id. A second
   active subscription for one seat is a refund conversation.

`{CHECKOUT_SESSION_ID}` is substituted by Stripe, not rendered by you. On
`2026-03-25.dahlia`+ an `integration_identifier` label lets you compare flows in
the Dashboard.

Three decisions belong to `stripe-best-practices`: **usage-based billing**
(Metronome for anything new; Billing Meters is a low-level primitive), **tax**
(`automatic_tax` collects nothing until a registration exists — enabling it is
not compliance), and **Connect** when money routes to third parties.

---

## The webhook is the payment

```ts
export async function POST(request: Request) {
  const body = await request.text();                    // RAW — not parsed JSON
  const signature = request.headers.get("stripe-signature");
  if (!signature) return json({ error: "missing signature" }, 400);

  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(body, signature, process.env.STRIPE_WEBHOOK_SECRET!);
  } catch {
    return json({ error: "invalid signature" }, 400);    // no detail — it is an oracle
  }

  const claim = await claimEvent(event.id);              // INSERT on a primary key
  if (claim === "duplicate") return json({ received: true, duplicate: true });

  try {
    await handle(event);
  } catch {
    await releaseEventClaim(event.id);                   // let the retry back in
    return json({ error: "handler error" }, 500);
  }
  return json({ received: true });
}
```

- **Raw body.** Re-serializing a parsed body changes bytes and the signature
  fails. Disable auto-parsing for this route.
- **Exempt this path — and only this path — from CSRF and session auth**, by
  exact match: a prefix match over `/api/billing` exempts checkout too, which is
  where the money is.
- **Claim before working.** `SELECT` then `INSERT` is a race; two deliveries
  40 ms apart both pass the read and both credit. Release the claim if
  processing throws, or the retry finds the event "processed" and the work is
  lost forever.
- **Answer honestly.** 200 handled or duplicate, 400 bad signature, 5xx try
  again, 200 for types you do not handle. Never 200 on failure to stop retries —
  that discards a payment quietly.
- **Order inside a handler:** fallible external calls first, then one
  transaction, then side effects that must not run twice (emails, provisioning)
  after it commits.

Per-event detail: [`references/webhook-events.md`](references/webhook-events.md).

---

## The redirect proves a browser

Stripe redirects when the card clears; the webhook lands when it lands. In that
window the user is on your success page and your database knows nothing.

Ship a **verify endpoint** the success page calls: retrieve the session, check
`metadata.userId` equals the caller, check `status === "complete"` and
`payment_status !== "unpaid"`, then perform *exactly the writes the webhook
would* — and let the unique constraint arbitrate. Whoever loses catches the
duplicate-key error and reports success.

The ownership check is security-critical: without it, any authenticated user who
learns a `cs_…` id claims someone else's purchase. This is also the only way
local development works — but it is a safety net, never the primary path. A user
who closes the tab must still get what they paid for.

---

## Renewal: billing_reason decides

`invoice.paid` fires for several different things. Granting product on all of
them is the most expensive mistake in this document.

| `billing_reason` | What it is | Grant? |
|---|---|---|
| `subscription_create` | first invoice | **no** — checkout did it |
| `subscription_cycle` | the renewal | **yes** |
| `subscription_update` | mid-cycle proration | **no** |
| `manual`, `subscription_threshold` | an invoice you or a meter raised | explicitly |

A quantity change emits `subscription_update` immediately. If that path grants,
a user who adds and removes a seat four times has been given four months of
product for four proration invoices.

**Read the period from the subscription item** —
`sub.items.data[0].current_period_start` / `current_period_end`. Recent API
versions moved it; code reading the old top-level fields gets `undefined` and
stores an epoch date, with no error.

Guard the grant with a marker (`lastGrantedPeriodStart`, or an audit row keyed
by invoice id) checked **inside** the same transaction as the grant, so the
webhook and the reconciliation job cannot both grant one period.

---

## `billing_mode` — a one-way choice made at creation

Stripe creates every subscription in one of two billing modes. The choice is made
at `subscriptions.create` (or `subscription_data` on a Checkout session), **cannot
be reversed**, and Stripe recommends **flexible** for new subscriptions.

It is in the body rather than a reference because it changes the arithmetic the
next two sections teach: under flexible mode a credit proration is computed from
the amount **originally debited**, so one change can emit **several** credit
prorations where classic emitted one. Code that takes `[0]` of the proration lines,
or assumes one credit per change, breaks quietly in the refund clawback path — the
one place here where a wrong number is money. The detail is in
`references/subscription-lifecycle.md`; choosing between the modes is a product
decision that `stripe-best-practices` owns.

## Seats and proration

```ts
await stripe.subscriptions.update(subId, {
  items: [{ id: itemId, quantity: newQuantity }],
  proration_behavior: "always_invoice",     // charge the difference now
  payment_behavior: "error_if_incomplete",  // a declined card FAILS this call
});
```

- `proration_behavior`: `always_invoice` bills now, `create_prorations` defers
  to the next invoice, `none` adjusts nothing — the right choice for a *revert*.
- **`error_if_incomplete` on upgrades.** Without it a declined card leaves the
  subscription upgraded and unpaid while your database agrees with the upgrade.
  Catch `StripeCardError` and answer 402.
- **Write ordering:** Stripe first, then your database. If the database write
  fails, revert Stripe with `proration_behavior: "none"` and log a revert
  failure loudly — that is the one state a human must fix. The reverse order
  bills for seats Stripe never sold.
- Cap quantity server-side, floor it at 1. Removing the last seat is a
  cancellation and goes through that path. Reducing below what is in use is a
  business decision: answer 409 with what must be released, and let the user
  choose which.

---

## Cancellation

- **`cancel_at_period_end: true`** is the default — the user keeps what they
  paid for. `status` stays `active`; a separate flag drives the UI.
- **Do the teardown in `customer.subscription.deleted`**, never beside the API
  call, so one path serves your UI, the portal and dunning alike.
- **The portal is a second writer.** Everything a user does there reaches you
  only as a webhook; a billing page that assumes otherwise goes stale in a week.
- On `invoice.payment_failed`, mark `past_due` and notify — do not cancel.
  Stripe's dunning decides the retries and the terminal state; cancelling early
  cancels customers whose next attempt would have cleared.

---

## Refunds arrive cumulative

`charge.amount_refunded` is **the total refunded so far**, not this refund. Two
partial refunds deliver `4000` then `9000`; read as an increment, that claws
back $130 against a $90 charge.

```ts
const totalRefunded = charge.amount_refunded / 100;
const increment = totalRefunded - stored.refundedTotal;
if (increment <= 0) return;                     // replay or reorder

const { count } = await db.purchase.updateMany({
  where: { id: stored.id, refundedTotal: stored.refundedTotal },   // compare-and-swap
  data:  { refundedTotal: totalRefunded },
});
if (count === 0) return;                        // a concurrent delivery won
await clawBack(increment);                      // clamp at zero; log if it would go negative
```

A refund belongs either to a one-off payment (find it by `payment_intent`) or to
a subscription invoice (no purchase row — resolve `charge.invoice` → invoice →
subscription). Handle both, or subscription refunds silently leave the customer
holding the product.

---

## Reconciliation

Webhooks are best-effort and outages are not hypothetical. Run a job that asks
Stripe what is true and repairs the difference:

- list subscriptions with `status: "all"`; create what is missing, update
  status, period, quantity and price where they differ;
- mark local rows canceled when Stripe has no such subscription — **excluding
  rows that were never Stripe's**. Comped, manual and other-provider plans carry
  synthetic ids, and cancelling them is a self-inflicted outage;
- keep the loop **sequential**: each iteration opens a transaction and may call
  an external API, and `Promise.all` exhausts the connection pool under exactly
  the conditions you wrote the job for;
- any grant it performs reuses the webhook's idempotency marker, or a nightly
  job becomes a nightly gift.

The same function is the "Sync now" button on the billing page. Money is minor
units: convert once, at the boundary, and compare in integer cents —
`Math.abs(20.83 - 20.84) > 0.01` is `true` in floating point.

---

## Depending on one provider

One provider for card payments is a single point of failure for revenue, and the
decision belongs to the business rather than to this skill. What the code owes it
is a seam: keep the charge behind an interface, keep the customer id yours rather
than Stripe's, and never let a Stripe object id be the only key to a paying
account. The full argument, the migration shapes and what a second provider costs
are in `references/provider-concentration.md`.

## Local development and the test matrix

Both in `references/testing-and-local-dev.md` — `stripe listen --forward-to`, the
CLI trigger verbs, the test cards and decline codes, and the clock tricks for
renewal and proration. The one thing to know before you get there: the signing
secret `stripe listen` prints is **not** the dashboard's, and using the wrong one
fails verification in a way that reads like a key problem.

## Before you ship

Not a second checklist — every rule below already has a section above, and a rule
with two homes drifts at one of them. These are the four whose failure is money
rather than an error page:

1. **The webhook is the payment.** Never grant on the redirect (§ *The webhook is
   the payment*, § *The redirect proves a browser*).
2. **Verify the signature against the raw body.** A parsed body fails verification
   for a reason that reads like a key problem.
3. **Every handler is idempotent on `event.id`.** Stripe retries, and a retry that
   grants twice is a refund conversation.
4. **Reconcile on a schedule.** A webhook that never arrived leaves a paid customer
   without access, and nothing in the logs says so (§ *Reconciliation*).

The full security checklist lives in `references/stripe-agent-toolchain.md`; every
pitfall it used to list is stated where the rule is, which is the only place it can
be kept true.

