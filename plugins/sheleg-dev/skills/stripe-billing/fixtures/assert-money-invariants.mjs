#!/usr/bin/env node
// The assertions a correct Stripe webhook handler must pass, and the proof that each one
// can fail.
//
//   node assert-money-invariants.mjs              # run them against the reference handler
//   node assert-money-invariants.mjs --self-test  # break the handler one rule at a time
//
// `--self-test` is the half that makes this evidence rather than decoration. For every
// invariant it names the rule whose removal MUST turn that invariant red, deletes exactly
// that rule, and fails if the assertion still passes. A check nobody has watched failing
// is indistinguishable from a check that cannot fail.
//
// It also prints the whole invariant x mutant matrix, because two rules that both explain
// a passing fixture mean neither is tested. Where `breaks` holds one rule, that fixture
// isolates it. Where it holds more, the overlap is written down instead of assumed away
// (`README.md` -> *What masks what*).
//
// To point this at YOUR handler: replace `createStore`/`createHandler` below with your
// own, keep the same three entry points (`deliver(event)`, `reconcile(...)`, and a store
// you can read counts off), and delete the `--self-test` block only after you have your
// own way of watching each assertion fail.
//
// No network, no filesystem writes, no clock. The only reads are the JSON fixtures beside
// this file.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import assert from 'node:assert/strict';
import {
  createStore, createHandler, subscriptionIdOf, RULES, CREDITS_PER_PERIOD,
} from './reference-handler.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const fixture = (name) => JSON.parse(readFileSync(path.join(HERE, name), 'utf8'));

const CYCLE_JAN = 'invoice-paid-subscription-cycle.json';
const CYCLE_JAN_REDELIVERY = 'invoice-paid-subscription-cycle-redelivery.json';
const CYCLE_FEB = 'invoice-paid-subscription-cycle-next-period.json';
const PRORATION = 'invoice-paid-subscription-update-proration.json';
const REFUND_PARTIAL = 'charge-refunded-partial.json';
const REFUND_REMAINDER = 'charge-refunded-remainder.json';
const SESSION_UNPAID = 'checkout-session-completed-async-unpaid.json';
const SESSION_FAILED = 'checkout-session-async-payment-failed.json';
const SESSION_PAID = 'checkout-session-completed-paid.json';
const DISCOUNT_CREATED = 'customer-discount-created-retention.json';
const DISCOUNT_CONSUMED = 'customer-subscription-updated-discount-consumed.json';
const CANCEL_FLEXIBLE = 'customer-subscription-updated-cancel-flexible.json';
const CANCEL_CLASSIC = 'customer-subscription-updated-cancel-classic.json';

/** A fresh store and handler per invariant: no assertion inherits another's state. */
function harness(without = []) {
  const store = createStore();
  const handler = createHandler(store, { without });
  return { store, handler };
}

function seedOneOffPurchase(store) {
  // The reader's own database row for a $90 credit pack, bought before the refunds.
  store.purchases.set('pi_PLACEHOLDER_creditpack', { amount: 9000, refundedTotal: 0 });
}

function periodOfCycle(event) {
  const line = event.data.object.lines.data[0];
  return { start: line.period.start, end: line.period.end };
}

// ---------------------------------------------------------------------- invariants
//
// `breaks` is a MEASURED list, not an intention: `--self-test` fails if the set of
// mutants that turn an invariant red is anything other than this.

