---
name: crypto-payments
description: >-
  Use when adding or auditing crypto checkout, crypto top-up, or payment webhooks — where a
  payer sends the wrong amount, a webhook arrives more than once, and the rate moves between
  quote and transfer. Covers invoice lifecycle and status mapping, webhook signature
  verification and the JSON-escaping trap, idempotent processing, IP allowlisting behind a
  proxy, CSRF exemption for callback routes, the conversion buffer, reconciliation fields,
  credit waterfalls, refund and AML-hold states, local development with a tunnel and signed mock
  callbacks, a test matrix and a security checklist. Triggers - "crypto payment", "crypto
  checkout", "pay with crypto", "USDT payment", "TRC20", "payment webhook", "IPN", "webhook
  signature", "underpayment", "Heleket", "NOWPayments", "приём криптоплатежей", "оплата
  криптой", "вебхук платежа", "недоплата". Not for card billing — use stripe-billing.
---

# Crypto payments

A card charge either succeeds or fails, and the amount is the amount. A crypto
payment is a **request that someone may partially satisfy, over-satisfy, satisfy
late, or satisfy after the price moved**. Almost every defect in a crypto
checkout comes from writing card-shaped code and meeting one of those cases in
production.

This skill is provider-neutral. Concrete request/response shapes for one gateway
live in [`references/heleket-provider.md`](references/heleket-provider.md);
the invariants below hold for Coinbase Commerce, NOWPayments, BTCPay, Heleket
and anything else that issues an invoice and calls you back.

> **Choosing a provider is a business and compliance decision, not a technical
> one.** Crypto payment processors differ sharply in regulatory standing —
> licensing, AML programme, sanctions exposure — and that standing changes.
> Check the current position of any processor before you route customer money
> through it, and re-check it periodically. This skill tells you how to
> integrate one correctly; it does not tell you which one to trust.

## Contents

