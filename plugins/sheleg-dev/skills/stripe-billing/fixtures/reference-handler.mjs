// A webhook handler that satisfies every money invariant this skill states, and the
// same handler with one rule removed at a time.
//
// It is deliberately tiny and dependency-free: an in-memory store standing in for your
// database, and the seven decisions the SKILL.md and `references/webhook-events.md`
// require. Point `assert-money-invariants.mjs` at YOUR handler instead and the
// assertions do not change — that is the whole purpose of shipping it.
//
// Two properties of the store matter, and both model a real database rather than a
// convenient one:
//
//   * `claimEvent` is ATOMIC. It is an `INSERT` on a primary key: a read and a write
//     with nothing between them. That is why a claim survives two deliveries in flight.
//   * every OTHER read awaits. A `SELECT` is a network round trip, so a read-then-check
//     -then-write is a race — which is exactly why the claim cannot be replaced by the
//     per-period grant marker, however well the marker handles a sequential replay.
//
// `without: ['claim']` and friends are not toy switches. Each one deletes the lines a
// generated handler routinely omits; `fixtures/README.md` shows the code each flag
// removes. Nothing here reaches the network, the filesystem or the clock.

export const RULES = Object.freeze([
  'claim',
  'billing-reason',
  'grant-marker',
  'ordering',
  'cumulative-refund',
  'async-gate',
  'conversion-id-from-metadata',
  // The baseline, and the broadest mutant: a handler that treats `invoice.paid` as
  // information and grants nothing. It breaks every grant assertion at once, which is the
  // point — without it, a handler that does nothing would satisfy every invariant about
  // NOT doing something twice.
  'grant-on-renewal',
  // The same baseline for the first grant: a handler that answers 200 to
  // `checkout.session.completed` and writes nothing. Without it, refusing every session
  // would satisfy every assertion about not granting an unpaid one.
  'grant-on-checkout',
]);

/** Credits one paid period is worth. Arbitrary; the assertions count grants, not credits. */
export const CREDITS_PER_PERIOD = 500;

const tick = () => new Promise((resolve) => setImmediate(resolve));

export function createStore() {
  return {
    processedEvents: new Set(),
    grantedPeriods: new Map(), // subscription id -> Set of period starts already granted
    subscriptions: new Map(), // the mirrored row: period, status, quantity, price
    purchases: new Map(), // payment intent -> { amount, refundedTotal } (minor units)
    credits: new Map(), // user id -> integer
    grants: [], // one row per grant actually applied
    clawbacks: [], // { paymentIntent, amount } in minor units
    conversions: [], // what the server sent to the ad platforms
    notifications: [], // side effects that must not run twice
    log: [],

    /** An INSERT on a primary key: atomic, and the only claim that survives a race. */
    claimEvent(id) {
      if (this.processedEvents.has(id)) return false;
      this.processedEvents.add(id);
      return true;
    },
    releaseEventClaim(id) {
      this.processedEvents.delete(id);
    },

    async readGrantedPeriods(subId) {
      await tick(); // a SELECT is a round trip
      return this.grantedPeriods.get(subId) || new Set();
    },
    markPeriodGranted(subId, periodStart) {
      const seen = this.grantedPeriods.get(subId) || new Set();
      seen.add(periodStart);
      this.grantedPeriods.set(subId, seen);
    },

    async readPurchase(paymentIntent) {
      await tick();
      return this.purchases.get(paymentIntent) || null;
    },
    /** compare-and-swap: writes only if nobody moved the total underneath us. */
    swapRefundedTotal(paymentIntent, expected, next) {
      const row = this.purchases.get(paymentIntent);
      if (!row || row.refundedTotal !== expected) return false;
      row.refundedTotal = next;
      return true;
    },

    addCredits(userId, amount) {
      this.credits.set(userId, (this.credits.get(userId) || 0) + amount);
    },
  };
}

