---
name: google-auth
description: >-
  Use when a server authenticates to Google in a Node.js or Python application — OAuth 2.0
  flows, verifying Google ID tokens server-side, service account authentication and keys,
  Application Default Credentials, Workload Identity Federation, API keys, or working with
  google-auth-library (Node.js) or google-auth (Python). Covers server-side ID token
  verification and security best practices. Triggers - "google auth", "OAuth 2.0 Google",
  "google-auth-library", "ADC", "Application Default Credentials", "service account",
  "Workload Identity Federation", "Google ID token", "verifyIdToken",
  "GOOGLE_APPLICATION_CREDENTIALS", "Google SSO", "авторизация Google", "сервисный аккаунт",
  "ключи сервисного аккаунта", "проверить ID-токен". For end-user web sign-in only, use the
  google-signin skill instead.
---

# Google Authentication for Node.js & Python

## Libraries

### Node.js

- `google-auth-library` — core auth library (OAuth2Client, GoogleAuth, JWT, Compute, Impersonated)
- `googleapis` — Google API client (wraps google-auth-library)

```bash
npm install google-auth-library
npm install googleapis
```

The `client.fetch()` calls below require google-auth-library **≥ 10.1.0** (the
fetch-compatible API landed in 10.1.0, 2025-06-12); on 9.x use
`client.request()` with the same arguments. Checked 2026-08-31: latest is 11.x
and keeps both methods.

### Python

- `google-auth` — core auth library (google.oauth2, google.auth, credentials, transport)
- `google-auth-oauthlib` — OAuth 2.0 user-credential flow helpers (Flow, InstalledAppFlow)
- `google-api-python-client` — Google API client (wraps google-auth)

```bash
pip install google-auth
pip install google-auth-oauthlib
pip install google-api-python-client
```

## Authentication Methods Overview

| Method | Use Case | Node.js Key Class | Python Key Module / Class |
|--------|----------|-------------------|---------------------------|
| **ADC** | Same identity for all users, server-to-server | `GoogleAuth` | `google.auth.default()` |
| **OAuth 2.0** | Actions on behalf of end users | `OAuth2Client` | `google_auth_oauthlib.flow.Flow` |
| **Sign In with Google (GIS)** | User sign-in/sign-up on websites — the google-signin skill's ground | GIS JS SDK + `verifyIdToken()` | GIS JS SDK + `id_token.verify_oauth2_token()` |
| **JWT / Service Account** | Server-to-server, single identity | `JWT` | `service_account.Credentials` |
| **API Key** | Public data, no user context | `OAuth2Client({ apiKey })` | passed to `googleapiclient.discovery.build(developerKey=)` |
| **Compute** | On GCP with attached service account | `Compute` | `google.auth.compute_engine.Credentials` |
| **Workload Identity Federation** | AWS/Azure/OIDC → GCP without SA keys | `ExternalAccountClient` | `google.auth.identity_pool.Credentials` / `google.auth.aws.Credentials` |

## Quick Patterns

### 1. Application Default Credentials (ADC)

**Node.js**

```js
const {GoogleAuth} = require('google-auth-library');

const auth = new GoogleAuth({
  scopes: 'https://www.googleapis.com/auth/cloud-platform'
});
const client = await auth.getClient();
const res = await client.fetch('https://dns.googleapis.com/dns/v1/projects/...');
```

**Python**

```python
import google.auth
import google.auth.transport.requests

credentials, project = google.auth.default(
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
request = google.auth.transport.requests.Request()
credentials.refresh(request)
```

ADC search order: attached service account → `gcloud auth application-default login` file → `GOOGLE_APPLICATION_CREDENTIALS` env var.

For detailed ADC setup and service account usage, see [references/adc-and-service-accounts.md](references/adc-and-service-accounts.md).

### 2. OAuth 2.0 Web Server Flow

**Node.js**

```js
const {OAuth2Client} = require('google-auth-library');

const client = new OAuth2Client({
  clientId: CLIENT_ID,
  clientSecret: CLIENT_SECRET,
  redirectUri: REDIRECT_URI
});

const authUrl = client.generateAuthUrl({
  access_type: 'offline',
  scope: ['https://www.googleapis.com/auth/userinfo.profile'],
  state: crypto.randomBytes(32).toString('hex'),
  include_granted_scopes: true
});

// After redirect: exchange code for tokens
const {tokens} = await client.getToken(code);
client.setCredentials(tokens);
```

**Python**

