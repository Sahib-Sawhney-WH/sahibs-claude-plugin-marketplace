# dataverse-web-apps

This skill provides guidance on building web applications (any language) that connect to Microsoft Dataverse. Use when users ask about ".NET Dataverse", "Node.js Dataverse", "JavaScript Dataverse", "REST API Dataverse", "web app Dataverse", "OAuth Dataverse", or need help with web application integration.

## Dataverse Web API

All languages can access Dataverse via the OData Web API.

**Base URL:** `https://yourorg.api.crm.dynamics.com/api/data/v9.2/`

### Authentication

Dataverse uses OAuth 2.0. Get an access token first:

```
POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
Content-Type: application/x-www-form-urlencoded

client_id={app_id}
&client_secret={secret}
&scope=https://yourorg.crm.dynamics.com/.default
&grant_type=client_credentials
```

### REST API Examples

**List records:**
```http
GET /api/data/v9.2/accounts?$select=name,telephone1&$top=10
Authorization: Bearer {access_token}
```

**Get single record:**
```http
GET /api/data/v9.2/accounts({guid})
Authorization: Bearer {access_token}
```

**Create record:**
```http
POST /api/data/v9.2/accounts
Authorization: Bearer {access_token}
Content-Type: application/json

{"name": "New Account", "telephone1": "555-0100"}
```

**Update record:**
```http
PATCH /api/data/v9.2/accounts({guid})
Authorization: Bearer {access_token}
Content-Type: application/json

{"telephone1": "555-0200"}
```

**Delete record:**
```http
DELETE /api/data/v9.2/accounts({guid})
Authorization: Bearer {access_token}
```

## Node.js Client

```javascript
const axios = require('axios');
const { ConfidentialClientApplication } = require('@azure/msal-node');

// Authentication
const msalConfig = {
    auth: {
        clientId: process.env.AZURE_CLIENT_ID,
        clientSecret: process.env.AZURE_CLIENT_SECRET,
        authority: `https://login.microsoftonline.com/${process.env.AZURE_TENANT_ID}`
    }
};

const cca = new ConfidentialClientApplication(msalConfig);

async function getToken() {
    const result = await cca.acquireTokenByClientCredential({
        scopes: [`${process.env.DATAVERSE_URL}/.default`]
    });
    return result.accessToken;
}

// Dataverse client
class DataverseClient {
    constructor(baseUrl) {
        this.baseUrl = `${baseUrl}/api/data/v9.2`;
    }

    async request(method, path, data = null) {
        const token = await getToken();
        const response = await axios({
            method,
            url: `${this.baseUrl}${path}`,
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
                'OData-MaxVersion': '4.0',
                'OData-Version': '4.0'
            },
            data
        });
        return response.data;
    }

    async listAccounts() {
        return this.request('get', '/accounts?$select=name,telephone1&$top=100');
    }

    async createAccount(data) {
        return this.request('post', '/accounts', data);
    }
}
```

## .NET Client

```csharp
using Microsoft.Identity.Client;
using System.Net.Http;
using System.Net.Http.Headers;

public class DataverseClient
{
    private readonly HttpClient _httpClient;
    private readonly string _baseUrl;
    private readonly IConfidentialClientApplication _app;

    public DataverseClient(string baseUrl, string tenantId, string clientId, string clientSecret)
    {
        _baseUrl = $"{baseUrl}/api/data/v9.2";
        _httpClient = new HttpClient();

        _app = ConfidentialClientApplicationBuilder
            .Create(clientId)
            .WithClientSecret(clientSecret)
            .WithAuthority($"https://login.microsoftonline.com/{tenantId}")
            .Build();
    }

    private async Task<string> GetTokenAsync()
    {
        var result = await _app.AcquireTokenForClient(
            new[] { $"{_baseUrl}/.default" }
        ).ExecuteAsync();
        return result.AccessToken;
    }

    public async Task<string> ListAccountsAsync()
    {
        var token = await GetTokenAsync();
        _httpClient.DefaultRequestHeaders.Authorization =
            new AuthenticationHeaderValue("Bearer", token);

        var response = await _httpClient.GetAsync(
            $"{_baseUrl}/accounts?$select=name,telephone1"
        );
        return await response.Content.ReadAsStringAsync();
    }
}
```

## OAuth Flows

### Client Credentials (Server-to-Server)
- Best for backend services
- No user interaction required
- Uses app registration + client secret

### Authorization Code (User Context)
- Best for user-facing apps
- User signs in via browser
- Access data as the user

### Device Code
- Best for CLI tools
- User enters code on separate device

## Security Best Practices

1. **Never expose client secrets** in frontend code
2. **Use HTTPS** for all API calls
3. **Implement token caching** to reduce auth calls
4. **Handle token refresh** before expiration
5. **Use minimal permissions** in app registration
6. **Validate user permissions** in your app

## References

- See `references/dotnet-client.md` for .NET examples
- See `references/nodejs-client.md` for Node.js examples
- See `references/oauth-flows.md` for authentication details
