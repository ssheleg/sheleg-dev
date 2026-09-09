# Callback route hardening — the proxy hop and the CSRF hole

Split out of `SKILL.md` on 2026-08-20, when its body measured ~4894 tokens against the
house working limit of 4750. Both sections below are web plumbing rather than payment
logic — they are about the request that carries a callback, not about the money in it —
which is why they are the seam. Signature verification (`SKILL.md`, *Webhook signature
verification*) is the real gate; these two are defence in depth, and each has a failure
mode that looks like "webhooks stopped working" rather than like a security event.

---

## Contents

- [IP allowlisting behind a proxy](#ip-allowlisting-behind-a-proxy)
- [CSRF exemption for callback routes](#csrf-exemption-for-callback-routes)
- [Crediting: lifecycle, grant and refund are separate (DV-05)](#crediting-lifecycle-grant-and-refund-are-separate-dv-05)

## IP allowlisting behind a proxy

Signature verification is the real gate; the allowlist is defence in depth and
cheap. It is also the single most common cause of "webhooks stopped working
after we moved to a load balancer".

```ts
function callerIp(req): string | null {
  // Trust ONLY the hop your own infrastructure appends.
  const xff = req.headers['x-forwarded-for'];
  if (typeof xff === 'string') {
    const hops = xff.split(',').map((s) => s.trim());
    return hops[hops.length - TRUSTED_PROXY_COUNT] ?? null;
  }
  return req.socket.remoteAddress ?? null;
}
```

Taking `xff[0]` trusts a header the client controls — anyone can claim to be the
gateway. Count from the right by the number of proxies you actually run, and
keep that number in configuration, because it changes when infrastructure does.

Allowlist the provider's published callback IPs, log a rejection with the
observed IP, and **never** fall back to "allow if the header is missing".

## CSRF exemption for callback routes

A gateway cannot present your CSRF token. Exempt the callback path explicitly
and narrowly:

```ts
// middleware.ts (Next.js)
export const config = { matcher: ['/((?!api/payments/webhook).*)'] };
```

Exempt the **one** path, by exact match, and make it the only route in your app
that skips CSRF. A prefix match on `/api/payments` exempts the checkout endpoint
too, which is where the money is.

---

Back to [`SKILL.md`](../SKILL.md) — *Webhook signature verification* is the gate these two
sit behind, and *Test matrix* in
[`testing-and-local-dev.md`](testing-and-local-dev.md) carries the non-allowlisted-IP case.


## Crediting: lifecycle, grant and refund are separate (DV-05)

The CAS advances the payment's lifecycle; the GRANT is a second, independent
step gated on a confirmed settlement; refunds and holds have their own path.
Conflating them credits money that never settled — a webhook that transitions
a payment to FAILED passes the CAS (`count: 1`) exactly as PAID does.

```ts
// 1. Advance the lifecycle by compare-and-swap. Fires for ANY non-final
//    transition — PAID, FAILED, UNDERPAID, REFUNDED alike — so it is NOT
//    permission to credit. It only records what the provider said.
const { count } = await db.payment.updateMany({
  where: { invoiceId, status: { notIn: FINAL_STATUSES } },
  data: { status: mapped, paidAmount, txid, network, settledAt: new Date() },
});

// 2. Refunds and holds are their own path — never swallowed as a duplicate.
if (mapped === 'REFUNDED' || mapped === 'ON_HOLD') {
  await recordRefundOrHold(invoiceId, mapped);         // own ledger, own rules
  return res.status(200).json({ ok: true });
}
if (count === 0) {
  return res.status(200).json({ ok: true, duplicate: true });  // already advanced
}

// 3. CREDIT ONLY A CONFIRMED SETTLEMENT, and only once — an immutable grant
//    row keyed by invoice is the business dedup, atomic with the credit.
//    FAILED/UNDERPAID/pending advance the lifecycle above and grant NOTHING.
if (mapped === 'PAID') {
  await db.$transaction(async (tx) => {
    try {
      await tx.grantLedger.create({ data: { invoiceId, amount: creditFor(invoiceId) } });
    } catch (e) {
      if (isUniqueViolation(e)) return;                // this settlement already granted
      throw e;
    }
    await creditUser(tx, invoiceId);
  });
}
```

`updateMany` + a status guard is a compare-and-swap for the LIFECYCLE, not the
grant: a CAS that advanced a payment to FAILED returns `count: 1` too, so the
credit hangs off `mapped === 'PAID'` and a UNIQUE grant row, never off the CAS.