```python
from google_auth_oauthlib.flow import Flow

flow = Flow.from_client_secrets_file(
    'client_secret.json',
    scopes=['https://www.googleapis.com/auth/userinfo.profile'],
    redirect_uri=REDIRECT_URI
)

authorization_url, state = flow.authorization_url(
    access_type='offline',
    include_granted_scopes='true'
)

# After redirect: exchange code for tokens
flow.fetch_token(code=code)
credentials = flow.credentials
```

`refresh_token` is only returned on the first authorization. Use `prompt: 'consent'` (Node.js) or `prompt='consent'` (Python) to force re-consent.

For the complete OAuth 2.0 flow (parameters, token exchange, refresh, revocation, incremental auth), see [references/oauth2-web-server.md](references/oauth2-web-server.md).

### 3. Verifying a Google ID Token — the library call

**Node.js**

```js
const {OAuth2Client} = require('google-auth-library');
const client = new OAuth2Client();

const ticket = await client.verifyIdToken({
  idToken: token,
  audience: WEB_CLIENT_ID,
});
const payload = ticket.getPayload();
```

**Python**

```python
from google.oauth2 import id_token
from google.auth.transport import requests

payload = id_token.verify_oauth2_token(token, requests.Request(), WEB_CLIENT_ID)
```

The call checks signature, `aud`, `exp` and `iss` — **and nothing else**. That is
the library contract, not the web sign-in contract: for the sign-in security
checklist (`nonce` binding, `email_verified`, login-CSRF defense, account
linking) use the **google-signin** skill — it is the one home for that contract,
and this skill deliberately does not restate it.

### 4. JWT / Service Account

**Node.js**

```js
const {JWT} = require('google-auth-library');
const keys = require('./service-account-key.json');

const client = new JWT({
  email: keys.client_email,
  key: keys.private_key,
  scopes: ['https://www.googleapis.com/auth/cloud-platform'],
});
const res = await client.fetch(url);
```

**Python**

```python
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

# Or from a dict already loaded into memory:
credentials = service_account.Credentials.from_service_account_info(
    info,
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
```

### 5. API Key

**Node.js**

```js
const {OAuth2Client} = require('google-auth-library');
const client = new OAuth2Client({ apiKey: 'my-api-key' });

// Or via GoogleAuth:
const {GoogleAuth} = require('google-auth-library');
const auth = new GoogleAuth({
  clientOptions: { apiKey: 'my-api-key' }
});
```

**Python**

```python
from googleapiclient.discovery import build

service = build('customsearch', 'v1', developerKey='my-api-key')
```

### 6. Token Refresh

**Node.js**

```js
client.on('tokens', (tokens) => {
  if (tokens.refresh_token) {
    // Store refresh_token — only sent on first auth
  }
  console.log(tokens.access_token);
});
```

**Python**

```python
from google.auth.transport.requests import Request

if credentials.expired and credentials.refresh_token:
    credentials.refresh(Request())
    # credentials.token is the new access token
    # credentials.expiry is the new expiration datetime
```

## Security Best Practices

- Never expose `client_secret` or service account keys in client-side code
- Always validate `state` parameter to prevent CSRF in OAuth flows
- Use `sub` (not `email`) as the unique user identifier from Google ID tokens
- Store `refresh_token` securely; it's only returned on first authorization
- Validate external credential configurations before use (check `token_url`, `service_account_impersonation_url` point to googleapis.com)
- Prefer Workload Identity Federation over service account keys for non-GCP environments
- For end-user web sign-in, apply the google-signin skill's full checklist — a partial restatement here is how the two skills drifted apart once already
- **Python-specific**: reuse a single `google.auth.transport.requests.Request()` instance across verifications for connection pooling; do not create a new one per call in hot paths

## Reference Files

- **[OAuth 2.0 Web Server Flow](references/oauth2-web-server.md)** — Complete OAuth 2.0 flow: parameters, consent, token exchange, refresh, revocation, incremental auth, error handling (Node.js + Python)
- **[ADC & Service Accounts](references/adc-and-service-accounts.md)** — Application Default Credentials setup, service account keys, JWT, Compute credentials, environment configuration (Node.js + Python)
- **[Sign In with Google](references/sign-in-with-google.md)** — Google Identity Services (GIS), ID token verification, CSRF protection, One Tap, FedCM (Node.js + Python)
- **[Workload Identity Federation](references/workload-identity.md)** — AWS, Azure, OIDC/SAML federation, workforce identity, executable-sourced credentials (Node.js + Python)
