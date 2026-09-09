---
name: frontend-performance
description: >-
  Use when building or auditing web pages for performance — running PageSpeed Insights,
  optimizing Lighthouse scores, fixing render-blocking resources, reducing bundle size,
  improving load times, or diagnosing slow page rendering. Covers Core Web Vitals (LCP, INP,
  CLS) and the Lighthouse diagnostics beside them (FCP, TBT, Speed Index), font loading strategies, CSS animation compositing, JavaScript
  bundle optimization, cache headers, code splitting, Content Security Policy, image
  optimization, and the contrast and heading issues that move a Lighthouse score. Triggers -
  "performance audit", "PageSpeed", "Lighthouse", "Core Web Vitals", "LCP", "CLS", "INP",
  "render-blocking", "bundle size", "code splitting", "lazy loading", "cache headers",
  "performance budget", "ускорить сайт", "медленно грузится", "оптимизация скорости", "вес
  бандла". Not for visual design or conversion work.
license: MIT
---

# Frontend Performance

Optimize frontend applications for maximum Lighthouse scores and real-user performance. This skill covers the technical performance layer -- for how it looks, see `sheleg-design`; for what the interface must do, see `super-ux`.

## Audit Workflow

1. **Measure** -- Run PageSpeed Insights or Lighthouse. Record scores and failing audits.
2. **Diagnose** -- Map each failing audit to a specific code-level cause (see checklist below).
3. **Prioritize** -- Fix by impact: P0 blocks rendering, P1 hurts metrics, P2 is informational.
4. **Implement** -- Apply fixes per the reference guides.
5. **Validate** -- `next build` (or framework equivalent) + re-run Lighthouse. Verify no regressions.

## Core Web Vitals, and the diagnostics beside them

**Two INDEPENDENT axes, and conflating them is the common error.** Axis one:
**is it a Core Web Vital** — what Google reports and ranks on (LCP, INP, CLS)
— or not. Axis two: **where can you measure it** — in the FIELD (real users,
CrUX) or only in the LAB (a synthetic run). These do not line up: a metric can
be not-CWV and still field-measurable. **FCP is the case that breaks the
one-axis story — it is NOT a Core Web Vital, yet it IS field-measurable**
(CrUX reports FCP; web.dev lists both lab and field tools for it). The earlier
claim that "only the three CWV are field-measurable" was wrong.

| Metric | Core Web Vital? | Field-measurable? | Good | Needs Work | Poor |
|---|---|---|---|---|---|
| LCP | yes | yes (CrUX) | < 2.5s | 2.5-4.0s | > 4.0s |
| INP | yes | yes (CrUX) | < 200ms | 200-500ms | > 500ms |
| CLS | yes | yes (CrUX) | < 0.1 | 0.1-0.25 | > 0.25 |
| FCP | no | **yes (CrUX)** | < 1.8s | 1.8-3.0s | > 3.0s |
| TBT | no | no (lab only) | < 200ms | 200-600ms | > 600ms |
| SI | no | no (lab only) | < 3.4s | 3.4-5.8s | > 5.8s |

**A field claim carries its provenance, always: p75** (the 75th-percentile
value Google classifies on, never a mean), the **device/cohort** (phone vs
desktop, and which population), the **period** (CrUX is a 28-day trailing
window), and the **sample size** (a thin origin has no field data — that is
`unknown`, not `good`). A number without these four is a lab number wearing a
field label.

**TBT is a diagnostic CORRELATE of INP, never a substitute for its evidence.**
A good lab TBT is a hint that INP may be fine; it does NOT PROVE INP, because
INP is measured on real interactions the lab did not perform. So a page with
CrUX FCP data and a Lighthouse TBT but **no field INP** reports **FCP =
field-supported, INP = unknown** — never "INP passed by TBT". Telling a client
their Speed Index is a failing Core Web Vital is telling them about a thing
Google does not rank; telling them INP passed because TBT did is telling them
about a measurement nobody took.

Thresholds and the classification verified against `web.dev/articles/vitals`,
2026-08-16.

## Performance Checklist

### Fonts (LCP, FCP)

