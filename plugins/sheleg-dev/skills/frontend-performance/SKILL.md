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

**Three metrics are Core Web Vitals. The other three are not**, and the difference
is not pedantry: only the first three are what Google reports and ranks on, and
only they are field-measurable. TBT is a *lab* metric — web.dev says it "is not
part of the Core Web Vitals set because they are not field-measurable" — and it
stands in for INP when you have no field data. Telling a client their Speed Index
is a failing Core Web Vital is telling them about a thing Google does not measure.

| Core Web Vital | Good | Needs Work | Poor |
|--------|------|------------|------|
| LCP (Largest Contentful Paint) | < 2.5s | 2.5-4.0s | > 4.0s |
| INP (Interaction to Next Paint) | < 200ms | 200-500ms | > 500ms |
| CLS (Cumulative Layout Shift) | < 0.1 | 0.1-0.25 | > 0.25 |

| Lab diagnostic | Good | Needs Work | Poor | Stands in for |
|--------|------|------------|------|---|
| FCP (First Contentful Paint) | < 1.8s | 1.8-3.0s | > 3.0s | early LCP signal |
| TBT (Total Blocking Time) | < 200ms | 200-600ms | > 600ms | INP, in the lab |
| SI (Speed Index) | < 3.4s | 3.4-5.8s | > 5.8s | perceived load |

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

### JavaScript (TBT, FCP, LCP)

- **Code split aggressively** -- Lazy-load below-the-fold sections. Only hero + nav in initial bundle.
- **Defer third-party scripts** -- GA, analytics, chat widgets load after interactive (`afterInteractive` or `defer`).
- **Target modern browsers** -- Set `browserslist` to avoid shipping polyfills for `Array.prototype.at`, `Object.fromEntries`, etc.:
  ```
  last 2 Chrome versions, last 2 Firefox versions, last 2 Safari versions, last 2 Edge versions
  ```
- **Tree-shake imports** -- Named imports only. No `import * as`.
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

- **Whitelist all loaded origins** -- CSP blocks = console errors = lower Best Practices score.
- **Audit after every third-party change** -- Adding analytics, fonts, or CDN scripts requires CSP updates.
- **Tighten after migration** -- If you move from external fonts to self-hosted, remove the old CSP entries.
- **Common CSP origins**:
  - Google Analytics: `https://www.googletagmanager.com`, `https://www.google-analytics.com`
  - Cloudflare: `https://static.cloudflareinsights.com`
  - Stripe: `https://js.stripe.com`

### Accessibility (Lighthouse A11y Score)

These directly affect the Lighthouse Accessibility score:

- **Contrast ratio** -- WCAG AA requires 4.5:1 for normal text, 3:1 for large text. Avoid opacity modifiers on text colors (e.g., `text-primary/80` in Tailwind reduces contrast). Use full-opacity color tokens.
- **Heading hierarchy** -- Sequential: `h1` -> `h2` -> `h3`. Never skip levels. Use non-heading elements (`<p>`) for visual-only "headings" (e.g., footer column titles).
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
