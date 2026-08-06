# Sign In with Google (Google Identity Services)

## Table of Contents
- [Overview](#overview)
- [Client-Side Integration](#client-side-integration)
- [Server-Side ID Token Verification](#server-side-id-token-verification)
- [CSRF Protection](#csrf-protection)
- [Nonce Verification](#nonce-verification)
- [ID Token Payload Fields](#id-token-payload-fields)
- [Account Linking Flows](#account-linking-flows)
- [Next.js / React Integration Pattern](#nextjs--react-integration-pattern)
- [FastAPI Integration Pattern](#fastapi-integration-pattern)
- [Flask Integration Pattern](#flask-integration-pattern)
- [FedCM Migration](#fedcm-migration)

## Overview

Sign In with Google (part of Google Identity Services / GIS) provides:
- **Personalized Sign-In Button** — branded Google sign-in button
- **One Tap** — low-friction prompt for returning users
- **Automatic Sign-In** — silent sign-in for previously consented users

GIS separates authentication (sign-in → ID token) from authorization (API access → access token). Use GIS for sign-in; use OAuth 2.0 authorization API separately for data access.

## Client-Side Integration

### HTML API (simplest)

```html
<script src="https://accounts.google.com/gsi/client" async></script>

<div id="g_id_onload"
  data-client_id="YOUR_CLIENT_ID.apps.googleusercontent.com"
  data-context="signin"
  data-ux_mode="popup"
  data-callback="handleCredentialResponse"
  data-auto_prompt="false">
</div>

<div class="g_id_signin"
  data-type="standard"
  data-shape="rectangular"
  data-theme="outline"
  data-text="signin_with"
  data-size="large"
  data-logo_alignment="left">
</div>

<script>
function handleCredentialResponse(response) {
  // response.credential = JWT ID token
  // Send to your server for verification
  fetch('/auth/google', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({credential: response.credential})
  });
}
</script>
```

### JavaScript API

```js
google.accounts.id.initialize({
  client_id: 'YOUR_CLIENT_ID.apps.googleusercontent.com',
  callback: handleCredentialResponse,
  auto_select: true,     // automatic sign-in
  cancel_on_tap_outside: false,
  nonce: myNonce          // optional: anti-replay nonce
});

// Render button
google.accounts.id.renderButton(
  document.getElementById('google-signin-btn'),
  {theme: 'outline', size: 'large', type: 'standard'}
);

// Show One Tap prompt
google.accounts.id.prompt();
```

### Redirect Mode

```html
<div id="g_id_onload"
  data-client_id="YOUR_CLIENT_ID"
  data-ux_mode="redirect"
  data-login_uri="https://example.com/auth/google">
</div>
```

## Server-Side ID Token Verification

### Node.js

```js
const {OAuth2Client} = require('google-auth-library');
const client = new OAuth2Client();

async function verifyGoogleToken(idToken) {
  const ticket = await client.verifyIdToken({
    idToken: idToken,
    audience: WEB_CLIENT_ID,
    // For multiple clients:
    // audience: [CLIENT_ID_1, CLIENT_ID_2]
  });
  const payload = ticket.getPayload();

  // payload.sub — unique Google Account ID (use as primary key)
  // payload.email — user's email
  // payload.email_verified — boolean
  // payload.name — full name
  // payload.picture — profile picture URL
  // payload.given_name — first name
  // payload.family_name — last name
  // payload.hd — hosted domain (Google Workspace)

  return payload;
}
```

### Python

```python
from google.oauth2 import id_token
from google.auth.transport import requests

# Reuse a single Request instance for connection pooling
request = requests.Request()

def verify_google_token(credential: str) -> dict:
    payload = id_token.verify_oauth2_token(
        credential,
        request,
        WEB_CLIENT_ID
        # For multiple clients, pass a list:
        # audience=[CLIENT_ID_1, CLIENT_ID_2]
    )

    if not payload.get('email_verified', False):
        raise ValueError('Google account email is not verified')

    # payload['sub'] — unique Google Account ID (use as primary key)
    # payload['email'] — user's email
    # payload['email_verified'] — boolean
    # payload['name'] — full name
    # payload.get('picture') — profile picture URL
    # payload.get('given_name') — first name
    # payload.get('family_name') — last name
    # payload.get('hd') — hosted domain (Google Workspace)

    return payload
```

### Verification Checks

Both `verifyIdToken` (Node.js) and `verify_oauth2_token` (Python) automatically verify:
- **JWT signature** — using Google's public keys (rotated regularly)
- **`aud` claim** — matches your client ID
- **`exp` claim** — token not expired
- **`iss` claim** — is `accounts.google.com` or `https://accounts.google.com`

### Additional Manual Checks

**Node.js**

```js
const payload = ticket.getPayload();

// Restrict to Google Workspace domain
if (payload.hd !== 'yourdomain.com') {
  throw new Error('Must use organization account');
}

// Verify email is authoritative
const isGoogleAuthoritative = (
  (payload.email_verified && payload.hd) ||     // Workspace account
  payload.email.endsWith('@gmail.com')           // Gmail account
);
```

**Python**

```python
# Restrict to Google Workspace domain
if payload.get('hd') != 'yourdomain.com':
    raise ValueError('Must use organization account')

# Verify email is authoritative
is_google_authoritative = (
    (payload.get('email_verified') and payload.get('hd'))
    or payload['email'].endswith('@gmail.com')
)
```

## CSRF Protection

GIS uses double-submit-cookie pattern.

### Node.js (Express)

```js
app.post('/auth/google', (req, res) => {
  const csrfTokenCookie = req.cookies['g_csrf_token'];
  const csrfTokenBody = req.body.g_csrf_token;

  if (!csrfTokenCookie || !csrfTokenBody) {
    return res.status(400).send('Missing CSRF token');
  }
  if (csrfTokenCookie !== csrfTokenBody) {
    return res.status(400).send('CSRF token mismatch');
  }

  const payload = await verifyGoogleToken(req.body.credential);
  // ... create session
});
```

### Python (FastAPI)

```python
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

class GoogleLoginRequest(BaseModel):
    credential: str
    g_csrf_token: str | None = None
    nonce: str | None = None

@router.post("/google")
async def google_login(request: Request, body: GoogleLoginRequest):
    # CSRF: match cookie against body (skip if cookie absent, e.g. cross-origin)
    if body.g_csrf_token:
        cookie_token = request.cookies.get("g_csrf_token")
        if cookie_token and cookie_token != body.g_csrf_token:
            raise HTTPException(status_code=403, detail="CSRF token mismatch")

    payload = verify_google_token(body.credential)
    # ... create session
```

### Python (Flask)

```python
from flask import Flask, request, jsonify, abort

@app.route('/auth/google', methods=['POST'])
def google_login():
    body = request.get_json()
    csrf_cookie = request.cookies.get('g_csrf_token')
    csrf_body = body.get('g_csrf_token')

    if not csrf_cookie or not csrf_body:
        abort(400, 'Missing CSRF token')
    if csrf_cookie != csrf_body:
        abort(400, 'CSRF token mismatch')

    payload = verify_google_token(body['credential'])
    # ... create session
```

## Nonce Verification

Pass a nonce to `google.accounts.id.initialize()` on the client, then verify it server-side against the token's `nonce` claim.

**Client-side:**

```js
const nonce = crypto.randomUUID();  // or any random string
google.accounts.id.initialize({
  client_id: CLIENT_ID,
  callback: handleResponse,
  nonce: nonce
});
// Send nonce alongside credential to your backend
```

**Server-side (Node.js):**

```js
const payload = ticket.getPayload();
if (payload.nonce !== expectedNonce) {
  throw new Error('Nonce mismatch');
}
```

**Server-side (Python):**

```python
if body.nonce:
    token_nonce = payload.get('nonce')
    if not token_nonce or token_nonce != body.nonce:
        raise ValueError('Nonce mismatch')
```

## ID Token Payload Fields

| Field | Description |
|-------|-------------|
| `sub` | Unique Google Account ID — **use as primary key** |
| `email` | User's email address |
| `email_verified` | Whether email is verified |
| `name` | Full name |
| `given_name` | First name |
| `family_name` | Last name |
| `picture` | Profile picture URL |
| `hd` | Hosted domain (Google Workspace only) |
| `iss` | Issuer (`accounts.google.com`) |
| `aud` | Your client ID |
| `exp` | Expiration time (Unix timestamp) |
| `iat` | Issued at time |
| `nonce` | Anti-replay nonce (if provided during initialization) |
| `locale` | User's locale |

**Important**: Use `sub` (not `email`) as the unique identifier. Email can be changed by the user.

## Account Linking Flows

After verifying the ID token, determine user state:

### Node.js

```js
async function handleGoogleSignIn(payload) {
  const googleId = payload.sub;
  const email = payload.email;

  // 1. Check if user exists by Google ID
  let user = await db.findUserByGoogleId(googleId);
  if (user) {
    return createSession(user);
  }

  // 2. Check if email matches existing account — link Google
  user = await db.findUserByEmail(email);
  if (user) {
    await db.linkGoogleAccount(user.id, googleId);
    return createSession(user);
  }

  // 3. New user — create account
  user = await db.createUser({
    googleId,
    email,
    name: payload.name,
    picture: payload.picture
  });
  return createSession(user);
}
```

### Python (SQLAlchemy)

```python
async def find_or_create_google_user(session, payload: dict):
    google_id = payload['sub']
    email = payload['email'].lower().strip()
    name = payload.get('name', '') or email.split('@')[0]
    picture = payload.get('picture')

    # 1. Match by google_id
    user = await session.scalar(select(User).where(User.google_id == google_id))
    if user:
        return user, False  # existing user

    # 2. Match by email — link Google account
    user = await session.scalar(select(User).where(User.email == email))
    if user:
        user.google_id = google_id
        user.auth_provider = 'google'
        user.picture_url = picture
        await session.commit()
        return user, False  # linked

    # 3. New user
    user = User(
        email=email,
        display_name=name,
        auth_provider='google',
        google_id=google_id,
        picture_url=picture,
        password_hash=None,
    )
    session.add(user)
    await session.commit()
    return user, True  # created
```

## Next.js / React Integration Pattern

### Client Component

```tsx
'use client';
import {useEffect, useRef, useCallback} from 'react';

declare global {
  interface Window { google: any; }
}

export function GoogleSignInButton({onSuccess}: {onSuccess: (credential: string, nonce: string) => void}) {
  const nonceRef = useRef(crypto.randomUUID());

  const handleResponse = useCallback((response: {credential: string}) => {
    onSuccess(response.credential, nonceRef.current);
    nonceRef.current = crypto.randomUUID();
  }, [onSuccess]);

  useEffect(() => {
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.onload = () => {
      window.google.accounts.id.initialize({
        client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID!,
        callback: handleResponse,
        nonce: nonceRef.current
      });
      window.google.accounts.id.renderButton(
        document.getElementById('google-signin-btn'),
        {theme: 'outline', size: 'large', width: 300}
      );
    };
    document.head.appendChild(script);
    return () => { script.remove(); };
  }, [handleResponse]);

  return <div id="google-signin-btn" />;
}
```

### Server Action / API Route (Node.js)

```ts
// app/api/auth/google/route.ts
import {OAuth2Client} from 'google-auth-library';
import {NextRequest, NextResponse} from 'next/server';

const client = new OAuth2Client();

export async function POST(req: NextRequest) {
  const {credential, nonce} = await req.json();

  const ticket = await client.verifyIdToken({
    idToken: credential,
    audience: process.env.GOOGLE_CLIENT_ID,
  });
  const payload = ticket.getPayload()!;

  if (nonce && payload.nonce !== nonce) {
    return NextResponse.json({error: 'Nonce mismatch'}, {status: 401});
  }

  // Create/find user, create session...
  return NextResponse.json({success: true, user: {email: payload.email, name: payload.name}});
}
```

## FastAPI Integration Pattern

```python
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

router = APIRouter()
_request = google_requests.Request()
CLIENT_ID = settings.google_client_id

class GoogleLoginRequest(BaseModel):
    credential: str
    g_csrf_token: str | None = None
    nonce: str | None = None

@router.post("/auth/google")
async def google_login(request: Request, body: GoogleLoginRequest):
    # 1. CSRF check
    if body.g_csrf_token:
        cookie_token = request.cookies.get("g_csrf_token")
        if cookie_token and cookie_token != body.g_csrf_token:
            raise HTTPException(status_code=403, detail="CSRF token mismatch")

    # 2. Verify Google ID token
    try:
        payload = id_token.verify_oauth2_token(body.credential, _request, CLIENT_ID)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    if not payload.get("email_verified", False):
        raise HTTPException(status_code=401, detail="Email not verified")

    # 3. Verify nonce
    if body.nonce:
        if payload.get("nonce") != body.nonce:
            raise HTTPException(status_code=401, detail="Nonce mismatch")

    # 4. Find or create user, issue app JWT...
    user, is_new = await find_or_create_google_user(db, payload)
    token = create_jwt(user.id, user.email)
    return {"token": token, "user": serialize_user(user)}
```

## Flask Integration Pattern

```python
from flask import Flask, request, jsonify, abort
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

app = Flask(__name__)
_request = google_requests.Request()
CLIENT_ID = 'YOUR_CLIENT_ID.apps.googleusercontent.com'

@app.route('/auth/google', methods=['POST'])
def google_login():
    body = request.get_json()

    # 1. CSRF check
    csrf_cookie = request.cookies.get('g_csrf_token')
    csrf_body = body.get('g_csrf_token')
    if csrf_cookie and csrf_body and csrf_cookie != csrf_body:
        abort(403, 'CSRF token mismatch')

    # 2. Verify Google ID token
    try:
        payload = id_token.verify_oauth2_token(body['credential'], _request, CLIENT_ID)
    except ValueError:
        abort(401, 'Invalid Google token')

    if not payload.get('email_verified', False):
        abort(401, 'Email not verified')

    # 3. Verify nonce
    nonce = body.get('nonce')
    if nonce and payload.get('nonce') != nonce:
        abort(401, 'Nonce mismatch')

    # 4. Find or create user, issue session/JWT...
    return jsonify({'success': True, 'email': payload['email']})
```

## FedCM — mandatory, not a migration you are planning

Google Identity Services moved to the Federated Credential Management (FedCM)
API in Chrome as part of Privacy Sandbox, and **FedCM became mandatory for One
Tap and Sign-In button implementations in August 2025** (verified 2026-08-06).
The transition-period escape hatch — the `use_fedcm` opt-out and the traffic
exemption that preceded it — is gone. A guide that presents FedCM as optional or
upcoming predates the cutover; date-check it before following it.

What this means in practice:

- The GIS library handles FedCM for you — **keep `gsi/client` loaded from
  Google and current**. A vendored or pinned copy is the one reliable way to
  break sign-in.
- Test in Chrome with third-party cookies disabled. That is the default
  condition now, not an edge case.
- FedCM renders a **browser-native** UI instead of the old iframe One Tap, so
  CSS overrides and screenshots written against the iframe no longer apply.
- Code that branched on the old `prompt()` notification callbacks
  (`isNotDisplayed()`, `getNotDisplayedReason()`) needs revisiting — the
  moment-notification shape changed with FedCM.

Source: [Migrate to FedCM](https://developers.google.com/identity/gsi/web/guides/fedcm-migration).

## Sign Out

```js
// Client-side sign out
google.accounts.id.disableAutoSelect();

// Also revoke server-side session
fetch('/auth/logout', {method: 'POST'});
```
