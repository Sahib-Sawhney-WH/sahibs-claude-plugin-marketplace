# Dataverse Plugin for Claude Code

A comprehensive Claude Code plugin for Microsoft Dataverse integration. Perform CRUD operations, query data, manage schemas, and get guidance on building Dataverse-backed applications.

## Features

- **MCP Server** with 13 Dataverse tools for direct data operations
- **6 Skills** covering SDK usage, queries, app development, and schema design
- **6 Commands** for setup, import/export, and code generation
- **2 Agents** for data operations and architecture guidance

## Quick Start

### Prerequisites

- Python 3.10+
- Access to a Microsoft Dataverse environment
- Azure AD app registration (for authentication)

### Installation

1. Install the plugin in Claude Code:
   ```bash
   claude --plugin-dir /path/to/dataverse-plugin
   ```

2. Install Python dependencies for the MCP server:
   ```bash
   pip install -r mcp/requirements.txt
   ```

3. Configure your connection:
   ```bash
   /dataverse:setup
   ```

## Components

### MCP Tools

| Tool | Description |
|------|-------------|
| `dataverse_connect` | Connect to Dataverse environment |
| `dataverse_list_tables` | List all tables |
| `dataverse_get_table_info` | Get table schema |
| `dataverse_query` | Query with OData |
| `dataverse_query_sql` | Query with SQL |
| `dataverse_get_record` | Get single record |
| `dataverse_create_record` | Create one record |
| `dataverse_create_records` | Bulk create records |
| `dataverse_update_record` | Update record |
| `dataverse_delete_record` | Delete record |
| `dataverse_create_table` | Create custom table |
| `dataverse_create_column` | Add columns to table |
| `dataverse_upload_file` | Upload file |
| `dataverse_download_file` | Download file |

### Skills

| Skill | Description |
|-------|-------------|
| `dataverse-sdk` | SDK usage, authentication, error handling |
| `dataverse-queries` | OData and SQL query syntax |
| `dataverse-python-apps` | Building Python apps with Dataverse |
| `dataverse-power-platform` | Power Apps, Power Automate, Power BI |
| `dataverse-web-apps` | Multi-language web app integration |
| `dataverse-schema-design` | Table design best practices |

### Commands

| Command | Description |
|---------|-------------|
| `/dataverse:setup` | Configure connection settings |
| `/dataverse:status` | Check connection and list tables |
| `/dataverse:import` | Import data from CSV/JSON |
| `/dataverse:export` | Export table data to file |
| `/dataverse:generate-client` | Generate typed Python client |
| `/dataverse:scaffold-app` | Scaffold new application |

### Agents

| Agent | Description |
|-------|-------------|
| `dataverse-assistant` | Data operations (CRUD, queries) |
| `dataverse-architect` | Schema design, architecture guidance |

## Authentication

The plugin supports three authentication methods:

### Interactive Browser (Development)
Opens a browser for user sign-in. Best for development.

### Device Code (Headless)
Displays a code to enter on another device. Use for servers without browsers.

### Client Secret (Production)
Service principal authentication. Requires:
- Azure Tenant ID
- Azure Client ID
- Azure Client Secret

## Configuration

Set environment variables or create `.claude/dataverse.local.md`:

```bash
# Environment variables
export DATAVERSE_URL="https://yourorg.crm.dynamics.com"
export DATAVERSE_AUTH_METHOD="client_secret"
export AZURE_TENANT_ID="00000000-0000-0000-0000-000000000000"
export AZURE_CLIENT_ID="00000000-0000-0000-0000-000000000000"
export AZURE_CLIENT_SECRET="your-secret"
```

## Usage Examples

### Query Records
```
"Query all active accounts from Dataverse"
"Find contacts with email ending in @contoso.com"
"Show me the top 10 opportunities by revenue"
```

### Create Records
```
"Create a new account named Contoso Ltd"
"Add a contact John Doe linked to account xyz"
```

### Design Help
```
"How should I design tables for a project management app?"
"What's the best way to structure customer orders?"
```

### App Development
```
"Help me build a FastAPI app that uses Dataverse"
"Generate a typed Python client for the account table"
```

## Project Structure

```
dataverse-plugin/
├── .claude-plugin/
│   └── plugin.json
├── mcp/
│   ├── dataverse_server.py
│   └── requirements.txt
├── skills/
│   ├── dataverse-sdk/
│   ├── dataverse-queries/
│   ├── dataverse-python-apps/
│   ├── dataverse-power-platform/
│   ├── dataverse-web-apps/
│   └── dataverse-schema-design/
├── commands/
│   ├── setup.md
│   ├── status.md
│   ├── import.md
│   ├── export.md
│   ├── generate-client.md
│   └── scaffold-app.md
├── agents/
│   ├── dataverse-assistant.md
│   └── dataverse-architect.md
├── .mcp.json
└── README.md
```

## License

MIT License

## Contributing

Contributions welcome! Please submit issues and pull requests.
