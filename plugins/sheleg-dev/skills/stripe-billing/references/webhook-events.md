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

**Proved, not asserted.** `fixtures/checkout-session-completed-paid.json` is the positive
control: `paid-session-grants-once` fails a handler that answers 200 and writes nothing. It
exists because without it, a handler refusing *every* session would satisfy
`unpaid-session-grants-nothing` and this pack would teach the opposite defect.

## Asynchronous payment methods

Bank debits, vouchers and bank transfers complete the session before the money
moves. `payment_status: "unpaid"` at `checkout.session.completed` means the
grant belongs to `async_payment_succeeded`, which may arrive days later — and
`async_payment_failed` means it never will. Both must be handled or the product
is either never granted or granted for a payment that failed.

**Proved, not asserted.** `fixtures/checkout-session-completed-async-unpaid.json` and
`fixtures/checkout-session-async-payment-failed.json` through
`fixtures/assert-money-invariants.mjs`: `unpaid-session-grants-nothing` fails any handler
that grants on `checkout.session.completed` without reading `payment_status`.

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

**Proved, not asserted.** Three assertions in `fixtures/assert-money-invariants.mjs` cover
this table: `renewal-grants-exactly-once` against
`fixtures/invoice-paid-subscription-cycle.json`,
`proration-invoice-grants-nothing` against
`fixtures/invoice-paid-subscription-update-proration.json` — whose line period starts at the
change date, so the marker lets it through and only `billing_reason` stops it — and
`reconciliation-does-not-regrant`, which drives the nightly repair rather than a webhook and
is the only fixture the event claim cannot save.

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
total under a compare-and-swap; see the `SKILL.md` section. **Proved, not asserted:**
`fixtures/charge-refunded-partial.json` then `fixtures/charge-refunded-remainder.json`
deliver `4000` and then `9000` against a `9000` charge, and `refund-total-is-cumulative`
fails a handler that reads either as an increment. Resolve the target
two ways: by `payment_intent` for one-off purchases, and by `charge.invoice` →
invoice → subscription for subscription refunds. A refund handler that only
knows the first path silently ignores every subscription refund.

`charge.dispute.created` is money already gone plus a fee. Treat it as a refund
for entitlement purposes and route it to a human — evidence has a deadline.

"Route it to a human" is a precondition in this pack rather than a sentence: the
`PreToolUse` gate at `plugins/sheleg-dev/hooks/money-gate.js` refuses
`stripe refunds create`, `stripe disputes close` and a POST to `…/v1/refunds` unless the
authorised person has signed that category off for the session. It stops an agent, not
your handler — the handler still needs the queue. The pack's `README.md` carries the
categories and how one is authorised.

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

**Proved, not asserted.** `fixtures/invoice-paid-subscription-cycle-next-period.json`
delivered *before* `fixtures/invoice-paid-subscription-cycle.json`:
`out-of-order-pair-does-not-rewind-state` requires both periods to be granted and the
mirrored row to still hold February. The two events carry different ids, so idempotency
cannot mask the defect — which is the only reason this fixture measures the ordering rule.

## Idempotency store

A claim records **receipt**, and only completion records **completion**. A row that
cannot tell the two apart turns every crash between them into a swallowed payment: the
retry is told "duplicate" about work that never finished. So the row carries a state —
`'processing'` on claim, `'completed'` exactly once, in the same transaction as the
grant — and a claim on an existing row answers by that state, never by mere existence.

```sql
CREATE TABLE processed_webhook_events (
  id           TEXT PRIMARY KEY,      -- Stripe's evt_… id
  source       TEXT NOT NULL,         -- 'stripe' — the table serves every provider
  state        TEXT NOT NULL DEFAULT 'processing',  -- 'processing' → 'completed', nothing else
  claimed_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ            -- set once, in the transaction that granted
);
CREATE INDEX ON processed_webhook_events (state, claimed_at);
```

- `claimEvent` = `INSERT`; a unique violation is not yet an answer — read the row's
  state. `'completed'` means duplicate: answer 200 and stop. `'processing'` younger
  than the claim expiry means another worker is (or may still be) on it: answer 5xx so
  this delivery retries too. `'processing'` older than the expiry belonged to a worker
  that died between receipt and completion — take it over with an `UPDATE … SET
  claimed_at = now() WHERE id = … AND state = 'processing' AND claimed_at < now() -
  <expiry>`, one row updated means the takeover is yours, zero means somebody beat you.
