---
name: ad-tracking
description: >-
  Use when setting up or modifying ad pixel integration, conversion tracking, consent
  management, purchase event tracking, retargeting audiences, or auditing an existing
  advertising analytics stack. Covers Google Analytics 4, Google Ads, Meta (Facebook) Pixel and
  LinkedIn Insight Tag in web applications: Consent Mode v2, standard events, e-commerce
  tracking, advanced matching, Enhanced Conversions, CSP configuration, user identification,
  cross-device tracking, and GDPR/DMA compliance. Triggers - "ad tracking", "conversion
  tracking", "meta pixel", "fbq", "google ads", "GA4", "gtag", "consent mode", "cookie consent",
  "enhanced conversions", "retargeting", "purchase event", "CAPI", "gclid", "UTM",
  "attribution", "отслеживание конверсий", "пиксель Meta", "согласие на куки", "ретаргетинг",
  "аналитика рекламы". Not for running the ad campaigns themselves.
---

# Advertising Analytics & Conversion Tracking Integration

Complete reference for integrating Google Analytics 4, Google Ads, Meta (Facebook) Pixel, and LinkedIn Insight Tag into web applications with proper consent management, standard event mapping, user identification, and GDPR/DMA compliance.

---

## What this skill covers

GA4, Google Ads, Meta Pixel and LinkedIn Insight Tag, all behind Consent Mode
v2. The body carries the minimal setup and the traps; the tables, schemas and
per-framework wiring live in `references/`, listed at the bottom.
## Architecture Overview

A modern advertising analytics stack consists of multiple pixels/tags that must all respect the same consent state. The architecture follows this pattern:

```
┌──────────────────────────────────────────────────────────┐
│                    CONSENT LAYER                          │
│  Cookie Consent Banner → localStorage → consent state     │
│  All pixels gated by the same consent storage key         │
└────────────────────┬─────────────────────────────────────┘
                     │ granted / denied
     ┌───────────────┼──────────────────┬──────────────────┐
     ▼               ▼                  ▼                  ▼
┌─────────┐   ┌────────────┐   ┌──────────────┐   ┌────────────┐
│  GA4 +   │   │  Meta      │   │  LinkedIn    │   │  Mixpanel  │
│  Google  │   │  Pixel     │   │  Insight     │   │  (product  │
│  Ads     │   │  (fbq)     │   │  Tag         │   │  analytics)│
└─────────┘   └────────────┘   └──────────────┘   └────────────┘
     │               │                  │                  │
     ▼               ▼                  ▼                  ▼
  Consent         Consent-gated     Consent-gated      Consent-gated
  Mode v2         (render only      (render only        (opt_in /
  (built-in)      when granted)     when granted)       opt_out)
```

**Key principle:** GA4 uses its own built-in Consent Mode v2 (defaults denied, updates on consent). All other pixels (Meta, LinkedIn, Mixpanel) use a consent-gated pattern — they are not rendered at all until the user grants consent. A shared `CustomEvent` allows dynamic consent changes without page reload.

---

## Consent

Read `references/consent-mode.md` for all seven consent signals, Advanced vs
Basic mode, region-specific defaults, granular consent and GTM wiring. Consent
Mode v2 is **mandatory** in the EU/EEA since March 2024.

**The order is the whole thing, and getting it wrong is invisible:**

```
1. dataLayer init + gtag() stub
2. gtag('consent', 'default', { …'denied', wait_for_update: 500 })
3. restore a stored decision → gtag('consent', 'update', …)
4. load gtag.js (async)
5. gtag('js', new Date()) + gtag('config', TAG_ID)
```

Steps 1–3 must run **synchronously before** gtag.js loads. A page that sets
defaults after the script has loaded looks correct in every test that begins by
accepting consent, and loses the denied population entirely.

**Denied is not off.** With Advanced mode Google still receives cookieless
pings and models conversions from them — roughly two thirds of the otherwise
lost data. Blocking the script instead throws that away.
## Google Analytics 4

### Setup

**Env var:** `NEXT_PUBLIC_GA_MEASUREMENT_ID` (format: `G-XXXXXXXXXX`)

**Script loading:**

```html
<!-- 1. Consent defaults (MUST be first) -->
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('consent', 'default', {
    ad_storage: 'denied', ad_user_data: 'denied',
    ad_personalization: 'denied', analytics_storage: 'denied',
    wait_for_update: 500
  });
  // Restore prior consent
  try {
    if (localStorage.getItem('consent_key') === 'granted') {
      gtag('consent', 'update', {
        ad_storage: 'granted', ad_user_data: 'granted',
        ad_personalization: 'granted', analytics_storage: 'granted'
      });
    }
  } catch(e) {}
</script>

<!-- 2. Load gtag.js -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>

<!-- 3. Configure -->
<script>
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX', { allow_enhanced_conversions: true });
</script>
```

