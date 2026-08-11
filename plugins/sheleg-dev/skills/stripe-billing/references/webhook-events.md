# Webhook events — the catalogue and the contract

**Load this when** writing or reviewing the webhook handler: which events to
subscribe to, what each payload actually carries, and the ordering and failure
rules that decide whether a payment becomes an entitlement exactly once.

## Contents

- [The endpoint contract](#the-endpoint-contract)
- [Which events to subscribe to](#which-events-to-subscribe-to)
- [checkout.session.completed](#checkoutsessioncompleted)
- [Asynchronous payment methods](#asynchronous-payment-methods)
- [invoice.paid](#invoicepaid)
- [invoice.payment_failed and dunning](#invoicepayment_failed-and-dunning)
- [customer.subscription.updated](#customersubscriptionupdated)
- [customer.subscription.deleted](#customersubscriptiondeleted)
- [charge.refunded and charge.dispute.created](#chargerefunded-and-chargedisputecreated)
- [Ordering is not guaranteed](#ordering-is-not-guaranteed)
- [Idempotency store](#idempotency-store)
- [What to log](#what-to-log)

## The endpoint contract

| Situation | Status | Why |
|---|---|---|
| handled successfully | 200 | |
| duplicate delivery | 200 | a non-2xx makes Stripe retry forever |
| event type you do not handle | 200 | subscribing to more than you handle is normal |
| missing or invalid signature | 400 | and no detail in the body — it is an oracle |
| webhook secret not configured | 500 | a misconfigured endpoint must not look healthy |
| your idempotency store is down | 503 | you cannot prove this is not a duplicate |
| handler threw | 500 | after releasing the claim, so the retry can work |

Stripe retries with exponential backoff for up to three days, then disables the
endpoint and emails the account. A handler that answers 200 on failure gets no
retry and no email — the payment is simply gone from your side.

Respond fast. Heavy work belongs in a queue: Stripe times out at 30 seconds and
counts the timeout as a failure.

## Which events to subscribe to

A subscription product needs seven; anything else is noise you will have to read
through during an incident.

| Event | Why |
|---|---|
| `checkout.session.completed` | the first grant |
| `checkout.session.async_payment_succeeded` | delayed methods that later clear |
| `checkout.session.async_payment_failed` | delayed methods that later fail |
| `invoice.paid` | renewals, and the proration invoices that must *not* grant |
| `invoice.payment_failed` | dunning starts; mark past due |
| `customer.subscription.updated` | plan change, quantity change, cancel scheduled, status change |
| `customer.subscription.deleted` | the teardown, from any source |
| `charge.refunded` | claw back what was granted |

Add `charge.dispute.created` if disputes are a real risk for your business, and
`customer.subscription.trial_will_end` if you run trials.

## checkout.session.completed

```ts
if (session.payment_status === "unpaid") return;   // an async method: wait for the async event
const userId = session.metadata?.userId;           // set at session creation
if (!userId) { log.error("session without userId"); return; }   // 200, but loudly
```

- `mode` is `"subscription"` or `"payment"` — branch on it before anything else.
- The session's `subscription` field is an **id**, not an object, unless you
  expanded it. Retrieve it to read items, quantity and period.
- Uniqueness key: the subscription id for subscriptions, the payment intent id
  for one-off payments. Put a unique constraint on the column and let the
  database arbitrate — the `SELECT` that precedes the `INSERT` is a race.
- A user that no longer exists is a 200 with an error log, not a 500. Retrying
  will not bring them back.

## Asynchronous payment methods

Bank debits, vouchers and bank transfers complete the session before the money
moves. `payment_status: "unpaid"` at `checkout.session.completed` means the
grant belongs to `async_payment_succeeded`, which may arrive days later — and
`async_payment_failed` means it never will. Both must be handled or the product
is either never granted or granted for a payment that failed.

## invoice.paid

The single most consequential field is `billing_reason`:

| Value | Meaning | Grant? |
|---|---|---|
| `subscription_create` | first invoice for a new subscription | **no** — checkout did it |
| `subscription_cycle` | the renewal | **yes** |
| `subscription_update` | mid-cycle proration (quantity or plan change) | **no** |
| `subscription_threshold` | a usage threshold was crossed | explicitly, if you use them |
| `manual` | an invoice you created | explicitly |

Reading the subscription id off an invoice depends on the API version. On
current versions it hangs off `invoice.parent.subscription_details.subscription`
and may be a string or an object:

```ts
function subscriptionIdOf(invoice: Stripe.Invoice): string | null {
  const ref = invoice.parent?.subscription_details?.subscription;
  if (typeof ref === "string") return ref;
  if (ref && typeof ref === "object") return ref.id;
  return null;                                     // not a subscription invoice
}
```

Period dates live on the **subscription item**
(`sub.items.data[0].current_period_start` / `current_period_end`), not on the
subscription. Code that reads the old top-level fields gets `undefined` and
stores an epoch date — no error, wrong renewal date forever.

Guard the grant with a marker that survives a replay: a `lastGrantedPeriodStart`
compared against the new period start, or an audit row keyed by `invoice.id`.
Check it **inside** the same transaction as the grant.

## invoice.payment_failed and dunning

Mark the subscription `past_due` and tell the user, with a link to the customer
portal — this is the highest-value notification in the whole integration.

Do not cancel anything here. Stripe's dunning settings decide how many retries
happen over how many days and what the terminal state is (`canceled` or
`unpaid`); when it ends you receive `customer.subscription.deleted` or an
`updated` with the final status. Cancelling early cancels customers whose second
attempt would have succeeded.

## customer.subscription.updated

One event covers plan change, quantity change, `cancel_at_period_end` flipping,
trial ending, and status transitions. Diff against your stored row and act only
on what actually changed.

The `previous_attributes` object on the event tells you what changed — but it is
on the **event**, not the subscription object, so a handler typed as
`(sub: Stripe.Subscription)` cannot see it. Pass the event through if you need
it.

For seat and metered products, quantity changes are usually driven by your own
endpoints, which already wrote the new quantity. Make this handler idempotent
against its own writes rather than trying to detect "who did this".

## customer.subscription.deleted

The teardown, and the only place it should live: it fires whether the
cancellation came from your UI, the customer portal, dunning, or an admin in the
Dashboard.

Order matters:

1. external calls that can fail (reclaim balances, disable provisioned
   resources) — outside the transaction, each individually caught;
2. one transaction: reclaim credit, unlink resources, mark canceled;
3. after commit: stop containers, send notifications, emit analytics.

Doing (3) inside the transaction sends "your subscription ended" for a
transaction that then rolls back.

## charge.refunded and charge.dispute.created

`amount_refunded` is **cumulative**. Compute the increment against your stored
total under a compare-and-swap; see the `SKILL.md` section. Resolve the target
two ways: by `payment_intent` for one-off purchases, and by `charge.invoice` →
invoice → subscription for subscription refunds. A refund handler that only
knows the first path silently ignores every subscription refund.

`charge.dispute.created` is money already gone plus a fee. Treat it as a refund
for entitlement purposes and route it to a human — evidence has a deadline.

## Ordering is not guaranteed

Events can arrive out of order, and Stripe's own docs say so. Two consequences:

- **Never derive state from arrival order.** Derive it from the object in the
  payload, or re-retrieve the object and use that.
- **Guard on state, not on time.** "Only apply if the stored period is older"
  beats "apply if this event is newer than the last one I saw", because the
  second one trusts a clock you do not own.

For a subscription whose state you cannot reconstruct from one event, retrieve
the subscription fresh inside the handler. One extra API call is cheaper than a
class of ordering bugs.

## Idempotency store

```sql
CREATE TABLE processed_webhook_events (
  id           TEXT PRIMARY KEY,      -- Stripe's evt_… id
  source       TEXT NOT NULL,         -- 'stripe' — the table serves every provider
  processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ON processed_webhook_events (processed_at);
```

- `claimEvent` = `INSERT`; unique violation means duplicate.
- `releaseEventClaim` = `DELETE`, called only when processing threw.
- Prune older than ~30 days on a schedule. Stripe stops retrying after three
  days, so anything older is dead weight — but do not prune to a window shorter
  than the retry window, or a late retry reprocesses.
- A failure to *claim* (database down) is a 503, never an optimistic "probably
  new".

## What to log

Structured, and enough to answer "what happened to this payment" without the
Dashboard: event id, event type, subscription or payment intent id, the user id
from metadata, the decision taken ("granted", "skipped: subscription_update",
"duplicate"), and the outcome. Never the raw payload — it contains customer
data — and never anything key-shaped.
