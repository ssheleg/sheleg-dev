# Testing and local development

Split out of `SKILL.md` on 2026-08-20 for the same reason as
[`callback-route-hardening.md`](callback-route-hardening.md): the body was ~4894 tokens
against a 4750 working limit, and the house answer at that point is a split rather than a
trim. This is the operational half — how you run the thing on a laptop, and what you have
to cover before believing a green suite.

`stripe-billing` ships the same pair of subjects at
[`../../stripe-billing/references/testing-and-local-dev.md`](../../stripe-billing/references/testing-and-local-dev.md),
and its *Mutation testing* section is the argument this matrix assumes: plant a defect
against every row before believing it.

---

## Local development

Two paths, and you want both:

**Skip the gateway.** A `SKIP_BILLING=true` branch that credits immediately and
logs loudly. Everyone building a feature that merely *touches* checkout should
use this. Make it impossible in production: assert `NODE_ENV !== 'production'`
at the branch, not just in config.

**Real gateway, tunnelled callback.** Callbacks cannot reach `localhost`:

```bash
cloudflared tunnel --url http://localhost:3000
# → https://random-name.trycloudflare.com  →  set as the callback base URL, restart the app
```

Then keep a **signed mock callback** in your test tooling — a script that builds
a real payload, signs it with the dev key and POSTs it. This is what makes the
sad paths (`wrong_amount`, `refund_fail`, `locked`) testable at all; you cannot
ask a gateway to underpay you on demand.

---

## Test matrix

Cover these, and plant a defect against each before believing the green:

| Case | What it catches |
|---|---|
| valid signature | the happy path |
| tampered signature | constant-time compare, 403 not 500 |
| signature over a payload containing a URL | the escaping trap |
| duplicate delivery of a settling status | idempotency guard |
| `paid_over` | crediting the received amount, not the invoiced |
| `wrong_amount` | no full credit on a partial payment |
| out-of-order delivery (final, then earlier) | the `notIn` guard, not timestamps |
| callback from a non-allowlisted IP | proxy-aware extraction |
| `refund_process` then `refund_fail` | refund is a state machine |
| `locked` | no credit, no auto-cancel |

---

Back to [`SKILL.md`](../SKILL.md). The provider-specific half — one credential, no sandbox
host, and what "test mode" actually toggles — is
[`heleket-provider.md`](heleket-provider.md), *The test/live boundary*.