export const INVARIANTS = [
  {
    id: 'renewal-grants-exactly-once',
    fixtures: [CYCLE_JAN],
    states: 'a paid renewal becomes exactly one grant, and the mirror carries its period',
    breaks: ['grant-on-renewal'],
    async run({ store, handler, assert }) {
      const event = fixture(CYCLE_JAN);
      const response = await handler.deliver(event);
      // `unmutated`: no rule in RULES makes this route answer anything but 200 with that
      // body, so neither assertion has ever been watched failing. They pin the envelope a
      // reader copies; they are not evidence, and the verdict line counts them apart.
      assert.unmutated.equal(response.status, 200);
      assert.unmutated.deepEqual(response.body, { received: true });
      assert.equal(store.grants.length, 1, 'a paid renewal granted nothing');
      assert.equal(store.credits.get('usr_PLACEHOLDER_alice'), CREDITS_PER_PERIOD);
      // `|| {}` on purpose: with no mirror row at all these two assertions must FAIL
      // rather than throw a TypeError on the line above them. A throw aborts the run, and
      // an assertion the runner never reached is one no mutant has been watched breaking.
      const mirror = store.subscriptions.get('sub_PLACEHOLDER_alice') || {};
      assert.equal(mirror.periodStart, 1767225600);
      assert.equal(mirror.periodEnd, 1769904000, 'the period is not the line period');
    },
  },
  {
    id: 'proration-invoice-grants-nothing',
    fixtures: [CYCLE_JAN, PRORATION],
    states: 'billing_reason subscription_update is a $40 proration, not a month of product',
    breaks: ['billing-reason', 'grant-on-renewal'],
    async run({ store, handler, assert }) {
      await handler.deliver(fixture(CYCLE_JAN));
      const response = await handler.deliver(fixture(PRORATION));
      // unmutated: nothing in RULES makes the endpoint answer 500 for a proration.
      assert.unmutated.equal(response.status, 200, 'a proration invoice must not fail the endpoint');
      assert.equal(store.grants.length, 1,
        'the proration granted a second period — a user who adds and removes a seat '
        + 'four times has been given four months of product');
      assert.ok(
        store.log.some((l) => l.decision === 'skipped: subscription_update'),
        'nothing recorded WHY the proration was skipped',
      );
    },
  },
  {
    id: 'sequential-redelivery-grants-once',
    fixtures: [CYCLE_JAN, CYCLE_JAN_REDELIVERY],
    states: 'the same evt_ delivered twice grants once AND runs its side effects once',
    breaks: ['claim', 'grant-on-renewal'],
    async run({ store, handler, assert }) {
      const first = await handler.deliver(fixture(CYCLE_JAN));
      const second = await handler.deliver(fixture(CYCLE_JAN_REDELIVERY));
      assert.unmutated.deepEqual(first.body, { received: true }); // the envelope, again
      assert.deepEqual(second.body, { received: true, duplicate: true },
        'the second delivery was not recognised as a duplicate');
      assert.equal(store.grants.length, 1, 'the redelivery granted a second time');
      assert.equal(store.notifications.length, 1, '"your renewal" was sent twice');
      assert.equal(store.conversions.length, 1,
        'the server-side conversion fired twice — the revenue is counted twice');
    },
  },
  {
    id: 'concurrent-redelivery-grants-once',
    fixtures: [CYCLE_JAN, CYCLE_JAN_REDELIVERY],
    states: 'two deliveries in flight at once grant once — the claim is an INSERT, not a SELECT',
    breaks: ['claim', 'grant-on-renewal'],
    async run({ store, handler, assert }) {
      // 40 ms apart in production; here, both before either has finished its first read.
      // This is the fixture that separates the event claim from the grant marker: the
      // marker reads before it writes, and a read is a round trip.
      const [a, b] = await Promise.all([
        handler.deliver(fixture(CYCLE_JAN)),
        handler.deliver(fixture(CYCLE_JAN_REDELIVERY)),
      ]);
      const bodies = [a.body, b.body];
      assert.equal(store.grants.length, 1, 'both deliveries granted');
      assert.equal(store.credits.get('usr_PLACEHOLDER_alice'), CREDITS_PER_PERIOD,
        'the user was credited twice for one renewal');
      assert.equal(store.conversions.length, 1, 'the conversion fired twice');
      assert.equal(bodies.filter((x) => x.duplicate === true).length, 1,
        'exactly one of the two deliveries must answer duplicate');
    },
  },
  {
    id: 'reconciliation-does-not-regrant',
    fixtures: [CYCLE_JAN],
    states: 'the nightly repair reuses the webhook marker — a nightly job is not a nightly gift',
    breaks: ['grant-marker', 'grant-on-renewal'],
    async run({ store, handler, assert }) {
      const event = fixture(CYCLE_JAN);
      await handler.deliver(event);
      const subId = subscriptionIdOf(event.data.object);
      const outcome = await handler.reconcile(subId, periodOfCycle(event), {
        userId: 'usr_PLACEHOLDER_alice',
      });
      assert.equal(outcome.granted, false, 'reconciliation granted a period the webhook granted');
      assert.equal(store.grants.length, 1);
      assert.equal(store.credits.get('usr_PLACEHOLDER_alice'), CREDITS_PER_PERIOD);
    },
  },
  {
    id: 'out-of-order-pair-does-not-rewind-state',
    fixtures: [CYCLE_FEB, CYCLE_JAN],
    states: 'February delivered before January leaves February in the mirror, and grants both',
    breaks: ['ordering', 'grant-on-renewal'],
    async run({ store, handler, assert }) {
      await handler.deliver(fixture(CYCLE_FEB)); // arrives first
      await handler.deliver(fixture(CYCLE_JAN)); // the earlier period, delivered late
      assert.equal(store.grants.length, 2, 'both periods were paid, so both are owed');
      const mirror = store.subscriptions.get('sub_PLACEHOLDER_alice') || {};
      assert.equal(mirror.periodStart, 1769904000,
        'the mirror was rewound to the older period — state derived from arrival order');
      assert.equal(mirror.periodEnd, 1772323200,
        'the renewal date now points at a period that already ended');
    },
  },
  {
    id: 'refund-total-is-cumulative',
    fixtures: [REFUND_PARTIAL, REFUND_REMAINDER],
    states: 'amount_refunded is the total so far: two partials claw back $90, not $130',
    breaks: ['cumulative-refund'],
    async run({ store, handler, assert }) {
      seedOneOffPurchase(store);
      await handler.deliver(fixture(REFUND_PARTIAL));
      await handler.deliver(fixture(REFUND_REMAINDER));
      const total = store.clawbacks.reduce((sum, c) => sum + c.amount, 0);
      assert.equal(total, 9000,
        `clawed back ${total} minor units against a 9000 charge — amount_refunded was read `
        + 'as an increment');
      assert.deepEqual(store.clawbacks.map((c) => c.amount), [4000, 5000]);
      assert.equal(store.purchases.get('pi_PLACEHOLDER_creditpack').refundedTotal, 9000);
    },
  },
  {
    id: 'sequential-redelivery-grants-once-by-count-alone',
    fixtures: [CYCLE_JAN, CYCLE_JAN_REDELIVERY],
    states: 'the same pair judged ONLY by the grant count — masked, and here to prove it',
    // Deliberately weaker than `sequential-redelivery-grants-once`, and kept because the
    // measurement is the finding: no SINGLE removed rule turns this red. Delete the event
    // claim and the per-period marker still refuses the second grant; delete the marker
    // and the claim still refuses the second delivery. A suite that judged a redelivery by
    // its grant count alone would ship with no idempotency and stay green.
    breaks: [['claim', 'grant-marker'], 'grant-on-renewal'],
    async run({ store, handler, assert }) {
      await handler.deliver(fixture(CYCLE_JAN));
      await handler.deliver(fixture(CYCLE_JAN_REDELIVERY));
      assert.equal(store.grants.length, 1, 'the redelivery granted a second time');
    },
  },
  {
    id: 'duplicate-refund-claws-back-once',
    fixtures: [REFUND_PARTIAL],
    states: 'the same charge.refunded twice claws back $40 once — also masked',
    // The second masked pair, and the reason the claim's own discriminating fixture is the
    // CONCURRENT delivery rather than any duplicate: the compare-and-swap's
    // `increment <= 0` catches a sequential replay by itself, and the claim catches it
    // without the swap. Neither is tested by this fixture alone.
    breaks: [['claim', 'cumulative-refund']],
    async run({ store, handler, assert }) {
      seedOneOffPurchase(store);
      await handler.deliver(fixture(REFUND_PARTIAL));
      await handler.deliver(fixture(REFUND_PARTIAL));
      const total = store.clawbacks.reduce((sum, c) => sum + c.amount, 0);
      assert.equal(total, 4000, `clawed back ${total} for one $40 refund`);
    },
  },
  {
    id: 'unpaid-session-grants-nothing',
    fixtures: [SESSION_UNPAID, SESSION_FAILED],
    states: 'the redirect proves a browser: an unpaid async session grants and converts nothing',
    breaks: ['async-gate'],
    async run({ store, handler, assert }) {
      const completed = await handler.deliver(fixture(SESSION_UNPAID));
      // unmutated: the envelope. Removing `async-gate` grants the session and still answers 200.
      assert.unmutated.equal(completed.status, 200, 'an unpaid session must still answer 200');
      assert.equal(store.grants.length, 0,
        'a session whose payment_status is unpaid was granted — the money has not moved');
      // unmutated, and the reason is a gap worth seeing: this handler emits conversions on
      // `invoice.paid` only, so no rule here can make a checkout session report one. The
      // assertion states the rule for a reader whose handler DOES emit from a session.
      assert.unmutated.equal(store.conversions.length, 0,
        'a purchase conversion was reported for a charge that has not cleared');
      await handler.deliver(fixture(SESSION_FAILED));
      assert.equal(store.grants.length, 0, 'the failed async payment still granted');
      assert.unmutated.equal(store.conversions.length, 0); // same gap as above
      assert.equal(store.credits.get('usr_PLACEHOLDER_bob'), undefined);
    },
  },
  {
    id: 'paid-session-grants-once',
    fixtures: [SESSION_PAID],
    states: 'the positive control: a card session that DID clear grants exactly once',
    // Without it, a handler that refuses every checkout session satisfies the assertion
    // above and this pack would have taught the opposite defect.
    breaks: ['grant-on-checkout'],
    async run({ store, handler, assert }) {
      const response = await handler.deliver(fixture(SESSION_PAID));
      assert.unmutated.deepEqual(response.body, { received: true }); // the envelope
      assert.equal(store.grants.length, 1, 'a cleared card session granted nothing');
      assert.equal(store.credits.get('usr_PLACEHOLDER_carol'), CREDITS_PER_PERIOD);
      assert.ok(store.subscriptions.has('sub_PLACEHOLDER_carol'));
    },
  },
  {
    id: 'conversion-id-survives-the-session',
    fixtures: [CYCLE_JAN],
    states: 'the conversion id comes from subscription metadata, so browser and server share it',
    breaks: ['conversion-id-from-metadata', 'grant-on-renewal'],
    async run({ store, handler, assert }) {
      await handler.deliver(fixture(CYCLE_JAN));
      assert.equal(store.conversions.length, 1);
      const [conversion = {}] = store.conversions;
      assert.equal(conversion.eventId, 'evtid_PLACEHOLDER_purchase_jan',
        'the server generated its own id — nothing will ever deduplicate against the pixel');
      assert.equal(conversion.eventName, 'Purchase', 'the event name is not byte-equal');
      assert.equal(conversion.source, 'webhook');
      assert.equal(conversion.value, 29);
      assert.equal(conversion.currency, 'USD');
    },
  },
  {
    id: 'retention-offer-is-consumed-once',
    fixtures: [DISCOUNT_CREATED, DISCOUNT_CONSUMED],
    states: 'a customer who took the save offer is not offered it again after the '
      + 'duration=once discount has left subscription.discounts',
    breaks: ['retention-eligibility'],
    async run({ store, handler, assert }) {
      const before = { id: 'sub_PLACEHOLDER_alice', status: 'active', discounts: [] };

      const first = await handler.offerRetention('cus_PLACEHOLDER_alice', before);
      // unmutated, and the positive control: every mutant here still makes the FIRST
      // offer. Without it, a handler that offers nobody anything would pass the rest.
      assert.unmutated.equal((first || {}).offerId, 'cancel-50-once');
      assert.equal(store.retentionOffers.length, 1,
        'the offer was shown and no row recorded it — an offer nobody wrote down cannot '
        + 'be counted, and the count is the only thing that stops the loop');

      await handler.deliver(fixture(DISCOUNT_CREATED));
      assert.equal(store.saves.length, 1,
        'the redemption was not recorded as a save — there is no portal event for a '
        + 'completed flow, so nothing else will ever say the cancellation was deflected');
      assert.equal((store.retentionOffers[0] || {}).redeemedAt, 1767225000);

      // The discounted invoice finalizes and Stripe REMOVES the discount from the array.
      const consumed = fixture(DISCOUNT_CONSUMED);
      await handler.deliver(consumed);
      const mirror = store.subscriptions.get('sub_PLACEHOLDER_alice') || {};
      assert.unmutated.deepEqual(mirror.discountIds, [],
        'the fixture is the moment the duration=once discount leaves the subscription');

      const second = await handler.offerRetention('cus_PLACEHOLDER_alice', consumed.data.object);
      assert.equal(second, null,
        'the offer was made a second time — one cancel-flow visit per cycle then rides '
        + 'half price forever, and every renewal looks ordinary in the logs');
      assert.equal(store.retentionOffers.length, 1, 'a second offer row was opened');
    },
  },
  {
    id: 'scheduled-cancellation-survives-billing-mode',
    fixtures: [CANCEL_FLEXIBLE, CANCEL_CLASSIC],
    states: 'a portal cancellation is stored under BOTH billing modes — flexible sets '
      + 'cancel_at and leaves cancel_at_period_end false',
    breaks: ['cancellation-timestamp'],
    async run({ store, handler, assert }) {
      await handler.deliver(fixture(CANCEL_FLEXIBLE));
      const flexible = store.subscriptions.get('sub_PLACEHOLDER_alice') || {};
      // unmutated: no rule here varies the mode or the reason the customer gave.
      assert.unmutated.equal(flexible.billingMode, 'flexible');
      assert.unmutated.equal(flexible.cancellationFeedback, 'too_expensive');
      assert.equal(flexible.cancelAt, 1769904000,
        'a cancellation scheduled under flexible billing_mode was stored as "not '
        + 'cancelling": the banner tells a customer who cancelled ten seconds ago that '
        + 'their plan renews, and nothing errors');

      await handler.deliver(fixture(CANCEL_CLASSIC));
      const classic = store.subscriptions.get('sub_PLACEHOLDER_bob') || {};
      // unmutated, and deliberately so: this is the control. Both readings agree on a
      // classic row, which is exactly why the flag alone survived until flexible mode.
      assert.unmutated.equal(classic.billingMode, 'classic');
      assert.unmutated.equal(classic.cancelAt, 1769904000);
    },
  },
];

