# Dataverse Authentication Patterns

## Overview

The Dataverse SDK uses Azure Identity for OAuth authentication. Choose the appropriate credential type based on your scenario.

## Credential Types

### InteractiveBrowserCredential
**Best for:** Development, testing, interactive scenarios

```python
from azure.identity import InteractiveBrowserCredential
from PowerPlatform.Dataverse.client import DataverseClient

credential = InteractiveBrowserCredential()
client = DataverseClient("https://yourorg.crm.dynamics.com", credential)
```

**How it works:**
1. Opens a browser window
2. User signs in with their Microsoft account
3. Tokens are cached for subsequent calls

### DeviceCodeCredential
**Best for:** Headless systems, SSH sessions, containers

```python
from azure.identity import DeviceCodeCredential

def device_code_callback(verification_uri, user_code, expires_in):
    print(f"Go to {verification_uri} and enter code: {user_code}")

credential = DeviceCodeCredential(
    prompt_callback=device_code_callback
)
client = DataverseClient("https://yourorg.crm.dynamics.com", credential)
```

**How it works:**
1. Displays a URL and code
2. User enters code on any device with a browser
3. Authentication completes after user signs in

### ClientSecretCredential
**Best for:** Production services, automation, scheduled jobs

```python
from azure.identity import ClientSecretCredential

credential = ClientSecretCredential(
    tenant_id="00000000-0000-0000-0000-000000000000",
    client_id="11111111-1111-1111-1111-111111111111",
    client_secret="your-client-secret"
)
client = DataverseClient("https://yourorg.crm.dynamics.com", credential)
```

**Prerequisites:**
1. Register an app in Azure AD
2. Grant Dataverse API permissions
3. Create a client secret
4. Add app user to Dataverse with appropriate security role

### ClientCertificateCredential
**Best for:** High-security production environments

```python
from azure.identity import ClientCertificateCredential

credential = ClientCertificateCredential(
    tenant_id="00000000-0000-0000-0000-000000000000",
    client_id="11111111-1111-1111-1111-111111111111",
    certificate_path="/path/to/certificate.pem"
)
```

### AzureCliCredential
**Best for:** Local development with Azure CLI

```python
from azure.identity import AzureCliCredential

# Requires: az login
credential = AzureCliCredential()
client = DataverseClient("https://yourorg.crm.dynamics.com", credential)
```

## Azure App Registration Setup

### Step 1: Register Application
1. Go to Azure Portal > Azure Active Directory > App registrations
2. Click "New registration"
3. Name: "Dataverse Python Client"
4. Supported account types: Single tenant
5. Redirect URI: `http://localhost` (for interactive auth)

### Step 2: Configure API Permissions
1. Go to API permissions
2. Add permission > APIs my organization uses
3. Search for "Dataverse" or "Common Data Service"
4. Select "user_impersonation" permission
5. Grant admin consent

### Step 3: Create Client Secret (for service principal)
1. Go to Certificates & secrets
2. New client secret
3. Copy the secret value immediately

### Step 4: Add App User to Dataverse
1. Go to Power Platform Admin Center
2. Select your environment
3. Settings > Users + permissions > Application users
4. New app user
5. Add your app and assign security role

## Environment Variables Pattern

```python
import os
from azure.identity import ClientSecretCredential

credential = ClientSecretCredential(
    tenant_id=os.environ["AZURE_TENANT_ID"],
    client_id=os.environ["AZURE_CLIENT_ID"],
    client_secret=os.environ["AZURE_CLIENT_SECRET"]
)

base_url = os.environ.get("DATAVERSE_URL", "https://yourorg.crm.dynamics.com")
client = DataverseClient(base_url, credential)
```

## Connection Testing

```python
def test_connection(client):
    """Test that connection is working."""
    try:
        tables = client.list_tables()
        print(f"Connected! Found {len(tables)} tables.")
        return True
    except Exception as e:
        print(f"Connection failed: {e}")
        return False
```

## Best Practices

1. **Reuse client instances** - Don't create new clients for each operation
2. **Use service principals in production** - Never use interactive auth in automated processes
3. **Store secrets securely** - Use Azure Key Vault or environment variables
4. **Implement token caching** - Azure Identity handles this automatically
5. **Handle token expiration** - The SDK handles refresh automatically
