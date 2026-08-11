# gtag.js API Reference

Source: [Google Tag Platform — gtag.js](https://developers.google.com/tag-platform/gtagjs)

## Contents

- [Table of Contents](#table-of-contents)
- [Overview](#overview)
- [Installation](#installation)
- [Tag ID Formats](#tag-id-formats)
- [Commands](#commands)
- [Parameter Scope & Precedence](#parameter-scope--precedence)
- [Data Routing](#data-routing)
- [Multi-Product Configuration](#multi-product-configuration)
- [Next.js / React Integration](#nextjs--react-integration)


## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Tag ID Formats](#tag-id-formats)
- [Commands](#commands)
  - [config](#config)
  - [event](#event)
  - [set](#set)
  - [get](#get)
  - [consent](#consent)
- [Parameter Scope & Precedence](#parameter-scope--precedence)
- [Data Routing](#data-routing)
- [Multi-Product Configuration](#multi-product-configuration)
- [Next.js / React Integration](#nextjs--react-integration)

## Overview

The Google tag (`gtag.js`) API consists of a single function:

```javascript
gtag(<command>, <command_parameters>);
```

Commands: `config`, `event`, `set`, `get`, `consent`.

`gtag()` can be called anywhere on the page **after** the Google tag snippet. Commands are
queued via `dataLayer.push()` and processed once the gtag.js script loads.

## Installation

Place immediately after `<head>` on every page:

```html
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=TAG_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'TAG_ID');
</script>
```

The `config` command is **required** — it sends data to Google products and enables features
like automatically collected events and conversion linking.

## Tag ID Formats

| Prefix | Type | Description |
|--------|------|-------------|
| `GT-XXXXXX` | Google tag | New-format Google tag ID |
| `G-XXXXXX` | Google tag (legacy) | Google Analytics 4 measurement ID |
| `AW-XXXXXX` | Google tag (legacy) | Google Ads account ID |
| `DC-XXXXXX` | Google tag (legacy) | Google Floodlight ID |

All prefixes are interchangeable with the Google tag. A single tag can have multiple IDs.
Universal Analytics (`UA-`) tags are **not** compatible.

## Commands

### config

Configures a target (product/account) and establishes data flow.

```javascript
gtag('config', 'TAG_ID', {<additional_config_params>});
```

The `config` command may also trigger product-specific behavior. For example, GA4's `config`
automatically sends a `page_view` event unless disabled:

```javascript
gtag('config', 'G-XXXXXXXXXX', { 'send_page_view': false });
```

Common config parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `send_page_view` | boolean | Auto-send `page_view` on config (default: `true` for GA4) |
| `debug_mode` | boolean | Enable GA4 DebugView for this session |
| `groups` | string | Assign this target to a named group for routing |
| `user_id` | string | Set a known user ID for cross-device tracking |
| `cookie_domain` | string | Domain for GA cookies (default: `'auto'`) |
| `cookie_expires` | number | Cookie expiration in seconds (default: `63072000` = 2 years) |
| `cookie_prefix` | string | Prefix for GA cookie names |
| `cookie_flags` | string | Additional flags for cookies (e.g. `'SameSite=None;Secure'`) |
| `page_title` | string | Override page title |
| `page_location` | string | Override page URL |

### event

Sends event data to all configured targets (or specific ones via `send_to`).

```javascript
gtag('event', '<event_name>', {<event_params>});
```

Event names are either **recommended** (predefined by Google) or **custom** (arbitrary).

```javascript
// Recommended event
gtag('event', 'login', { method: 'Google' });

// Custom event
gtag('event', 'newsletter_signup', { time: Date.now() });
```

Key event parameters:

| Parameter | Description |
|-----------|-------------|
| `send_to` | Route event to specific target(s) or group(s) |
| `event_callback` | Function called after event is processed |
| `event_timeout` | Max ms to wait before calling callback (default: 2000) |

### set

Defines parameters associated with **every subsequent event** on the page.

```javascript
gtag('set', {<parameter_value_pairs>});
```

```javascript
// All subsequent events will include these campaign params
gtag('set', {
  'campaign_name': 'Black Friday Sale',
  'campaign_id': '1234'
});
```

Use sparingly — prefer `config` or `event` params when possible.

### get

Retrieves values from gtag.js, including values set with `set`.

```javascript
gtag('get', '<target>', '<field_name>', callback);
```

Available fields:

| Field | Supported targets |
|-------|------------------|
| `client_id` | GA4 (`G-*`) |
| `session_id` | GA4 (`G-*`) |
| `session_number` | GA4 (`G-*`) |
| `gclid` | Floodlight (`DC-*`), Google Ads (`AW-*`) |

```javascript
// Get GA4 client ID
gtag('get', 'G-XXXXXXXXXX', 'client_id', (clientId) => {
  console.log('Client ID:', clientId);
});

// Get into a Promise
const clientIdPromise = new Promise(resolve => {
  gtag('get', 'G-XXXXXXXXXX', 'client_id', resolve);
});
```

### consent

Configures consent state. See [consent-mode.md](consent-mode.md) for full patterns.

```javascript
gtag('consent', '<consent_arg>', {<consent_params>});
```

`consent_arg`: `'default'` (set initial state) or `'update'` (change after user action).

| Parameter | Values | Description |
|-----------|--------|-------------|
| `ad_storage` | `'granted'` / `'denied'` | Advertising cookies/identifiers |
| `ad_user_data` | `'granted'` / `'denied'` | User data sent for advertising |
| `ad_personalization` | `'granted'` / `'denied'` | Personalized advertising |
| `analytics_storage` | `'granted'` / `'denied'` | Analytics cookies (`_ga`, `_ga_*`) |
| `wait_for_update` | positive integer (ms) | Time to wait for CMP consent update |

## Parameter Scope & Precedence

Parameters can be set at three scopes. Higher-precedence scopes override lower ones:

```
event  >  config  >  set (global)
```

```javascript
gtag('set', { 'currency': 'EUR' });                    // global
gtag('config', 'G-XXXXXX', { 'currency': 'USD' });     // config-scoped
gtag('event', 'purchase', { 'currency': 'GBP' });      // event-scoped → GBP wins
```

Setting a parameter in one scope does NOT modify the value in another scope.

## Data Routing

### Default routing

All events go to every target configured with `config` (the `default` group):

```javascript
gtag('config', 'G-XXXXXX');   // added to 'default' group
gtag('event', 'sign_in');     // sent to G-XXXXXX
```

### send_to — Route to specific targets

Override default routing with `send_to`:

```javascript
gtag('event', 'sign_in', { 'send_to': 'G-XXXXXX-2' });
```

### Groups — Route to named sets

```javascript
gtag('config', 'G-XXXXXX-3', { 'groups': 'agency' });
gtag('config', 'G-XXXXXX-9', { 'groups': 'agency' });

// Sends only to G-XXXXXX-3 and G-XXXXXX-9
gtag('event', 'sign_in', { 'send_to': 'agency' });
```

A target can belong to multiple groups:

```javascript
gtag('config', 'G-XXXXXX-1', { 'groups': ['agency', 'internal'] });
```

### send_to with arrays

Route a single event to multiple specific targets:

```javascript
gtag('event', 'add_to_cart', {
  'send_to': ['G-XXXXXX-1', 'AW-YYYYYY'],
  'items': [{ 'id': 'U1234', 'name': 'Widget', 'price': 9.99 }]
});
```

## Multi-Product Configuration

A single Google tag can send data to GA4, Google Ads, and Floodlight simultaneously:

```html
<script async src="https://www.googletagmanager.com/gtag/js?id=TAG_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());

  gtag('config', 'G-XXXXXX');       // GA4
  gtag('config', 'AW-YYYYYY');      // Google Ads
  gtag('config', 'DC-ZZZZZZ');      // Floodlight

  // GA4 + Ads get ecommerce
  gtag('event', 'purchase', {
    'send_to': ['G-XXXXXX', 'AW-YYYYYY'],
    'transaction_id': 'T_123',
    'value': 29.99,
    'currency': 'USD'
  });

  // Ads-specific conversion
  gtag('event', 'conversion', {
    'send_to': 'AW-YYYYYY/AbC-D_efG-h12_34-567',
    'value': 29.99,
    'currency': 'USD'
  });
</script>
```

## Next.js / React Integration

### Using next/script (App Router)

```tsx
import Script from 'next/script';

const GA_ID = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID;

export function GoogleAnalytics() {
  if (!GA_ID) return null;
  return (
    <>
      {/* Consent defaults + dataLayer stub (must run first) */}
      <Script id="gtag-consent" strategy="beforeInteractive"
        dangerouslySetInnerHTML={{ __html: `
          window.dataLayer=window.dataLayer||[];
          function gtag(){dataLayer.push(arguments);}
          gtag('consent','default',{
            'ad_storage':'denied','ad_user_data':'denied',
            'ad_personalization':'denied','analytics_storage':'denied',
            'wait_for_update':500
          });
        `}} />

      {/* Load gtag.js */}
      <Script src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`}
        strategy="afterInteractive" />

      {/* Configure */}
      <Script id="gtag-config" strategy="afterInteractive"
        dangerouslySetInnerHTML={{ __html: `
          window.dataLayer=window.dataLayer||[];
          function gtag(){dataLayer.push(arguments);}
          gtag('js',new Date());
          gtag('config','${GA_ID}');
        `}} />
    </>
  );
}
```

### NEXT_PUBLIC_* in Docker builds

`NEXT_PUBLIC_*` variables are inlined at **build time**. For Docker deployments,
declare `ARG` + `ENV` in the builder stage before `npm run build`:

```dockerfile
ARG NEXT_PUBLIC_GA_MEASUREMENT_ID
ENV NEXT_PUBLIC_GA_MEASUREMENT_ID=$NEXT_PUBLIC_GA_MEASUREMENT_ID
RUN npm run build
```

### trackEvent helper (TypeScript)

```typescript
declare global {
  interface Window { gtag?: (...args: unknown[]) => void; }
}

export function trackEvent(name: string, params?: Record<string, unknown>) {
  if (typeof window === 'undefined') return;
  if (typeof window.gtag !== 'function') return;
  if (window.location.hostname === 'localhost') {
    console.debug('[GA]', name, params);
    return;
  }
  window.gtag('event', name, params);
}
```

### SPA page_view (App Router)

GA4 with enhanced measurement automatically tracks `page_view` via the History API
(`pushState`). Manual page views are only needed for hash routing (`#/path`).

If needed, send manual page views on route change:

```typescript
'use client';
import { usePathname } from 'next/navigation';
import { useEffect } from 'react';

export function usePageView() {
  const pathname = usePathname();
  useEffect(() => {
    if (typeof window.gtag === 'function') {
      window.gtag('event', 'page_view', {
        page_path: pathname,
        page_location: window.location.href,
        page_title: document.title,
      });
    }
  }, [pathname]);
}
```
