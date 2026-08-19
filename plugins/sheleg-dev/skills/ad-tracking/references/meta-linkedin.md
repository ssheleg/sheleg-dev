# Meta Pixel & LinkedIn — Reference

**Load this when** the work is Meta or LinkedIn rather than Google: the parameter object per standard event, the firing wrapper and its consent gate, advanced matching with hashed identifiers and what must never be sent, and deduplication against the Conversions API.

Moved out of `SKILL.md` when the body was 906 lines against a 500-line budget.
Everything here is detail the body used to carry inline; the body keeps the
setup snippet and the traps.

## Contents

- [Parameter object properties](#parameter-object-properties) — what Meta accepts per event
- [Standard events](#standard-events) — the seventeen, and the four that carry a funnel
- [Firing events](#firing-events) — the wrapper and its consent gate
- [Advanced matching](#advanced-matching) — hashed identifiers
- [What must never be sent](#what-must-never-be-sent) — the categories that are a terms breach, not a tuning choice
- [Deduplication with the Conversions API](#deduplication-with-the-conversions-api) — the contract that stops one purchase counting twice
- [LinkedIn conversion tracking](#linkedin-conversion-tracking) — Insight Tag, Campaign Manager rules, `lintrk`
- [Meta Events Manager verification](#meta-events-manager-verification) — reading it back

### Parameter Object Properties

| Property | Type | Description |
|---|---|---|
| `value` | float | **Required for Purchase.** Monetary amount. |
| `currency` | string | ISO 4217 code (e.g. `USD`, `EUR`). Required with `value`. |
| `content_name` | string | Name of the page/product |
| `content_category` | string | Category (e.g. `subscription`, `tokens`) |
| `content_type` | string | `product` or `product_group` |
| `content_ids` | string[] | Product IDs / SKUs |
| `contents` | object[] | Array of `{ id, quantity }` objects |
| `num_items` | integer | Item count at checkout |
| `predicted_ltv` | float | Predicted lifetime value (for Subscribe) |
| `status` | boolean | Registration status (for CompleteRegistration) |

### Standard Events

Meta defines 17 standard events. The most important for SaaS conversion funnels:

| Event | When | Parameters | Notes |
|---|---|---|---|
| `PageView` | Every page load | (automatic from base code) | Fires from the init script |
| `CompleteRegistration` | User signs up | `content_name` (method), `status: true` | Separate from GA4 `sign_up` |
| `InitiateCheckout` | Checkout started | `value`, `currency`, `content_name`, `content_category`, `num_items` | |
| `Purchase` | Purchase completed | `value` (required), `currency` (required), `content_name`, `content_category`, `content_type`, `contents[]` | `value` + `currency` are **mandatory** for optimisation |
| `Subscribe` | Recurring subscription | `value`, `currency`, `predicted_ltv` | Distinct from one-time Purchase |
| `Lead` | Lead form submitted | (optional params) | |
| `ViewContent` | Key content viewed | `content_name`, `content_category` | |
| `AddToCart` | Item added to cart | `content_name`, `value`, `currency` | |
| `Search` | Search performed | `search_string` | |

### Firing Events

```javascript
// Standard event
fbq('track', 'Purchase', {
  value: 30.00,
  currency: 'USD',
  content_name: 'Monthly Plan',
  content_type: 'product',
  contents: [{ id: 'plan_monthly', quantity: 1 }]
});

// Custom event
fbq('trackCustom', 'ShareDiscount', { promotion: 'share_10_percent' });
```

### Advanced Matching

Advanced Matching sends hashed user data (email, name, phone) to Meta for better conversion attribution. Two approaches:

**1. At init time (initial page load):**

```javascript
fbq('init', 'PIXEL_ID', {
  em: 'user@example.com',     // email — Meta hashes automatically
  fn: 'john',                  // first name (lowercase)
  ln: 'doe',                   // last name (lowercase)
  ph: '1234567890',            // phone (digits only, no formatting)
  ct: 'new york',              // city (lowercase)
  st: 'ny',                    // state (2-letter code)
  zp: '10001',                 // zip code
  country: 'us',               // country (2-letter ISO)
});
```

**2. After user identification (re-init):**

Call `fbq('init', PIXEL_ID, userData)` again after the user logs in. The pixel merges the data. This is the recommended approach for SPA/SSR apps where user data isn't available at first load.

```typescript
export function setFbAdvancedMatching(data: { em?: string; fn?: string }) {
  if (typeof window.fbq === "function" && PIXEL_ID) {
    window.fbq("init", PIXEL_ID, data);
  }
}
```

### What must never be sent

Advanced Matching is the one place a tracking integration can breach Meta's terms
by accident, because the wrapper accepts whatever you hand it and hashes it
without judgement. SHA-256 does **not** make a value safe to send: hashing is a
matching mechanism, not a permission. That the wrapper receives a hash at all is checkable:
`identifiers-reach-the-server-hashed` in `fixtures/assert-dedup-contract.mjs` requires every
`user_data.em` entry to be 64 hex characters and refuses anything with an `@` in it. What may
be hashed in the first place is the table below, and no assertion decides it.

Meta's Business Tools Terms prohibit sharing data that "includes or is based on"
any of these, and the prohibition covers the Pixel, the Conversions API, the
Facebook SDK for App Events, Offline Conversions and the App Events API alike:

| Never send | Why it is not a judgement call |
|---|---|
| Health information | Named in the terms. Meta also runs a signals-filtering mechanism that drops data it categorises as potentially health-related before it reaches ads ranking — so the data is both a breach and useless |
| Financial information | Named in the terms |
| Consumer report information | Named in the terms |
| Social security numbers, credit card numbers | Named as identifiers Meta does not permit |
| Data from or about children under 13 | Named in the terms |
| Anything sensitive under applicable law or industry guidance | The terms defer to local definitions, so the list above is a floor and not a ceiling |

**The event NAME is covered too**, and this is the half integrations miss: "the
names you choose and criteria you establish for your events, conversions, and any
custom audiences you create must not reflect, imply or be based on any category of
sensitive information." A `trackCustom('DiabetesPlanPurchase')` is a breach with
an empty parameter object.

**The practical rule:** the eleven Advanced Matching keys — `em`, `fn`, `ln`,
`ph`, `external_id`, `ge`, `db`, `ct`, `st`, `zp`, `country` — are the whole
allowed surface. Anything you were about to add beside them is the thing to stop
and check.

Source: Meta Business Tools Terms and the Sensitive Health Information help
centre, read 2026-08-16. Re-read before quoting: the categories move.

### Deduplication with the Conversions API

**Send both, and let Meta discard one.** Browser and server events are not an
either/or — the pixel is blocked often enough that server-side is the reliable
source, and the browser event carries signals the server cannot see. The whole
job is making sure the pair collapses into one conversion instead of two.

**Two fields must match, not one.** Meta compares:

| Pixel | Conversions API |
|---|---|
| `eventID` | `event_id` |
| `event` (the event name) | `event_name` |

Both. An integration that generates a shared `event_id` and lets the two sides
disagree on the name — `Purchase` in the browser, `purchase` on the server — has
two events that will never deduplicate, and the revenue is counted twice. This is
the single most common way this goes wrong, because the `event_id` half is
obvious and the `event_name` half is not.

**The window is 48 hours**, and it runs from when Meta receives the *first* event
carrying a given `event_id` — not from when the purchase happened. A server event
retried out of a dead-letter queue two days later is a second conversion.

```javascript
// One id, generated once, used by both sides.
const eventId = crypto.randomUUID();

// Browser
fbq('track', 'Purchase', { value: 30.00, currency: 'USD' }, { eventID: eventId });

// Server — the SAME event_name string, not a variant
await sendCapi({
  event_name: 'Purchase',     // must equal the pixel's 'Purchase' exactly
  event_id: eventId,
  event_time: Math.floor(Date.now() / 1000),
  action_source: 'website',
  user_data: { /* hashed */ },
  custom_data: { value: 30.00, currency: 'USD' },
});
```

**The alternative method, and its trap.** Where you cannot thread an id through,
Meta will also deduplicate on `event_name` plus `fbp` and/or `external_id`, held
consistent across both sources. It is weaker in a specific direction: *"server
events will not be discarded if a browser event has not been received in the past
48 hours, even if an identical browser event arrives after the server event."*
So the browser event must arrive **first**. For a purchase confirmed by a webhook
— which is the pattern this skill teaches, because the webhook is the payment —
the server event usually arrives first, and this method then does nothing. Use
`event_id`.

Neither method deduplicates within a single source: two pixel fires of the same
purchase are two conversions no matter what.

**Proved, not asserted.** `fixtures/purchase-pixel-browser.json` and
`fixtures/purchase-capi-server.json` are the two payloads one purchase produces, and
`fixtures/assert-dedup-contract.mjs` compares them: `pixel-and-capi-carry-one-event-name`
fails an emitter that sends `Purchase` from the browser and a lowercased variant from the
server, which is the half of this contract that gets missed. The shape itself is a ratchet —
`the-shipped-capi-fixture-is-what-a-correct-emitter-sends` requires the emitted body to equal
the fixture byte for byte, so **the fixtures are the reference output rather than an
illustration**.

Source: [Deduplicate pixel and Conversions API
events](https://developers.facebook.com/docs/marketing-api/conversions-api/deduplicate-pixel-and-server-events),
read 2026-08-16.

### LinkedIn conversion tracking

**Env var:** `NEXT_PUBLIC_LINKEDIN_PARTNER_ID` (numeric string).

The Insight Tag is consent-gated on the same wrapper as the Meta Pixel — it loads
`insight.min.js` and ships a `noscript` pixel fallback.

```javascript
_linkedin_partner_id = "PARTNER_ID";
window._linkedin_data_partner_ids = window._linkedin_data_partner_ids || [];
window._linkedin_data_partner_ids.push(_linkedin_partner_id);
```

**Conversions are configured in Campaign Manager, not in code.** The Insight Tag
tracks page views by itself, and URL rules match those page loads to conversions:

1. Campaign Manager → Analyze → Conversion tracking → Create conversion
2. Define the URL rules (`/thank-you`, `/onboarding`)
3. The tag matches page loads against them

For an event-based conversion rather than a URL one:
`window.lintrk('track', { conversion_id: 123456 })`.

**LinkedIn has no equivalent of the `event_id` contract above.** There is no
browser/server pair to deduplicate here, which is why a URL rule that matches a
page a user can refresh counts every refresh — put the rule on a page reached once,
or use `lintrk` from the code path that actually completed the action.

**Docs:**
- [LinkedIn Insight Tag setup](https://www.linkedin.com/help/lms/answer/a418880)
- [LinkedIn conversion tracking](https://www.linkedin.com/help/lms/answer/a423304)

### Meta Events Manager Verification

1. Install the **Meta Pixel Helper** Chrome extension
2. Go to Events Manager → Data Sources → select Pixel → **Test Events**
3. Enter your site URL and walk through the funnel
4. Verify events appear in real-time with correct parameters
5. Check Advanced Matching: Events Manager → Settings → Advanced Matching tab

### Best Practices

- Always include `value` and `currency` on Purchase events (required for ROAS optimisation)
- Use `predicted_ltv` on Subscribe events for better Value-Based Optimisation
- Fire `CompleteRegistration` immediately on signup, not after onboarding
- Use standard events over custom events when possible — Meta optimises ads for standard events
- Include `contents[]` array with product IDs for Advantage+ catalog campaigns
- The `PageView` event fires automatically from the base code — do not fire it manually
- For SPAs, the pixel tracks route changes automatically via pushState/replaceState

**Docs:**
- [Meta Pixel standard events specifications](https://www.facebook.com/business/help/402791146561655?id=1205376682832142)
- [Best practices for Meta Pixel setup](https://www.facebook.com/business/help/218844828315224?id=1205376682832142)
- [Conversion tracking & advanced matching](https://developers.facebook.com/docs/meta-pixel/implementation/conversion-tracking#advanced_match)
- [Meta Pixel reference](https://developers.facebook.com/docs/meta-pixel/reference)
- [Advanced Matching parameters](https://developers.facebook.com/docs/meta-pixel/advanced/advanced-matching)
- [Meta Pixel Helper extension](https://www.facebook.com/business/help/198460973553498)

---

