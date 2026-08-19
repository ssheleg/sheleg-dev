#!/usr/bin/env node
// The assertions a correct purchase emitter must pass, and the proof that each one can
// fail.
//
//   node assert-dedup-contract.mjs              # run them against the reference emitter
//   node assert-dedup-contract.mjs --self-test  # break the emitter one rule at a time
//
// `--self-test` is what makes this evidence: for every assertion it deletes the rule whose
// removal MUST turn that assertion red, and fails if the assertion still passes. It then
// prints which fixture ISOLATES each rule — because two rules that both explain a passing
// fixture mean neither is tested.
//
// The runner is duplicated from `stripe-billing/fixtures/assert-money-invariants.mjs` on
// purpose. A reader installs one skill, not six, so a shared import would resolve to
// nothing in the common case; this pack has to run from its own directory alone.
//
// No network, no filesystem writes, no clock, and no access token anywhere in this
// directory — the sink collects what WOULD have been sent.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createSink, createEmitter, RULES, EVENT_NAME } from './reference-emitter.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const fixture = (name) => JSON.parse(readFileSync(path.join(HERE, name), 'utf8'));

const PIXEL_BROWSER = 'purchase-pixel-browser.json';
const CAPI_SERVER = 'purchase-capi-server.json';
const CAPI_FORBIDDEN = 'purchase-capi-from-thank-you-page.json';

/** The purchase is read OUT of the fixture, so the values have one home. */
function purchaseFrom(name, cleared) {
  const event = fixture(name).data[0];
  return {
    conversionEventId: event.event_id,
    value: event.custom_data.value,
    currency: event.custom_data.currency,
    contentIds: event.custom_data.content_ids,
    numItems: event.custom_data.num_items,
    externalId: event.user_data.external_id[0],
    emailSha256: event.user_data.em[0],
    // The raw address a wrong emitter would send instead. sha256 of this string is the
    // `em` above, so the two fixtures are consistent and neither is a real person.
    email: 'placeholder@example.invalid',
    clientIpAddress: event.user_data.client_ip_address,
    clientUserAgent: event.user_data.client_user_agent,
    fbp: event.user_data.fbp,
    fbc: event.user_data.fbc,
    eventTime: event.event_time,
    eventSourceUrl: event.event_source_url,
    cleared,
  };
}

/** Carol paid by card: the charge cleared, and the webhook says so. */
const CLEARED = () => purchaseFrom(CAPI_SERVER, true);
/** Bob chose a bank debit: the session completed, the money has not moved and may not. */
const NOT_CLEARED = () => purchaseFrom(CAPI_FORBIDDEN, false);

function harness(without = []) {
  const sink = createSink();
  return { sink, emitter: createEmitter(sink, { without }) };
}

/** The real sequence: the browser fires on the thank-you page, the webhook lands when it lands. */
function runPurchase({ sink, emitter }, purchase) {
  emitter.onThankYouPage(purchase);
  if (purchase.cleared) emitter.onChargeCleared(purchase);
  return sink;
}

