# Next.js Performance Patterns

## Font Optimization with `next/font`

### Migration from `<link>` to `next/font/google`

Replace external Google Fonts links with `next/font/google` imports. This:
- Inlines font CSS at build time (no render-blocking request)
- Self-hosts font files from `/_next/static/` (no external dependency)
- Eliminates need for `preconnect` hints and Google Fonts CSP entries
- Enables automatic subsetting

**Before (bad):**
```tsx
// layout.tsx
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
<link href="https://fonts.googleapis.com/css2?family=DM+Sans&family=Outfit&display=swap" rel="stylesheet" />
```

**After (good):**
```tsx
// layout.tsx
import { DM_Sans, Outfit } from "next/font/google";

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
  weight: ["400", "500", "600", "700", "800"],
  display: "swap",
});

export default function RootLayout({ children }) {
  return (
    <html lang="en" className={`${dmSans.variable} ${outfit.variable}`}>
      <body>{children}</body>
    </html>
  );
}
```

Then reference via CSS variables in `globals.css`:
```css
body { font-family: var(--font-dm-sans), system-ui, sans-serif; }
h1, h2, h3 { font-family: var(--font-outfit), system-ui, sans-serif; }
```

### Multiple Font Families

Load only fonts actually used. Each family adds ~20-50KB. Three families is a practical maximum for landing pages.

If using variable fonts (weight ranges), specify the range:
```tsx
const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
  weight: ["400", "500", "600", "700"],  // or omit for variable font full range
  display: "swap",
});
```

## Code Splitting with `next/dynamic`

Lazy-load below-the-fold sections to reduce initial JavaScript bundle:

```tsx
import dynamic from "next/dynamic";

// Above-the-fold: import normally
import { HeroSection } from "@/components/hero";
import { Navbar } from "@/components/navbar";

// Below-the-fold: lazy load
const Testimonials = dynamic(() =>
  import("@/components/testimonials").then((m) => m.TestimonialsSection)
);
const FAQ = dynamic(() =>
  import("@/components/faq").then((m) => m.FAQSection)
);
const Pricing = dynamic(() =>
  import("@/components/pricing").then((m) => m.PricingSection)
);
```

Only use `next/dynamic` for components that are:
- Below the initial viewport (not visible without scrolling)
- Heavy (> 10KB compressed)
- Not critical for SEO (search engines execute JS but slower)

Do NOT dynamically import the hero, navbar, or footer -- these must render immediately.

## Cache Headers in `next.config.ts`

Add cache headers for static assets:

```typescript
// next.config.ts
const nextConfig = {
  async headers() {
    return [
      {
        source: "/:path*.:ext(svg|png|jpg|jpeg|gif|webp|ico|woff|woff2)",
        headers: [
          {
            key: "Cache-Control",
            value: "public, max-age=31536000, immutable",
          },
        ],
      },
    ];
  },
};
```

**Critical:** Next.js uses `path-to-regexp` for route matching. Common pattern mistakes:

| Pattern | Works? | Why |
|---------|--------|-----|
| `/:path*{.svg,.png}` | No | Braces are literal in path-to-regexp |
| `/:path*.(svg\|png)` | No | Pipe needs to be inside a named param |
| `/:path*.:ext(svg\|png\|jpg)` | Yes | Regex parameter syntax |

Test patterns before deploying:
```javascript
const { match } = require("path-to-regexp");
const fn = match("/:path*.:ext(svg|png|jpg)");
console.log(fn("/logo.svg"));    // { params: { path: ["logo"], ext: "svg" } }
console.log(fn("/page"));        // false
```

## Content Security Policy

Configure CSP in `next.config.ts` security headers:

```typescript
{
  source: "/(.*)",
  headers: [
    {
      key: "Content-Security-Policy",
      value: [
        "default-src 'self'",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://www.googletagmanager.com https://www.google-analytics.com https://static.cloudflareinsights.com",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob: https:",
        "font-src 'self'",
        "connect-src 'self' https://www.google-analytics.com https://vitals.vercel-insights.com",
      ].join("; "),
    },
  ],
}
```

**Rules:**
- After migrating fonts to `next/font`, remove `fonts.googleapis.com` from `style-src` and `fonts.gstatic.com` from `font-src` -- self-hosted fonts are covered by `'self'`.
- Every new third-party script/style requires a CSP update.
- CSP violations show as console errors and directly lower the Best Practices score.

## Script Loading Strategy

Use `next/script` for third-party scripts:

```tsx
import Script from "next/script";

// Google Analytics -- load after page is interactive
<Script
  src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`}
  strategy="afterInteractive"
/>
```

| Strategy | When | Use For |
|----------|------|---------|
| `beforeInteractive` | Before hydration | Critical polyfills, A/B test scripts |
| `afterInteractive` | After hydration (default) | Analytics, tracking |
| `lazyOnload` | After everything | Chat widgets, social embeds |
| `worker` | In web worker (experimental) | Heavy non-critical scripts |

Never use raw `<script>` tags in Next.js -- they bypass optimization.

## Image Optimization

```tsx
import Image from "next/image";

// LCP hero image -- priority load
<Image
  src="/hero.webp"
  alt="Product dashboard showing analytics"
  width={1200}
  height={630}
  priority
  sizes="100vw"
/>

// Below-fold image -- lazy load (default)
<Image
  src="/feature.webp"
  alt="Feature screenshot"
  width={600}
  height={400}
  sizes="(max-width: 768px) 100vw, 50vw"
/>
```

**Rules:**
- Always set `priority` on the LCP image (usually the hero).
- Always provide `sizes` for responsive images.
- Always provide `width` and `height` to prevent CLS.
- Use `alt=""` for decorative images (logos next to brand text).
- Remote images require `remotePatterns` in `next.config.ts`.

## Bundle Analysis

```bash
# Install analyzer
npm install -D @next/bundle-analyzer

# Add to next.config.ts
const withBundleAnalyzer = require("@next/bundle-analyzer")({
  enabled: process.env.ANALYZE === "true",
});
module.exports = withBundleAnalyzer(nextConfig);

# Run analysis
ANALYZE=true next build
```

Look for:
- Large dependencies (lodash, moment.js) that can be replaced
- Duplicate packages across chunks
- Server-only code leaking into client bundles

## Browserslist Configuration

Add to `package.json` to reduce polyfill shipping:

```json
{
  "browserslist": [
    "last 2 Chrome versions",
    "last 2 Firefox versions",
    "last 2 Safari versions",
    "last 2 Edge versions"
  ]
}
```

This tells SWC to skip polyfills for `Array.prototype.at`, `Object.fromEntries`, `String.prototype.trimStart`, etc. Saves ~10-15KB on typical bundles.

Note: Some polyfills are bundled by Next.js core and cannot be eliminated via `browserslist`.