/** The API version moved this; a string OR an object, and `null` for a non-subscription invoice. */
export function subscriptionIdOf(invoice) {
  const ref = invoice.parent
    && invoice.parent.subscription_details
    && invoice.parent.subscription_details.subscription;
  if (typeof ref === 'string') return ref;
  if (ref && typeof ref === 'object') return ref.id;
  return null;
}

function invoiceMetadata(invoice) {
  return (invoice.parent
    && invoice.parent.subscription_details
    && invoice.parent.subscription_details.metadata) || {};
}

/** Period dates live on the line, not on the top-level invoice, and not on the subscription. */
function periodOf(invoice) {
  const lines = (invoice.lines && invoice.lines.data) || [];
  const line = lines.find((l) => !l.proration) || lines[0];
  if (!line || !line.period) return null;
  return { start: line.period.start, end: line.period.end, line };
}

export function createHandler(store, options = {}) {
  const without = new Set(options.without || []);
  for (const rule of without) {
    if (!RULES.includes(rule)) throw new Error(`unknown rule: ${rule}`);
  }
  const has = (rule) => !without.has(rule);
  let generated = 0;

  function conversionIdFor(invoice) {
    if (has('conversion-id-from-metadata')) {
      // Written at session creation into `subscription_data.metadata`, which is why it
      // still exists on a renewal invoice a year after the session is gone.
      return invoiceMetadata(invoice).conversionEventId || null;
    }
    generated += 1;
    return `evtid_generated_at_emission_${generated}`;
  }

  async function invoicePaid(event) {
    const invoice = event.data.object;
    if (has('billing-reason') && invoice.billing_reason !== 'subscription_cycle') {
      store.log.push({ event: event.id, decision: `skipped: ${invoice.billing_reason}` });
      return [];
    }
    if (!has('grant-on-renewal')) {
      store.log.push({ event: event.id, decision: 'skipped: renewals not implemented' });
      return [];
    }
    const subId = subscriptionIdOf(invoice);
    const period = periodOf(invoice);
    if (!subId || !period) {
      store.log.push({ event: event.id, decision: 'skipped: not a subscription invoice' });
      return [];
    }
    const metadata = invoiceMetadata(invoice);
    const userId = metadata.userId;

    const granted = await store.readGrantedPeriods(subId);
    if (has('grant-marker') && granted.has(period.start)) {
      store.log.push({ event: event.id, decision: 'skipped: period already granted' });
      return [];
    }
    store.markPeriodGranted(subId, period.start);
    store.addCredits(userId, CREDITS_PER_PERIOD);
    store.grants.push({
      subscription: subId, userId, periodStart: period.start, source: 'webhook', event: event.id,
    });

    // The mirror moves FORWARD only. Arrival order is not state.
    const mirror = store.subscriptions.get(subId);
    if (!has('ordering') || !mirror || period.start > mirror.periodStart) {
      store.subscriptions.set(subId, {
        periodStart: period.start,
        periodEnd: period.end,
        status: 'active',
        quantity: period.line.quantity,
        priceId: period.line.pricing
          && period.line.pricing.price_details
          && period.line.pricing.price_details.price,
      });
    }

    const conversionId = conversionIdFor(invoice);
    store.log.push({ event: event.id, decision: 'granted' });
    return [
      () => store.notifications.push({ userId, kind: 'renewal', periodStart: period.start }),
      () => store.conversions.push({
        eventId: conversionId,
        eventName: 'Purchase',
        source: 'webhook',
        value: invoice.amount_paid / 100,
        currency: (invoice.currency || '').toUpperCase(),
      }),
    ];
  }

  async function chargeRefunded(event) {
    const charge = event.data.object;
    const row = await store.readPurchase(charge.payment_intent);
    if (!row) {
      // The other half of the fork: a subscription refund has no purchase row and is
      // resolved `charge.invoice` -> invoice -> subscription. Out of this pack's scope,
      // and named rather than silently dropped.
      store.log.push({ event: event.id, decision: 'skipped: no purchase row (subscription refund path)' });
      return [];
    }
    if (!has('cumulative-refund')) {
      store.clawbacks.push({ paymentIntent: charge.payment_intent, amount: charge.amount_refunded });
      store.log.push({ event: event.id, decision: 'clawed back amount_refunded' });
      return [];
    }
    const increment = charge.amount_refunded - row.refundedTotal;
    if (increment <= 0) {
      store.log.push({ event: event.id, decision: 'skipped: replay or reorder' });
      return [];
    }
    if (!store.swapRefundedTotal(charge.payment_intent, row.refundedTotal, charge.amount_refunded)) {
      store.log.push({ event: event.id, decision: 'skipped: a concurrent delivery won' });
      return [];
    }
    store.clawbacks.push({ paymentIntent: charge.payment_intent, amount: increment });
    store.log.push({ event: event.id, decision: 'clawed back the increment' });
    return [];
  }

  async function sessionCompleted(event) {
    const session = event.data.object;
    if (has('async-gate') && session.payment_status === 'unpaid') {
      // An async method. The grant belongs to `async_payment_succeeded`, which may
      // arrive days later -- or never.
      store.log.push({ event: event.id, decision: 'skipped: payment_status unpaid' });
      return [];
    }
    if (!has('grant-on-checkout')) {
      store.log.push({ event: event.id, decision: 'skipped: checkout not implemented' });
      return [];
    }
    return grantForSession(session, event.id);
  }

  function grantForSession(session, eventId) {
    const subId = session.subscription;
    if (store.subscriptions.has(subId)) {
      store.log.push({ event: eventId, decision: 'duplicate: subscription already granted' });
      return [];
    }
    store.subscriptions.set(subId, {
      periodStart: null, periodEnd: null, status: 'active', quantity: 1, priceId: null,
    });
    store.addCredits(session.metadata.userId, CREDITS_PER_PERIOD);
    store.grants.push({
      subscription: subId,
      userId: session.metadata.userId,
      periodStart: null,
      source: 'webhook',
      event: eventId,
    });
    return [];
  }

  async function handle(event) {
    switch (event.type) {
      case 'invoice.paid':
        return invoicePaid(event);
      case 'charge.refunded':
        return chargeRefunded(event);
      case 'checkout.session.completed':
      case 'checkout.session.async_payment_succeeded':
        return sessionCompleted(event);
      case 'checkout.session.async_payment_failed':
        store.log.push({ event: event.id, decision: 'async payment failed: nothing granted' });
        return [];
      default:
        return []; // 200 for a type we do not handle
    }
  }

  /** The route Stripe posts to. Signature verification is the caller's; see SKILL.md. */
  async function deliver(event) {
    if (has('claim') && !store.claimEvent(event.id)) {
      return { status: 200, body: { received: true, duplicate: true } };
    }
    let afterCommit = [];
    try {
      afterCommit = await handle(event);
    } catch (error) {
      if (has('claim')) store.releaseEventClaim(event.id);
      return { status: 500, body: { error: 'handler error' } };
    }
    for (const effect of afterCommit) effect(); // side effects run after the commit
    return { status: 200, body: { received: true } };
  }

  /**
   * The nightly repair, and the "Sync now" button. It has NO event id, so the event
   * claim cannot protect it -- only the per-period grant marker can. This is the entry
   * point that separates the two.
   */
  async function reconcile(subId, period, metadata) {
    const granted = await store.readGrantedPeriods(subId);
    if (has('grant-marker') && granted.has(period.start)) {
      store.log.push({ event: 'reconcile', decision: 'skipped: period already granted' });
      return { granted: false };
    }
    store.markPeriodGranted(subId, period.start);
    store.addCredits(metadata.userId, CREDITS_PER_PERIOD);
    store.grants.push({
      subscription: subId, userId: metadata.userId, periodStart: period.start,
      source: 'reconciliation', event: 'reconcile',
    });
    return { granted: true };
  }

  return { deliver, reconcile };
}
