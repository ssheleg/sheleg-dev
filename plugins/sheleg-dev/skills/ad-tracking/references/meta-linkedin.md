# Meta Pixel & LinkedIn — Reference

**Load this when** the work is Meta or LinkedIn rather than Google: the parameter object per standard event, the firing wrapper and its consent gate, advanced matching with hashed identifiers and what must never be sent, and deduplication against the Conversions API.

Moved out of `SKILL.md` when the body was 906 lines against a 500-line budget.
Everything here is detail the body used to carry inline; the body keeps the
setup snippet and the traps.

## Contents

- [Parameter object properties](#parameter-object-properties) — what Meta accepts per event
- [Firing events](#firing-events) — the wrapper and its consent gate
- [Advanced matching](#advanced-matching) — hashed identifiers, and what must never be sent
- [Everything below](#) — LinkedIn conversion detail, deduplication with CAPI

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