// ------------------------------------------------- one assertion, one measurement
//
// Why the assertions are not called straight through `node:assert`. Until 2026-08-20 the
// runner returned on the FIRST throw and the matrix compared one row per invariant, so an
// invariant was measured as a single unit: any assertion that was not the sole
// discriminator could be replaced by `assert.ok(true)` and nothing went red. Measured that
// day — three neutered assertions (the `clawbacks.map` deepEqual, the `mirror.periodEnd`
// equality, and the `response.body` deepEqual) left `--self-test` at exit 0 still printing
// *"12 assertions, each watched failing"*, and `npm test` at 0 with them.
//
// So the `assert` an invariant receives is a RECORDER: same API, but a failure is
// remembered instead of thrown and the assertions after it still run. Each call site is one
// assertion with its own identity — its line in this file — and `--self-test` asks the
// question per assertion rather than per invariant.
//
// Two kinds, and the difference is declared at the call site rather than in a table:
//
//   assert.equal(...)        a DISCRIMINATING assertion. At least one mutant must turn it
//                            red, or it is not evidence of anything.
//   assert.unmutated.equal() an assertion NO mutant in this pack varies. It pins the
//                            envelope or a field the rules do not touch, so it has never
//                            been watched failing and the verdict line counts it apart
//                            rather than as evidence. Measured, not asserted: the self-test
//                            fails if a mutant does break one, because that is a
//                            discriminator hiding in the wrong list.
//
// A reader pointing this at their own handler keeps writing `assert.equal`; the recorder is
// API-compatible with `node:assert/strict` for the methods below.

