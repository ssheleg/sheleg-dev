# Price integrity — one number, proved

**Load this when** a price appears in more than one file, when a pricing page or
funnel quotes a total before checkout, or when someone needs to prove the
advertised price is the charged price.

The failure this file exists to prevent is silent by construction. Checkout
sends Stripe a **price id** and Stripe holds the amount, so a wrong number in
your code never fails a request, never throws, and never shows up in a test. It
is only ever shown to customers — which is why it can survive for months.

## Contents

- [Catalogue modelling](#catalogue-modelling)
- [Product ids in code, price ids in configuration](#product-ids-in-code-price-ids-in-configuration)
- [Test and live mode](#test-and-live-mode)
- [One source for every displayed number](#one-source-for-every-displayed-number)
- [Quoting a total before checkout](#quoting-a-total-before-checkout)
- [Tiered pricing](#tiered-pricing)
- [Proving it against Stripe](#proving-it-against-stripe)
- [Money arithmetic](#money-arithmetic)
- [Currencies](#currencies)

## Catalogue modelling

Stripe's own rule, and it decides how your code is shaped:

- **One Product per plan a customer can choose.** Starter, Professional and
  Enterprise are three Products.
- **Multiple Prices on one Product only for variants of the same plan** —
  monthly vs annual, or per currency.

Tiers sharing one Product means every line item on every invoice shows the same
name, and customers cannot tell what they bought. It also destroys the mapping
this file depends on, because "which plan is this" stops being answerable from
the product id.

The `plan` object is deprecated. Use Prices.

## Product ids in code, price ids in configuration

Prices are immutable and get replaced when you reprice; Products survive.

```ts
const PRODUCTS = { PRO_MONTHLY: "prod_…", PRO_ANNUAL: "prod_…" } as const;

const PINNED_PRICES: Record<string, string> = {
  [PRODUCTS.PRO_MONTHLY]: "price_…",   // pinned from the Dashboard, dated in a comment
  [PRODUCTS.PRO_ANNUAL]:  "",          // "" = resolve dynamically
};
```

Pinning matters after a reprice, when the product has two active prices and
`prices.list({ active: true, limit: 1 })` returns them in an order nobody
promised. Keep the dynamic lookup as a fallback so a newly created product works
before anyone pins it.

## Test and live mode

Two accounts, two sets of ids, one codebase.

- Select with a variable **separate from the secret key**
  (`STRIPE_PRODUCT_MODE=test|production`). One variable that does both cannot be
  checked for consistency; two can.
- **Validation allowlists must contain both modes' ids.** Your database holds
  rows written against test and rows written against live, and a webhook asking
  "is this a product we sell" against only the current mode rejects real history.
- Translate `resource_missing` into the sentence that is actually true:

```ts
throw new Error(
  `Product ${productId} not found. STRIPE_PRODUCT_MODE="${mode}", ` +
  `key starts "${(process.env.STRIPE_SECRET_KEY ?? "").slice(0, 7)}…". ` +
  `The key and the product must be in the same mode.`
);
```

Left raw, that error reads as "somebody deleted the product" and sends people to
the Dashboard for an hour.

## One source for every displayed number

Every surface that shows money reads from **one** module: the pricing page, the
funnel, the billing page, the admin revenue view, the emails.

The observed failure mode is not a typo; it is a **second definition**. A page
declares `const ANNUAL_PRICE = 300` while the shared map says the annual plan is
$250 a year, and both are "right" in their own file. Because the savings badge
is computed from the same local constants, the error compounds: the page
advertised a 17% saving against a real 31% one, undersold by its own marketing.

Guard it with a test that reads the page source and refuses a literal:

```ts
it("keeps no price of its own", () => {
  expect(PAGE).not.toMatch(/const\s+(MONTHLY_PRICE|ANNUAL_PRICE)\s*=\s*\d/);
  expect(PAGE).toMatch(/from\s+"@\/lib\/pricing"/);
});
```

A test that only checks the numbers agree passes the moment someone copies the
right number into a second file — and then drifts. Test for the *second
definition*, which is the actual defect.

## Quoting a total before checkout

If a screen shows a total before the button, that number is a promise. Compute
it in one function used by both the screen and the checkout call, and clamp its
inputs there rather than trusting a control or a URL parameter.

Quote what the customer will actually have afterwards, too. When one balance
funds two different things — a seat and, say, usage credit — a screen that says
"you can afford this" while the purchase consumes the entire balance is telling
the truth about the seat and lying about the outcome. Do the subtraction once,
in the same function, and let every screen quote that.

## Tiered pricing

Two shapes, and calling one by the other's name misprices every account:

```ts
// Volume: ALL units are priced at the tier the quantity lands in.
function volume(qty: number, tiers: Tier[]) {
  const t = tiers.find((t) => t.upTo === null || qty <= t.upTo)!;
  return { perUnit: t.unitAmount, total: qty * t.unitAmount };
}

// Graduated: each range is charged at its own rate.
function graduated(qty: number, tiers: Tier[]) {
  let total = 0, left = qty, prev = 0;
  for (const t of tiers) {
    const end = t.upTo ?? Infinity;
    const used = Math.min(left, end - prev);
    total += used * t.unitAmount;
    left -= used; prev = end;
    if (left <= 0) break;
  }
  return { total: round2(total), effectiveRate: round2(total / qty) };
}
```

Whichever you implement, **Stripe must be configured the same way** — the tier
mode lives on the Price. Your table and Stripe's price are two copies of one
truth, so they belong in the conformance check below.

## Proving it against Stripe

A unit test cannot ask Stripe: there is no network in CI and no live key. So the
check runs where the live key is — a scheduled job in production, read-only.

```ts
for (const productId of Object.values(PRODUCTS)) {
  const { data } = await stripe.prices.list({ product: productId, active: true, limit: 10 });
  for (const p of data) {
    if (p.unit_amount === null) continue;                  // metered or tiered price
    const interval = p.recurring?.interval ?? null;
    if (interval !== null && interval !== "month" && interval !== "year") {
      log.warn("interval this check cannot reduce", { productId, interval });
      continue;                                            // do NOT guess
    }
    facts.push({ productId, name: nameOf(productId), unitAmount: p.unit_amount, interval });
  }
}
const { mismatches, missing } = comparePrices(EXPECTED_MONTHLY_USD, facts);
```

Three rules that make the job worth having:

- **Read-only.** A job that "corrects" prices turns one bad read into a
  repricing.
- **Report findings as findings.** A job whose purpose is to detect something
  and which returns a clean success on a detection has told nobody. Give the run
  a third outcome (`success_with_findings`) that pages a channel; an empty
  findings list is not a finding.
- **Refuse to reduce an interval you do not understand.** A weekly price treated
  as monthly reports conformance while the business charges four times what the
  code believes.

`missing` matters as much as `mismatches`: a plan the code prices and Stripe has
no active price for is a plan the customer cannot buy.

## Money arithmetic

- Stripe speaks **minor units** (integer cents). Convert once, at the boundary.
- Compare money in integer cents. `Math.abs(20.83 - 20.84) > 0.01` is `true` in
  floating point — a tolerance expressed in dollars reports drift at exactly the
  tolerance it claims to allow. Compare `Math.round(a * 100)` against
  `Math.round(b * 100)`.
- Allow one cent of slack when comparing a stored monthly equivalent to an
  annual price ($250 / 12 = $20.83), or every annual plan reports drift forever.
- Prefer integer cents or a decimal type in the database. Floats for money are a
  slow leak; if you inherit them, at least round at every write with one shared
  helper.

## Currencies

Multi-currency is not a formatting problem. Each currency is its own Price on
the Product, amounts are not derived by conversion, and the currency of a
subscription is fixed at creation — a customer cannot switch without a new
subscription. Store the currency alongside every amount you persist; a number
without its currency is unreconcilable the moment you sell in a second one.
