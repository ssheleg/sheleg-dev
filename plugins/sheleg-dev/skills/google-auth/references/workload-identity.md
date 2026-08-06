# Workload & Workforce Identity Federation (Node.js & Python)

## Table of Contents
- [Overview](#overview)
- [AWS Federation](#aws-federation)
- [Azure Federation](#azure-federation)
- [OIDC Provider Federation](#oidc-provider-federation)
- [Custom Subject Token Supplier](#custom-subject-token-supplier)
- [Workforce Identity Federation](#workforce-identity-federation)
- [Executable-Sourced Credentials](#executable-sourced-credentials)
- [Using External Identities](#using-external-identities)
- [Configurable Token Lifetime](#configurable-token-lifetime)
- [Security Considerations](#security-considerations)

## Overview

Workload Identity Federation lets non-GCP workloads (AWS, Azure, OIDC/SAML providers) access Google Cloud without service account keys. It works by exchanging an external token for a short-lived GCP access token via the Security Token Service (STS).

Benefits:
- No service account key management
- No key rotation needed
- Short-lived credentials only
- Works across cloud providers

## AWS Federation

### Setup

1. Create a workload identity pool
2. Add AWS as identity provider
3. Grant `roles/iam.workloadIdentityUser` to external identity
4. Generate credential configuration:

```bash
gcloud iam workload-identity-pools create-cred-config \
  projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_ID/providers/$AWS_PROVIDER_ID \
  --service-account $SERVICE_ACCOUNT_EMAIL \
  --aws \
  --output-file /path/to/config.json
```

### Custom AWS Supplier — Node.js

For non-EC2 environments (ECS, EKS, Fargate):

```ts
import {AwsClient, AwsSecurityCredentials, AwsSecurityCredentialsSupplier, ExternalAccountSupplierContext} from 'google-auth-library';
import {fromNodeProviderChain} from '@aws-sdk/credential-providers';

class AwsSupplier implements AwsSecurityCredentialsSupplier {
  private readonly region: string;
  constructor(region: string) { this.region = region; }

  async getAwsRegion(context: ExternalAccountSupplierContext): Promise<string> {
    return this.region;
  }

  async getAwsSecurityCredentials(context: ExternalAccountSupplierContext): Promise<AwsSecurityCredentials> {
    const creds = await fromNodeProviderChain()();
    return {
      accessKeyId: creds.accessKeyId,
      secretAccessKey: creds.secretAccessKey,
      token: creds.sessionToken
    };
  }
}

const authClient = new AwsClient({
  audience: '//iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_ID/providers/$PROVIDER_ID',
  subject_token_type: 'urn:ietf:params:aws:token-type:aws4_request',
  aws_security_credentials_supplier: new AwsSupplier('us-east-1'),
  service_account_impersonation_url: 'https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/$EMAIL:generateAccessToken',
});
```

### Custom AWS Supplier — Python

```python
from google.auth import aws
from google.auth import exceptions

class CustomAwsSecurityCredentialsSupplier(aws.AwsSecurityCredentialsSupplier):

    def get_aws_security_credentials(self, context, request):
        try:
            # Return valid AWS security credentials.
            # These are NOT cached by google-auth — implement caching here.
            return aws.AwsSecurityCredentials(
                access_key_id=ACCESS_KEY_ID,
                secret_access_key=SECRET_ACCESS_KEY,
                session_token=SESSION_TOKEN
            )
        except Exception as e:
            raise exceptions.RefreshError(e, retryable=True)

    def get_aws_region(self, context, request):
        return 'us-east-1'

supplier = CustomAwsSecurityCredentialsSupplier()

credentials = aws.Credentials(
    audience='//iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_ID/providers/$PROVIDER_ID',
    subject_token_type='urn:ietf:params:aws:token-type:aws4_request',
    aws_security_credentials_supplier=supplier,
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
```

## Azure Federation

```bash
gcloud iam workload-identity-pools create-cred-config \
  projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_ID/providers/$AZURE_PROVIDER_ID \
  --service-account $SERVICE_ACCOUNT_EMAIL \
  --azure \
  --output-file /path/to/config.json
```

## OIDC Provider Federation

### File-Sourced

```bash
gcloud iam workload-identity-pools create-cred-config \
  projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_ID/providers/$OIDC_PROVIDER_ID \
  --service-account $SERVICE_ACCOUNT_EMAIL \
  --credential-source-file $PATH_TO_OIDC_TOKEN \
  --output-file /path/to/config.json
```

### URL-Sourced

```bash
gcloud iam workload-identity-pools create-cred-config \
  projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_ID/providers/$OIDC_PROVIDER_ID \
  --service-account $SERVICE_ACCOUNT_EMAIL \
  --credential-source-url $URL_TO_GET_TOKEN \
  --credential-source-headers Metadata-Flavor=Google \
  --output-file /path/to/config.json
```

## Custom Subject Token Supplier

For OIDC/SAML tokens from custom sources.

### Node.js

```ts
import {IdentityPoolClient, SubjectTokenSupplier, ExternalAccountSupplierContext} from 'google-auth-library';

class CustomSupplier implements SubjectTokenSupplier {
  async getSubjectToken(context: ExternalAccountSupplierContext): Promise<string> {
    // Implement caching — library does not cache
    const audience = context.audience;
    const subjectTokenType = context.subjectTokenType;
    return fetchTokenFromProvider();
  }
}

const client = new IdentityPoolClient({
  audience: '//iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_ID/providers/$PROVIDER_ID',
  subject_token_type: 'urn:ietf:params:oauth:token-type:id_token',
  subject_token_supplier: new CustomSupplier()
});
```

### Python

```python
from google.auth import identity_pool
from google.auth import exceptions

class CustomSubjectTokenSupplier(identity_pool.SubjectTokenSupplier):

    def get_subject_token(self, context, request):
        try:
            # Implement caching — library does not cache external tokens.
            audience = context.audience
            subject_token_type = context.subject_token_type
            return fetch_token_from_provider()
        except Exception as e:
            raise exceptions.RefreshError(e, retryable=True)

supplier = CustomSubjectTokenSupplier()

credentials = identity_pool.Credentials(
    audience='//iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_ID/providers/$PROVIDER_ID',
    subject_token_type='urn:ietf:params:oauth:token-type:id_token',
    subject_token_supplier=supplier,
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
```

## Workforce Identity Federation

For human users (employees, partners) authenticating via external IdP (Azure AD, Okta, AD FS).

### Generate Config

```bash
# OIDC
gcloud iam workforce-pools create-cred-config \
  locations/global/workforcePools/$WORKFORCE_POOL_ID/providers/$PROVIDER_ID \
  --subject-token-type=urn:ietf:params:oauth:token-type:id_token \
  --credential-source-file=$PATH_TO_TOKEN \
  --workforce-pool-user-project=$PROJECT_NUMBER \
  --output-file=/path/to/config.json

# SAML
gcloud iam workforce-pools create-cred-config \
  locations/global/workforcePools/$WORKFORCE_POOL_ID/providers/$PROVIDER_ID \
  --credential-source-file=$PATH_TO_SAML_ASSERTION \
  --subject-token-type=urn:ietf:params:oauth:token-type:saml2 \
  --workforce-pool-user-project=$PROJECT_NUMBER \
  --output-file=/path/to/config.json
```

### Browser-Based Login

```bash
gcloud auth application-default login --login-config=$LOGIN_CONFIG
```

Default refresh token lifetime: 1 hour (configurable up to 12 hours via pool session duration).

## Executable-Sourced Credentials

For custom token retrieval via local executable:

```bash
gcloud iam workload-identity-pools create-cred-config \
  projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_ID/providers/$PROVIDER_ID \
  --service-account=$SERVICE_ACCOUNT_EMAIL \
  --subject-token-type=$SUBJECT_TOKEN_TYPE \
  --executable-command="/path/to/command --arg=value" \
  --executable-timeout-millis=30000 \
  --executable-output-file=/path/to/cached-token.json \
  --output-file /path/to/config.json
```

Requires: `export GOOGLE_EXTERNAL_ACCOUNT_ALLOW_EXECUTABLES=1`

### Executable Response Format

Success (OIDC):
```json
{"version": 1, "success": true, "token_type": "urn:ietf:params:oauth:token-type:id_token", "id_token": "HEADER.PAYLOAD.SIGNATURE", "expiration_time": 1620499962}
```

Error:
```json
{"version": 1, "success": false, "code": "401", "message": "Caller not authorized."}
```

### Environment Variables Set for Executable

| Variable | Description |
|----------|-------------|
| `GOOGLE_EXTERNAL_ACCOUNT_AUDIENCE` | Audience from config |
| `GOOGLE_EXTERNAL_ACCOUNT_IMPERSONATED_EMAIL` | SA email (if impersonating) |
| `GOOGLE_EXTERNAL_ACCOUNT_OUTPUT_FILE` | Output file path (if set) |
| `GOOGLE_EXTERNAL_ACCOUNT_TOKEN_TYPE` | Expected subject token type |

## Using External Identities

After generating a config JSON, use with ADC.

### Environment Setup

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/config.json
```

### Node.js

```js
const {GoogleAuth} = require('google-auth-library');

const auth = new GoogleAuth({
  scopes: 'https://www.googleapis.com/auth/cloud-platform',
  projectId: 'CLOUD_RESOURCE_PROJECT_ID' // avoids needing roles/browser
});
const client = await auth.getClient();
const res = await client.fetch(url);
```

Or explicit initialization:

```js
const {ExternalAccountClient} = require('google-auth-library');
const jsonConfig = require('/path/to/config.json');

const client = ExternalAccountClient.fromJSON(jsonConfig);
client.scopes = ['https://www.googleapis.com/auth/cloud-platform'];
```

### Python

```python
import google.auth

# Via ADC (auto-detects external account config from GOOGLE_APPLICATION_CREDENTIALS)
credentials, project = google.auth.default(
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
```

Or load from file explicitly:

```python
import google.auth

credentials, project = google.auth.load_credentials_from_file(
    '/path/to/config.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
```

Or direct instantiation by credential type:

```python
# Identity Pool (OIDC/SAML)
from google.auth import identity_pool

credentials = identity_pool.Credentials.from_file(
    '/path/to/config.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)

# AWS
from google.auth import aws

credentials = aws.Credentials.from_file(
    '/path/to/config.json',
    scopes=['https://www.googleapis.com/auth/cloud-platform']
)
```

Requirements for ADC with external identities:
- Grant `roles/browser` to the service account (or specify `projectId` explicitly)
- Enable Cloud Resource Manager API on the project

## Configurable Token Lifetime

```bash
gcloud iam workload-identity-pools create-cred-config \
  ... \
  --service-account-token-lifetime-seconds=3600
```

- Default: 3600 (1 hour)
- Min: 600 (10 minutes), Max: 43200 (12 hours)
- Lifetimes > 1 hour require org policy: `constraints/iam.allowServiceAccountCredentialLifetimeExtension`

## Security Considerations

- **Validate external credential configs** — verify `token_url`, `token_info_url`, `service_account_impersonation_url` point to `googleapis.com`
- **Restrict executable access** — prevent unauthorized processes from reading credentials from stdout
- **Make config files read-only** — prevent modification of executable command paths
- **Prefer file/URL-sourced** over executable-sourced credentials when possible
- **Implement caching** in custom suppliers — neither the Node.js nor Python library caches external tokens
