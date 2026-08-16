# GA4 Event Tracking — Reference


**Load this when** you are designing the event schema: recommended vs custom events, naming rules, parameter limits, the item object, the ecommerce funnel, SaaS/subscription events, and a typed `trackEvent` wrapper.

## Contents

- [Table of Contents](#table-of-contents)
- [Event Types](#event-types)
- [Recommended Events](#recommended-events)
- [Custom Events](#custom-events)
- [Parameter Rules](#parameter-rules)
- [Ecommerce Events](#ecommerce-events)
- [SaaS / Subscription Events](#saas--subscription-events)
- [trackEvent Wrapper Pattern](#trackevent-wrapper-pattern)

## Table of Contents

- [Event Types](#event-types)
- [Recommended Events](#recommended-events)
- [Custom Events](#custom-events)
- [Parameter Rules](#parameter-rules)
- [Ecommerce Events](#ecommerce-events)
- [SaaS / Subscription Events](#saas--subscription-events)
- [trackEvent Wrapper Pattern](#trackevent-wrapper-pattern)

## Event Types

| Type | Description | Setup |
|------|-------------|-------|
| **Automatic** | `page_view`, `first_visit`, `session_start` | Always collected |
| **Enhanced measurement** | `scroll`, `click` (outbound), `file_download`, `video_*`, `site_search` | Toggle in GA4 Admin |
| **Recommended** | Predefined names Google recognizes (`login`, `sign_up`, `purchase`, etc.) | Implement with exact name |
| **Custom** | Any name you define for app-specific actions | Implement + create custom dimension in GA4 |

## Recommended Events

Use these exact names — GA4 recognizes them for built-in reports and features.

### Authentication & Engagement

| Event | Parameters | When |
|-------|-----------|------|
| `login` | `method` (string) | User logs in |
| `sign_up` | `method` (string) | User registers |
| `share` | `method`, `content_type`, `item_id` | User shares content |
| `search` | `search_term` | User searches |

### Ecommerce (Core Flow)

| Event | Required Params | When |
|-------|----------------|------|
| `view_item` | `currency`, `value`, `items[]` | User views product |
| `add_to_cart` | `currency`, `value`, `items[]` | Added to cart |
| `remove_from_cart` | `currency`, `value`, `items[]` | Removed from cart |
| `view_cart` | `currency`, `value`, `items[]` | Cart viewed |
| `begin_checkout` | `currency`, `value`, `items[]` | Checkout started |
| `add_payment_info` | `currency`, `value`, `payment_type` | Payment info added |
| `add_shipping_info` | `currency`, `value`, `shipping_tier` | Shipping selected |
| `purchase` | `transaction_id`, `currency`, `value`, `items[]` | Purchase completed |
| `refund` | `transaction_id`, `currency`, `value` | Refund issued |

### Content & Engagement

| Event | Parameters | When |
|-------|-----------|------|
| `select_content` | `content_type`, `content_id` | User selects content |
| `view_promotion` | `creative_name`, `promotion_id` | Promo viewed |
| `select_promotion` | `creative_name`, `promotion_id` | Promo clicked |

## Custom Events

For app-specific actions not covered by recommended events.

### Naming Rules

- Use `snake_case` (lowercase with underscores)
- Max 40 characters
- Must start with a letter
- No reserved prefixes: `_`, `firebase_`, `ga_`, `google_`, `gtag.`
- No reserved names: `ad_click`, `ad_impression`, `app_remove`, etc.

### Examples for SaaS Apps

```javascript
trackEvent('send_message');
trackEvent('report_started');
trackEvent('report_completed', { tool_calls: 5, tokens: 1200 });
trackEvent('copy_report');
trackEvent('share_report');
trackEvent('generate_artifact', { artifact_type: 'pdf' });
trackEvent('feedback_prompt_shown');
trackEvent('submit_feedback', { rating: 5 });
trackEvent('upgrade_prompt_shown');
trackEvent('limit_reached_shown');
```

## Parameter Rules

### Built-in Parameters (Auto-populated)

These parameters automatically map to GA4 dimensions without extra configuration:
`method`, `search_term`, `currency`, `value`, `transaction_id`, `payment_type`,
`shipping_tier`, `coupon`, `item_id`, `item_name`, `item_category`.

### Custom Parameters

Custom parameters require creating a **custom dimension** or **custom metric** in GA4 Admin
to appear in reports:

1. GA4 Admin > Custom definitions > Create custom dimension
2. Set scope: Event-scoped (most common) or User-scoped
3. Map to the parameter name used in code

Limits per property:
- 50 event-scoped custom dimensions
- 25 user-scoped custom dimensions
- 50 custom metrics

### Parameter Value Limits

- String values: max 100 characters
- Event name: max 40 characters
- Up to 25 custom parameters per event
- `items[]` array: max 200 items

## Ecommerce Events

### Item Object Structure

```javascript
gtag('event', 'purchase', {
  transaction_id: 'T_12345',
  value: 29.99,
  currency: 'USD',
  items: [{
    item_id: 'plan_pro',
    item_name: 'Pro Plan',
    item_category: 'subscription',
    price: 29.99,
    quantity: 1
  }]
});
```

### Ecommerce Funnel

Track the complete funnel for conversion analysis:

```
view_item → add_to_cart → begin_checkout → add_payment_info → purchase
```

Each step should include consistent `items[]` data for funnel analysis.

## SaaS / Subscription Events

Common event patterns for SaaS products:

```javascript
// Paywall / upgrade flow
trackEvent('view_paywall');
trackEvent('begin_checkout', { plan_slug: 'pro_monthly' });
trackEvent('purchase', { plan: 'pro_monthly', value: 29.99, currency: 'USD' });

// Subscription management
trackEvent('view_subscription_panel');
trackEvent('change_plan', { plan_slug: 'enterprise_annual' });
trackEvent('cancel_subscription');

// Engagement quality
trackEvent('feature_used', { feature: 'export_pdf' });
trackEvent('onboarding_step', { step: 3, step_name: 'connect_data' });
trackEvent('activation_complete');
```

## trackEvent Wrapper Pattern

Always use a wrapper to guard against gtag not being loaded:

```javascript
function trackEvent(name, params) {
  if (typeof gtag === 'function') gtag('event', name, params);
}
```

Benefits:
- No errors if gtag hasn't loaded yet (deferred loading)
- No errors if user declined consent and gtag is unavailable
- Single point to add logging, filtering, or batching later

### Extended Wrapper with Debug Support

```javascript
function trackEvent(name, params) {
  if (typeof gtag !== 'function') return;
  if (location.hostname === 'localhost') {
    console.debug('[GA]', name, params);
    return;
  }
  gtag('event', name, params);
}
```

---

## User identification

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

Moved out of `SKILL.md` on 2026-08-16: the body was 5273 tokens against a
< 5000 budget, and identity is the other half of the question this file already
owns — an event name says what happened, identity says who it happened to.

