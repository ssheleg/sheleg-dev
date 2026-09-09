# OAuth 2.0 Web Server Flow (Node.js & Python)


## Contents

- [Prerequisites](#prerequisites)
- [Step 1: Set Authorization Parameters](#step-1-set-authorization-parameters)
- [Step 2: Redirect to Google](#step-2-redirect-to-google)
- [Step 3: Handle Callback](#step-3-handle-callback)
- [Step 4: Use Access Token](#step-4-use-access-token)
- [Refreshing Tokens](#refreshing-tokens)
- [Revoking Tokens](#revoking-tokens)
- [Incremental Authorization](#incremental-authorization)
- [Error Reference](#error-reference)
- [Complete Express Example](#complete-express-example)
- [Complete Flask Example](#complete-flask-example)
- [Complete FastAPI Example](#complete-fastapi-example)
- [Scopes Reference](#scopes-reference)

## Prerequisites

1. Enable APIs in [Google Cloud Console](https://console.developers.google.com/apis/library)
2. Create OAuth 2.0 Client ID at [Clients page](https://console.developers.google.com/auth/clients):
   - Application type: **Web application**
   - Set authorized redirect URIs
3. Download `client_secret.json`
4. Install dependencies:

**Node.js**

```bash
npm install googleapis crypto express express-session
```

**Python**

```bash
pip install google-auth google-auth-oauthlib google-api-python-client flask
```

## Step 1: Set Authorization Parameters

### Node.js

**One OAuth2 client PER request, never a shared singleton.** A module-level
`oauth2Client` whose `setCredentials(tokens)` runs on every callback is mutated
by every concurrent login — two users signing in at once end up with each
other's tokens. Build the client inside the handler; the client id/secret are
shared config, the CREDENTIALS are per principal and never assigned to a
process-wide object.

```js
const {google} = require('googleapis');
const crypto = require('crypto');

// A fresh client per request — the credentials it will hold are this user's.
function newOAuthClient() {
  return new google.auth.OAuth2(YOUR_CLIENT_ID, YOUR_CLIENT_SECRET, YOUR_REDIRECT_URL);
}

const oauthClient = newOAuthClient();

// State is REQUIRED, crypto-random, single-use with a TTL, and bound to the
// server session — not a value the client can echo back to itself.
const state = crypto.randomBytes(32).toString('hex');
req.session.oauthState = { value: state, expires: Date.now() + 10 * 60 * 1000 };

const authorizationUrl = oauthClient.generateAuthUrl({
  access_type: 'offline',          // 'online' (default) or 'offline' (gets refresh_token)
  scope: [
    'https://www.googleapis.com/auth/drive.metadata.readonly',
    'https://www.googleapis.com/auth/calendar.readonly'
  ],
  include_granted_scopes: true,    // incremental authorization
  state: state,                    // CSRF protection
  // prompt: 'consent',            // force re-consent (returns new refresh_token)
  // login_hint: 'user@example.com'
});
```

### Python

```python
from google_auth_oauthlib.flow import Flow
import secrets
import time

flow = Flow.from_client_secrets_file(
    'client_secret.json',
    scopes=[
        'https://www.googleapis.com/auth/drive.metadata.readonly',
        'https://www.googleapis.com/auth/calendar.readonly'
    ],
    redirect_uri=YOUR_REDIRECT_URL
)

state = secrets.token_hex(32)
# Server-bound, random, with a TTL: the callback consumes it atomically.
session['oauth_state'] = {'value': state, 'expires': time.time() + 600}

authorization_url, state = flow.authorization_url(
    access_type='offline',             # gets refresh_token
    include_granted_scopes='true',     # incremental authorization
    state=state,                       # CSRF protection
    # prompt='consent',                # force re-consent
    # login_hint='user@example.com'
)
```

### Authorization Parameters Reference

| Parameter | Required | Description |
|-----------|----------|-------------|
| `client_id` | Yes | From Cloud Console |
| `redirect_uri` | Yes | Must match authorized redirect URI exactly |
| `response_type` | Yes | Set to `code` (handled by library) |
| `scope` | Yes | Space-delimited or array of scopes |
| `access_type` | Recommended | `offline` to get refresh_token |
| `state` | Recommended | Random string for CSRF protection |
| `include_granted_scopes` | Optional | `true` for incremental authorization |
| `login_hint` | Optional | Email or `sub` identifier |
| `prompt` | Optional | `none`, `consent`, or `select_account` |

## Step 2: Redirect to Google

### Node.js

```js
res.redirect(authorizationUrl);
```

### Python (Flask)

```python
return redirect(authorization_url)
```

## Step 3: Handle Callback

### The session cookie is opaque — credentials live server-side, encrypted

**A signed cookie is not an encrypted one.** Flask's default session and
Starlette's `SessionMiddleware` SIGN the cookie (tamper-evident) but do NOT
encrypt it — anyone holding the cookie can base64-decode and read every value
in it, which the official docs confirm. So the cookie carries **only a random
opaque session id**; the Google credentials (`token`, `refresh_token`,
`client_secret`) go into a **server-side encrypted store**, fetched by
`(session_id, principal)` — never into the cookie, the redirect URL, or the
response body.

```python
# The cookie holds ONLY an opaque id. Credentials are server-side, encrypted.
session['sid'] = session.get('sid') or secrets.token_urlsafe(32)
credential_store.put(                      # encrypted at rest, keyed by (sid, principal)
    sid=session['sid'], principal=userinfo['sub'],
    credentials={'token': credentials.token,
                 'refresh_token': credentials.refresh_token,
                 'client_secret': credentials.client_secret, ...})
# Never: session['credentials'] = {...}     ← readable in the cookie
# Never: log or return the tokens            ← no console.log(tokens.access_token)
```

Four more, because a leaked secret does not announce itself: **never log a
token or a credential** (no `console.log(tokens.access_token)`; sanitize logs
by allow-list, so no token, `client_secret` or `refresh_token` reaches a line,
a stack trace or an error message); the session signing secret is a **required
production secret with NO dev fallback** (a hardcoded default signs every
deployment's cookies with a key in the repo — missing in production is
**fail-closed**, refuse to boot); the auth cookie is **`Secure`, and the
callback refuses plain HTTP** — an OAuth code or token over `http://` is a code
or token on the wire; and **a credential-store read or write that FAILS is an
auth failure** — re-prompt the user or return 503, never proceed as if the
credentials loaded (a silent empty read logs the user in as nobody).

### Node.js

```js
const url = require('url');

app.get('/oauth2callback', async (req, res) => {
  const q = url.parse(req.url, true).query;

  if (q.error) {
    return res.status(400).send('Authorization failed');   // never log the raw error/token
  }

  // Validate state BEFORE the token exchange: it must be PRESENT on both sides
  // (undefined === undefined must NOT pass), unexpired, and consumed atomically
  // so a replay of the same callback cannot reuse it.
  const saved = req.session.oauthState;
  delete req.session.oauthState;                            // single-use: consume it now
  if (!q.state || !saved || saved.value !== q.state || Date.now() > saved.expires) {
    return res.status(403).send('State invalid, missing, expired or already used');
  }

  const oauthClient = newOAuthClient();                     // a client for THIS request
  const {tokens} = await oauthClient.getToken(q.code);
  oauthClient.setCredentials(tokens);                       // credentials stay on the local client

  // tokens.access_token — short-lived access token
  // tokens.refresh_token — long-lived (only on first auth!)
  // tokens.expiry_date — expiration timestamp
  // tokens.scope — granted scopes (check for partial consent)

  const grantedScopes = tokens.scope.split(' ');
});
```

### Python (Flask)

```python
@app.route('/oauth2callback')
def oauth2callback():
    if request.args.get('error'):
        return 'Authorization failed', 400

    # Validate state BEFORE the token exchange, and consume it atomically:
    # pop() removes it in the same step, so a replayed callback finds nothing.
    # Presence is required on BOTH sides — None == None must NOT pass.
    saved = session.pop('oauth_state', None)
    got = request.args.get('state')
    if (not got or not saved or saved['value'] != got
            or time.time() > saved['expires']):
        abort(403, 'State invalid, missing, expired or already used')

    flow = Flow.from_client_secrets_file(
        'client_secret.json',
        scopes=SCOPES,
        redirect_uri=YOUR_REDIRECT_URL,
        state=saved['value']
    )
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    # credentials.token — access token
    # credentials.refresh_token — only on first auth!
    # credentials.expiry — expiration datetime
    # credentials.scopes — granted scopes

    # Cookie: opaque id only. Credentials: server-side, encrypted, keyed by
    # (session id, principal) — never serialized into the signed cookie.
    session['sid'] = session.get('sid') or secrets.token_urlsafe(32)
    credential_store.put(session['sid'], principal=userinfo['sub'], credentials={
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': list(credentials.scopes),
    })
    return redirect('/profile')
```

### Python (FastAPI)

```python
import secrets
import time

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow

@router.get('/oauth2callback')
async def oauth2callback(request: Request):
    if request.query_params.get('error'):
        raise HTTPException(400, 'Authorization failed')

    # Consume atomically (pop) and validate BEFORE the exchange; a wrong,
    # expired or replayed state must never start a token exchange.
    saved = request.session.pop('oauth_state', None)
    got = request.query_params.get('state')
    if (not got or not saved or saved['value'] != got
            or time.time() > saved['expires']):
        raise HTTPException(403, 'State invalid, missing, expired or already used')

    flow = Flow.from_client_secrets_file(
        'client_secret.json',
        scopes=SCOPES,
        redirect_uri=YOUR_REDIRECT_URL,
        state=saved['value']
    )
    flow.fetch_token(code=request.query_params.get('code'))
    credentials = flow.credentials

    # Store credentials in session or database
    request.session['credentials'] = credentials_to_dict(credentials)
    return RedirectResponse('/profile')
```

## Step 4: Use Access Token

### Node.js

```js
// Preferred: Authorization header
const res = await oauth2Client.fetch('https://www.googleapis.com/drive/v3/files');

// Or with googleapis client:
const drive = google.drive({version: 'v3', auth: oauth2Client});
const fileList = await drive.files.list();
```

### Python

```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

credentials = Credentials(**session['credentials'])
drive = build('drive', 'v3', credentials=credentials)
file_list = drive.files().list().execute()
```

## Refreshing Tokens

### Node.js

```js
// Auto-refresh: the library handles this if refresh_token is set
oauth2Client.setCredentials({
  refresh_token: STORED_REFRESH_TOKEN
});

// Manual refresh:
const {credentials} = await oauth2Client.refreshAccessToken();

// Listen for new tokens:
oauth2Client.on('tokens', (tokens) => {
  if (tokens.refresh_token) {
    // Store in database — only sent once!
  }
  // Never log a token or a credential (FIX-DV-07) — a token in a log is a
  // token anyone with log access holds.
});
```

### Python

```python
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

credentials = Credentials(
    token=stored_access_token,
    refresh_token=stored_refresh_token,
    token_uri='https://oauth2.googleapis.com/token',
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET
)

# Manual refresh:
if credentials.expired and credentials.refresh_token:
    credentials.refresh(Request())
    # credentials.token is the new access token
    # credentials.expiry is the new expiration datetime
    # Persist new token to storage
```

**Note**: `google-api-python-client` (`build(...)`) auto-refreshes credentials before each API call if a refresh_token is available.

## Revoking Tokens

### Node.js

```js
// Revoke access token:
await oauth2Client.revokeToken(access_token);

// Revoke refresh token:
await oauth2Client.revokeToken(refresh_token);

// Or revoke credentials on the client:
await oauth2Client.revokeCredentials();
```

### Python

```python
import google.oauth2.credentials
from google.auth.transport.requests import Request

# Revoke via requests library:
import requests as http_requests

http_requests.post(
    'https://oauth2.googleapis.com/revoke',
    params={'token': credentials.token},
    headers={'content-type': 'application/x-www-form-urlencoded'}
)
```

After revocation, redirect user to re-consent if needed.

## Incremental Authorization

Request additional scopes later without re-requesting all scopes:

### Node.js

```js
const newAuthUrl = oauth2Client.generateAuthUrl({
  access_type: 'offline',
  scope: ['https://www.googleapis.com/auth/gmail.readonly'],
  include_granted_scopes: true,
  state: newState
});
```

### Python

```python
flow = Flow.from_client_secrets_file(
    'client_secret.json',
    scopes=['https://www.googleapis.com/auth/gmail.readonly'],
    redirect_uri=YOUR_REDIRECT_URL
)
authorization_url, state = flow.authorization_url(
    access_type='offline',
    include_granted_scopes='true',
    state=new_state
)
```

## Error Reference

| Error | Cause |
|-------|-------|
| `access_denied` | User denied consent |
| `admin_policy_enforced` | Workspace admin blocked scopes |
| `redirect_uri_mismatch` | redirect_uri doesn't match Cloud Console config |
| `invalid_client` | Wrong client_secret |
| `deleted_client` | OAuth client was deleted |
| `invalid_grant` | Token expired or invalidated; re-authenticate user |
| `invalid_request` | Missing/malformed parameters |
| `org_internal` | Project restricts to specific GCP org accounts |

## Complete Express Example

```js
const express = require('express');
const session = require('express-session');
const crypto = require('crypto');
const {google} = require('googleapis');

const app = express();
app.use(session({secret: 'your-secret', resave: false, saveUninitialized: false}));

// A client per request — client id/secret are config, credentials are per user.
function newOAuthClient() {
  return new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID, process.env.GOOGLE_CLIENT_SECRET,
    'http://localhost:3000/oauth2callback');
}

const SCOPES = ['https://www.googleapis.com/auth/userinfo.profile'];

app.get('/auth', (req, res) => {
  const state = crypto.randomBytes(32).toString('hex');
  req.session.oauthState = { value: state, expires: Date.now() + 10 * 60 * 1000 };

  const url = newOAuthClient().generateAuthUrl({
    access_type: 'offline',
    scope: SCOPES,
    state,
    include_granted_scopes: true
  });
  res.redirect(url);
});

app.get('/oauth2callback', async (req, res) => {
  if (req.query.error) return res.redirect('/error');
  const saved = req.session.oauthState;
  delete req.session.oauthState;                    // single-use
  if (!req.query.state || !saved || saved.value !== req.query.state
      || Date.now() > saved.expires) return res.status(403).send('CSRF');

  const {tokens} = await newOAuthClient().getToken(req.query.code);
  req.session.tokens = tokens;
  res.redirect('/profile');
});

app.get('/profile', async (req, res) => {
  if (!req.session.tokens) return res.redirect('/auth');
  const oauthClient = newOAuthClient();             // local to this request
  oauthClient.setCredentials(req.session.tokens);

  const oauth2 = google.oauth2({version: 'v2', auth: oauthClient});
  const {data} = await oauth2.userinfo.get();
  res.json(data);
});

app.listen(3000);
```

## Complete Flask Example

```python
import os
import secrets
from flask import Flask, redirect, request, session, jsonify, abort
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret')

CLIENT_ID = os.environ['GOOGLE_CLIENT_ID']
CLIENT_SECRET = os.environ['GOOGLE_CLIENT_SECRET']
REDIRECT_URI = 'http://localhost:5000/oauth2callback'
SCOPES = ['https://www.googleapis.com/auth/userinfo.profile']

@app.route('/auth')
def auth():
    flow = Flow.from_client_config(
        {
            'web': {
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    state = secrets.token_hex(32)
    session['oauth_state'] = {'value': state, 'expires': time.time() + 600}
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        state=state
    )
    return redirect(authorization_url)


@app.route('/oauth2callback')
def oauth2callback():
    if request.args.get('error'):
        return 'Authorization failed', 400
    saved = session.pop('oauth_state', None)   # single-use: consume BEFORE exchange
    got = request.args.get('state')
    if (not got or not saved or saved['value'] != got
            or time.time() > saved['expires']):
        abort(403, 'State invalid, missing, expired or already used')

    flow = Flow.from_client_config(
        {
            'web': {
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        state=saved['value']
    )
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    userinfo = build('oauth2', 'v2', credentials=creds).userinfo().get().execute()
    # Opaque id in the cookie; credentials in the server-side encrypted store.
    session['sid'] = session.get('sid') or secrets.token_urlsafe(32)
    credential_store.put(session['sid'], principal=userinfo['id'], credentials={
        'token': creds.token, 'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri, 'client_id': creds.client_id,
        'client_secret': creds.client_secret, 'scopes': list(creds.scopes or []),
    })
    session['principal'] = userinfo['id']
    return redirect('/profile')


@app.route('/profile')
def profile():
    stored = credential_store.get(session.get('sid'), session.get('principal'))
    if not stored:
        return redirect('/auth')
    creds = Credentials(**stored)
    service = build('oauth2', 'v2', credentials=creds)
    user_info = service.userinfo().get().execute()
    return jsonify(user_info)


if __name__ == '__main__':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # dev only
    app.run(port=5000, debug=True)
```

## Complete FastAPI Example

```python
import os
import secrets
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # dev only

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key='dev-secret')

CLIENT_ID = os.environ['GOOGLE_CLIENT_ID']
CLIENT_SECRET = os.environ['GOOGLE_CLIENT_SECRET']
REDIRECT_URI = 'http://localhost:8000/oauth2callback'
SCOPES = ['https://www.googleapis.com/auth/userinfo.profile']

CLIENT_CONFIG = {
    'web': {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
        'token_uri': 'https://oauth2.googleapis.com/token',
    }
}

@app.get('/auth')
async def auth(request: Request):
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    state = secrets.token_hex(32)
    request.session['oauth_state'] = {'value': state, 'expires': time.time() + 600}
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        state=state
    )
    return RedirectResponse(authorization_url)


@app.get('/oauth2callback')
async def oauth2callback(request: Request):
    if request.query_params.get('error'):
        raise HTTPException(400, 'Authorization failed')
    saved = request.session.pop('oauth_state', None)   # single-use: consume BEFORE exchange
    got = request.query_params.get('state')
    if (not got or not saved or saved['value'] != got
            or time.time() > saved['expires']):
        raise HTTPException(403, 'State invalid, missing, expired or already used')

    flow = Flow.from_client_config(
        CLIENT_CONFIG, scopes=SCOPES, redirect_uri=REDIRECT_URI,
        state=saved['value']
    )
    flow.fetch_token(code=request.query_params.get('code'))
    creds = flow.credentials
    userinfo = build('oauth2', 'v2', credentials=creds).userinfo().get().execute()
    # Opaque id in the cookie; credentials in the server-side encrypted store.
    sid = request.session.get('sid') or secrets.token_urlsafe(32)
    request.session['sid'] = sid
    request.session['principal'] = userinfo['id']
    credential_store.put(sid, principal=userinfo['id'], credentials={
        'token': creds.token, 'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri, 'client_id': creds.client_id,
        'client_secret': creds.client_secret, 'scopes': list(creds.scopes or []),
    })
    return RedirectResponse('/profile')


@app.get('/profile')
async def profile(request: Request):
    stored = credential_store.get(request.session.get('sid'),
                                  request.session.get('principal'))
    if not stored:
        return RedirectResponse('/auth')
    creds = Credentials(**stored)
    service = build('oauth2', 'v2', credentials=creds)
    user_info = service.userinfo().get().execute()
    return user_info
```

## Scopes Reference

Full list: https://developers.google.com/identity/protocols/oauth2/scopes

Common scopes:
- `openid` — OpenID Connect
- `https://www.googleapis.com/auth/userinfo.email` — User email
- `https://www.googleapis.com/auth/userinfo.profile` — User profile info
- `https://www.googleapis.com/auth/drive.readonly` — Read-only Drive
- `https://www.googleapis.com/auth/calendar.readonly` — Read-only Calendar
- `https://www.googleapis.com/auth/cloud-platform` — Full GCP access