### Commands and events

Read `references/gtag-api.md` → **Commands** for `config` / `event` / `set` /
`get` / `consent` with parameter scope and precedence, and
`references/event-tracking.md` → **Recommended Events** for the GA4 names
Google Ads can import (`sign_up`, `login`, `begin_checkout`, `purchase`,
`generate_lead`, `view_item`) with their required parameters.

**SPA page views are not automatic when you send them yourself.** Enhanced
measurement fires `page_view` on History API changes; adding a manual one on
route change double-counts every navigation. Send manual page views only for
hash routing.
### SPA Page Tracking

GA4 with enhanced measurement automatically tracks `page_view` via the History API for Single Page Applications. Manual `page_view` tracking is only needed for hash routing (`#/path`). Consent state persists across SPA route changes.

**Docs:**
- [Set up the Google tag](https://developers.google.com/tag-platform/gtagjs)
- [gtag.js API reference](https://developers.google.com/tag-platform/gtagjs/reference)
- [Recommended events](https://developers.google.com/tag-platform/gtagjs/reference/events)
- [Event parameters](https://developers.google.com/tag-platform/gtagjs/reference/parameters)
- [Data routing & groups](https://developers.google.com/tag-platform/gtagjs/routing)

---

## Google Ads Conversion Tracking

### Architecture

GA4 and Google Ads share the same gtag.js snippet. When `NEXT_PUBLIC_GOOGLE_ADS_ID` (format: `AW-XXXXXXXXX`) is set, add a second `config` call:

```javascript
gtag('config', 'G-XXXXXXXXXX');  // GA4
gtag('config', 'AW-XXXXXXXXX');  // Google Ads
```

Both share consent state, first-party cookies, and the dataLayer pipeline.

### Enhanced Conversions

Enhanced Conversions improve attribution by matching hashed user data (email, phone) with Google accounts. Setup:

1. Enable in GA4 config: `allow_enhanced_conversions: true`
2. Set user data before conversion events fire:

```javascript
gtag('set', 'user_data', {
  email: 'user@example.com',        // Google hashes automatically
  phone_number: '+1234567890',       // optional
});
```

3. Enable in Google Ads console: Tools → Conversions → Enhanced conversions → Turn on

### user_id (Cross-Device Tracking)

Set GA4 `user_id` after authentication to enable cross-device tracking and audience building:

```javascript
gtag('config', 'G-XXXXXXXXXX', {
  user_id: 'USER_123',
  send_page_view: false    // prevent duplicate page_view
});
```

### gclid Preservation Through External Redirects

The `gclid` from Google Ads auto-tagging is stored in the `_gcl_aw` first-party cookie. This cookie persists across external redirects (e.g. Stripe Checkout → return URL) because it's set on your domain. No additional code needed.

### Google Ads console setup

Read `references/gtag-api.md` → **Multi-Product Configuration** for wiring one
gtag loader to both GA4 and Ads. In the Ads console the conversion action must
be **Primary** and its attribution window set before the first click lands, or
early conversions are attributed under the old settings and cannot be
recomputed.
## Meta (Facebook) Pixel

### Setup

**Env var:** `NEXT_PUBLIC_META_PIXEL_ID` (numeric string)

**Base code (consent-gated):**

```javascript
!function(f,b,e,v,n,t,s){if(f.fbq)return;n=f.fbq=function(){n.callMethod?
n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!f._fbq)f._fbq=n;
n.push=n;n.loaded=!0;n.version='2.0';n.queue=[];t=b.createElement(e);t.async=!0;
t.src=v;s=b.getElementsByTagName(e)[0];s.parentNode.insertBefore(t,s)}
(window,document,'script','https://connect.facebook.net/en_US/fbevents.js');
fbq('init', 'PIXEL_ID');
fbq('track', 'PageView');
```

**noscript fallback (required for pixel verification):**

```html
<noscript>
  <img height="1" width="1" style="display:none"
    src="https://www.facebook.com/tr?id=PIXEL_ID&ev=PageView&noscript=1"/>
</noscript>
```

### Standard Events

Meta defines 17 standard events. The four that carry a SaaS funnel are
`CompleteRegistration`, `InitiateCheckout`, `Purchase` and `Subscribe`, and only
`Purchase` has mandatory parameters: `value` and `currency`, without which Meta
cannot optimise. The full table — every event, its parameters and the traps —
is in `references/meta-linkedin.md` → **Standard events**.

### Deeper Meta and LinkedIn detail

Read `references/meta-linkedin.md` for the parameter object per event, the
firing wrapper, advanced matching (hashed identifiers, and what must never be
sent) and CAPI deduplication.
## LinkedIn Insight Tag

Consent-gated on the same wrapper as the Meta Pixel, env var
`NEXT_PUBLIC_LINKEDIN_PARTNER_ID`. Conversions are configured in Campaign Manager
rather than in code, so there is nothing to deduplicate and nothing that fails
silently in the bundle — but a URL rule on a refreshable page counts every
refresh. Setup snippet, the Campaign Manager steps and `lintrk` are in
`references/meta-linkedin.md` → **LinkedIn conversion tracking**.

## User Identification

One rule the body keeps, because getting it wrong corrupts attribution rather
than losing it: **identify before you track, never after**. An event fired for an
anonymous id and re-attributed later is two users to every platform that already
ingested it. The per-platform strategy, the Mixpanel `alias` vs `identify`
distinction and the timing rules are in `references/event-tracking.md` →
**User identification**.

## Event naming

Read `references/event-tracking.md` → **Recommended Events** and **Parameter
Rules**. GA4 reserves a set of names and silently drops events that collide
with them; the reference lists which.
## E-commerce

Read `references/event-tracking.md` → **Ecommerce Events** for the GA4 item
schema and the full purchase / add_to_cart / begin_checkout set.

**Deduplication is the part that silently doubles revenue.** A purchase fired
from both the browser and the server (Conversions API, server-side GA4) must
carry the SAME `event_id` / `transaction_id`, or both are counted. Run
`fixtures/assert-dedup-contract.mjs` rather than reloading the thank-you page:
`pixel-and-capi-carry-one-event-id` and `pixel-and-capi-carry-one-event-name` fail an
emitter that shares one field and not the other,
`no-purchase-reported-before-the-charge-cleared` fails one that reports from the redirect,
and `the-browser-event-is-kept` fails one that drops the pixel. `--self-test` deletes each
rule and watches the matching assertion go red.

**A purchase is not a browser event, and that decides where it comes from.**
Every other event on the list is something a person did in a tab, so the browser
is its natural source. A purchase is the outcome of a charge that succeeded
inside a payment system, and the only thing that knows it succeeded is the
provider's webhook. Firing it from the thank-you page means firing it from the
one place that has no idea whether the charge cleared — which is why a purchase
event exists for every session that reached the page and a refund exists for
none of them.

The consequence is an ordering, not a preference:

1. **The webhook handler is the source of truth for the purchase.** It writes the
   entitlement, and the same handler sends the server-side conversion. If the
   handler is where the money is recorded, it is where the event belongs.
2. **The browser event stays, and it stays subordinate.** Keep it for the
   attribution signals only the browser carries (click ids, the consent state,
   the session), give it the `event_id` the server will reuse, and treat the
   server as authoritative when they disagree.
3. **Everything the browser loses, it loses closest to the money.** Blockers, a
   mobile browser terminating a tab on redirect, a payment provider's hosted page
   ending the session before the return leg — each of them removes the *last*
   step preferentially, so the browser-only purchase count is biased low by an
   amount you cannot measure from inside the browser.

Reconcile against the provider rather than the analytics dashboard: the count of
succeeded charges in a period is a number the payment system will give you
exactly, and it is the only external check on this event that is not itself
telemetry. See `stripe-billing` → **Depending on one provider** for what else
that reconciliation surfaces.
## Content Security Policy

Read `references/performance-security.md` → **Content Security Policy** for the
full directive set per platform.

**The trap:** a nonce on the gtag loader is not enough — Google injects further
scripts at runtime, so `script-src` needs the Google domains as well, and a CSP
that passes on the landing page can still break the checkout where the Ads
conversion tag loads.
## Next.js

Read `references/gtag-api.md` → **Next.js / React Integration** for the
component tree, and `references/performance-security.md` → **Script Loading
Strategies** for `next/script` strategy choice and SPA route changes.

**Two traps that are not obvious from either:**

- `NEXT_PUBLIC_*` is inlined at **build** time. In a Docker build the variable
  must exist in the builder stage; injecting it at runtime leaves the literal
  string in the bundle and every event goes nowhere.
- An authenticated area and an embed/widget page need different gating — the
  dashboard already has consent, an embed may have none and must not assume
  the parent page's.
## UTM Attribution

### Capture Flow

1. `UtmCapture` component reads UTM params from URL on page load → stores in localStorage
2. On registration (credentials): read UTM from localStorage, send in POST body, save to DB
3. On registration (OAuth): UTM persists in localStorage through redirect → synced after return via API call
4. Mixpanel `people.set_once()` stores initial UTM as permanent user properties
5. Clear localStorage after successful DB sync

### UTM Parameters

| Parameter | Purpose | Example |
|---|---|---|
| `utm_source` | Traffic source | `google`, `facebook`, `newsletter` |
| `utm_medium` | Marketing medium | `cpc`, `social`, `email` |
| `utm_campaign` | Campaign name | `spring_sale_2025` |
| `utm_content` | Ad creative variant | `banner_a`, `text_link` |
| `utm_term` | Paid search keyword | `ai+chatbot` |

### gclid / fbclid / li_fat_id

Google, Meta, and LinkedIn append their own click IDs to URLs:
- `gclid` — Google Ads click ID (stored in `_gcl_aw` cookie by gtag.js automatically)
- `fbclid` — Meta click ID (stored in `_fbc` cookie by fbevents.js automatically)
- `li_fat_id` — LinkedIn click ID (handled by Insight Tag)

These are handled automatically by the respective SDKs. Do not strip them from URLs.

---

## Verification

Read `references/performance-security.md` → **Debug & Testing** for the full
per-platform checklist (GA4 DebugView, Meta Test Events, LinkedIn tag helper)
and the consent round-trip.

**The check that catches most of it:** open the site in a fresh incognito
window, deny consent, and confirm in DevTools → Network that no `_ga` or
`_gcl_*` cookie is set and that collect requests carry `gcs=G100`. A tag that
fires correctly *after* consent while ignoring the denied default is the
failure this whole skill exists to prevent, and it looks fine in every test
that starts by accepting.
## Troubleshooting

### Common Issues

| Problem | Cause | Fix |
|---|---|---|
| No events in GA4 | Consent defaults not set before gtag.js loads | Ensure consent `default` call is **before** the script tag |
| CSP violations in console | Missing domain in CSP header | Add the domain to the correct CSP directive |
| Meta Pixel not firing | Consent-gated component not rendering | Check localStorage consent value, check CustomEvent listener |
| Duplicate `PageView` events | Multiple pixel instances or route change listeners | Ensure pixel init code has `if(f.fbq)return;` guard |
| Purchase events without value | Missing `value`/`currency` params | Both GA4 and Meta **require** these for conversion optimisation |
| Advanced Matching not working | `fbq('init')` called before pixel SDK loads | Ensure `fbevents.js` is loaded before calling `setFbAdvancedMatching()` |
| Enhanced Conversions not matching | `user_data` set after conversion event | Call `setEnhancedConversionData()` **before** the conversion event fires |
| gclid lost after Stripe redirect | — (shouldn't happen) | `_gcl_aw` cookie is first-party, persists across redirects |
| Events firing on localhost | Missing `isLocal` guard | Add `if (window.location.hostname === 'localhost') return;` |

### Debug Mode

Enable debug logging for local development:

```typescript
const isLocal = window.location.hostname === "localhost";
if (isLocal) {
  console.debug("[Analytics]", eventName, params);
  return; // don't fire real events
}
```

---

## Official documentation

Google: [Consent Mode v2](https://developers.google.com/tag-platform/security/guides/consent) ·
[gtag.js](https://developers.google.com/tag-platform/gtagjs/reference) ·
[GA4 events](https://developers.google.com/analytics/devguides/collection/ga4/reference/events).
Meta: [Pixel](https://developers.facebook.com/docs/meta-pixel) ·
[Conversions API](https://developers.facebook.com/docs/marketing-api/conversions-api).
LinkedIn: [Insight Tag](https://www.linkedin.com/help/lms/answer/a418880).
Compliance: [EU DMA](https://digital-markets-act.ec.europa.eu/).
## Deep references

The sections above are the integration surface across four platforms; these carry
the depth this file deliberately does not. Each opens with its own **Load this
when** line, so the trigger has one home and this table stays an index.

| File | Read it when |
|---|---|
| [`references/consent-mode.md`](references/consent-mode.md) | **consent is the task** |
| [`references/gtag-api.md`](references/gtag-api.md) | you are **calling gtag directly** |
| [`references/event-tracking.md`](references/event-tracking.md) | you are **designing the event schema** |
| [`references/performance-security.md`](references/performance-security.md) | the tag **costs Lighthouse points or fails CSP** |
| [`references/meta-linkedin.md`](references/meta-linkedin.md) | the work is **Meta or LinkedIn rather than Google** |

For the page-speed side of the same problem — what the tag does to LCP and TBT,
and what to do about it — see the `frontend-performance` skill in this pack.
