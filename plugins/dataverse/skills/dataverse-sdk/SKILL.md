# dataverse-sdk

This skill provides guidance on using the PowerPlatform Dataverse Client SDK for Python. Use when users ask about "Dataverse SDK", "Dataverse Python", "DataverseClient", "Dataverse authentication", "Dataverse CRUD operations", "create Dataverse records", "query Dataverse", "Dataverse connection", or need help with the Microsoft Dataverse Python SDK.

## Quick Start

Install the SDK:
```bash
pip install PowerPlatform-Dataverse-Client azure-identity
```

Basic setup:
```python
from azure.identity import InteractiveBrowserCredential
from PowerPlatform.Dataverse.client import DataverseClient

credential = InteractiveBrowserCredential()
client = DataverseClient("https://yourorg.crm.dynamics.com", credential)
```

## Authentication Methods

### Interactive Browser (Development)
```python
from azure.identity import InteractiveBrowserCredential
credential = InteractiveBrowserCredential()
```
Opens a browser window for user to sign in. Best for development and testing.

### Device Code (Headless Systems)
```python
from azure.identity import DeviceCodeCredential
credential = DeviceCodeCredential()
```
Displays a code to enter on a separate device. Use for servers without browsers.

### Client Secret (Production/Automation)
```python
from azure.identity import ClientSecretCredential
credential = ClientSecretCredential(
    tenant_id="your-tenant-id",
    client_id="your-app-id",
    client_secret="your-secret"
)
```
Service principal authentication for automated processes. Requires Azure app registration.

## CRUD Operations

### Create Records
```python
# Single record
account_ids = client.create("account", {"name": "Contoso Ltd"})
account_id = account_ids[0]

# Multiple records (bulk)
payloads = [
    {"name": "Company A"},
    {"name": "Company B"},
]
ids = client.create("account", payloads)
```

### Read Records
```python
# Single record by ID
account = client.get("account", account_id)

# Query with filters
pages = client.get(
    "account",
    select=["name", "telephone1"],
    filter="statecode eq 0",
    top=100
)
for page in pages:
    for record in page:
        print(record["name"])
```

### Update Records
```python
# Single update
client.update("account", account_id, {"telephone1": "555-0199"})

# Bulk update
client.update("account", ids, {"industry": "Technology"})
```

### Delete Records
```python
# Single delete
client.delete("account", account_id)

# Bulk delete
client.delete("account", ids, use_bulk_delete=True)
```

## Error Handling

```python
from PowerPlatform.Dataverse.core.errors import HttpError, ValidationError

try:
    client.get("account", "invalid-id")
except HttpError as e:
    print(f"HTTP {e.status_code}: {e.message}")
    if e.is_transient:
        print("Retry may succeed")
except ValidationError as e:
    print(f"Validation error: {e.message}")
```

## Key Concepts

- **Schema Names**: Use table/column schema names (e.g., `"account"`, `"new_MyTable"`)
- **Custom Prefix**: Custom tables require prefix (e.g., `"new_"`, `"cr123_"`)
- **Logical Names**: Column names in responses are lowercase logical names
- **Paging**: Large results are automatically paged via iterators

## References

- See `references/auth-patterns.md` for detailed authentication examples
- See `references/crud-examples.md` for comprehensive CRUD patterns
- See `references/error-handling.md` for error handling best practices
