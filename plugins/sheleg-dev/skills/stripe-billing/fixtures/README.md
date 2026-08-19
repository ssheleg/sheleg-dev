# Money fixtures and the assertion pack

**Copy this whole directory into your repository.** It is the executable half of what
`SKILL.md` and `references/webhook-events.md` state in prose: nine real Stripe event
bodies, twelve invariants a correct webhook handler must hold — 45 assertions between
them — and a self-test that breaks the handler one rule at a time so you can watch each
assertion fail on its own.

Two commands, no dependencies, no network, no key:

```bash
node assert-money-invariants.mjs              # 12 invariants / 45 assertions
node assert-money-invariants.mjs --self-test  # break one rule at a time; EACH ASSERTION must go red
```

Point it at **your** handler by replacing the two imports at the top of
`assert-money-invariants.mjs`. The assertions do not change — that is the point of shipping
them rather than describing them.

## Contents

- [The fixtures](#the-fixtures)
- [The assertions](#the-assertions)
- [What each mutant deletes](#what-each-mutant-deletes)
- [What masks what](#what-masks-what)
- [Placeholders](#placeholders)

## The fixtures

Every file is a webhook event body shaped the way Stripe sends it on
`2026-07-29.dahlia` — the period on the invoice **line**, the subscription id under
`parent.subscription_details`, `amount_refunded` cumulative, minor units throughout.

| File | What it is | Why it exists |
|---|---|---|
| `invoice-paid-subscription-cycle.json` | the January renewal, `billing_reason: subscription_cycle` | the one `invoice.paid` that **must** grant |
| `invoice-paid-subscription-cycle-redelivery.json` | the same `evt_` again, `pending_webhooks` 0 | Stripe re-delivers the same body; only the id matters |
| `invoice-paid-subscription-update-proration.json` | a mid-cycle seat change, `billing_reason: subscription_update`, two proration lines | its line period starts at the **change date**, later than the granted cycle — so a per-period marker lets it through and only `billing_reason` stops it |
| `invoice-paid-subscription-cycle-next-period.json` | the February renewal | delivered *before* January, it is the out-of-order pair |
| `charge-refunded-partial.json` | $40 refunded of a $90 charge, `amount_refunded: 4000` | step one of the cumulative refund |
| `charge-refunded-remainder.json` | the other $50, `amount_refunded: 9000` | read as an increment this claws back $130 against a $90 charge |
| `checkout-session-completed-async-unpaid.json` | a bank-debit session, `payment_status: "unpaid"` | the session completed and the money has not moved |
| `checkout-session-async-payment-failed.json` | days later: it never cleared | the redirect proved a browser and nothing else |
| `checkout-session-completed-paid.json` | a card session that did clear | the positive control: without it, a handler refusing every session would pass the two above |

The refund pair resolves to a **purchase row**, not a Stripe object: a $90 credit pack with
`refundedTotal: 0`, seeded by the assertion pack because it is your database's, not
Stripe's.

## The assertions

Run `node assert-money-invariants.mjs` and each line names the invariant it holds:

| Assertion | Fixtures | What a wrong handler does |
|---|---|---|
| `renewal-grants-exactly-once` | cycle | grants nothing, and a paying customer has no access |
| `proration-invoice-grants-nothing` | cycle + proration | gives a month of product for a $40 proration invoice |
| `sequential-redelivery-grants-once` | cycle + redelivery | answers `received` twice and sends the renewal notice and the server-side conversion twice |
| `concurrent-redelivery-grants-once` | cycle + redelivery, in flight together | both deliveries pass the marker's `SELECT` and both credit |
| `sequential-redelivery-grants-once-by-count-alone` | cycle + redelivery | *nothing* — kept because that is the finding; see below |
| `reconciliation-does-not-regrant` | cycle | the nightly repair grants a period the webhook already granted |
| `out-of-order-pair-does-not-rewind-state` | February then January | stores the older period, so the renewal date points at a period that ended |
| `refund-total-is-cumulative` | both refunds | claws back $130 against a $90 charge |
| `duplicate-refund-claws-back-once` | one refund, twice | *nothing* — the second masked pair; see below |
| `unpaid-session-grants-nothing` | unpaid + failed | grants the product and reports a purchase for a charge that failed |
| `paid-session-grants-once` | `checkout-session-completed-paid.json` | answers 200 and writes nothing — the positive control, without which refusing every session would pass the row above |
| `conversion-id-survives-the-session` | cycle | generates its own conversion id, and the browser event never deduplicates against it |

## What each mutant deletes

`--self-test` removes exactly one rule at a time from `reference-handler.mjs`. Each one is
a line a generated handler routinely omits:

| Rule | The code it removes | The generated handler that ships without it |
|---|---|---|
| `claim` | `if (!store.claimEvent(event.id)) return duplicate` | reads the processed table, then writes it — two deliveries 40 ms apart both pass the read |
| `billing-reason` | `if (invoice.billing_reason !== 'subscription_cycle') return` | handles `invoice.paid` as "a payment arrived" |
| `grant-marker` | `if (granted.has(period.start)) return` | grants whenever an event says paid, including from the reconciliation job |
| `ordering` | `if (period.start > mirror.periodStart)` around the mirror write | writes whatever arrived last |
| `cumulative-refund` | the stored total, the increment and the compare-and-swap | claws back `amount_refunded` |
| `async-gate` | `if (session.payment_status === 'unpaid') return` | grants on `checkout.session.completed`, full stop |
| `conversion-id-from-metadata` | reading `conversionEventId` out of the subscription metadata | generates an id at emission time |
| `grant-on-renewal` | the grant itself | treats `invoice.paid` as information |
| `grant-on-checkout` | the first grant | answers 200 to `checkout.session.completed` and writes nothing |

## What masks what

The whole reason `--self-test` prints a matrix: **when two rules can both explain a passing
fixture, neither is tested.** Two pairs in this pack do exactly that, and the fixtures that
separate them are here because of it rather than by design.

- **the event claim and the per-period grant marker.** A redelivery judged by the grant
  count alone is refused by either one. `sequential-redelivery-grants-once-by-count-alone`
  is the fixture that measures it: no *single* removed rule turns it red, only
  `claim`+`grant-marker` together. The claim's own discriminating fixture is therefore the
  **concurrent** delivery — the marker reads before it writes, and a read is a round trip —
  and the marker's is the **reconciliation** entry point, which has no event id at all.
- **the event claim and the refund compare-and-swap.** A duplicate `charge.refunded` is
  refused by the claim, and by `increment <= 0` without it.
  `duplicate-refund-claws-back-once` records that, and the cumulative pair with two
  *distinct* event ids is what actually tests the arithmetic.

`--self-test` fails if any rule has no fixture that isolates it, so this stays true.

## Placeholders

Every id spells `PLACEHOLDER`: `sub_PLACEHOLDER_alice`, `ch_PLACEHOLDER_creditpack`,
`cus_PLACEHOLDER_bob`. There is no key, token, signing secret or real customer id anywhere
in this directory — signature verification happens before any of this and is
`SKILL.md`'s subject, not these fixtures'. The email is `placeholder@example.invalid` and
the one 64-hex string is its SHA-256.
