# Application Default Credentials & Service Accounts (Node.js & Python)


## Contents

- [Table of Contents](#table-of-contents)
- [ADC Overview](#adc-overview)
- [ADC Search Order](#adc-search-order)
- [Setting Up ADC](#setting-up-adc)
- [Using ADC in Code](#using-adc-in-code)
- [Service Account Keys (JWT)](#service-account-keys-jwt)
- [Compute Credentials](#compute-credentials)
- [Impersonated Credentials](#impersonated-credentials)
- [Downscoped Client](#downscoped-client)
- [ID Tokens](#id-tokens)
- [Environment Variables](#environment-variables)

## Table of Contents
- [ADC Overview](#adc-overview)
- [ADC Search Order](#adc-search-order)
- [Setting Up ADC](#setting-up-adc)
- [Using ADC in Code](#using-adc-in-code)
- [Service Account Keys (JWT)](#service-account-keys-jwt)
- [Compute Credentials](#compute-credentials)
- [Impersonated Credentials](#impersonated-credentials)
- [Downscoped Client](#downscoped-client)
- [ID Tokens](#id-tokens)
- [Environment Variables](#environment-variables)

## ADC Overview

Application Default Credentials (ADC) automatically finds credentials based on the environment. Best for server-to-server and same-identity-for-all-users scenarios.

## ADC Search Order

1. **Attached service account** — via GCP metadata server (Compute Engine, Cloud Run, GKE, etc.)
2. **`gcloud auth application-default login`** — local credential file
3. **`GOOGLE_APPLICATION_CREDENTIALS`** — env var pointing to a credential JSON file

Credential file locations from `gcloud auth application-default login`:
- **macOS/Linux**: `$HOME/.config/gcloud/application_default_credentials.json`
- **Windows**: `%APPDATA%\gcloud\application_default_credentials.json`

## Setting Up ADC

### Local Development

```bash
# Login with user credentials (generates local ADC file)
gcloud auth application-default login

# With specific scopes
gcloud auth application-default login \
  --scopes=https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/drive

# With service account impersonation
gcloud auth application-default login \
  --impersonate-service-account=SA_EMAIL@PROJECT.iam.gserviceaccount.com
```

### Production (GCP)

Attach a service account to the resource (Compute Engine VM, Cloud Run service, GKE pod, etc.). No code changes needed — ADC uses the metadata server automatically.

### External Environments

Set `GOOGLE_APPLICATION_CREDENTIALS` to point to a credential JSON file:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
# Or a workload identity federation config:
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/workload-config.json
```

## Using ADC in Code

### Node.js

```js
const {GoogleAuth} = require('google-auth-library');

const auth = new GoogleAuth({
  scopes: 'https://www.googleapis.com/auth/cloud-platform'
});

const client = await auth.getClient();
const projectId = await auth.getProjectId();
const url = `https://dns.googleapis.com/dns/v1/projects/${projectId}`;
const res = await client.fetch(url);
```

#### With googleapis

```js
const {google} = require('googleapis');

const auth = new google.auth.GoogleAuth({
  scopes: ['https://www.googleapis.com/auth/cloud-platform']
});
const authClient = await auth.getClient();
google.options({auth: authClient});

const storage = google.storage('v1');
const buckets = await storage.buckets.list({project: projectId});
```

### Python

```python
import google.auth

credentials, project = google.auth.default()

# With specific scopes:
credentials, project = google.auth.default(
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
```

#### With google-api-python-client

```python
from googleapiclient.discovery import build
import google.auth

credentials, project = google.auth.default(
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
storage = build('storage', 'v1', credentials=credentials)
buckets = storage.buckets().list(project=project).execute()
```

#### With authorized requests

```python
import google.auth
import google.auth.transport.requests

credentials, project = google.auth.default(
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
request = google.auth.transport.requests.Request()
credentials.refresh(request)

# Use with requests library
authed_session = google.auth.transport.requests.AuthorizedSession(credentials)
response = authed_session.get('https://storage.googleapis.com/...')
```

#### Load from file explicitly

```python
import google.auth

credentials, project = google.auth.load_credentials_from_file(
    '/path/to/credentials.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
```

## Service Account Keys (JWT)

### Node.js — From JSON Key File

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

### Node.js — From Environment Variable

```js
const {JWT} = require('google-auth-library');

const keysEnvVar = process.env['GOOGLE_CREDENTIALS'];
if (!keysEnvVar) throw new Error('GOOGLE_CREDENTIALS not set');
const keys = JSON.parse(keysEnvVar);

const client = new JWT({
  email: keys.client_email,
  key: keys.private_key,
  scopes: ['https://www.googleapis.com/auth/cloud-platform'],
});
```

### Python — From JSON Key File

```python
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
```

### Python — From Dictionary

```python
import json
from google.oauth2 import service_account

info = json.loads(os.environ['GOOGLE_CREDENTIALS'])
credentials = service_account.Credentials.from_service_account_info(
    info,
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
```

### Python — With Subject (Domain-Wide Delegation)

```python
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
    'service-account-key.json',
    scopes=['https://www.googleapis.com/auth/gmail.readonly'],
    subject='user@yourdomain.com'
)
```

### Service Account Key JSON Structure

```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "key-id",
  "private_key": "-----BEGIN RSA PRIVATE KEY-----\n...",
  "client_email": "sa-name@project-id.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
```

**Security**: Service account keys are a security risk. Prefer Workload Identity Federation or attached service accounts. If using keys, rotate regularly and restrict access.

## Compute Credentials

For code running on GCP with an attached service account.

### Node.js

```js
const {auth, Compute} = require('google-auth-library');

const client = new Compute({
  serviceAccountEmail: 'my-sa@project.iam.gserviceaccount.com' // optional
});
const projectId = await auth.getProjectId();
const res = await client.fetch(url);
```

In most cases, prefer `GoogleAuth` (ADC) over direct `Compute` usage.

### Python

```python
from google.auth import compute_engine

credentials = compute_engine.Credentials(
    service_account_email='my-sa@project.iam.gserviceaccount.com'  # optional
)
```

In most cases, prefer `google.auth.default()` (ADC) over direct `compute_engine.Credentials`.

## Impersonated Credentials

Use IAM Credentials API to impersonate a target service account.

### Node.js

```js
const {GoogleAuth, Impersonated} = require('google-auth-library');

const auth = new GoogleAuth();
const sourceClient = await auth.getClient();

const targetClient = new Impersonated({
  sourceClient: sourceClient,
  targetPrincipal: 'target-sa@project.iam.gserviceaccount.com',
  lifetime: 30,        // seconds
  delegates: [],       // optional chain
  targetScopes: ['https://www.googleapis.com/auth/cloud-platform']
});

const res = await targetClient.fetch(url);
```

### Python

```python
from google.auth import impersonated_credentials
import google.auth

source_credentials, _ = google.auth.default()

target_credentials = impersonated_credentials.Credentials(
    source_credentials=source_credentials,
    target_principal='target-sa@project.iam.gserviceaccount.com',
    target_scopes=['https://www.googleapis.com/auth/cloud-platform'],
    lifetime=300  # seconds (default: 3600)
)
```

The source credential needs the **Service Account Token Creator** role (`roles/iam.serviceAccountTokenCreator`).

## Downscoped Client

Restrict permissions of a short-lived credential (Cloud Storage only).

### Node.js

```js
const {GoogleAuth, DownscopedClient} = require('google-auth-library');

const auth = new GoogleAuth({scopes: 'https://www.googleapis.com/auth/cloud-platform'});
const client = await auth.getClient();

const cab = {
  accessBoundary: {
    accessBoundaryRules: [{
      availablePermissions: ['inRole:roles/storage.objectViewer'],
      availableResource: '//storage.googleapis.com/projects/_/buckets/my-bucket',
      availabilityCondition: {
        expression: "resource.name.startsWith('projects/_/buckets/my-bucket/objects/prefix')"
      }
    }]
  }
};

const downscopedClient = new DownscopedClient(client, cab);
const refreshedAccessToken = await downscopedClient.getAccessToken();
```

### Python

```python
from google.auth import _default
from google.auth import credentials as ga_credentials
import google.auth

credentials, _ = google.auth.default(
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

# Downscoping is done via the STS API; the Python library exposes it through
# google.auth.downscoped.DownscopedCredentials (available in google-auth >= 2.0):
from google.auth import downscoped

credential_access_boundary = downscoped.CredentialAccessBoundary(rules=[
    downscoped.AccessBoundaryRule(
        available_resource='//storage.googleapis.com/projects/_/buckets/my-bucket',
        available_permissions=['inRole:roles/storage.objectViewer'],
    )
])

downscoped_credentials = downscoped.DownscopedCredentials(
    source_credentials=credentials,
    credential_access_boundary=credential_access_boundary
)
```

## ID Tokens

### Fetching ID Tokens (for Cloud Run / Cloud Functions / IAP)

#### Node.js

```js
const {GoogleAuth} = require('google-auth-library');

const targetUrl = 'https://cloud-run-1234-uc.a.run.app';
const auth = new GoogleAuth();
const client = await auth.getIdTokenClient(targetUrl);
const res = await client.fetch(targetUrl);
```

#### Python

```python
import google.oauth2.id_token
import google.auth.transport.requests

request = google.auth.transport.requests.Request()
target_audience = 'https://cloud-run-1234-uc.a.run.app'

# Fetch a raw ID token string
token = google.oauth2.id_token.fetch_id_token(request, target_audience)

# Or get refreshable ID token credentials
credentials = google.oauth2.id_token.fetch_id_token_credentials(
    target_audience, request=request
)
credentials.refresh(request)
# credentials.token is the ID token
```

#### Python — Service Account ID Token

```python
from google.oauth2 import service_account

credentials = service_account.IDTokenCredentials.from_service_account_file(
    'service-account-key.json',
    target_audience='https://cloud-run-1234-uc.a.run.app'
)
request = google.auth.transport.requests.Request()
credentials.refresh(request)
# credentials.token is the ID token
```

### Verifying IAP Headers

#### Node.js

```js
const {OAuth2Client} = require('google-auth-library');

const client = new OAuth2Client();
const response = await client.getIapCerts();
const ticket = await client.verifySignedJwtWithCertsAsync(
  idToken,
  response.pubkeys,
  `/projects/PROJECT_NUMBER/apps/PROJECT_ID`,
  ['https://cloud.google.com/iap']
);
```

#### Python

```python
from google.oauth2 import id_token
from google.auth.transport import requests

request = requests.Request()

decoded = id_token.verify_token(
    iap_jwt,
    request,
    audience=f'/projects/{PROJECT_NUMBER}/apps/{PROJECT_ID}',
    certs_url='https://www.gstatic.com/iap/verify/public_key'
)
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to credential JSON file |
| `GOOGLE_CLOUD_PROJECT` | Default project ID |
| `GCLOUD_PROJECT` | Alias for project ID |
| `HTTPS_PROXY` / `https_proxy` | Proxy for HTTPS requests |