- [The lifecycle, and where money goes missing](#the-lifecycle-and-where-money-goes-missing)
- [Status mapping — and finality](#status-mapping--and-finality)
- [Webhook signature verification](#webhook-signature-verification)
- [Idempotent webhook processing](#idempotent-webhook-processing)
- [IP allowlisting behind a proxy](#ip-allowlisting-behind-a-proxy)
- [CSRF exemption for callback routes](#csrf-exemption-for-callback-routes)
- [The conversion buffer](#the-conversion-buffer)
- [Reconciliation fields](#reconciliation-fields)
- [Crediting: the amount waterfall](#crediting-the-amount-waterfall)
- [Refunds and AML holds](#refunds-and-aml-holds)
- [Local development](#local-development)
- [Test matrix](#test-matrix)
- [Security checklist](#security-checklist)
- [Common pitfalls](#common-pitfalls)

---

## The lifecycle, and where money goes missing

```
your app                gateway                 blockchain
   │  create invoice ─────►│
   │◄──── invoice id, address, amount, expiry
   │                       │
   │   (user pays) ────────┼──────────────────────►│
   │                       │◄── confirmations ─────│
   │◄──── webhook: status change (MAY REPEAT)
   │  credit the user      │
   │◄──── webhook: status change (again, later)
```

Three facts that shape every design decision:

1. **The callback is at-least-once.** Providers retry until you 200. A handler
   that credits on every delivery credits three times.
2. **The paid amount is not the invoiced amount.** Underpayment, overpayment and
   "paid a different currency than quoted" are normal states, not errors.
3. **Status is not monotonic in the way you expect.** A payment can go
   `pending → paid → refund_process → refund_paid`, or sit in an AML hold for
   days. Model the terminal set explicitly.

**Never derive entitlement from the redirect back to your site.** The user's
browser returning to `/success` proves the user has a browser. Credit on the
webhook, or on a server-side status poll — never on a client-side landing.

---

## Status mapping — and finality

Every gateway has its own vocabulary. Map it to **your** states once, in one
function, and define the terminal set explicitly:

```ts
const FINAL_STATUSES = ['PAID', 'FAILED', 'REFUNDED', 'EXPIRED'] as const;

function mapStatus(providerStatus: string): PaymentStatus {
  switch (providerStatus) {
    case 'paid':
    case 'paid_over':        return 'PAID';       // over-payment still pays
    case 'wrong_amount':     return 'UNDERPAID';  // partial — DO NOT credit in full
    case 'confirm_check':    return 'CONFIRMING'; // seen, not yet confirmed
    case 'cancel':
    case 'fail':
    case 'system_fail':      return 'FAILED';
    case 'refund_process':   return 'REFUNDING';
    case 'refund_paid':      return 'REFUNDED';
    case 'locked':           return 'AML_HOLD';   // compliance review, may take days
    default:                 return 'PENDING';
  }
}
```

`paid_over` is the one people get wrong in both directions: treating it as a
failure loses a paying customer, treating it as exactly-paid quietly gives away
the excess. Credit the **received** amount, not the invoiced one — see the
waterfall below.

---

## Webhook signature verification

The callback is an unauthenticated public endpoint until you prove otherwise.

```ts
import { createHash, timingSafeEqual } from 'node:crypto';

function sign(payload: unknown, apiKey: string): string {
  const json = JSON.stringify(payload);
  return createHash('md5')
    .update(Buffer.from(json).toString('base64') + apiKey)
    .digest('hex');
}

function verify(body: Record<string, unknown>, apiKey: string): boolean {
  const { sign: given, ...rest } = body;          // signature is never part of the signed payload
  if (typeof given !== 'string') return false;
  const expected = sign(rest, apiKey);
  const a = Buffer.from(expected, 'utf8');
  const b = Buffer.from(given, 'utf8');
  return a.length === b.length && timingSafeEqual(a, b);   // length check FIRST — timingSafeEqual throws on mismatch
}
```

Three rules, each of which has burned a real integration:

- **Compare in constant time.** `===` on a signature leaks it a byte at a time.
  And check lengths first: `timingSafeEqual` *throws* on unequal buffers, so a
  naive call turns a forged signature into a 500 instead of a 403.
- **Sign exactly what the provider signed.** Re-serializing the parsed body can
  change it. Keep the raw body if the framework lets you.
- **Mind the escaping.** Some gateways (PHP-based ones especially) sign JSON
  produced by `json_encode`, which escapes forward slashes as `\/` and
  non-ASCII as `\uXXXX`. `JSON.stringify` does neither. If your signature is
  correct for payloads with no URL and wrong for payloads containing one, this
  is why. **Try both encodings and accept either** — the alternative is
  rejecting real callbacks:

  ```ts
  const candidates = [json, json.replace(/\//g, '\\/')];
  return candidates.some((c) => timingSafeCompare(md5(b64(c) + key), given));
  ```

Verify the signature **before** parsing anything into your domain, and return
403 without detail on failure. A verbose error is an oracle.

---

## Idempotent webhook processing

Do not read-then-write. Make the database refuse the second delivery:

```ts
const { count } = await db.payment.updateMany({
  where: {
    invoiceId,
    status: { notIn: FINAL_STATUSES },   // ← the guard: a settled payment cannot re-settle
  },
  data: { status: mapped, paidAmount, txid, network, settledAt: new Date() },
});

if (count === 0) {
  // already final: a retry, or a late duplicate. Acknowledge and do nothing.
  return res.status(200).json({ ok: true, duplicate: true });
}

await creditUser(...);   // only reachable once per invoice
```

`updateMany` + a status guard is a compare-and-swap. `findFirst` followed by
`update` is a race, and the two deliveries that arrive 40ms apart will both pass
the read.

**Always return 200 for a duplicate.** A 409 makes the provider retry forever.

---

## IP allowlisting behind a proxy

Signature verification is the real gate; the allowlist is defence in depth and
cheap. It is also the single most common cause of "webhooks stopped working
after we moved to a load balancer".

```ts
function callerIp(req): string | null {
  // Trust ONLY the hop your own infrastructure appends.
  const xff = req.headers['x-forwarded-for'];
  if (typeof xff === 'string') {
    const hops = xff.split(',').map((s) => s.trim());
    return hops[hops.length - TRUSTED_PROXY_COUNT] ?? null;
  }
  return req.socket.remoteAddress ?? null;
}
```

Taking `xff[0]` trusts a header the client controls — anyone can claim to be the
gateway. Count from the right by the number of proxies you actually run, and
keep that number in configuration, because it changes when infrastructure does.

Allowlist the provider's published callback IPs, log a rejection with the
observed IP, and **never** fall back to "allow if the header is missing".

---

## CSRF exemption for callback routes

A gateway cannot present your CSRF token. Exempt the callback path explicitly
and narrowly:

```ts
// middleware.ts (Next.js)
export const config = { matcher: ['/((?!api/payments/webhook).*)'] };
```

Exempt the **one** path, by exact match, and make it the only route in your app
that skips CSRF. A prefix match on `/api/payments` exempts the checkout endpoint
too, which is where the money is.

---

## The conversion buffer

You quote in USD. The user pays in a coin whose rate moves between your quote
and their transfer. Without a margin, a rate move of a fraction of a percent
turns a full payment into `wrong_amount`, and now you are handling a partial
payment for no reason.

```ts
const BUFFER = 0.01;                       // 1%
const invoiceAmount = round(amountUsd * (1 + BUFFER), 2);
```

Two rules:

- **Buffer the invoice, credit the intent.** Charge the buffered amount, credit
  the user for what they meant to buy. The buffer covers drift; it is not
  revenue and should not appear in what the user is told they bought.
- **Store both numbers.** `amountUsd` (intent) and `invoicedAmount` (what you
  asked for) are different, and support questions are unanswerable without both.

Pick the buffer from observed rate volatility for the coins you accept, not from
this document.

---

## Reconciliation fields

Six months later someone asks "did this payment actually arrive, and how much
did we net". Store enough to answer it **at webhook time** — the gateway's
retention is not your retention:

| Field | Why |
|---|---|
| `merchantAmount` | what you net after the gateway's commission — never equals the invoice |
| `paidAmount` + `payerCurrency` | what actually arrived, in what coin |
| `paidAmountUsd` | the gateway's own USD valuation at settlement |
| `commission` | so net vs gross is arithmetic, not archaeology |
| `txid` | the only link to the chain; without it a dispute is unresolvable |
| `network` | TRC20 vs ERC20 vs BEP20 — same coin, different chain, different fee |
| `from` | payer address, for AML questions you will eventually be asked |

Write them on the settling webhook, in the same update that flips the status.

---

## Crediting: the amount waterfall

What do you credit when the numbers disagree? Prefer the most authoritative,
fall back in a fixed order, and log which one won:

```ts
const credit = payment.paidAmountUsd     // gateway's valuation of what arrived
            ?? payment.tokenAmount        // what the plan says this purchase grants
            ?? payment.amountUsd;         // the original intent — last resort
```

The order matters: valuing an over-payment at the intent silently keeps the
excess, and valuing an under-payment at the intent gives away product. Write an
audit row naming the source, or the first disputed balance is unprovable.

---

## Refunds and AML holds

Crypto has no chargeback, which people mistake for "no reversals".

- **Refunds are a multi-step state**, not an event: `refund_process` →
  `refund_paid` | `refund_fail`. A user is not refunded when you asked for it.
- **AML holds are open-ended.** A `locked` payment may resolve in hours or
  never. Surface it honestly ("under review by the payment provider"), do not
  credit, do not auto-cancel, and do not retry the invoice — a second invoice
  during a hold is how you end up with two payments and one product.
- **Never auto-refund from the webhook.** Route holds and refunds to a queue a
  human can see.

---

## Local development

Two paths, and you want both:

**Skip the gateway.** A `SKIP_BILLING=true` branch that credits immediately and
logs loudly. Everyone building a feature that merely *touches* checkout should
use this. Make it impossible in production: assert `NODE_ENV !== 'production'`
at the branch, not just in config.

**Real gateway, tunnelled callback.** Callbacks cannot reach `localhost`:

```bash
cloudflared tunnel --url http://localhost:3000
# → https://random-name.trycloudflare.com  →  set as the callback base URL, restart the app
```

Then keep a **signed mock callback** in your test tooling — a script that builds
a real payload, signs it with the dev key and POSTs it. This is what makes the
sad paths (`wrong_amount`, `refund_fail`, `locked`) testable at all; you cannot
ask a gateway to underpay you on demand.

---

## Test matrix

Cover these, and plant a defect against each before believing the green:

| Case | What it catches |
|---|---|
| valid signature | the happy path |
| tampered signature | constant-time compare, 403 not 500 |
| signature over a payload containing a URL | the escaping trap |
| duplicate delivery of a settling status | idempotency guard |
| `paid_over` | crediting the received amount, not the invoiced |
| `wrong_amount` | no full credit on a partial payment |
| out-of-order delivery (final, then earlier) | the `notIn` guard, not timestamps |
| callback from a non-allowlisted IP | proxy-aware extraction |
| `refund_process` then `refund_fail` | refund is a state machine |
| `locked` | no credit, no auto-cancel |

---

## Security checklist

- [ ] Signature verified before any domain parsing; constant-time compare; lengths checked first
- [ ] Both JSON escapings accepted, or the raw body signed
- [ ] Webhook idempotent via a compare-and-swap on a non-final status
- [ ] Duplicates answered 200, never 409
- [ ] IP allowlist counts proxy hops from the right; no allow-on-missing-header
- [ ] CSRF exempted for exactly one path, by exact match
- [ ] Entitlement never granted from a client-side redirect
- [ ] API key and merchant id from environment, never in the repository
- [ ] Callback URL is HTTPS in every environment that is not a local tunnel
- [ ] `SKIP_BILLING` asserted impossible in production
- [ ] Reconciliation fields written at settlement time
- [ ] Refunds and AML holds routed to a human, never automated from the webhook

---

## Common pitfalls

| Symptom | Cause |
|---|---|
| Signature valid for some payloads, invalid for others | forward-slash / unicode escaping difference |
| 500s on forged callbacks | `timingSafeEqual` on unequal buffers throws |
| User credited two or three times | read-then-write instead of compare-and-swap |
| Provider retries forever | duplicate answered with 409 |
| Webhooks died after an infra change | `x-forwarded-for` hop counting |
| "Paid" users with no product | credited from the browser redirect |
| Half the payments land as `wrong_amount` | no conversion buffer |
| Cannot answer "how much did we net" | commission and `merchantAmount` never stored |