const SELF = import.meta.url;
const METHODS = ['equal', 'notEqual', 'deepEqual', 'notDeepEqual', 'ok', 'match', 'doesNotMatch'];

/**
 * The line in THIS file that called the recorder.
 *
 * `captureStackTrace(holder, boundary)` drops `boundary` and everything above it, so the
 * top frame is the assertion's own line — no frame counting, which is what makes the
 * identity survive a refactor of the recorder itself.
 */
function siteOf(boundary) {
  const holder = {};
  Error.captureStackTrace(holder, boundary);
  const frame = (holder.stack || '').split('\n').slice(1).find((f) => f.includes(SELF));
  const m = frame && frame.match(/:(\d+):\d+\)?\s*$/);
  return m ? Number(m[1]) : 0;
}

function recorder() {
  const seen = new Map(); // line -> { site, unmutated, ok, why }

  function record(site, unmutated, name, args) {
    let ok = true;
    let why = null;
    try {
      assert[name](...args);
    } catch (error) {
      ok = false;
      why = error.message.split('\n')[0];
    }
    const prev = seen.get(site);
    if (prev) {
      prev.ok = prev.ok && ok;
      prev.why = prev.why || why;
    } else {
      seen.set(site, { site, unmutated, ok, why });
    }
  }

  const bind = (unmutated) => {
    const api = {};
    for (const name of METHODS) {
      const call = (...args) => record(siteOf(call), unmutated, name, args);
      api[name] = call;
    }
    return api;
  };

  const api = bind(false);
  api.unmutated = bind(true);
  return { api, seen };
}

