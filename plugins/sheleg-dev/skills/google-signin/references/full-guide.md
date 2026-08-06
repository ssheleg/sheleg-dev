# Google Sign-In (GIS) — Complete Guide: How It Works, How to Set It Up

> Self-contained, shareable guide. Explains the Google Identity Services (GIS)
> ID-token flow end-to-end, how to configure it from scratch in any web app,
> and the full security checklist. The reference implementation cited
> throughout is Prowl (`web/auth.py`, `web/server.py`, `web/static/js/app.js`)
> — but every section works standalone for any stack.

---

## 1. The two Google auth flows — and which one this is

Google offers two distinct browser auth mechanisms. Do not mix them up:

| | **GIS ID-token flow** (this guide) | OAuth 2.0 authorization-code flow |
|---|---|---|
| Purpose | *Authentication* — "who is this user?" | *Authorization* — "let me call Google APIs on the user's behalf" |
| What you get | One **ID token** (a JWT signed by Google) | `code` → exchanged server-side for `access_token` + `refresh_token` |
| Redirect URI needed | **No** (popup/One Tap posts the token to your JS callback) | Yes |
| Client secret needed | **No** (verification uses Google's public keys) | Yes |
| Google APIs callable after | None | Yes (Gmail, Drive, Calendar… per granted scopes) |
| Library | `https://accounts.google.com/gsi/client` | `google-auth-oauthlib` / OAuth endpoints |

If you only need "Sign in with Google" → GIS ID-token flow. Simpler, no
secrets, no redirect URIs, no token storage for Google APIs.

## 2. How the GIS flow works — step by step

```
 Browser                       Google                        Your backend
 ───────                       ──────                        ────────────
 1. load gsi/client script
 2. google.accounts.id.initialize({client_id, callback, nonce})
 3. renderButton(#container)
 4. user clicks button ──────► account-chooser popup
                               (user picks account,
                                consents on first use)
 5. callback receives  ◄────── ID token (JWT, RS256-signed
    {credential: "<jwt>"}       by Google's private key)
 6. POST /api/auth/google {credential, nonce} ─────────────► 7. verify ID token:
                                                                - signature vs Google JWKS
                                                                  (https://www.googleapis.com/oauth2/v3/certs)
                                                                - aud == YOUR client_id
                                                                - iss == accounts.google.com
                                                                - exp not passed
                                                                - email_verified == true
                                                                - nonce matches
                                                             8. find-or-create user,
                                                                link accounts
                                                             9. issue YOUR OWN session
                                                                (app JWT / cookie)
 10. store session, user is logged in ◄─────────────────────
```

Key mental model: **the Google ID token is proof of identity, not a session.**
You verify it once, then issue your *own* session token. Google's token is
never stored and never used again.

### 2.1 What's inside the ID token

A standard JWT with three base64url parts (`header.payload.signature`).
Payload claims you care about:

```json
{
  "iss": "https://accounts.google.com",
  "aud": "1234567890-abc.apps.googleusercontent.com",  // YOUR client ID
  "sub": "10769150350006150715113082367",              // stable Google user ID
  "email": "user@gmail.com",
  "email_verified": true,
  "name": "Ada Lovelace",
  "picture": "https://lh3.googleusercontent.com/…",
  "nonce": "d9b2d63d-…",       // echoed from initialize() — replay defense
  "iat": 1719410000,
  "exp": 1719413600            // ~1 hour lifetime
}
```

- **`sub` is the permanent user key.** Emails can change; `sub` never does.
  Store `sub` as `google_id` and match returning users by it, not by email.
- **`aud` must equal your client ID** — otherwise a token minted for another
  site would log users into yours.
- The signature is RS256 over Google's rotating public keys (JWKS). Client
  libraries fetch and cache those keys for you.

### 2.2 Frontend (reference: `web/static/js/app.js:16-110`, `web/static/index.html:246-296`)

```html
<!-- index.html -->
<meta name="google-client-id" content="__GOOGLE_CLIENT_ID__">  <!-- injected server-side from env -->
<script src="https://accounts.google.com/gsi/client" async defer></script>
<div id="google-signin-btn"></div>
```

```js
// app.js (essentials)
var _googleNonce = '';

function _renderGoogleButton() {
  var clientId = _getGoogleClientId();          // read from the <meta> tag
  if (!clientId) return;                        // Google auth not configured → hide, degrade honestly
  if (typeof google === 'undefined' || !google.accounts) {
    // gsi/client loads async — retry up to 20 × 150 ms instead of dropping the button
    if (_googleRenderRetries++ < 20) setTimeout(_renderGoogleButton, 150);
    return;
  }
  _googleNonce = crypto.randomUUID();           // fresh nonce per render — replay defense

  google.accounts.id.initialize({
    client_id: clientId,
    callback: handleGoogleCredential,
    auto_select: false,
    cancel_on_tap_outside: true,
    nonce: _googleNonce,
  });
  google.accounts.id.renderButton(
    document.getElementById('google-signin-btn'),
    { theme: 'outline', size: 'large', type: 'standard', text: 'continue_with', width: 308 },
  );
}

async function handleGoogleCredential(response) {
  // response.credential = the Google-signed ID token (JWT)
  var resp = await fetch('/api/auth/google', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ credential: response.credential, nonce: _googleNonce }),
  });
  var data = await resp.json();
  if (!resp.ok) { showError(data.detail); return; }
  // backend has set an HttpOnly session cookie; store display fields only
  AppState.saveCredentials(data.access_token, data.email, data.user_id, /* … */);
}
```

On logout, also call `google.accounts.id.disableAutoSelect()` so One Tap
doesn't silently re-login the user.

**Why serve the client ID via a server-injected `<meta>` tag:** one source of
truth (the `GOOGLE_CLIENT_ID` env var), no hardcoded IDs in JS bundles, and
environments (dev/staging/prod) can use different OAuth clients without a
rebuild. The client ID is public — not a secret — but drift between
environments is a classic outage.

### 2.3 Backend verification (reference: `web/auth.py:230-255`)

Never decode the JWT yourself and trust the payload. Use Google's library —
it fetches/caches JWKS, checks signature, `aud`, `iss`, `exp`:

```python
# pip install google-auth
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

_transport = google_requests.Request()   # reuse one instance (connection pooling)

def verify_google_token(credential: str) -> dict:
    if not GOOGLE_CLIENT_ID:
        raise ValueError("Google Sign-In is not configured (GOOGLE_CLIENT_ID missing)")
    try:
        payload = id_token.verify_oauth2_token(credential, _transport, GOOGLE_CLIENT_ID)
    except Exception as exc:
        raise ValueError(f"Invalid Google token: {exc}") from exc
    if not payload.get("email_verified"):
        raise ValueError("Google account email is not verified")
    return payload
```

Node equivalent: `google-auth-library` → `client.verifyIdToken({ idToken, audience: CLIENT_ID })`.

### 2.4 Account linking — the three-way branch (reference: `web/auth.py:358-435`)

Every Google login resolves to exactly one of three cases:

1. **Returning Google user** — a record with this `google_id` (`sub`) exists
   → issue session. Refresh `name`/`picture` if they changed.
2. **Existing email/password account, no `google_id`** — link Google to it
   (set `google_id`, mark `email_verified=True`) → issue session.
   ⚠️ **Pre-hijacking guard** (see §4.3): only auto-link if the existing
   account's email ownership was verified. Otherwise refuse with "sign in
   with your password".
3. **Brand-new user** — create the account with `email_verified=True` (the
   Google token already proved inbox ownership), empty password hash → issue
   session.

Then issue your own session. Prowl issues an HS256 app JWT (72 h, `ver` claim
for global revocation) delivered as an **HttpOnly, Secure, SameSite=Strict
cookie** — out of reach of JS/XSS, never sent cross-site.

## 3. Setup from scratch (~10 minutes)

### 3.1 Google Cloud Console

1. <https://console.cloud.google.com/> → create/pick a project.
2. **APIs & Services → OAuth consent screen**: user type **External**, fill
   app name / support email / developer email. Scopes: none needed beyond the
   defaults (GIS only uses `openid email profile`). Publish the app (while
   "Testing", only allowlisted test users can sign in).
3. **APIs & Services → Credentials → Create credentials → OAuth client ID**:
   - Application type: **Web application**.
   - **Authorized JavaScript origins**: every origin the button renders on —
     e.g. `https://yourapp.com`, `https://www.yourapp.com`, and for dev
     `http://localhost:8000` (origin = scheme+host+port, **no path, no
     trailing slash**).
   - **Authorized redirect URIs: leave empty** — the GIS popup flow doesn't
     redirect.
4. Copy the **Client ID** (`…apps.googleusercontent.com`). There is a client
   secret on that page — the GIS ID-token flow **never uses it**; don't ship it.

### 3.2 App configuration

```bash
# .env
GOOGLE_CLIENT_ID=1234567890-abc123.apps.googleusercontent.com
```

- Inject it into the page server-side (Prowl: `server.py` replaces
  `__GOOGLE_CLIENT_ID__` in the served HTML with the env value).
- If the env var is empty → the button silently doesn't render and the
  backend returns "not configured". Honest degradation, no crash.

### 3.3 Content-Security-Policy

If you set a CSP, GIS needs (reference: `web/server.py:625-642`):

```
script-src  … https://accounts.google.com;
connect-src … https://accounts.google.com;
frame-src   … https://accounts.google.com;
```

### 3.4 Dependencies

```bash
pip install google-auth        # Python
npm i google-auth-library      # Node
```

## 4. Security checklist (each item maps to a real attack)

### 4.1 Token verification — non-negotiable

- ☑ Verify **signature** against Google JWKS (the library does it). Never
  `jwt.decode(..., verify=False)`.
- ☑ Verify **`aud` == your client ID** — blocks tokens minted for other apps.
- ☑ Verify **`exp`** (library) — blocks stale tokens.
- ☑ Require **`email_verified == true`** — Google accounts can exist with
  unverified emails (e.g. Workspace-imported); skipping this lets an attacker
  claim someone else's address.

### 4.2 Nonce — replay defense

Generate a fresh random nonce per button render, pass it to
`google.accounts.id.initialize({nonce})`, send it alongside the credential,
compare server-side with the token's `nonce` claim
(`web/auth.py:375-376`). A stolen/logged ID token can't be replayed later
because the nonce won't match the new session's nonce.

### 4.3 Account pre-hijacking guard (P3-01 in Prowl)

Attack: attacker registers `victim@gmail.com` with a password *before* the
victim ever visits. Later the victim clicks "Sign in with Google". Naïve
auto-linking attaches victim's Google to the **attacker's** record — attacker
keeps password access to the merged account (its data and wallet).

Defense (`web/auth.py:392-417`): when a Google login matches an existing
**password** account whose email was **never verified**, refuse to auto-link;
tell the user to sign in with the password. Link only when email ownership of
the existing record is proven.

### 4.4 Login-CSRF (P3-03 in Prowl)

Attack: attacker's page force-POSTs the **attacker's own** Google credential
to your `/api/auth/google`; the victim's browser gets logged into the
attacker's account (victim then unknowingly feeds data/payments into it).

Defense (`web/server.py:1657-1686`), covering both possible delivery flows:

- **Form-POST flow** (GIS `login_uri` auto-POST): GIS double-submits
  `g_csrf_token` in body *and* cookie — compare both, constant-time
  (`hmac.compare_digest`). Reject if either is missing.
- **JS-fetch flow** (this app): no `g_csrf_token`, so enforce same-origin via
  **Fetch-Metadata** (`Sec-Fetch-Site: same-origin`) with an Origin-allowlist
  fallback. These headers are browser-set and unforgeable by page script.

### 4.5 Session hygiene

- ☑ Session cookie: **HttpOnly + Secure + SameSite=Strict** (XSS-exfil and
  CSRF resistant). `web/server.py:1604-1620`.
- ☑ Your app JWT carries a **version claim** (`ver`) checked against the
  user's stored `auth_version` → bumping it revokes all outstanding sessions
  ("log out everywhere").
- ☑ Rate-limit `/api/auth/*` (unauthenticated, internet-reachable).
- ☑ Log auth events (success/failure, user id prefix) — never log the
  credential/JWT itself.

### 4.6 What is public vs secret

| Value | Status |
|---|---|
| `GOOGLE_CLIENT_ID` | Public (visible in page source — fine) |
| Google client secret | **Unused** in GIS flow — don't put it in the app at all |
| Your app JWT secret (`WEB_JWT_SECRET`) | Secret — rotate via runbook; refuse to boot in prod with a default |
| Google ID token | Sensitive in transit; verify once, never store, never log |

## 5. Troubleshooting

| Symptom | Cause → fix |
|---|---|
| Button never renders | `gsi/client` not loaded yet (retry loop handles it); or empty client ID meta; or CSP blocks `accounts.google.com` |
| `[GSI_LOGGER] The given origin is not allowed for the given client ID` | Current origin missing from **Authorized JavaScript origins** (check port and `www.` exactly). Changes take minutes to propagate |
| `Invalid Google token: Token used too early/expired` | Server clock skew → sync NTP |
| `Wrong recipient / audience mismatch` | Frontend and backend use different client IDs — single env source of truth |
| 403 `access_denied` at consent | OAuth consent screen still in **Testing** and the user isn't a test user → publish the app |
| Works locally, fails in prod | Prod origin not in Authorized origins; or cookie has `Secure` on plain HTTP (Prowl dev: `PROWL_INSECURE_COOKIES=1`) |
| One Tap doesn't show / FedCM warnings | Third-party-cookie phase-out: GIS auto-migrates to FedCM; keep `gsi/client` unmodified and current — the rendered button flow is unaffected |
| User "lost password" but signed up via Google | Expected: Google-only accounts have empty password hash. Recovery = sign in with Google using the same email |

## 6. Reference implementation map (Prowl)

| Concern | Where |
|---|---|
| Client ID config | `web/auth.py:72` (`GOOGLE_CLIENT_ID` env) |
| Token verification | `web/auth.py:230-255` (`verify_google_token`) |
| Three-way linking + pre-hijack guard | `web/auth.py:358-435` (`google_auth_user`) |
| Endpoint + CSRF (both flows) | `web/server.py:1657-1690` (`/api/auth/google`) |
| Cookie policy | `web/server.py:1596-1620` |
| CSP allowances | `web/server.py:625-642` |
| Frontend button + nonce + callback | `web/static/js/app.js:16-110` |
| GIS script + meta + container | `web/static/index.html:246-296` |
| App JWT issue/verify/revocation | `web/auth.py:151-209` |
| Email canonicalization (anti-abuse) | `web/auth.py:116-145` |

## 7. Minimal end-to-end skeleton (copy-paste starting point, FastAPI)

```python
# --- backend ---
import os, hmac
from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
_transport = google_requests.Request()
app = FastAPI()

class GoogleAuthRequest(BaseModel):
    credential: str
    nonce: str | None = None
    g_csrf_token: str | None = None

@app.post("/api/auth/google")
async def google_auth(req: Request, data: GoogleAuthRequest, response: Response):
    # CSRF: double-submit for form-POST flow, Fetch-Metadata for JS flow
    if data.g_csrf_token:
        cookie = req.cookies.get("g_csrf_token") or ""
        if not hmac.compare_digest(cookie, data.g_csrf_token):
            raise HTTPException(403, "CSRF token mismatch")
    elif req.headers.get("sec-fetch-site", "same-origin") not in ("same-origin", "none"):
        raise HTTPException(403, "Cross-site request rejected")

    try:
        payload = id_token.verify_oauth2_token(data.credential, _transport, GOOGLE_CLIENT_ID)
    except Exception as exc:
        raise HTTPException(401, f"Invalid Google token: {exc}")
    if not payload.get("email_verified"):
        raise HTTPException(401, "Google account email is not verified")
    if data.nonce and payload.get("nonce") != data.nonce:
        raise HTTPException(401, "Nonce mismatch")

    user = await find_or_create_user(          # your 3-way linking here (§2.4, §4.3)
        google_id=payload["sub"], email=payload["email"].lower().strip(),
        name=payload.get("name"), picture=payload.get("picture"),
    )
    session_jwt = issue_app_session(user)      # your own JWT/session
    response.set_cookie("auth", session_jwt, httponly=True, secure=True,
                        samesite="strict", max_age=72 * 3600, path="/")
    return {"user_id": user.id, "email": user.email}
```

```html
<!-- --- frontend --- -->
<script src="https://accounts.google.com/gsi/client" async defer></script>
<div id="gbtn"></div>
<script>
  const NONCE = crypto.randomUUID();
  window.onload = () => {
    google.accounts.id.initialize({
      client_id: "YOUR_CLIENT_ID.apps.googleusercontent.com",
      nonce: NONCE,
      callback: async ({ credential }) => {
        const r = await fetch("/api/auth/google", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ credential, nonce: NONCE }),
        });
        if (r.ok) location.href = "/app";
      },
    });
    google.accounts.id.renderButton(document.getElementById("gbtn"),
      { theme: "outline", size: "large", text: "continue_with" });
  };
</script>
```

---

*Last verified against the Prowl codebase on 2026-07-08. If line numbers
drift, search for the function names — they are stable.*
