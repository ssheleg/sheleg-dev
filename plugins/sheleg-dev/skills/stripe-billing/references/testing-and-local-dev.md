# Testing and local development

**Load this when** setting up local webhooks, writing the first billing test, or
deciding whether an existing suite would actually catch a money defect.

## Contents

- [Local webhooks](#local-webhooks)
- [Triggering events](#triggering-events)
- [The skip-billing branch](#the-skip-billing-branch)
- [Test cards](#test-cards)
- [What to mock](#what-to-mock)
- [A webhook idempotency test](#a-webhook-idempotency-test)
- [Mutation testing — the only proof that counts](#mutation-testing--the-only-proof-that-counts)
- [Asserting on source](#asserting-on-source)
- [Staging verification by hand](#staging-verification-by-hand)
- [Production readiness](#production-readiness)

## Local webhooks

Stripe cannot reach `localhost`. Two ways in, and the first is better:

```bash
stripe listen --forward-to localhost:3000/api/billing/webhook
# ⇒ prints "Ready! Your webhook signing secret is whsec_…"
```

That secret is **not** the one on the Dashboard endpoint. Using the Dashboard's
value against forwarded events produces a signature failure on every delivery,
which looks exactly like a code bug. Put the `stripe listen` value in the local
env and nowhere else.

Filter the firehose when debugging one flow:

```bash
stripe listen --events checkout.session.completed,invoice.paid \
  --forward-to localhost:3000/api/billing/webhook
```

A public tunnel (`cloudflared tunnel --url http://localhost:3000`, `ngrok`) plus
a real Dashboard endpoint is the other path. Use it when you need Stripe's own
retry behaviour, or when the flow involves a hosted redirect back to a public
URL.

## Triggering events

```bash
stripe trigger checkout.session.completed
stripe trigger invoice.payment_failed
stripe trigger customer.subscription.deleted
stripe trigger --help          # the full list of supported fixtures
```

`stripe trigger` creates real objects in test mode, which is its strength and
its limit: the payload is Stripe's fixture, not yours, so `metadata.userId` is
absent and a handler that requires it will bail. For the paths that depend on
your own metadata, drive the handler directly from a saved payload (below).

Re-delivery is the cheapest idempotency check you own: in the Dashboard, find a
delivered event and press **Resend**. The balance must not move, and the log
must say "duplicate".

## The skip-billing branch

```ts
const SKIP_BILLING = process.env.SKIP_BILLING === "true";
if (SKIP_BILLING) {
  if (process.env.NODE_ENV === "production") throw new Error("SKIP_BILLING in production");
  // create a local subscription with an obviously fake id
}
```

- Assert at the **branch**, not only in configuration. A config file is one
  merge away from being wrong; the throw is not.
- Fake ids get a recognisable prefix (`dev_sub_…`) and a predicate
  (`isDevSubscription`) that every Stripe-facing path consults. Without it,
  cancel, portal and reconciliation all call Stripe with an id it has never
  seen.
- Provide the upgrade path: when billing is switched on for an account that
  already holds a fake subscription, replace it with a real one in a transaction
  rather than leaving two.

## Test cards

Full list: the official `stripe:test-cards` skill, or
`docs.stripe.com/testing.md`. The four that matter for billing:

| Card | Behaviour |
|---|---|
| `4242 4242 4242 4242` | succeeds |
| `4000 0000 0000 0341` | attaches fine, **fails on the first charge** — the renewal path |
| `4000 0000 0000 9995` | declined for insufficient funds — the upgrade 402 path |
| `4000 0025 0000 3155` | requires 3DS authentication |

The second one is the one people skip and the one that catches the most: it is
how you see dunning, `past_due` and your own recovery messaging without waiting
a month.

Test clocks (`stripe.testHelpers.testClocks`) advance a customer through
renewals, trial ends and dunning in seconds. They are the only honest way to
test a yearly plan.

## What to mock

Mock at the **SDK boundary**, never at your own handler's. The point of these
tests is that your handler does the right thing with a payload Stripe would
actually send.

```ts
vi.mock("@/lib/stripe", () => ({
  getStripe: () => ({
    webhooks: { constructEvent: () => savedEventFixture },   // signature already verified
    subscriptions: { retrieve: vi.fn().mockResolvedValue(savedSubscription) },
  }),
}));
```

Save real payloads: run the flow once against test mode, copy the event JSON out
of the Dashboard, and commit it as a fixture. Hand-written payloads drift from
reality in exactly the fields that matter — `parent.subscription_details`, the
item-level period, `billing_reason`.

Make the database mock **stateful** where the test is about state. An
idempotency test against a mock that returns "not found" every time proves
nothing:

```ts
const seen = new Set<string>();
processedWebhookEvent: {
  create: async ({ data }) => {
    if (seen.has(data.id)) throw p2002();     // reproduce the unique constraint
    seen.add(data.id); return data;
  },
}
```

## A webhook idempotency test

```ts
it("credits exactly once when the same event is delivered twice", async () => {
  const req = () => new Request("http://x/api/billing/webhook", {
    method: "POST", headers: { "stripe-signature": "t=1,v1=deadbeef" }, body: "{}",
  });

  const first  = await POST(req());
  const second = await POST(req());

  expect(await first.json()).toMatchObject({ received: true });
  expect(await second.json()).toMatchObject({ duplicate: true });
  expect(creditSpy).toHaveBeenCalledTimes(1);        // ← the assertion that matters
});
```

Drive the **real** exported handler. A test that calls a private helper proves
the helper works and says nothing about the route Stripe posts to.

## Mutation testing — the only proof that counts

For every guard, delete it and re-run. A test that still passes is decoration.

| Delete this | A real test fails with |
|---|---|
| the ownership check in the verify route | "session does not belong to user" |
| `if (billing_reason !== "subscription_cycle") return` | a grant on a proration invoice |
| the claim-before-work call | two credits for one event |
| `releaseEventClaim` in the catch | the retry finds it "processed" and nothing happens |
| the cumulative subtraction in the refund path | a refund larger than the charge |
| `payment_behavior: "error_if_incomplete"` | an upgrade recorded despite a decline |
| the non-Stripe guard in reconciliation | comped subscriptions cancelled |

Do this once per guard, write down what failed, and you have a suite you can
believe. Skip it and you have a green build.

## Asserting on source

Some invariants are one line whose *absence* is the whole defect, and no runtime
assertion is cheaper than reading the file:

```ts
const SRC = readFileSync("src/lib/stripe.ts", "utf8");
it("constructs the client with retries and a pinned version", () => {
  expect(SRC).toMatch(/maxNetworkRetries:\s*[1-3]\b/);
  expect(SRC).toMatch(/apiVersion:\s*"[\d-]+\.\w+"/);
});
```

Use this sparingly — it is a ratchet against regression, not a substitute for
behavioural tests — but it is the right tool for "this option must never be
removed".

## Staging verification by hand

Before the first real charge, on staging, with a real key in test mode:

- [ ] complete a checkout; the subscription appears locally within seconds
- [ ] in the Dashboard, **Resend** that event; nothing changes and the log says duplicate
- [ ] cancel from the **customer portal**; local state follows
- [ ] pay a renewal with the `…0341` card; `past_due` is set and the user is told
- [ ] refund half a charge in the Dashboard; the clawback is half, not all
- [ ] refund the other half; the total clawed back equals the charge, not more
- [ ] add a seat with the `…9995` card; a 402, and nothing changed locally
- [ ] stop the app, deliver an event, restart; Stripe's retry lands it
- [ ] point the app at an empty database and run reconciliation; nothing is cancelled

## Production readiness

- [ ] webhook endpoint registered for live mode, subscribed to exactly the events you handle
- [ ] `STRIPE_WEBHOOK_SECRET` is the **live endpoint's** secret, not `stripe listen`'s
- [ ] the live key is a restricted key with only the permissions the app uses
- [ ] `STRIPE_PRODUCT_MODE` and the key are both live, and something asserts they agree
- [ ] the price conformance job is scheduled and its findings reach a human
- [ ] the reconciliation job is scheduled
- [ ] alerts exist for: signature failures, handler 5xx, endpoint disabled by Stripe
- [ ] a runbook names who to page when Stripe and the database disagree