// ------------------------------------------------------------------------- runners

async function runOne(invariant, without) {
  const { api, seen } = recorder();
  const { store, handler } = harness(without);
  let threw = null;
  try {
    await invariant.run({ store, handler, assert: api });
  } catch (error) {
    // A real error — a `TypeError` on a row the mutant never wrote, say. It aborts the
    // remaining assertions, and it is still the invariant going red.
    threw = error.message.split('\n')[0];
  }
  const sites = [...seen.values()];
  return {
    threw,
    sites,
    failed: sites.filter((s) => !s.ok),
    broke: Boolean(threw) || sites.some((s) => !s.ok),
  };
}

async function runAll() {
  let failed = 0;
  let asserted = 0;
  for (const invariant of INVARIANTS) {
    const result = await runOne(invariant, []);
    asserted += result.sites.length;
    if (result.broke) {
      failed += 1;
      console.error(`FAIL ${invariant.id}`);
      for (const s of result.failed) console.error(`     :${s.site} ${s.why}`);
      if (result.threw) console.error(`     threw: ${result.threw}`);
    } else {
      console.log(`pass ${invariant.id} (${result.sites.length} assertions) — ${invariant.states}`);
    }
  }
  if (failed) {
    console.error(`\n${failed} of ${INVARIANTS.length} money invariants failed`);
    return 1;
  }
  console.log(`\nOK: ${INVARIANTS.length} money invariants hold against the handler `
    + `(${asserted} assertions)`);
  return 0;
}