export const INVARIANTS = [
  {
    id: 'pixel-and-capi-carry-one-event-id',
    fixtures: [PIXEL_BROWSER, CAPI_SERVER],
    states: 'one id, generated once and used by both sides, or the revenue counts twice',
    breaks: ['shared-event-id'],
    run({ sink, emitter, assert }) {
      runPurchase({ sink, emitter }, CLEARED());
      // The browser side is read from the SHIPPED fixture rather than from the sink. That
      // is deliberate: it keeps this assertion independent of whether the browser event
      // fired at all, which is a different rule with its own fixture. Reading both sides
      // out of one emitter is how the two got tangled on the first pass.
      const pixelId = fixture(PIXEL_BROWSER)[3].eventID;
      const serverId = sink.capi[0].data[0].event_id;
      assert.equal(serverId, pixelId,
        `the pixel carries ${pixelId} and the server sent ${serverId} — nothing will ever `
        + 'deduplicate these two, and one purchase is two conversions');
    },
  },
  {
    id: 'pixel-and-capi-carry-one-event-name',
    fixtures: [PIXEL_BROWSER, CAPI_SERVER],
    states: 'Meta compares the name as well as the id, and the name is the half that is missed',
    breaks: ['exact-event-name'],
    run({ sink, emitter, assert }) {
      runPurchase({ sink, emitter }, CLEARED());
      const pixelName = fixture(PIXEL_BROWSER)[1];   // the browser contract, not the sink
      const serverName = sink.capi[0].data[0].event_name;
      assert.equal(serverName, pixelName,
        `'${pixelName}' in the browser and '${serverName}' on the server: a shared id `
        + 'deduplicates nothing when the names differ');
      assert.equal(serverName, EVENT_NAME);
    },
  },
  {
    id: 'no-purchase-reported-before-the-charge-cleared',
    fixtures: [CAPI_FORBIDDEN],
    states: 'the thank-you page has no idea whether the money moved, so it reports nothing',
    breaks: ['webhook-sourced'],
    run({ sink, emitter, assert }) {
      runPurchase({ sink, emitter }, NOT_CLEARED());
      assert.equal(sink.capi.length, 0,
        'a Conversions API purchase was sent for a charge that has not cleared — this is '
        + 'the event that exists for every session that reached the page and for no refund');
      assert.equal(sink.pixel.length, 0,
        'a Purchase pixel fired for a session whose payment is still pending');
      assert.notDeepEqual(sink.capi[0], fixture(CAPI_FORBIDDEN));
    },
  },
  {
    id: 'the-browser-event-is-kept',
    fixtures: [PIXEL_BROWSER],
    states: 'the browser event stays and stays subordinate — it carries the click ids',
    breaks: ['keep-browser-event'],
    run({ sink, emitter, assert }) {
      runPurchase({ sink, emitter }, CLEARED());
      assert.equal(sink.pixel.length, 1,
        'no browser event fired: the click id, the consent state and the session are lost, '
        + 'and only the browser had them');
      // `|| []` on purpose: with no browser event at all this must FAIL rather than throw a
      // TypeError, because an assertion the runner never reached is one no mutant has been
      // watched breaking — which is how it sat unmeasured until 2026-08-20.
      assert.equal((sink.pixel[0] || [])[0], 'track',
        'the browser event is not a `track` call — the pixel contract is `fbq(\'track\', …)`');
    },
  },
  {
    id: 'identifiers-reach-the-server-hashed',
    fixtures: [CAPI_SERVER],
    states: 'advanced matching sends hashes, never the address itself',
    breaks: ['hashed-identifiers'],
    run({ sink, emitter, assert }) {
      runPurchase({ sink, emitter }, CLEARED());
      const userData = sink.capi[0].data[0].user_data;
      for (const value of userData.em) {
        assert.match(value, /^[0-9a-f]{64}$/,
          `user_data.em carried ${JSON.stringify(value)} — a raw identifier, not a sha256`);
      }
      assert.ok(!JSON.stringify(userData).includes('@'),
        'user_data carries something with an @ in it');
    },
  },
  {
    id: 'the-shipped-capi-fixture-is-what-a-correct-emitter-sends',
    fixtures: [CAPI_SERVER, PIXEL_BROWSER],
    states: 'the fixtures are the reference output, byte for byte — not an illustration',
    // Broad by construction: it compares the whole body, so every rule that changes any
    // field turns it red. It is here so a reader can trust the fixtures they copy.
    breaks: ['shared-event-id', 'exact-event-name', 'hashed-identifiers', 'keep-browser-event'],
    run({ sink, emitter, assert }) {
      runPurchase({ sink, emitter }, CLEARED());
      assert.deepEqual(sink.capi[0], fixture(CAPI_SERVER));
      assert.deepEqual(sink.pixel[0], fixture(PIXEL_BROWSER));
    },
  },
];