- `completeEvent` = `UPDATE … SET state = 'completed', completed_at = now()` — inside
  the transaction that writes the grant, so a row that says completed is one whose
  business write committed.
- `releaseEventClaim` = `DELETE … WHERE state = 'processing'`, called only when
  processing threw and the route answered 5xx. A crashed worker never reaches this
  line — that is what the expiry exists for.
- The claim expiry is comfortably longer than your slowest handler run (say, twice the
  route timeout). Too short reprocesses live work; there is no "too long" that loses an
  event, only one that delays its recovery.
- Prune completed rows older than ~30 days on a schedule. Stripe stops retrying after three
  days, so anything older is dead weight — but do not prune to a window shorter
  than the retry window, or a late retry reprocesses.
- A failure to *claim* (database down) is a 503, never an optimistic "probably
  new".

**Proved, not asserted.** `fixtures/invoice-paid-subscription-cycle-redelivery.json` carries
the same `evt_` as the cycle invoice. `sequential-redelivery-grants-once` requires the second
delivery to answer `duplicate` and the renewal notice and the conversion to fire once;
`concurrent-redelivery-grants-once` delivers both **at the same time**, which is the fixture
that separates this claim from the per-period marker, because the marker reads before it
writes and the claim does not.

## One transaction, then the outbox

The business application is ONE transaction: the entitlement, the business
dedup marker (the per-period grant row), the completion mark and the **outbox
rows** for every side effect commit together, or none of them exist. A crash
before the commit applies nothing — the claim still says `processing`, and the
retry runs the whole application again. A crash after the commit changes
nothing either: the work is durable, the retry reads `completed`, and the side
effects wait in the outbox.

The outbox delivers **at least once**, so the consumer carries its **own
dedup key** — event id + effect kind — remembered across rows. A redelivered
outbox row must send nothing twice: the email provider and the ad platform do
not participate in your transaction, and the consumer key is the only thing
standing between a queue hiccup and a second "your renewal" email with a
double-counted conversion.

**The mirror is state; the ledger is history — and conflicts only delay.**
The subscription mirror (current period, status, quantity) lives apart from
the grant ledger: the mirror moves FORWARD only (a late-arriving older event
never rewinds a confirmed period — the ordering rule), while the ledger keeps
one row per granted period forever. And a database serialization conflict
retries inside the same claim, bounded (three attempts in the reference);
past the bound the route answers 5xx with the claim released, so the
redelivery brings the renewal back — a conflict may delay a grant, never
lose it, and a swallowed conflict answered 200 is a renewal that silently
never happened.

**The crash between receipt and completion is proved too.**
`crash-after-receipt-is-retryable` kills the worker after the claim and requires the
retry arriving past the claim expiry to be let in and to grant;
`in-flight-claim-answers-retry-later` requires the retry arriving *inside* the window
to be told 5xx come back — not "duplicate", which is an answer about a completed row;
`completion-is-recorded-with-the-grant` requires the claim row to leave `'processing'`
the moment the grant commits; and `duplicate-of-completed-never-regrants` ages a
completed row past the expiry and requires the late retry to answer duplicate and
grant nothing. All four run against `fixtures/reference-handler.mjs`.

**And the transaction boundary is proved.** `transaction-rolls-back-whole`
crashes inside the transaction and requires no grant, no marker, no outbox row
and no completion to survive; `crash-before-commit-applies-nothing` lets the
retry in through the expired claim and requires everything applied exactly
once; `committed-retry-sends-once` redelivers every outbox row and requires
the notice and the conversion to fire once — the consumer key at work.
`serialization-conflict-does-not-lose-the-renewal` injects a conflict and
requires the retried transaction to land the grant;
`exhausted-retries-answer-5xx-and-the-redelivery-lands` exhausts the bound
and requires an honest 5xx followed by exactly one grant on redelivery.

## What to log

Structured, and enough to answer "what happened to this payment" without the
Dashboard: event id, event type, subscription or payment intent id, the user id
from metadata, the decision taken ("granted", "skipped: subscription_update",
"duplicate"), and the outcome. Never the raw payload — it contains customer
data — and never anything key-shaped.
