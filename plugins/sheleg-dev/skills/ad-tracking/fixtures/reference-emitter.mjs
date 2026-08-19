// A purchase emitter that satisfies the deduplication contract this skill states, and the
// same emitter with one rule removed at a time.
//
// Two call sites, and which one may report a purchase is the whole invariant:
//
//   onChargeCleared(purchase)  <- the webhook handler, the only place that knows the money
//                                 moved. Sends the Conversions API event.
//   onThankYouPage(purchase)   <- the browser. Fires the pixel with the id the server will
//                                 reuse, and reports nothing on its own authority.
//
// `without: ['shared-event-id']` and friends delete the lines a generated integration
// routinely omits; `fixtures/README.md` shows the code each flag removes. Nothing here
// reaches the network — the sink collects what WOULD have been sent, which is what the
// assertions read. No access token appears in this directory at all.

export const RULES = Object.freeze([
  'shared-event-id',
  'exact-event-name',
  'webhook-sourced',
  'keep-browser-event',
  'hashed-identifiers',
]);

/** Meta compares `event_name` as well as the id, and it is the half that gets missed. */
export const EVENT_NAME = 'Purchase';

export function createSink() {
  return { pixel: [], capi: [] };
}

function customData(purchase) {
  return {
    value: purchase.value,
    currency: purchase.currency,
    content_ids: purchase.contentIds,
    content_type: 'product',
    num_items: purchase.numItems,
  };
}

export function createEmitter(sink, options = {}) {
  const without = new Set(options.without || []);
  for (const rule of without) {
    if (!RULES.includes(rule)) throw new Error(`unknown rule: ${rule}`);
  }
  const has = (rule) => !without.has(rule);
  let generated = 0;

  /** One id, generated once at session creation, carried by both sides. */
  function eventIdFor(purchase) {
    if (has('shared-event-id')) return purchase.conversionEventId;
    generated += 1;
    return `evtid_generated_at_emission_${generated}`;
  }

  function eventNameFor(side) {
    if (has('exact-event-name')) return EVENT_NAME;
    // The trap: an id that matches and a name that does not deduplicates nothing.
    return side === 'server' ? EVENT_NAME.toLowerCase() : EVENT_NAME;
  }

  function userData(purchase) {
    const identifiers = has('hashed-identifiers')
      ? { em: [purchase.emailSha256], external_id: [purchase.externalId] }
      : { em: [purchase.email], external_id: [purchase.externalId] };
    return {
      ...identifiers,
      client_ip_address: purchase.clientIpAddress,
      client_user_agent: purchase.clientUserAgent,
      fbp: purchase.fbp,
      fbc: purchase.fbc,
    };
  }

  function capiBody(purchase) {
    return {
      data: [{
        event_name: eventNameFor('server'),
        event_time: purchase.eventTime,
        event_id: eventIdFor(purchase),
        event_source_url: purchase.eventSourceUrl,
        action_source: 'website',
        user_data: userData(purchase),
        custom_data: customData(purchase),
      }],
    };
  }

  return {
    /** The webhook handler. `cleared` is the provider's word, not the browser's. */
    onChargeCleared(purchase) {
      if (purchase.cleared !== true) {
        // Reached only by a caller that guessed. The gate below is the one that matters.
        return { sent: false, why: 'the charge has not cleared' };
      }
      sink.capi.push(capiBody(purchase));
      return { sent: true };
    },

    /**
     * The thank-you page. It fires the pixel and NOTHING ELSE: a browser cannot know
     * whether the charge cleared, and for an async method it usually has not.
     */
    onThankYouPage(purchase) {
      if (!has('webhook-sourced')) {
        // The defect: reporting the purchase from the one place with no idea whether the
        // money moved. `purchase-capi-from-thank-you-page.json` is what this sends.
        sink.capi.push(capiBody(purchase));
      }
      if (has('webhook-sourced') && purchase.cleared !== true) {
        // Not even the pixel: a Purchase fired here exists for every session that reached
        // the page, including the ones that never paid.
        return { fired: false, why: 'the charge has not cleared' };
      }
      if (!has('keep-browser-event')) {
        // The other direction: dropping the browser event loses the click ids, the consent
        // state and the session that only the browser carries.
        return { fired: false, why: 'browser event removed' };
      }
      sink.pixel.push([
        'track',
        eventNameFor('browser'),
        customData(purchase),
        { eventID: eventIdFor(purchase) },
      ]);
      return { fired: true };
    },
  };
}
