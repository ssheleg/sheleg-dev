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
  "enhanced conversions", "advanced matching", "retargeting", "remarketing",
  "purchase event", "pixel", "ad pixel", "CAPI", "linkedin insight", "conversion API",
  "gclid", "UTM", "attribution", "ad funnel", "ROAS tracking", "ad analytics".
---

# Advertising Analytics & Conversion Tracking Integration

Complete reference for integrating Google Analytics 4, Google Ads, Meta (Facebook) Pixel, and LinkedIn Insight Tag into web applications with proper consent management, standard event mapping, user identification, and GDPR/DMA compliance.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Consent Management (Consent Mode v2)](#consent-management)
3. [Google Analytics 4 (GA4)](#google-analytics-4)
4. [Google Ads Conversion Tracking](#google-ads-conversion-tracking)
5. [Meta (Facebook) Pixel](#meta-facebook-pixel)
6. [LinkedIn Insight Tag](#linkedin-insight-tag)
7. [User Identification & Cross-Device Tracking](#user-identification)
8. [Standard Events Mapping (Cross-Platform)](#standard-events-mapping)
9. [E-Commerce / Purchase Tracking](#e-commerce-tracking)
10. [Content Security Policy (CSP)](#content-security-policy)
11. [Next.js / React Implementation Patterns](#nextjs-implementation)
12. [UTM Attribution](#utm-attribution)
13. [Testing & Verification](#testing-and-verification)
14. [Troubleshooting](#troubleshooting)
15. [Official Documentation Links](#official-documentation-links)
16. [Deep references](#deep-references)

---

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

## Consent Management

### Consent Mode v2 (Google)

Google Consent Mode v2 is **mandatory** for EU/EEA since March 2024 (DMA compliance). It controls how Google tags behave before and after user consent.

**Four consent signals:**

| Signal | Controls | Default |
|---|---|---|
| `analytics_storage` | GA4 cookies (`_ga`, `_ga_*`) | `denied` |
| `ad_storage` | Google Ads cookies (`_gcl_*`, `_gac_*`) | `denied` |
| `ad_user_data` | Sending user data to Google for ads | `denied` |
| `ad_personalization` | Remarketing / personalized ads | `denied` |

**Critical implementation order:**

```
1. dataLayer init + gtag() function stub
2. gtag('consent', 'default', { all signals: 'denied', wait_for_update: 500 })
3. Check localStorage → if granted → gtag('consent', 'update', { all: 'granted' })
4. Load gtag.js script (async)
5. gtag('js', new Date()) + gtag('config', TAG_ID)
```

Consent defaults **MUST** execute synchronously before the gtag.js script loads. The `wait_for_update: 500` gives the CMP time to update consent before tags fire.

**When consent is denied, Google still collects "cookieless pings"** — anonymised, aggregated data for conversion modelling. This is the key advantage of Consent Mode over simply not loading the tag.

### Consent Banner Requirements (GDPR / DMA)

- Show on first visit only (check localStorage)
- Offer explicit **Accept** and **Decline** buttons (no pre-ticked boxes)
- On accept: `localStorage.setItem(key, 'granted')` + `gtag('consent', 'update', { all: 'granted' })`
- On decline: `localStorage.setItem(key, 'denied')` + `gtag('consent', 'update', { all: 'denied' })`
- Consent updates must happen **on the same page, before any navigation**
- Expose a global function (e.g. `window.appCookieSettings()`) to re-open the banner
- Dispatch a `CustomEvent` so consent-gated pixels (Meta, LinkedIn) can react without page reload
- Use `role="dialog"` and `aria-label` for accessibility
- Link to the privacy policy

### Consent-Gated Pattern (for non-Google pixels)

Meta Pixel, LinkedIn Insight, and similar pixels don't have a built-in consent mode. Instead, use a consent-gated component pattern:

```typescript
"use client";
import { useState, useEffect } from "react";
import Script from "next/script";

export function ConsentGatedPixel() {
  const [consented, setConsented] = useState(false);

  useEffect(() => {
    // 1. Check initial consent from localStorage
    try {
      setConsented(localStorage.getItem(CONSENT_KEY) === "granted");
    } catch {}

    // 2. Listen for dynamic consent changes
    const handler = (e: Event) => {
      setConsented((e as CustomEvent).detail?.granted === true);
    };
    window.addEventListener(CONSENT_CHANGE_EVENT, handler);
    return () => window.removeEventListener(CONSENT_CHANGE_EVENT, handler);
  }, []);

  // 3. Don't render anything until consent is granted
  if (!consented) return null;

  return <Script ... />;
}
```

This pattern ensures:
- Pixel script is **never loaded** before consent (no cookies set, no requests sent)
- Pixel loads immediately if consent was previously granted (localStorage check)
- Pixel activates dynamically if user grants consent mid-session (CustomEvent listener)

### updateConsent() — Unified Consent Update

The consent update function should:
1. Persist to localStorage
2. Update Google Consent Mode (`gtag('consent', 'update', ...)`)
3. Dispatch a CustomEvent for non-Google pixels

```typescript
export function updateConsent(granted: boolean) {
  const state = granted ? "granted" : "denied";
  try { localStorage.setItem(CONSENT_KEY, state); } catch {}

  if (typeof window.gtag === "function") {
    window.gtag("consent", "update", {
      ad_storage: state,
      ad_user_data: state,
      ad_personalization: state,
      analytics_storage: state,
    });
  }

  window.dispatchEvent(
    new CustomEvent(CONSENT_CHANGE_EVENT, { detail: { granted } })
  );
}
```

**Docs:**
- [Google Consent Mode setup](https://developers.google.com/tag-platform/security/guides/consent?consentmode=advanced)
- [Consent Mode for EEA](https://support.google.com/google-ads/answer/13554116)

---

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

### GA4 API Commands

| Command | Purpose | Example |
|---|---|---|
| `config` | Configure a target, establish data flow | `gtag('config', 'G-XXXXXX')` |
| `event` | Send event data | `gtag('event', 'login', { method: 'Google' })` |
| `set` | Set params for all subsequent events | `gtag('set', 'user_data', { email: '...' })` |
| `get` | Read values (client_id, session_id) | `gtag('get', 'G-XXXXXX', 'client_id', cb)` |
| `consent` | Set/update consent state | `gtag('consent', 'update', { ... })` |

### GA4 Recommended Events (for Google Ads)

These event names are pre-defined by Google and automatically recognised by Google Ads when GA4 is linked:

| Event | When to fire | Required parameters |
|---|---|---|
| `sign_up` | User registration | `method` |
| `login` | User login | `method` |
| `begin_checkout` | Checkout started | `value`, `currency`, `items[]` |
| `purchase` | Purchase completed | `transaction_id`, `value`, `currency`, `items[]` |
| `generate_lead` | Lead form submitted | `value`, `currency` |
| `view_item` | Product/plan viewed | `value`, `currency`, `items[]` |
| `page_view` | Page load (automatic with enhanced measurement) | — |

**Important:** For custom events tracked via a unified `trackEvent()` helper, consider whether GA4 should receive parameters or only the event name. Custom dimensions in GA4 have limited cardinality and poor reporting UX. A common pattern is to bake context into the event name itself (e.g. `sub_purchased_month`, `tokens_purchased_100`) rather than using custom parameters.

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

### Google Ads Console Setup

After deploying code:

1. **Link GA4 to Google Ads:** GA4 Admin → Product links → Google Ads links → Link
2. **Import key events as conversions:** Google Ads → Tools → Conversions → Import → GA4 → select `purchase`, `sign_up`, `begin_checkout`, `generate_lead`
3. **Configure conversion values:** Set `purchase` as primary (value-based bidding), others as secondary
4. **Build remarketing audiences:** GA4 → Audiences (e.g. "Started checkout but didn't purchase") — auto-syncs to linked Ads account
5. **Enable Enhanced Conversions:** Google Ads → Tools → Conversions → select conversion → Enhanced conversions → Turn on

**Docs:**
- [Google Ads conversion tracking](https://support.google.com/google-ads/answer/6095947)
- [Enhanced conversions](https://support.google.com/google-ads/answer/11062876)
- [Import GA4 conversions](https://support.google.com/google-ads/answer/11957412)

---

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

## Standard Events Mapping

Cross-platform event mapping for common conversion actions:

| User Action | GA4 Event | Meta Pixel Event | Mixpanel Event | Notes |
|---|---|---|---|---|
| Page view | `page_view` (auto) | `PageView` (auto) | `$mp_web_page_view` (auto) | All automatic |
| Registration | `sign_up` | `CompleteRegistration` | `sign_up` | Different event names! |
| Login | `login` | — | `login` | Meta has no login event |
| Start checkout | `begin_checkout` | `InitiateCheckout` | `begin_checkout` | |
| Purchase | `purchase` | `Purchase` | `purchase` | Both need `value`+`currency` |
| Subscribe | `purchase` (with items) | `Subscribe` | `purchase` (with `item_category`) | Meta has distinct Subscribe |
| Lead form | `generate_lead` | `Lead` | `generate_lead` | |
| View product | `view_item` | `ViewContent` | — | |
| Cookie consent | — | — | `cookie_consent` | Product analytics only |

**Key nuance:** Meta's `Purchase` and `Subscribe` are **separate** events. For recurring subscriptions, fire **both** `Purchase` (for ROAS) and `Subscribe` (for subscription optimisation). For one-time purchases (e.g. token bundles), fire only `Purchase`.

---

## E-Commerce Tracking

### Unified Purchase Helper

Create a single `trackPurchase()` function that fires to all platforms:

```typescript
export function trackPurchase(opts: {
  transaction_id: string;
  value: number;
  currency?: string;
  item_category: "subscription" | "tokens";
  item_name: string;
  ga_slug: string;           // baked-in GA4 event name suffix
  quantity?: number;
}) {
  const currency = opts.currency ?? "USD";
  const qty = Math.max(opts.quantity ?? 1, 1);

  // GA4: standard `purchase` + descriptive `purchase_{slug}`
  if (typeof window.gtag === "function") {
    window.gtag("event", "purchase", {
      transaction_id: opts.transaction_id,
      value: opts.value,
      currency,
      items: [{ item_id: opts.ga_slug, item_name: opts.item_name,
                item_category: opts.item_category, price: opts.value / qty,
                quantity: qty }],
    });
    window.gtag("event", `purchase_${opts.ga_slug}`);
  }

  // Mixpanel: rich properties
  if (typeof window.mixpanel?.track === "function") {
    window.mixpanel.track("purchase", {
      transaction_id: opts.transaction_id, value: opts.value,
      currency, item_category: opts.item_category,
      item_name: opts.item_name, quantity: qty,
    });
  }

  // Meta Pixel: Purchase standard event
  if (typeof window.fbq === "function") {
    window.fbq("track", "Purchase", {
      value: opts.value, currency,
      content_name: opts.item_name,
      content_category: opts.item_category,
      content_type: "product",
      contents: [{ id: opts.ga_slug, quantity: qty }],
    });
  }
}
```

### GA4 E-Commerce Event Spec

GA4 e-commerce events require an `items[]` array:

```javascript
{
  item_id: "sku_123",           // required
  item_name: "Pro Plan",        // required
  item_category: "subscription",
  price: 30.00,
  quantity: 1,
  item_brand: "YourApp",       // optional
  item_variant: "monthly",      // optional
}
```

**GA4 e-commerce funnel:** `view_item` → `add_to_cart` → `begin_checkout` → `purchase`

Not all steps are required. At minimum, track `begin_checkout` and `purchase` with `items[]` for Google Ads conversion value optimisation.

### Deduplication

Always include `transaction_id` in purchase events. Both GA4 and Meta deduplicate events with the same transaction ID within a window:
- GA4: deduplicates within 24 hours
- Meta: use the same `event_id` parameter or rely on `order_id` in contents

---

## Content Security Policy

When adding tracking pixels, update CSP headers. Required domains per platform:

### Google Analytics + Ads

| Directive | Domains |
|---|---|
| `script-src` | `https://*.googletagmanager.com`, `https://*.google-analytics.com`, `https://*.googleadservices.com` |
| `img-src` | `https://*.googletagmanager.com`, `https://*.google-analytics.com`, `https://*.googleadservices.com`, `https://*.google.com`, `https://*.doubleclick.net` |
| `connect-src` | `https://*.google-analytics.com`, `https://analytics.google.com`, `https://*.googleadservices.com`, `https://*.google.com`, `https://*.doubleclick.net` |

### Meta (Facebook) Pixel

| Directive | Domains |
|---|---|
| `script-src` | `https://connect.facebook.net` |
| `img-src` | `https://www.facebook.com` |
| `connect-src` | `https://www.facebook.com`, `https://connect.facebook.net` |

### LinkedIn Insight Tag

| Directive | Domains |
|---|---|
| `script-src` | `https://snap.licdn.com` |
| `img-src` | `https://px.ads.linkedin.com` |
| `connect-src` | `https://px.ads.linkedin.com`, `https://snap.licdn.com` |

### Mixpanel

| Directive | Domains |
|---|---|
| `script-src` | `https://*.mxpnl.com` |
| `img-src` | `https://*.mxpnl.com`, `https://*.mixpanel.com` |
| `connect-src` | `https://*.mxpnl.com`, `https://*.mixpanel.com` |

**Always test CSP in production** — open browser DevTools console and check for CSP violation errors after adding new pixels.

---

## Next.js Implementation

### Script Loading Strategies

| Strategy | Use for | Behaviour |
|---|---|---|
| `beforeInteractive` | Consent defaults + dataLayer stub | Runs in `<head>` before hydration |
| `afterInteractive` | gtag.js load + config | Runs after page hydration |
| `lazyOnload` | Meta Pixel, LinkedIn Insight, Mixpanel | Runs after `window.load` event |

**GA4 must use `afterInteractive`** because consent defaults need to be set before the script loads. Meta Pixel and LinkedIn can use `lazyOnload` since they're consent-gated anyway.

### NEXT_PUBLIC_* in Docker Builds

`NEXT_PUBLIC_*` variables are inlined at **build time** by Next.js. For Docker/CI:

```dockerfile
ARG NEXT_PUBLIC_GA_MEASUREMENT_ID
ARG NEXT_PUBLIC_META_PIXEL_ID
ENV NEXT_PUBLIC_GA_MEASUREMENT_ID=$NEXT_PUBLIC_GA_MEASUREMENT_ID
ENV NEXT_PUBLIC_META_PIXEL_ID=$NEXT_PUBLIC_META_PIXEL_ID
RUN npm run build
```

### Root Layout Component Tree

```tsx
<body>
  {/* GA4: always rendered, uses built-in Consent Mode */}
  <GoogleAnalytics />

  {/* These are consent-gated: only render when granted */}
  <LinkedInInsight />
  <MetaPixel />
  <MixpanelAnalytics />

  {/* Consent banner */}
  <CookieConsent />

  {/* UTM capture (always) */}
  <UtmCapture />

  {children}
</body>
```

### Authenticated Layout (Dashboard)

```tsx
<>
  {/* User identification for all platforms */}
  <MixpanelIdentify userId={userId} email={email} name={name} />
  <GA4Identify userId={userId} email={email} />
  {/* Meta Advanced Matching is called inside MixpanelIdentify */}

  {children}
</>
```

### Embed/Widget Pages (No Consent Gate)

For embed pages running inside third-party iframes where localStorage may be partitioned:
- GA4: initialise with `analytics_storage: 'granted'`, all ad consent `denied`
- Mixpanel: load unconditionally with autocapture disabled
- Meta Pixel / LinkedIn: **do not load** (no consent mechanism in tiny widgets)

---

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

## Testing and Verification

### Google Analytics 4

| Tool | How |
|---|---|
| **GA4 DebugView** | `gtag('config', 'G-XXXXXX', { debug_mode: true })` → GA4 Admin → DebugView |
| **Tag Assistant** | [tagassistant.google.com](https://tagassistant.google.com) → connect to site |
| **Network tab** | Filter `google-analytics.com`, check `_gcs` param (`G111` = all granted) |
| **dataLayer inspection** | Console: `dataLayer.filter(e => e[0] === 'consent')` |

### Meta Pixel

| Tool | How |
|---|---|
| **Pixel Helper** | [Chrome extension](https://www.facebook.com/business/help/198460973553498) — shows events in real-time |
| **Test Events** | Events Manager → Data Sources → Pixel → Test Events → enter URL |
| **Network tab** | Filter `facebook.com/tr` — inspect query params for event data |

### LinkedIn

| Tool | How |
|---|---|
| **LinkedIn Insight Tag Helper** | Chrome extension |
| **Campaign Manager** | Analyze → Conversion tracking → verify conversion status |

### Consent Verification Checklist

1. Open incognito → visit site → verify NO tracking requests fire (Network tab)
2. Decline cookies → verify NO tracking requests fire
3. Accept cookies → verify all pixels load, `PageView` events fire
4. Refresh page → verify pixels load immediately (consent remembered)
5. Check localStorage for consent key

### Full Funnel Test

Walk through the entire user journey and verify events at each step:

```
Landing page → PageView (GA4 + Meta)
    ↓
Register → sign_up (GA4) + CompleteRegistration (Meta)
    ↓
Onboarding → Advanced Matching sent (Meta) + user_id set (GA4)
    ↓
Start checkout → begin_checkout (GA4) + InitiateCheckout (Meta)
    ↓
Complete purchase → purchase (GA4) + Purchase (Meta) + Subscribe (Meta, if subscription)
    ↓
Lead form → generate_lead (GA4) + Lead (Meta)
```

---

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

## Official Documentation Links

### Google

- [Google tag (gtag.js) setup](https://developers.google.com/tag-platform/gtagjs)
- [gtag.js API reference](https://developers.google.com/tag-platform/gtagjs/reference)
- [Recommended events](https://developers.google.com/tag-platform/gtagjs/reference/events)
- [Event parameters](https://developers.google.com/tag-platform/gtagjs/reference/parameters)
- [Consent Mode v2 setup](https://developers.google.com/tag-platform/security/guides/consent?consentmode=advanced)
- [Consent Mode for EEA](https://support.google.com/google-ads/answer/13554116)
- [Enhanced Conversions](https://support.google.com/google-ads/answer/11062876)
- [Import GA4 conversions to Google Ads](https://support.google.com/google-ads/answer/11957412)
- [Google Ads conversion tracking](https://support.google.com/google-ads/answer/6095947)
- [Data routing & groups](https://developers.google.com/tag-platform/gtagjs/routing)
- [Tag Assistant](https://tagassistant.google.com)

### Meta (Facebook)

- [Meta Pixel overview](https://developers.facebook.com/docs/meta-pixel)
- [Meta Pixel implementation guide](https://developers.facebook.com/docs/meta-pixel/get-started)
- [Standard events specifications](https://www.facebook.com/business/help/402791146561655?id=1205376682832142)
- [Best practices for Meta Pixel setup](https://www.facebook.com/business/help/218844828315224?id=1205376682832142)
- [Conversion tracking & custom events](https://developers.facebook.com/docs/meta-pixel/implementation/conversion-tracking)
- [Advanced Matching](https://developers.facebook.com/docs/meta-pixel/advanced/advanced-matching)
- [Advanced Matching (conversion tracking docs)](https://developers.facebook.com/docs/meta-pixel/implementation/conversion-tracking#advanced_match)
- [Meta Pixel reference](https://developers.facebook.com/docs/meta-pixel/reference)
- [Meta Pixel Helper extension](https://www.facebook.com/business/help/198460973553498)
- [Meta Events Manager](https://www.facebook.com/events_manager2)
- [Conversions API (server-side)](https://developers.facebook.com/docs/marketing-api/conversions-api)

### LinkedIn

- [LinkedIn Insight Tag setup](https://www.linkedin.com/help/lms/answer/a418880)
- [LinkedIn conversion tracking](https://www.linkedin.com/help/lms/answer/a423304)
- [LinkedIn Campaign Manager](https://www.linkedin.com/campaignmanager)

### Compliance

- [GDPR — EU General Data Protection Regulation](https://gdpr.eu/)
- [DMA — Digital Markets Act](https://commission.europa.eu/strategy-and-policy/priorities-2019-2024/europe-fit-digital-age/digital-markets-act-ensuring-fair-and-open-digital-markets_en)
- [Google Consent Mode and the DMA](https://blog.google/around-the-globe/google-europe/google-consent-mode-and-the-dma/)

---

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

For the page-speed side of the same problem — what the tag does to LCP and TBT,
and what to do about it — see the `frontend-performance` skill in this pack.
