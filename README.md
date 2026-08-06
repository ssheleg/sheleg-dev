# sheleg-dev

The integration layer a product reaches once it has users: **money in, tracking,
sign-in, and speed.**

Part of the [ssheleg skill family](https://github.com/ssheleg/sshlg-skills).

---

## The five skills

| Skill | Answers |
|---|---|
| **`crypto-payments`** | how do I take crypto without losing money to under-payment, duplicate webhooks or rate drift |
| **`ad-tracking`** | how do GA4, Google Ads, Meta and LinkedIn fire correctly under Consent Mode v2 |
| **`google-signin`** | how do I let people sign in with Google without handing someone their account |
| **`google-auth`** | how does my *server* authenticate to Google — OAuth, ADC, service accounts, federation |
| **`frontend-performance`** | why is the Lighthouse score bad and which fix actually moves it |

Each carries its own references and loads them only when the work reaches them.

**`crypto-payments`** — status mapping with an explicit terminal set;
signature verification in constant time, with the forward-slash escaping trap
that makes signatures valid for some payloads and not others; idempotency as a
compare-and-swap (`updateMany` with a non-final status guard) instead of the
read-then-write race; proxy-aware IP allowlisting that counts hops from the
right; CSRF exemption scoped to exactly one path; the conversion buffer; the
reconciliation fields that make "what did we actually receive" answerable six
months later; refunds and AML holds as states, not events.

**`ad-tracking`** — one unified consent update across four platforms, standard
event mapping, e-commerce with deduplication, per-platform CSP, Next.js
patterns. Four deep references on the Google tag: consent mode, the gtag API,
event schema design, and performance/security.

**`google-signin`** — the ID-token flow treated as a security problem: the
three-way account-linking branch with the **pre-hijacking guard**, login-CSRF
covering both delivery flows, nonce and replay protection, and a checklist where
every item maps to a named attack.

**`google-auth`** — OAuth 2.0 web-server flow, Application Default Credentials
and its search order, service-account JWT including domain-wide delegation,
Workload and Workforce Identity Federation, impersonation, downscoping. Node and
Python side by side throughout.

**`frontend-performance`** — Core Web Vitals with an audit workflow and a budget
template; font loading; GPU-composited animation and what to do instead of
animating `background-position`; code splitting, cache headers, CSP; and the
accessibility rules — contrast, heading order, alt text, target size — that move
a Lighthouse score.

---

## Install

**Claude Code plugin** (recommended):

```bash
/plugin marketplace add ssheleg/sheleg-dev
/plugin install sheleg-dev@sheleg-dev
```

**npm installer** — copies all five skills into `~/.claude/skills/`:

```bash
npx @ssheleg/sheleg-dev
```

**Any of 70+ agents:**

```bash
npx skills add ssheleg/sheleg-dev
```

**Whole family at once:**

```bash
npx --yes sshlg-skills@latest update
```

Restart your agent afterwards — skills load at session start.

---

## A note on `crypto-payments`

The skill is provider-neutral on purpose. The reusable engineering — signature
verification, idempotency, the buffer, reconciliation — is provider-shaped, and
the invariants hold across Coinbase Commerce, NOWPayments, BTCPay and others.
One gateway's concrete wire format lives in a reference, together with the
compliance position on record for it.

**Choosing a payment processor is a business and compliance decision, not a
technical one.** Processors differ in licensing, AML programme and sanctions
exposure, and that standing changes. This pack tells you how to integrate one
correctly. It does not tell you which one to trust.

---

## Verify

```bash
python3 test/validate.py
```

One version across `package.json`, `plugin.json`, `marketplace.json` and the top
`CHANGELOG` entry; front matter inside the Agent Skills limits (over-long front
matter does not error — hosts truncate it silently, which is worse); and
`SKILL.md` ↔ `references/` agreement in **both** directions, so neither a
dangling link nor a file nobody loads can ship.

CI plants a defect against every one of those guards and requires the validator
to fail. A green from a check nobody has watched fail is not evidence.

---

## License

MIT © ssheleg
