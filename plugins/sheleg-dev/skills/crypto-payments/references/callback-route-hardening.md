# Callback route hardening — the proxy hop and the CSRF hole

Split out of `SKILL.md` on 2026-08-20, when its body measured ~4894 tokens against the
house working limit of 4750. Both sections below are web plumbing rather than payment
logic — they are about the request that carries a callback, not about the money in it —
which is why they are the seam. Signature verification (`SKILL.md`, *Webhook signature
verification*) is the real gate; these two are defence in depth, and each has a failure
mode that looks like "webhooks stopped working" rather than like a security event.

---

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