// ------------------------------------------------- one assertion, one measurement
//
// Why the assertions are not called straight through `node:assert`. Until 2026-08-20 the
// runner returned on the FIRST throw and the matrix compared one row per invariant, so an
// invariant was measured as a single unit: any assertion that was not the sole
// discriminator could be replaced by `assert.ok(true)` and nothing went red. Measured that
// day in this pack too — the PII guard below (*"user_data carries something with an @ in
// it"*, advertised by name at `references/meta-linkedin.md`) was neutered and
// `--self-test` stayed at exit 0, because the `assert.match` above it discriminated the
// same rule.
//
// So the `assert` an invariant receives is a RECORDER: same API, but a failure is
// remembered instead of thrown and the assertions after it still run. Each call site is one
// assertion with its own identity — its line in this file — and `--self-test` asks the
// question per assertion rather than per invariant.
//
// `assert.unmutated.equal(...)` marks an assertion NO mutant in this pack varies: it pins
// something the rules do not touch, so it has never been watched failing and the verdict
// counts it apart rather than as evidence. Measured, not asserted — the self-test fails
// both when a plain assertion turns out unbreakable and when an `unmutated` one turns out
// breakable.
//
// Duplicated from `stripe-billing/fixtures/assert-money-invariants.mjs` for the reason
// given at the top: a reader installs one skill, not six.

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
  const { sink, emitter } = harness(without);
  let threw = null;
  try {
    await invariant.run({ sink, emitter, assert: api });
  } catch (error) {
    // A real error — a read off a row the mutant never wrote, say. It aborts the remaining
    // assertions, and it is still the invariant going red.
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
    console.error(`\n${failed} of ${INVARIANTS.length} deduplication assertions failed`);
    return 1;
  }
  console.log(`\nOK: ${INVARIANTS.length} deduplication invariants hold against the emitter `
    + `(${asserted} assertions)`);
  return 0;
}

async function selfTest() {
  const problems = [];
  const matrix = [];
  const coverage = []; // one row per ASSERTION: which mutants turn that call site red
  for (const invariant of INVARIANTS) {
    // The clean run is the census: it names every assertion this invariant executes. One
    // that records nothing has a run() which never took the recorder, so nothing about it
    // is measured — the failure mode of the injection itself.
    const clean = await runOne(invariant, []);
    if (clean.broke) {
      problems.push(`${invariant.id}: fails against the unmutated emitter `
        + `(${(clean.failed[0] && `:${clean.failed[0].site} ${clean.failed[0].why}`) || clean.threw})`);
    }
    if (!clean.sites.length) {
      problems.push(`${invariant.id}: recorded no assertion — its run() does not take the `
        + '`assert` the runner passes it, so nothing about it is measured');
    }
    const broken = new Map(clean.sites.map((s) => [s.site, []]));

    const broke = [];
    for (const rule of RULES) {
      const r = await runOne(invariant, [rule]);
      if (r.broke) broke.push(rule);
      for (const s of r.failed) if (broken.has(s.site)) broken.get(s.site).push(rule);
    }
    matrix.push({ id: invariant.id, broke });

    for (const site of clean.sites) {
      coverage.push({
        invariant: invariant.id,
        site: site.site,
        unmutated: site.unmutated,
        by: broken.get(site.site) || [],
      });
    }

    const expected = [...invariant.breaks].sort().join(', ');
    const measured = [...broke].sort().join(', ');
    if (expected !== measured) {
      problems.push(`${invariant.id}: declares breaks [${expected || '-'}], measured [${measured || '-'}]`);
    }
    if (broke.length === 0) {
      problems.push(`${invariant.id}: no mutant breaks it — the assertion cannot fail`);
    }
  }

  const width = Math.max(...matrix.map((row) => row.id.length));
  console.log(`\ninvariant x mutant — ${RULES.length} mutants, `
    + 'and which removed rule turns each invariant red\n');
  for (const row of matrix) {
    console.log(`  ${row.id.padEnd(width)}  ${row.broke.join(', ') || '(nothing)'}`);
  }

  // The per-ASSERTION half, and the one the table above cannot give: an invariant goes red
  // as a unit, so a dead assertion inside a live one is invisible there.
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
    const isolating = matrix.filter((row) => row.broke.length === 1 && row.broke[0] === rule);
    if (isolating.length) {
      console.log(`  ${rule.padEnd(20)} ${isolating.map((r) => r.id).join(', ')}`);
    } else {
      problems.push(`no fixture isolates ${rule} — every assertion it breaks is also broken `
        + 'by another rule, so neither is proven');
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
    + `${RULES.length} mutants; ${pinned} declared unmutated and measured unbreakable; `
    + `${RULES.length} rules, each isolated by a fixture`);
  return 0;
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  const mode = process.argv.includes('--self-test') ? selfTest : runAll;
  process.exit(await mode());
}
