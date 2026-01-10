---
description: Check Dataverse connection status and list tables
allowed-tools:
  - Read
  - mcp__dataverse__dataverse_connect
  - mcp__dataverse__dataverse_list_tables
---

# Dataverse Status Command

Check the current Dataverse connection status and list available tables.

## Instructions

When the user runs `/dataverse:status`:

1. **Check for configuration**
   - Read `.claude/dataverse.local.md` if it exists
   - Extract connection settings

2. **Connect to Dataverse**
   - Use `dataverse_connect` MCP tool with configured settings
   - Report success or failure

3. **List tables**
   - Use `dataverse_list_tables` MCP tool
   - Show count of tables
   - List first 20 tables alphabetically

4. **Report status**
   - Connection: Connected/Disconnected
   - Environment URL
   - Auth method
   - Table count
   - Sample tables

### Output Format

```
Dataverse Connection Status
===========================

Status: Connected
Environment: https://yourorg.crm.dynamics.com
Auth Method: interactive
Tables Found: 245

Sample Tables:
- account
- contact
- lead
- opportunity
- new_customtable
...

Use the dataverse MCP tools to query data:
- dataverse_query: Query records
- dataverse_get_record: Get single record
- dataverse_create_record: Create record
```

### Error Handling

If connection fails:
- Show the error message
- Suggest running `/dataverse:setup` to configure
- Check if credentials are expired
