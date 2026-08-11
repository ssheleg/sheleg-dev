# OAuth 2.0 Web Server Flow (Node.js & Python)


## Contents

- [Table of Contents](#table-of-contents)
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

## Table of Contents
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

```js
const {google} = require('googleapis');
const crypto = require('crypto');

const oauth2Client = new google.auth.OAuth2(
  YOUR_CLIENT_ID,
  YOUR_CLIENT_SECRET,
  YOUR_REDIRECT_URL
);

const state = crypto.randomBytes(32).toString('hex');
req.session.state = state;

const authorizationUrl = oauth2Client.generateAuthUrl({
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

flow = Flow.from_client_secrets_file(
    'client_secret.json',
    scopes=[
        'https://www.googleapis.com/auth/drive.metadata.readonly',
        'https://www.googleapis.com/auth/calendar.readonly'
    ],
    redirect_uri=YOUR_REDIRECT_URL
)

state = secrets.token_hex(32)
session['state'] = state

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

### Node.js

```js
const url = require('url');

app.get('/oauth2callback', async (req, res) => {
  const q = url.parse(req.url, true).query;

  if (q.error) {
    console.log('Error: ' + q.error);
    return res.status(400).send('Authorization failed');
  }

  if (q.state !== req.session.state) {
    return res.status(403).send('State mismatch. Possible CSRF attack');
  }

  const {tokens} = await oauth2Client.getToken(q.code);
  oauth2Client.setCredentials(tokens);

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

    if request.args.get('state') != session.get('state'):
        abort(403, 'State mismatch. Possible CSRF attack')

    flow = Flow.from_client_secrets_file(
        'client_secret.json',
        scopes=SCOPES,
        redirect_uri=YOUR_REDIRECT_URL,
        state=session['state']
    )
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    # credentials.token — access token
    # credentials.refresh_token — only on first auth!
    # credentials.expiry — expiration datetime
    # credentials.scopes — granted scopes

    session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': list(credentials.scopes)
    }
    return redirect('/profile')
```

### Python (FastAPI)

```python
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow

@router.get('/oauth2callback')
async def oauth2callback(request: Request):
    if request.query_params.get('error'):
        raise HTTPException(400, 'Authorization failed')

    state = request.session.get('state')
    if request.query_params.get('state') != state:
        raise HTTPException(403, 'State mismatch')

    flow = Flow.from_client_secrets_file(
        'client_secret.json',
        scopes=SCOPES,
        redirect_uri=YOUR_REDIRECT_URL,
        state=state
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
  console.log('New access_token:', tokens.access_token);
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

const oauth2Client = new google.auth.OAuth2(
  process.env.GOOGLE_CLIENT_ID,
  process.env.GOOGLE_CLIENT_SECRET,
  'http://localhost:3000/oauth2callback'
);

const SCOPES = ['https://www.googleapis.com/auth/userinfo.profile'];

app.get('/auth', (req, res) => {
  const state = crypto.randomBytes(32).toString('hex');
  req.session.state = state;

  const url = oauth2Client.generateAuthUrl({
    access_type: 'offline',
    scope: SCOPES,
    state,
    include_granted_scopes: true
  });
  res.redirect(url);
});

app.get('/oauth2callback', async (req, res) => {
  if (req.query.error) return res.redirect('/error');
  if (req.query.state !== req.session.state) return res.status(403).send('CSRF');

  const {tokens} = await oauth2Client.getToken(req.query.code);
  req.session.tokens = tokens;
  res.redirect('/profile');
});

app.get('/profile', async (req, res) => {
  if (!req.session.tokens) return res.redirect('/auth');
  oauth2Client.setCredentials(req.session.tokens);

  const oauth2 = google.oauth2({version: 'v2', auth: oauth2Client});
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
    session['state'] = state
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
    if request.args.get('state') != session.get('state'):
        abort(403, 'State mismatch')

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
        state=session['state']
    )
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    session['credentials'] = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': list(creds.scopes or [])
    }
    return redirect('/profile')


@app.route('/profile')
def profile():
    if 'credentials' not in session:
        return redirect('/auth')
    creds = Credentials(**session['credentials'])
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
    request.session['state'] = state
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
    if request.query_params.get('state') != request.session.get('state'):
        raise HTTPException(403, 'State mismatch')

    flow = Flow.from_client_config(
        CLIENT_CONFIG, scopes=SCOPES, redirect_uri=REDIRECT_URI,
        state=request.session['state']
    )
    flow.fetch_token(code=request.query_params.get('code'))
    creds = flow.credentials
    request.session['credentials'] = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': list(creds.scopes or [])
    }
    return RedirectResponse('/profile')


@app.get('/profile')
async def profile(request: Request):
    if 'credentials' not in request.session:
        return RedirectResponse('/auth')
    creds = Credentials(**request.session['credentials'])
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
