# GA4 Performance & Security — Reference


## Contents

- [Table of Contents](#table-of-contents)
- [Script Loading Strategies](#script-loading-strategies)
- [Content Security Policy](#content-security-policy)
- [Next.js / React Integration](#nextjs--react-integration)
- [SPA (Single Page Application) Handling](#spa-single-page-application-handling)
- [Debug & Testing](#debug--testing)
- [Common Mistakes](#common-mistakes)
- [Multi-Page Consistency](#multi-page-consistency)

## Table of Contents

- [Script Loading Strategies](#script-loading-strategies)
- [Content Security Policy](#content-security-policy)
- [SPA (Single Page Application) Handling](#spa-single-page-application-handling)
- [Debug & Testing](#debug--testing)
- [Common Mistakes](#common-mistakes)
- [Multi-Page Consistency](#multi-page-consistency)

## Script Loading Strategies

### Standard Async (default)

```html
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

- Downloads in parallel, executes as soon as available
- Best for: static pages, marketing sites, pages where analytics are important

### Deferred (post-load)

```html
<script>
  window.addEventListener('load', function() {
    var s = document.createElement('script');
    s.src = 'https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX';
    s.async = true;
    s.onload = function() {
      gtag('js', new Date());
      gtag('config', 'G-XXXXXXXXXX');
    };
    document.head.appendChild(s);
  });
</script>
```

- Loads after all critical resources (HTML, CSS, fonts, images)
- Best for: SPA main shells, app pages where UX is priority
- Events queued in `dataLayer` before load fire once the script arrives

### Preconnect Hint

Add in `<head>` to reduce DNS/TLS latency:

```html
<link rel="preconnect" href="https://www.googletagmanager.com" crossorigin>
<link rel="preconnect" href="https://www.google-analytics.com" crossorigin>
```

Use with deferred loading for best of both worlds.

### Performance Impact

| Strategy | LCP impact | TBT impact | Data completeness |
|----------|-----------|-----------|-------------------|
| Standard async | Small | Minimal | Full |
| Deferred (post-load) | None | None | Slight first-hit delay |
| No preconnect | +100-200ms cold | — | Full |

## Content Security Policy

### Minimal CSP Directives for GA4

```
script-src 'self' https://www.googletagmanager.com;
img-src https://www.googletagmanager.com;
connect-src https://www.google-analytics.com https://analytics.google.com;
```

### With Nonce (Recommended for Inline Scripts)

Server generates a unique nonce per request:

```html
<script nonce="RANDOM_NONCE_VALUE">
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  // ... consent defaults ...
</script>
```

CSP header:

```
script-src 'nonce-RANDOM_NONCE_VALUE' https://www.googletagmanager.com;
```

### EU Region-Specific Endpoints

For EU users, Google may route to regional endpoints. Add:

```
connect-src https://www.google-analytics.com
            https://analytics.google.com
            https://region1.google-analytics.com;
```

### Avoid `'unsafe-inline'`

Using nonces or hashes is strongly preferred. Only fall back to `'unsafe-inline'` if your
server cannot generate nonces (e.g. static hosting with no server-side rendering).

For static sites: move all inline GA code to an external file (e.g. `/js/analytics.js`)
and use `'self'` in `script-src`.

## Next.js / React Integration

### Script Loading with next/script

```tsx
import Script from 'next/script';

// beforeInteractive — runs in <head> before hydration
<Script id="gtag-consent" strategy="beforeInteractive"
  dangerouslySetInnerHTML={{ __html: `...consent defaults...` }} />

// afterInteractive — runs after page becomes interactive (default)
<Script src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXX"
  strategy="afterInteractive" />

// lazyOnload — runs during idle time (lowest priority)
<Script src="..." strategy="lazyOnload" />
```

| Strategy | Runs when | Use for |
|----------|-----------|---------|
| `beforeInteractive` | In `<head>`, before any JS | Consent defaults, dataLayer stub |
| `afterInteractive` | After hydration | gtag.js load + config |
| `lazyOnload` | Browser idle | Non-critical third-party scripts |

### Docker Build-Time Variables

`NEXT_PUBLIC_*` variables are statically inlined during `npm run build`.
If building in Docker, declare them as build args:

```dockerfile
# In the builder stage, BEFORE npm run build
ARG NEXT_PUBLIC_GA_MEASUREMENT_ID
ENV NEXT_PUBLIC_GA_MEASUREMENT_ID=$NEXT_PUBLIC_GA_MEASUREMENT_ID
RUN npm run build
```

Without this, the variable resolves to `undefined` in the production bundle.

### Preconnect in Next.js

Add preconnect hints in the root layout metadata:

```tsx
export const metadata: Metadata = {
  other: {
    'link': [
      { rel: 'preconnect', href: 'https://www.googletagmanager.com', crossOrigin: 'anonymous' },
      { rel: 'preconnect', href: 'https://www.google-analytics.com', crossOrigin: 'anonymous' },
    ]
  }
};
```

Or use `<link>` directly in the layout's `<head>` (if using a custom `<head>`).

## SPA (Single Page Application) Handling

GA4 with gtag.js tracks `page_view` automatically via the browser History API.
If your SPA uses hash routing or custom navigation, send manual page views:

```javascript
// On route change
gtag('event', 'page_view', {
  page_title: document.title,
  page_location: window.location.href,
  page_path: window.location.pathname
});
```

### When Manual page_view Is Needed

| Routing type | Auto page_view works? | Manual needed? |
|-------------|----------------------|----------------|
| Full page reload | Yes | No |
| History API (`pushState`) | Yes (enhanced measurement) | Usually no |
| Hash routing (`#/path`) | No | Yes |
| Custom SPA router | Depends | Test with DebugView |

### Consent on SPA Route Changes

Consent state persists across SPA route changes — no need to re-initialize.
Only re-initialize consent defaults on full page reloads.

## Debug & Testing

### GA4 DebugView

Enable for the current session:

```javascript
gtag('config', 'G-XXXXXXXXXX', { 'debug_mode': true });
```

Or via URL parameter: `?debug_mode=true` (requires allowlisting in GA4 Admin).

View in: GA4 > Admin > DebugView.

### Tag Assistant

1. Visit [tagassistant.google.com](https://tagassistant.google.com)
2. Connect your site
3. Check:
   - Tags firing correctly
   - Consent state per tag
   - Event parameters

### Browser DevTools Checks

```javascript
// Verify dataLayer contents
console.table(dataLayer);

// Check consent state
dataLayer.filter(item => item[0] === 'consent');

// Verify cookies (should be absent when denied)
document.cookie.split(';').filter(c => c.trim().startsWith('_ga'));

// Check localStorage
localStorage.getItem('app_cookie_consent');
```

### Network Tab Verification

Filter by `google-analytics.com` or `googletagmanager.com`:
- `collect` requests = measurement pings
- Check payload for `_gcs` parameter (consent state encoding)
- `gcs=G111` = all granted; `gcs=G100` = only analytics granted

## Common Mistakes

| Mistake | Impact | Fix |
|---------|--------|-----|
| Consent defaults after gtag.js loads | First pageview ignores consent | Move defaults before `<script async src="...">` |
| Missing `wait_for_update` | CMP loads too late, data lost | Add `wait_for_update: 500` |
| No `gtag()` stub before consent call | `gtag is not defined` error | Define `function gtag(){dataLayer.push(arguments)}` first |
| Hardcoded measurement ID in many files | Painful to change | Use a config file, env var, or template variable |
| Not calling `gtag('consent','update')` on decline | Consent state stays in limbo | Always update on both accept and decline |
| Banner shows on every page load | Broken localStorage check | Verify `getItem` returns the correct key |
| No way to re-open consent banner | GDPR non-compliance | Expose `window.appCookieSettings()` or footer link |
| Tracking events on localhost | Polluted production data | Guard with hostname check in `trackEvent` |
| Custom event names in camelCase | Inconsistent with GA4 conventions | Use `snake_case` |
| Forgetting custom dimension setup | Custom params invisible in reports | Create dimension in GA4 Admin for each custom param |

## Multi-Page Consistency

When GA4 is implemented across multiple HTML pages (not a SPA):

1. **Use identical consent default blocks** in every page's `<head>`
2. **Share the same localStorage key** for consent across all pages
3. **Use the same measurement ID** everywhere
4. **Load `consent.js` on every page** (or its minified version)
5. **Consider a shared snippet file** (or server-side include) to avoid drift

### Minification

Include `consent.js` in build/minification pipeline:

```bash
terser js/consent.js -o js/consent.min.js -c -m
```

Use the minified version in production, source version in development.
