---
description: Configure Dataverse connection settings
argument-hint: "[environment_url]"
allowed-tools:
  - Read
  - Write
  - Edit
  - AskUserQuestion
  - Bash
---

# Dataverse Setup Command

Configure the connection to a Microsoft Dataverse environment.

## Instructions

When the user runs `/dataverse:setup`, help them configure their Dataverse connection.

### Steps

1. **Get environment URL**
   - If provided as argument, use it
   - Otherwise, ask for the Dataverse URL (e.g., https://yourorg.crm.dynamics.com)

2. **Determine authentication method**
   - Ask which auth method they want to use:
     - Interactive Browser (development)
     - Device Code (headless systems)
     - Client Secret (production/automation)

3. **For Client Secret auth, collect:**
   - Azure Tenant ID
   - Azure Client ID (App ID)
   - Client Secret value

4. **Create/update configuration file**
   - Create `.claude/dataverse.local.md` with the settings
   - Include environment variables template

5. **Test the connection**
   - Use the MCP dataverse_connect tool to verify
   - Show number of tables found

### Configuration File Template

```yaml
---
dataverse_url: https://yourorg.crm.dynamics.com
auth_method: interactive  # or: device_code, client_secret
# For client_secret auth:
# tenant_id: 00000000-0000-0000-0000-000000000000
# client_id: 00000000-0000-0000-0000-000000000000
---

# Dataverse Connection Configuration

This file stores your Dataverse connection settings.

## Environment Variables

For production, set these environment variables:
- DATAVERSE_URL
- DATAVERSE_AUTH_METHOD
- AZURE_TENANT_ID (for client_secret)
- AZURE_CLIENT_ID (for client_secret)
- AZURE_CLIENT_SECRET (for client_secret)
```

### Tips

- The Dataverse URL should NOT include a trailing slash
- For interactive auth, a browser window will open on first use
- For client_secret, ensure the app is registered in Azure AD and has Dataverse permissions
- Never commit client secrets to version control
