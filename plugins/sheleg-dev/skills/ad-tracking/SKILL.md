---
name: ad-tracking
description: >-
  Comprehensive guide for integrating advertising analytics and conversion tracking
  with Google Analytics 4 (GA4), Google Ads, Meta (Facebook) Pixel, and LinkedIn Insight Tag
  in web applications. Covers Consent Mode v2, standard events, e-commerce tracking,
  advanced matching, Enhanced Conversions, CSP configuration, user identification,
  cross-device tracking, and GDPR/DMA compliance. Use when setting up or modifying
  ad pixel integration, conversion tracking, consent management, purchase event tracking,
  retargeting audiences, or auditing an existing advertising analytics stack.
  Triggers: "ad tracking", "conversion tracking", "facebook pixel", "meta pixel", "fbq",
  "google ads", "google analytics", "GA4", "gtag", "consent mode", "cookie consent",
  "enhanced conversions", "advanced matching", "retargeting"."remarketing",
  "purchase event", "pixel", "CAPI", "linkedin insight", "conversion API",
  "gclid", "UTM", "attribution", "ad funnel", "ROAS tracking", 
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

### Deeper Meta and LinkedIn detail

Read `references/meta-linkedin.md` for the parameter object per event, the
firing wrapper, advanced matching (hashed identifiers, and what must never be
sent) and CAPI deduplication.
## LinkedIn Insight Tag

### Setup

**Env var:** `NEXT_PUBLIC_LINKEDIN_PARTNER_ID` (numeric string)

The LinkedIn Insight Tag is consent-gated (same pattern as Meta Pixel). It loads the `insight.min.js` script and includes a noscript pixel fallback.

```javascript
_linkedin_partner_id = "PARTNER_ID";
window._linkedin_data_partner_ids = window._linkedin_data_partner_ids || [];
window._linkedin_data_partner_ids.push(_linkedin_partner_id);
```

### Conversion Tracking

LinkedIn conversions are configured in Campaign Manager (not in code). The Insight Tag automatically tracks page views, and you define URL-based conversion rules in the LinkedIn Campaign Manager:

1. Campaign Manager → Analyze → Conversion tracking → Create conversion
2. Define URL rules (e.g. `/thank-you`, `/onboarding`)
3. LinkedIn Insight Tag automatically matches page loads to conversion rules

For event-based conversions, use `window.lintrk('track', { conversion_id: 123456 })`.

**Docs:**
- [LinkedIn Insight Tag setup](https://www.linkedin.com/help/lms/answer/a418880)
- [LinkedIn conversion tracking](https://www.linkedin.com/help/lms/answer/a423304)

---

## User Identification

### Cross-Platform Identification Strategy

| Platform | Method | When | What it enables |
|---|---|---|---|
| GA4 | `user_id` via `gtag('config', TAG_ID, { user_id })` | After login/onboarding | Cross-device tracking, audience building |
| GA4 | Enhanced Conversions via `gtag('set', 'user_data', { email })` | After login/onboarding | Better conversion attribution |
| Meta Pixel | Advanced Matching via `fbq('init', PIXEL_ID, { em, fn })` | After login/onboarding | Better conversion attribution, larger custom audiences |
| Mixpanel | `alias()` + `identify()` | After login/onboarding | Merge anonymous → identified user profiles |

**All identification calls should be placed in a single identification component** that runs in the dashboard/authenticated layout. This ensures:
- User data is sent once per session
- All platforms receive identification data at the same time
- Pre-login anonymous events merge into the identified profile

### Alias vs Identify (Mixpanel)

- `alias(userId, anonymousId)` — creates a permanent link between the anonymous and real user ID. Must be called **exactly once** per user, **before** `identify()`. Use a localStorage flag to prevent duplicate calls.
- `identify(userId)` — sets the user ID for all subsequent events.

### Timing

Fire identification in a `useEffect` in the authenticated layout:

```typescript
useEffect(() => {
  // 1. Mixpanel alias + identify
  // 2. GA4 user_id + Enhanced Conversions
  // 3. Meta Advanced Matching
}, [userId, email, name]);
```

---

## Event naming

Read `references/event-tracking.md` → **Recommended Events** and **Parameter
Rules**. GA4 reserves a set of names and silently drops events that collide
with them; the reference lists which.
## E-commerce

Read `references/event-tracking.md` → **Ecommerce Events** for the GA4 item
schema and the full purchase / add_to_cart / begin_checkout set.

**Deduplication is the part that silently doubles revenue.** A purchase fired
from both the browser and the server (Conversions API, server-side GA4) must
carry the SAME `event_id` / `transaction_id`, or both are counted. Test it by
reloading the thank-you page: a purchase that increments twice is a
deduplication bug, not a tracking success.
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

The sections above are the integration surface across four platforms. When the
work is specifically Google's tag — and it usually becomes that — these carry
the depth this file deliberately does not:

| File | Read it when |
|---|---|
| [`references/consent-mode.md`](references/consent-mode.md) | **consent is the task**: advanced vs basic mode and what each still sends, all consent types, region-specific defaults, granular consent with its localStorage schema, the update flow, GTM wiring, exactly what tags do when denied, URL passthrough, ads data redaction, and how to verify in Tag Assistant / DevTools / DebugView |
| [`references/gtag-api.md`](references/gtag-api.md) | you are **calling gtag directly**: every command (`config`, `event`, `set`, `get`, `consent`), tag-ID formats, parameter scope and precedence, `send_to` routing and groups, multi-product configuration, and the Next.js App Router integration including the Docker `NEXT_PUBLIC_*` build-time trap |
| [`references/event-tracking.md`](references/event-tracking.md) | you are **designing the event schema**: recommended vs custom events, naming rules, parameter limits, the item object, the ecommerce funnel, SaaS/subscription events, and a typed `trackEvent` wrapper |
| [`references/performance-security.md`](references/performance-security.md) | the tag is **costing you Lighthouse points or failing CSP**: loading strategies and their measured impact, CSP directives with and without a nonce, EU region endpoints, SPA page_view handling, and verification in the network tab |
| [`references/meta-linkedin.md`](references/meta-linkedin.md) | the work is **Meta or LinkedIn rather than Google**: the parameter object per standard event, the firing wrapper and its consent gate, advanced matching with hashed identifiers and what must never be sent, and deduplication against the Conversions API |

For the page-speed side of the same problem — what the tag does to LCP and TBT,
and what to do about it — see the `frontend-performance` skill in this pack.