/**
 * The broadest mutant: a handler that grants nothing at all. It breaks every assertion
 * about a grant, so it is excluded when asking which fixture ISOLATES a rule — otherwise
 * it would appear beside every answer and hide the ones that matter.
 */
const BROAD = ['grant-on-renewal'];

const key = (mutant) => [...mutant].sort().join('+');

async function selfTest() {
  const problems = [];

  // Every single rule, plus each multi-rule mutant some invariant declares. A combination
  // exists only where the measurement forced it: where two rules cover each other, no
  // single removal turns the assertion red, and pretending otherwise is the failure mode
  // this block was written to make visible.
  const combos = [];
  for (const invariant of INVARIANTS) {
    for (const declared of invariant.breaks) {
      if (!Array.isArray(declared)) continue;
      if (!combos.some((c) => key(c) === key(declared))) combos.push(declared);
    }
  }
  const mutants = [...RULES.map((rule) => [rule]), ...combos];

  const matrix = [];
  const coverage = []; // one row per ASSERTION: which mutants turn that call site red
  for (const invariant of INVARIANTS) {
    // The clean run is the census: it names every assertion this invariant executes, and
    // whether each is declared discriminating or shape. An invariant that records nothing
    // is one whose `run` never took the recorder — the failure mode of the injection.
    const clean = await runOne(invariant, []);
    if (clean.broke) {
      problems.push(`${invariant.id}: fails against the unmutated handler `
        + `(${(clean.failed[0] && `:${clean.failed[0].site} ${clean.failed[0].why}`) || clean.threw})`);
    }
    if (!clean.sites.length) {
      problems.push(`${invariant.id}: recorded no assertion — its run() does not take the `
        + '`assert` the runner passes it, so nothing about it is measured');
    }
    const broken = new Map(clean.sites.map((s) => [s.site, []]));

    const singles = [];
    for (const rule of RULES) {
      const r = await runOne(invariant, [rule]);
      if (r.broke) singles.push(rule);
      for (const s of r.failed) if (broken.has(s.site)) broken.get(s.site).push(rule);
    }
    // Minimal mutants only: a combination containing a rule that already breaks the
    // assertion on its own says nothing new.
    const minimalCombos = [];
    for (const combo of combos) {
      if (combo.some((rule) => singles.includes(rule))) continue;
      const r = await runOne(invariant, combo);
      if (r.broke) minimalCombos.push(combo);
      for (const s of r.failed) if (broken.has(s.site)) broken.get(s.site).push(key(combo));
    }
    const broke = [...singles.map((r) => [r]), ...minimalCombos];
    matrix.push({ id: invariant.id, broke, singles });

    for (const site of clean.sites) {
      coverage.push({
        invariant: invariant.id,
        site: site.site,
        unmutated: site.unmutated,
        by: broken.get(site.site) || [],
      });
    }

    const expected = invariant.breaks
      .map((b) => key(Array.isArray(b) ? b : [b])).sort().join(', ');
    const measured = broke.map(key).sort().join(', ');
    if (expected !== measured) {
      problems.push(
        `${invariant.id}: declares breaks [${expected || '-'}], measured [${measured || '-'}]`,
      );
    }
    if (broke.length === 0) {
      problems.push(`${invariant.id}: no mutant breaks it — the assertion cannot fail`);
    }
  }

  const width = Math.max(...matrix.map((row) => row.id.length));
  console.log(`\ninvariant x mutant — ${mutants.length} mutants, `
    + 'and the minimal removal that turns each assertion red\n');
  for (const row of matrix) {
    console.log(`  ${row.id.padEnd(width)}  ${row.broke.map(key).join(', ') || '(nothing)'}`);
  }

  // The per-ASSERTION half, and the one the per-invariant table above cannot give: an
  // invariant goes red as a unit, so a dead assertion inside a live one is invisible there.
  console.log('\nassertion x mutant — every call site, and what turns IT red\n');
  for (const row of coverage) {
    const label = `${row.invariant}:${row.site}`.padEnd(width + 6);
    if (row.unmutated) {
      console.log(`  ${label}  unmutated — no rule varies what it checks`);
      if (row.by.length) {
        problems.push(`${row.invariant} :${row.site} is declared assert.unmutated and `
          + `[${row.by.join(', ')}] breaks it — it discriminates, so drop the .unmutated`);
      }
    } else {
      console.log(`  ${label}  ${row.by.join(', ') || '(nothing)'}`);
      if (!row.by.length) {
        problems.push(`${row.invariant} :${row.site} is broken by no mutant — the assertion `
          + 'cannot fail. Either it is not testing anything, or no rule varies what it '
          + 'checks and it belongs on assert.unmutated, which the verdict counts apart');
      }
    }
  }

  console.log('\nisolation — the fixture that separates each rule from every other\n');
  for (const rule of RULES) {
    const isolating = matrix.filter((row) => {
      const exact = row.broke.filter((m) => m.length === 1 && m[0] === rule);
      if (exact.length !== 1) return false;
      // The broad baseline is allowed to co-occur: it breaks every grant assertion by
      // construction, so it hides nothing. Any OTHER co-occurring rule does.
      return row.broke
        .filter((m) => !(m.length === 1 && m[0] === rule))
        .every((m) => m.every((r) => BROAD.includes(r)));
    });
    if (isolating.length) {
      console.log(`  ${rule.padEnd(28)} ${isolating.map((r) => r.id).join(', ')}`);
    } else {
      problems.push(`no fixture isolates ${rule} — every assertion it breaks is also `
        + 'broken by another rule, so neither is proven');
    }
  }

  if (problems.length) {
    console.error(`\nFAIL: ${problems.length} problem(s) with the assertion pack itself`);
    for (const p of problems) console.error(`  - ${p}`);
    return 1;
  }
  const pinned = coverage.filter((r) => r.unmutated).length;
  console.log(`\nOK: ${INVARIANTS.length} invariants over ${coverage.length} assertions — `
    + `${coverage.length - pinned} watched failing ONE CALL SITE AT A TIME against `
    + `${mutants.length} mutants; ${pinned} declared unmutated and measured unbreakable; `
    + `${RULES.length} rules, each isolated by a fixture`);
  return 0;
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  const mode = process.argv.includes('--self-test') ? selfTest : runAll;
  process.exit(await mode());
}
