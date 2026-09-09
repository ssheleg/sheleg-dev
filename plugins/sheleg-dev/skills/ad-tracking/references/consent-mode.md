# Consent Mode v2 — Detailed Patterns


**Load this when** consent is the task: advanced vs basic mode and what each still sends, all consent types, region-specific defaults, granular consent with its localStorage schema, the update flow, GTM wiring, exactly what tags do when denied, URL passthrough, ads data redaction, and how to verify in Tag Assistant / DevTools / DebugView.

## Contents

- [Status check — 2026](#status-check--2026)
- [Advanced vs Basic Mode](#advanced-vs-basic-mode)
- [All Consent Types](#all-consent-types)
- [Region-Specific Defaults](#region-specific-defaults)
- [Granular Consent](#granular-consent)
- [Consent Update Flow](#consent-update-flow)
- [GTM Implementation](#gtm-implementation)
- [Tag Behavior When Denied](#tag-behavior-when-denied)
- [URL Passthrough](#url-passthrough)
- [Ads Data Redaction](#ads-data-redaction)
- [Verification](#verification)

## Status check — 2026

Consent Mode v2 has been required since **March 2024** for anyone using Google
advertising products with EEA or UK traffic. The **certified CMP** requirement
(Consent Management Platform programme) is scoped to Google's **publisher**
products — AdSense, Ad Manager, AdMob — where a hand-rolled banner is no longer
sufficient; on the advertiser side (Google Ads, GA4) a certified CMP is
Google's recommendation, not a stated requirement. Verify the programme's
current scope and your CMP's certification before treating either box as
ticked. *(Checked 2026-08-06; scope per Google's CMP programme pages.)*

## Advanced vs Basic Mode

| Mode | Tags load before consent? | Cookieless pings? | Conversion modeling? |
|------|--------------------------|-------------------|---------------------|
| **Basic** | No — tags blocked until consent granted | No | **General** modeling only — Google models from aggregate patterns, less accurately; "no modeling" was never true |
| **Advanced** | Yes — tags load with denied defaults | Yes | **Advertiser-specific** modeling from your own cookieless pings |

**Which mode is three separate questions, not one default.** *Provider policy:*
Google's modeling is stronger under Advanced (advertiser-specific vs general).
*Business choice:* Advanced sends cookieless pings BEFORE consent — how much
recovered attribution is worth that is yours to decide. *Jurisdiction:* whether
pre-consent pings are lawful where your users are is counsel's question — some
EEA regulators read them restrictively, and Basic is the conservative answer.
The recovery figures Google has cited (~65–70%) come from its own dated,
campaign-specific case studies — **your recovery is unknown until measured on
your traffic**; an unmeasured percentage is not a promise.

Advanced mode = `gtag('consent', 'default', { ... 'denied' ... })` then load tags normally.
Basic mode = physically block `<script>` tags until consent granted.

## All Consent Types

| Signal | Controls | Required for |
|--------|----------|-------------|
| `ad_storage` | Advertising cookies/identifiers (e.g. `_gcl_*`) | Google Ads, remarketing |
| `ad_user_data` | Sending user data to Google for advertising | Google Ads conversion tracking |
| `ad_personalization` | Personalized advertising/remarketing | Remarketing audiences |
| `analytics_storage` | Analytics cookies (e.g. `_ga`, `_ga_*`) | GA4 full measurement |
| `functionality_storage` | Functional cookies (e.g. language prefs) | Optional |
| `personalization_storage` | Personalization cookies (e.g. recommendations) | Optional |
| `security_storage` | Security cookies (e.g. CSRF tokens) | Optional |

For GA4 + Google Ads, the four required signals are: `ad_storage`, `ad_user_data`,
`ad_personalization`, `analytics_storage`.

## Region-Specific Defaults

Scope consent defaults to specific regions to avoid blocking measurement where not required:

```javascript
// Deny by default in EEA + UK
gtag('consent', 'default', {
  'ad_storage': 'denied',
  'ad_user_data': 'denied',
  'ad_personalization': 'denied',
  'analytics_storage': 'denied',
  'region': ['AT','BE','BG','HR','CY','CZ','DK','EE','FI','FR',
             'DE','GR','HU','IE','IT','LV','LT','LU','MT','NL',
             'PL','PT','RO','SK','SI','ES','SE','IS','LI','NO','GB'],
  'wait_for_update': 500
});

// Granted by default everywhere else — a recorded BUSINESS choice, not legal
// advice: whether a banner is needed outside the listed regions is a
// jurisdiction question (ePrivacy transpositions, US state laws, LGPD…).
gtag('consent', 'default', {
  'ad_storage': 'granted',
  'ad_user_data': 'granted',
  'ad_personalization': 'granted',
  'analytics_storage': 'granted'
});
```

The most specific region match wins. If a user is in Germany (`DE`), the first block applies.
If in the US, the second block applies (no consent banner needed).

**When to use region-specific defaults:**
- Site serves both EEA and non-EEA users
- Want to avoid showing consent banner to US/non-EU users
- Need to maximize measurement while staying compliant

**When to deny globally:**
- Simpler implementation
- Want consistent UX worldwide
- Targeting primarily EEA/UK audience

## Granular Consent

For sites that want separate analytics vs advertising consent:

```javascript
// User accepts analytics but declines ads
gtag('consent', 'update', {
  'ad_storage': 'denied',
  'ad_user_data': 'denied',
  'ad_personalization': 'denied',
  'analytics_storage': 'granted'
});
```

This requires a more complex consent banner with multiple toggles/categories.
For most sites, a simple accept-all / decline-all is sufficient.

### localStorage Schema for Granular Consent

```javascript
// Simple (binary)
localStorage.setItem('app_cookie_consent', 'granted');  // or 'denied'

// Granular (JSON)
localStorage.setItem('app_cookie_consent', JSON.stringify({
  analytics: 'granted',
  advertising: 'denied',
  timestamp: Date.now()
}));
```

## Consent Update Flow

```
User clicks "Accept All"
  └─> localStorage.setItem('key', 'granted')
  └─> gtag('consent', 'update', {
        'ad_storage': 'granted',
        'ad_user_data': 'granted',
        'ad_personalization': 'granted',
        'analytics_storage': 'granted'
      })
  └─> Hide banner

User clicks "Decline"
  └─> localStorage.setItem('key', 'denied')
  └─> gtag('consent', 'update', {
        'ad_storage': 'denied',
        'ad_user_data': 'denied',
        'ad_personalization': 'denied',
        'analytics_storage': 'denied'
      })
  └─> Hide banner
```

After `gtag('consent', 'update', ...)`:
- If changed to `granted`: GA4 writes cookies and begins full tracking
- If changed to `denied`: GA4 switches to cookieless pings (advanced mode)
- Queued events from before the update are processed with the new consent state

## GTM Implementation

When using Google Tag Manager instead of gtag.js directly:

1. Create a **Consent Initialization** trigger (fires before all other triggers)
2. Add a tag with the default consent state
3. Use the CMP's built-in GTM template (if available) or custom HTML tag
4. The CMP updates consent via `gtag('consent', 'update', ...)`
5. GTM built-in consent checks gate tag firing automatically

GTM consent overview is configured in Admin > Container Settings > Enable consent overview.

## Tag Behavior When Denied

When `analytics_storage` is denied, GA4 in advanced mode:
- Sends cookieless pings (no `_ga` cookie written)
- Pings include: page URL, timestamp, user agent, referrer
- Does NOT include: client ID, session ID, user-scoped dimensions
- Google uses these pings for **behavioral modeling** to estimate metrics

When `ad_storage` is denied:
- No `_gcl_*` cookies written
- Conversion linker disabled
- Google uses **conversion modeling** to estimate conversions

## URL Passthrough

When `ad_storage` is denied, ad click info (gclid, dclid) can't be stored in cookies.
URL passthrough appends this data as URL parameters across pages instead:

```javascript
gtag('set', 'url_passthrough', true);
```

Place this **before** any `config` commands. When enabled, these query params may appear in URLs:
`gclid`, `dclid`, `gclsrc`, `_gl`, `wbraid`.

**When to use:** Running Google Ads with users who may deny consent. Not needed for analytics-only setups.

Ensure:
1. Redirects on your site pass all query parameters through
2. Analytics tools ignore these parameters in page URLs
3. Parameters don't interfere with site behavior

## Ads Data Redaction

Further redact ad data when `ad_storage` is denied:

```javascript
gtag('set', 'ads_data_redaction', true);
```

When enabled and `ad_storage` is `denied`:
- Ad click identifiers in network requests are redacted
- Network requests are sent through a cookieless domain
- No effect when `ad_storage` is `granted`

**When to use:** Extra privacy compliance; recommended for EU-focused sites.

## Verification

### Using Tag Assistant (tagassistant.google.com)

1. Open Tag Assistant and connect to your site
2. Check the "Consent" tab for each tag
3. Verify:
   - "On-page Default" shows `denied` for all signals
   - "On-page Update" shows correct state after user action
   - "Current State" reflects the actual consent

### Using Browser DevTools

```javascript
// Check dataLayer for consent commands
dataLayer.filter(e => e[0] === 'consent');

// Check if GA cookies exist (should be absent when denied)
document.cookie.split(';').filter(c => c.trim().startsWith('_ga'));

// Check localStorage consent value
localStorage.getItem('app_cookie_consent');
```

### GA4 DebugView

Enable debug mode to see real-time events:

```javascript
gtag('config', 'G-XXXXXXXXXX', { 'debug_mode': true });
```

Events appear in GA4 > Admin > DebugView with consent state indicators.