- **Self-host fonts** -- Never load from external CDNs via `<link>` tags. Use framework font optimization (`next/font/google`, `@fontsource`, etc.) to inline CSS and self-host files.
- **Preload critical fonts** -- The font used by the LCP element must load early.
- **Limit font families** -- Max 3 families. Each family adds ~20-50KB.
- **Subset fonts** -- Only load needed character sets (`latin`, `latin-ext`).
- **Use `font-display: swap`** -- Prevents invisible text during load (FOIT).
- **Remove unused preconnects** -- If fonts are self-hosted, `preconnect` to font CDNs is dead weight.

**Before any of these changes: MEASURE, don't prescribe.** The items below are
optimization HEURISTICS, not blanket rules — each is conditional on evidence,
and applied blind it can lose function for a score. Before changing anything,
check three things: the **performance trace + the scenarios** (what a low-end
device on a slow network actually waits for), the **browser-support contract**
(who must the page still work for), and the **accessibility owner** (structure
is theirs, not the score's). A change ships only with acceptance covering:
low-end/slow-network scenarios, keyboard + heading structure intact, the
supported-browser matrix still served, NO new unapproved CSP origin, and
several comparable before/after measurements showing the win **with no
functional loss**.

### JavaScript (TBT, FCP, LCP)

- **Code split by the MEASURED waterfall** -- lazy-load what the trace shows the first paint does not need; "only hero + nav in the initial bundle" is a starting hypothesis, not a rule — a section the scenario needs above the fold stays, whatever the score says.
- **Defer third-party scripts** -- GA, analytics, chat widgets load after interactive (`afterInteractive` or `defer`).
- **Target the browsers your USERS run** -- `browserslist` follows a stated user-support policy (your analytics, your contract), not a default "last 2". The `last 2` line below is an EXAMPLE; shipping it without checking who it drops is how a working browser stops being served for a polyfill saving:
  ```
  # example only — replace with your measured support matrix
  last 2 Chrome versions, last 2 Firefox versions, last 2 Safari versions, last 2 Edge versions
  ```
- **Tree-shake imports** -- prefer named imports where the bundle analyzer shows `import * as` pulling dead weight; it is a tree-shaking aid, not a ban — a namespace import that costs nothing measured is not a defect.
- **Analyze bundles** -- Use `@next/bundle-analyzer`, `source-map-explorer`, or `vite-plugin-visualizer`.

### CSS & Animations (CLS)

- **Composite-only animations** -- Only animate `transform` and `opacity` (GPU-composited). Never animate `background-position`, `width`, `height`, `top/left`, `margin`, `padding`.
- **Use `will-change` sparingly** -- Add `will-change: transform` or `will-change: filter` only on elements that actually animate.
- **Inline critical CSS** -- Framework should handle this (Next.js does automatically).
- **Avoid layout shifts** -- Set explicit `width`/`height` on images and embeds. Reserve space for dynamic content.

### Images (LCP, CLS)

- **Use `<Image>` component** -- Framework-optimized components (`next/image`, Astro `<Image>`) auto-resize, convert to WebP/AVIF, and add `width`/`height`.
- **Priority-load LCP image** -- Add `priority` (Next.js) or `fetchpriority="high"` to the hero/LCP image.
- **Lazy-load below-fold** -- All images below the initial viewport get `loading="lazy"`.
- **Size budget**: Hero < 200KB, thumbnails < 50KB, icons as SVG.
- **Responsive `sizes`** -- Always provide `sizes` attribute for responsive images.

### Caching (Repeat Visits)

- **Static assets**: `Cache-Control: public, max-age=31536000, immutable` for hashed files (JS, CSS, fonts, images).
- **HTML**: `Cache-Control: public, max-age=0, must-revalidate` (or framework default).
- **Verify patterns** -- Test cache header `source` patterns against actual URLs. Common mistake: glob-style patterns (`{.svg,.png}`) don't work in all frameworks' path-matching (e.g., Next.js uses `path-to-regexp`). Use regex parameter syntax instead:
  ```
  /:path*.:ext(svg|png|jpg|jpeg|gif|webp|ico|woff|woff2)
  ```

### Content Security Policy (Best Practices)

- **Approve origins by FUNCTIONAL NECESSITY, not for the score** -- an origin enters the CSP because the page genuinely needs it, and each is reviewed; whitelisting everything the page happens to load to silence console errors trades the whole point of a CSP for a Best-Practices number. No new origin ships unapproved.
- **Audit after every third-party change** -- Adding analytics, fonts, or CDN scripts requires CSP updates.
- **Tighten after migration** -- If you move from external fonts to self-hosted, remove the old CSP entries.
- **Common CSP origins**:
  - Google Analytics: `https://www.googletagmanager.com`, `https://www.google-analytics.com`
  - Cloudflare: `https://static.cloudflareinsights.com`
  - Stripe: `https://js.stripe.com`

### Accessibility (Lighthouse A11y Score)

These directly affect the Lighthouse Accessibility score:

- **Contrast ratio** -- WCAG AA requires 4.5:1 for normal text, 3:1 for large text. Avoid opacity modifiers on text colors (e.g., `text-primary/80` in Tailwind reduces contrast). Use full-opacity color tokens.
- **Heading hierarchy follows STRUCTURE, decided with the accessibility owner** -- sequential `h1`->`h2`->`h3`, no skipped levels. Demote a heading to `<p>` only when it is genuinely NOT a section title; downgrading a real footer-section heading to `<p>` to quiet a Lighthouse audit removes structure a screen-reader user navigates by. Accessibility is the owner here, not the score.
- **Alt text** -- Decorative images next to identical text get `alt=""`. Informative images get descriptive alt. Never duplicate adjacent text.
- **Tap targets** -- Minimum 48x48px on mobile. Applies to buttons, links, form inputs.

## Framework-Specific Guides

- **Next.js**: See [references/nextjs.md](references/nextjs.md) for `next/font`, `next/image`, `next/dynamic`, `next/script`, cache headers in `next.config`, CSP configuration, and bundle analysis.
- **CSS/Animation**: See [references/css-performance.md](references/css-performance.md) for compositing rules, gradient animation alternatives, `will-change` usage, and critical CSS strategies.
- **Accessibility**: See [references/accessibility-perf.md](references/accessibility-perf.md) for contrast calculations, heading hierarchy rules, and ARIA patterns that affect Lighthouse.

## Common PageSpeed Failures & Fixes

| Audit | Cause | Fix |
|-------|-------|-----|
| "Eliminate render-blocking resources" | External font CSS, large CSS files | Self-host fonts, inline critical CSS |
| "Reduce unused JavaScript" | Full page bundle loaded upfront | Code-split with dynamic imports |
| "Avoid non-composited animations" | Animating `background-position`, `width`, etc. | Replace with `transform`/`opacity`/`filter` |
| "Serve static assets with efficient cache policy" | Missing or short `Cache-Control` headers | Set `max-age=31536000, immutable` for hashed assets |
| "Background/foreground colors do not have sufficient contrast" | Opacity modifiers on text colors | Use full-opacity color tokens |
| "Heading elements not in sequential order" | Skipped heading levels (h1 -> h4) | Fix hierarchy or use `<p>` for non-structural headings |
| "Browser errors logged to console" | CSP blocking scripts/styles | Whitelist required origins in CSP |
| "Image elements do not have [alt] attributes" | Missing or redundant alt text | Add descriptive alt, or `alt=""` for decorative |
| "Avoid chaining critical requests" | Waterfall of blocking resources | Preload critical resources, self-host |
| "Legacy JavaScript" | Polyfills for modern APIs | Update `browserslist` targets |

## Performance Budget Template

Set these limits for landing pages:

| Resource | Budget |
|----------|--------|
| Total page weight | < 1.5 MB |
| JavaScript (compressed) | < 200 KB |
| CSS (compressed) | < 50 KB |
| Fonts (total) | < 150 KB |
| Hero image | < 200 KB |
| LCP | < 2.5s (mobile) |
| FCP | < 1.8s (mobile) |
| CLS | < 0.1 |
| TBT | < 200ms |

## Related Skills

- `sheleg-design` -- how it looks and moves, including the motion budget this page's
  numbers constrain
- `super-ux` -- what the interface must do, and the flows a slow page loses
- `seo-aeo-audit` -- technical SEO and crawlability, which reads the same Core Web
  Vitals from the field rather than the lab

Four names that used to sit here — `frontend-design`, `landing-page-design`,
`next-best-practices`, `responsive-design` — resolved to nothing installable, and
`seo-audit` was one character-class away from the real `seo-aeo-audit`, which is
how a typo survives review.
