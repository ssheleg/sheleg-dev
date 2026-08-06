# Accessibility Rules That Affect Lighthouse Score

These accessibility issues are automatically detected by Lighthouse and directly reduce the Accessibility score.

## Color Contrast

### WCAG AA Requirements

| Text Type | Minimum Ratio | Example |
|-----------|--------------|---------|
| Normal text (< 18px or < 14px bold) | 4.5:1 | Body copy, labels, section headers |
| Large text (>= 18px or >= 14px bold) | 3:1 | Headings, hero text |
| UI components & graphical objects | 3:1 | Buttons, icons, form borders |

### Common Failures in Dark Themes

Dark themes are the most common source of contrast failures because designers use opacity to create visual hierarchy:

| Pattern | Problem | Fix |
|---------|---------|-----|
| `text-primary/80` | 80% opacity reduces contrast below 4.5:1 | Use `text-primary` (full opacity) |
| `text-muted-foreground/60` | 60% opacity on already-muted color | Use `text-muted-foreground` |
| `text-white/60` on dark bg | Insufficient contrast | Use `text-white/80` minimum, test with tool |
| `text-gray-400` on `bg-gray-900` | May or may not pass depending on exact values | Test with contrast checker |

### Tailwind Opacity vs Dedicated Color Tokens

**Bad (Lighthouse failure):**
```html
<p class="text-primary/80">Section Label</p>
<span class="text-muted-foreground/60">Subtitle</span>
```

**Good:**
```html
<p class="text-primary">Section Label</p>
<span class="text-muted-foreground">Subtitle</span>
```

If you need visual hierarchy without reducing contrast below WCAG thresholds:
- Use `font-weight` differences (semibold vs regular)
- Use `font-size` differences (sm vs xs)
- Use `letter-spacing` and `uppercase` for labels
- Use a dedicated lighter color token that still passes contrast (e.g., define `--muted-accent` that's tested for 4.5:1)

### Checking Contrast

Use Chrome DevTools: inspect element -> color picker shows contrast ratio against computed background.

Or calculate manually: `(L1 + 0.05) / (L2 + 0.05)` where L1 is the lighter relative luminance.

### Intentional Low-Contrast Exceptions

Some design systems (cyberpunk, neon, etc.) intentionally use low-contrast text as an aesthetic choice (`text-cyan-400/60`, `text-white/40`). These should:
- Be reviewed with visual testing, not bulk-replaced
- Only be used on decorative, non-essential text
- Never be used on actionable elements (buttons, links, form labels)

## Heading Hierarchy

### Rules

1. **One `<h1>` per page** -- typically the main page title or hero headline.
2. **Sequential descent** -- `h1` -> `h2` -> `h3` -> `h4`. Never skip levels.
3. **Non-structural "headings"** use `<p>` or `<span>` -- footer column titles, sidebar labels, card subtitles are not document headings.

### Common Violations

| Location | Violation | Fix |
|----------|-----------|-----|
| Footer column titles as `<h4>` | h1 -> h2 -> h4 (skips h3) | Change to `<p class="font-semibold text-xs uppercase ...">` |
| Multiple `<h1>` per page | Each section has its own h1 | Use `<h2>` for section titles |
| Card titles as `<h3>` inside a section with no `<h2>` | Heading skip | Wrap cards in a section with an `<h2>` |

### Screen Reader Impact

Screen reader users navigate by heading level. Skipped levels break expected navigation patterns and confuse the document outline.

## Image Alt Text

### Decision Tree

```
Is the image decorative (purely visual, no information)?
├── YES → alt=""
│   Examples: background patterns, decorative borders, logos next to brand text
└── NO → Write descriptive alt text
    ├── Is it informative? → Describe the content
    │   Example: alt="Dashboard showing 50% growth in monthly users"
    ├── Is it functional (link/button)? → Describe the action
    │   Example: alt="Download PDF report"
    └── Is it complex (chart/diagram)? → Summarize + provide long description
        Example: alt="Sales trend chart" + aria-describedby for details
```

### Redundancy Rule

If an image appears next to text that says the same thing, the image is decorative:

**Bad (screen reader announces "PrivateClawd" twice):**
```html
<img alt="PrivateClawd" src="/logo.svg" />
<span>PrivateClawd</span>
```

**Good:**
```html
<img alt="" src="/logo.svg" />
<span>PrivateClawd</span>
```

## Interactive Element Sizing

Minimum tap target: **48x48px** (Google), **44x44px** (Apple HIG).

```css
/* Ensure minimum tap target even for small visual buttons */
.icon-button {
  min-width: 44px;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
```

Adjacent tap targets need at least 8px spacing to prevent accidental taps.

## Focus Indicators

Lighthouse checks for visible focus indicators on interactive elements:

```css
/* Never remove focus outlines without replacement */
:focus-visible {
  outline: 2px solid var(--ring);
  outline-offset: 2px;
}

/* Bad -- removes accessibility */
*:focus { outline: none; }
```

## ARIA Landmarks

Ensure the page has proper landmark regions. Lighthouse checks for:

- `<main>` -- one per page, wrapping primary content
- `<nav>` -- navigation regions
- `<header>` / `<footer>` -- page header and footer
- `role="search"` on search forms

Landmarks enable screen reader users to jump between page sections.

## Language Attribute

```html
<html lang="en">
```

Always set the `lang` attribute on `<html>`. Lighthouse flags its absence. Use the correct BCP 47 language tag for the page's primary language.
