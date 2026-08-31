---
name: google-signin
description: >-
  Use when implementing, reviewing or debugging Google login / sign-in / sign-up on a website —
  wiring the GIS button or One Tap, verifying Google ID tokens on the server, linking Google to
  existing password accounts, or fixing "origin is not allowed for the given client ID". Covers
  GCP OAuth client setup, backend ID-token verification, three-way account linking with the pre-
  hijacking guard, login-CSRF defense, nonce/replay protection and a mandatory security
  checklist. Triggers - "sign in with google", "google login", "google sign-in button", "GIS",
  "google.accounts.id", "gsi/client", "verify google token", "one tap", "account linking",
  "login csrf", "g_csrf_token", "вход через Google", "кнопка входа Google", "связать аккаунты",
  "проверить токен Google". For the broader library surface use google-auth instead.
---

# Google Sign-In (GIS) — production web login

Condensed operating instructions. Full narrative guide with diagrams, token
anatomy, troubleshooting table, and a copy-paste FastAPI + JS skeleton:
[references/full-guide.md](references/full-guide.md) — read it when
implementing from scratch; its FastAPI + JS skeleton is the reference
implementation this skill ships.

## Pick the right flow first

- Only need "who is this user?" → **GIS ID-token flow** (this skill): load
  `https://accounts.google.com/gsi/client`, receive one Google-signed JWT,
  verify server-side. No redirect URI, no client secret, no Google-token
  storage.
- Need to call Google APIs (Gmail/Drive/Calendar) on the user's behalf →
  OAuth 2.0 **authorization-code** flow instead (redirect URI + client
  secret + refresh tokens). Never use the code flow just for login.

## Core flow (ID-token)

1. Frontend: `google.accounts.id.initialize({ client_id, callback, nonce })`
   + `renderButton()`. Generate a **fresh random nonce per render**
   (`crypto.randomUUID()`). The GSI script loads async — retry rendering
   (e.g. 20 × 150 ms) instead of silently dropping the button.
2. Callback receives `{ credential }` — a Google-signed ID token (JWT).
   POST it with the nonce to your backend. Never treat it as a session.
3. Backend: verify with the official lib — Python
   `google.oauth2.id_token.verify_oauth2_token(credential, transport, CLIENT_ID)`,
   Node `google-auth-library` `verifyIdToken({ idToken, audience })`. That
   checks signature (Google JWKS), `aud`, `iss`, `exp`. Never hand-decode
   and trust the payload.
4. Additionally require `email_verified == true` and token `nonce` claim ==
   submitted nonce.
5. Find-or-create the user, then issue YOUR OWN session (app JWT) as an
   **HttpOnly + Secure + SameSite=Strict cookie**. Google's token is
   verified once, never stored, never logged.

## Identity & account linking (three-way branch)

Key the user on `sub` (stable Google user ID; store as `google_id`) — never
on email (emails change, `sub` doesn't). On each Google login:

1. Record with this `google_id` exists → login (refresh name/picture).
2. Email matches an existing account without `google_id` → link, BUT apply
   the **pre-hijacking guard**: if that account is password-based and its
   email was never verified, REFUSE the auto-link ("sign in with your
   password instead"). Otherwise an attacker who pre-registered the
   victim's email with a known password captures the victim's first Google
   login into the attacker's record.
3. No match → create the user with `email_verified=True`, empty password
   hash.

## Login-CSRF (cover BOTH delivery flows)

- Form-POST flow (`login_uri` auto-POST): GIS double-submits `g_csrf_token`
  in body AND cookie — compare constant-time (`hmac.compare_digest`);
  reject if either side is missing.
- JS-fetch flow: no `g_csrf_token` — enforce same-origin via Fetch-Metadata
  (`Sec-Fetch-Site: same-origin`) with an Origin-allowlist fallback.

Without this, an attacker's page can force-POST the *attacker's* credential
and silently log the victim into the attacker's account.

## Setup (GCP)

1. Cloud Console → APIs & Services → OAuth consent screen (External;
   publish it — in "Testing" only allowlisted users can sign in).
2. Credentials → Create OAuth client ID → **Web application** →
   **Authorized JavaScript origins** = every origin the button renders on,
   incl. `http://localhost:<port>` for dev (scheme+host+port, no path, no
   trailing slash). **Authorized redirect URIs: leave empty** for GIS.
3. Ship only `GOOGLE_CLIENT_ID` (public; env var; one source of truth —
   inject into HTML server-side, e.g. via a `<meta>` tag). The client
   secret is UNUSED in the GIS flow — never put it in the app.
4. CSP if present: allow `https://accounts.google.com` in `script-src`,
   `connect-src`, `frame-src`.
5. If `GOOGLE_CLIENT_ID` is empty → hide the button and return
   "not configured" server-side (honest degradation, no crash).

## Security checklist (verify ALL before calling it done)

- [ ] Signature verified via official lib against Google JWKS (no
      `verify=False`, no manual base64 decode-and-trust)
- [ ] `aud` == your client ID; `exp` enforced
- [ ] `email_verified` required
- [ ] Nonce: fresh per render, checked server-side against the token claim
- [ ] Pre-hijacking guard on email-based linking
- [ ] Login-CSRF: `g_csrf_token` double-submit AND same-origin check for
      the JS flow
- [ ] Own session cookie: HttpOnly + Secure + SameSite=Strict
- [ ] `/api/auth/*` rate-limited; auth events logged WITHOUT the credential
- [ ] Session revocation path exists (e.g. an `auth_version`/`ver` claim
      check)
- [ ] Logout also calls `google.accounts.id.disableAutoSelect()`

## Debugging quick table

| Symptom | Fix |
|---|---|
| "The given origin is not allowed for the given client ID" | Add the exact origin (port, `www.`) to Authorized JavaScript origins; propagation takes minutes |
| Button never renders | GSI async race (add retry loop), empty client ID, or CSP blocks `accounts.google.com` |
| "Token used too early/expired" | Server clock skew → sync NTP |
| Audience mismatch | Frontend/backend client IDs differ → single env source of truth |
| `access_denied` on consent | Consent screen still in Testing → publish the app |
| Works locally, breaks in prod | Prod origin missing in GCP, or `Secure` cookie served over plain HTTP |
| One Tap missing / FedCM console warnings | FedCM is mandatory since Aug 2025 and the opt-out is gone (checked 2026-08-06). Load `gsi/client` from Google and keep it current — a vendored or pinned copy is the real break. The rendered button flow is unaffected; code branching on the old `isNotDisplayed()` moment callbacks is not |
