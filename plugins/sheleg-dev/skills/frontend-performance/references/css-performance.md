# CSS & Animation Performance


## Contents

- [GPU-Composited Properties](#gpu-composited-properties)
- [Gradient Animation Alternatives](#gradient-animation-alternatives)
- [`will-change` Usage](#will-change-usage)
- [Critical CSS](#critical-css)
- [Layout Shift Prevention](#layout-shift-prevention)
- [Tailwind CSS Performance](#tailwind-css-performance)

## GPU-Composited Properties

The browser can animate these properties on the GPU compositor thread without triggering layout or paint:

| Property | GPU-composited | Use For |
|----------|---------------|---------|
| `transform` | Yes | Movement, scaling, rotation |
| `opacity` | Yes | Fading in/out |
| `filter` | Yes (most browsers) | Blur, hue-rotate, brightness |
| `background-position` | **No** | Avoid animating |
| `width` / `height` | **No** | Avoid animating |
| `top` / `left` / `right` / `bottom` | **No** | Use `transform: translate()` instead |
| `margin` / `padding` | **No** | Avoid animating |
| `border-radius` | **No** | Avoid animating |
| `box-shadow` | **No** | Use `opacity` on a pseudo-element instead |
| `color` / `background-color` | **No** | Pre-render both states, animate `opacity` |

Animating non-composited properties triggers layout recalculation and paint on every frame, causing jank and increasing CLS.

## Gradient Animation Alternatives

### Problem: Animated `background-position`

```css
/* BAD -- triggers paint on every frame */
@keyframes gradient-shift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}
.animate-gradient {
  background-size: 200% 200%;
  animation: gradient-shift 6s ease infinite;
}
```

This is flagged by Lighthouse as "non-composited animation" because `background-position` cannot be GPU-composited.

### Fix Option A: `filter: hue-rotate()` (recommended)

```css
@keyframes gradient-shift {
  0%, 100% { filter: hue-rotate(0deg); }
  50% { filter: hue-rotate(30deg); }
}
.animate-gradient {
  animation: gradient-shift 6s ease infinite;
  will-change: filter;
}
```

Pros: GPU-composited, subtle color variation, minimal code change.
Cons: Shifts all colors (not just the gradient), effect is different from background-position scrolling.

### Fix Option B: Transform on pseudo-element

```css
.animate-gradient {
  position: relative;
  overflow: hidden;
}
.animate-gradient::before {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(to right, #a855f7, #d946ef, #a855f7);
  background-size: 200% 100%;
  animation: gradient-slide 6s ease infinite;
  will-change: transform;
  z-index: -1;
}
@keyframes gradient-slide {
  0%, 100% { transform: translateX(0); }
  50% { transform: translateX(-50%); }
}
```

Pros: True sliding gradient, fully GPU-composited.
Cons: More complex markup, doesn't work with `bg-clip-text`.

### Fix Option C: Remove animation

```css
.animate-gradient {
  /* Static gradient, no animation */
}
```

Simplest fix. Use when the animation is subtle and non-essential.

## `will-change` Usage

`will-change` hints the browser to promote an element to its own compositor layer.

**Rules:**
- Only add to elements that actually animate
- Remove after animation completes (for one-shot animations)
- Never use `will-change: auto` (it's the default, useless)
- Never apply to more than a few elements -- each promoted layer uses GPU memory

```css
/* Good -- only on animated elements */
.animate-gradient { will-change: filter; }
.slide-in { will-change: transform; }

/* Bad -- blanket application */
* { will-change: transform; }
```

## Critical CSS

### Framework Handling

Most modern frameworks handle critical CSS automatically:
- **Next.js**: Inlines CSS for initial render via built-in optimization
- **Astro**: Scoped styles are inlined per-component
- **Vite/SvelteKit**: CSS is extracted and linked efficiently

### Manual Optimization

If the framework doesn't handle it:

1. Extract CSS used by above-the-fold elements
2. Inline it in `<style>` within `<head>`
3. Load remaining CSS asynchronously:
   ```html
   <link rel="preload" href="/styles.css" as="style" onload="this.onload=null;this.rel='stylesheet'">
   <noscript><link rel="stylesheet" href="/styles.css"></noscript>
   ```

## Layout Shift Prevention

| Element | Fix |
|---------|-----|
| Images | Always set `width` and `height` attributes |
| Embeds/iframes | Set explicit dimensions or use `aspect-ratio` |
| Dynamic content | Reserve space with `min-height` |
| Web fonts | Use `font-display: swap` + size-adjusted fallback |
| Ads/banners | Reserve slot with fixed dimensions |
| Sticky headers | Account for height with `scroll-padding-top` |

### Font CLS Mitigation

When fonts swap from fallback to web font, text reflows and causes CLS. Mitigate with:

```css
/* Size-adjust the fallback to match the web font */
@font-face {
  font-family: "Fallback";
  src: local("Arial");
  size-adjust: 105%;
  ascent-override: 95%;
  descent-override: 22%;
  line-gap-override: 0%;
}
body {
  font-family: "YourWebFont", "Fallback", sans-serif;
}
```

`next/font` does this automatically when you use the `variable` option.

## Tailwind CSS Performance

- **Purge unused classes** -- Tailwind v3+ does this automatically in production. Ensure `content` paths cover all template files.
- **Avoid runtime class generation** -- Never use string interpolation for Tailwind classes (`text-${color}-500`). Tailwind can't detect these at build time.
- **Opacity modifiers and contrast** -- `text-primary/80` creates 80% opacity, which may fail WCAG contrast. Prefer full-opacity tokens for text, use opacity only on decorative elements.
- **Minimize `@apply`** -- Excessive `@apply` bloats CSS. Use component composition instead.
