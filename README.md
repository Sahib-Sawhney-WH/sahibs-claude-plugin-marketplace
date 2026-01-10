# Sahib's Claude Plugin Marketplace

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A curated collection of Claude Code plugins for enterprise development, microservices, and Microsoft ecosystem integration.

## Available Plugins

| Plugin | Description | Version |
|--------|-------------|---------|
| **[dapr](plugins/dapr/)** | Comprehensive DAPR development for Python microservices with multi-cloud support (Azure, AWS, GCP). All 12 DAPR building blocks + AI agents. | 2.5.0 |
| **[dataverse](plugins/dataverse/)** | Microsoft Dataverse integration - CRUD operations, OData/SQL queries, metadata management, and app development assistance. | 0.1.0 |

## Installation

### Add the Marketplace

```bash
/plugin marketplace add Sahib-Sawhney-WH/sahibs-claude-plugin-marketplace
```

### Browse Available Plugins

```bash
/plugin menu
```

### Install Individual Plugins

```bash
# Install DAPR plugin
/plugin install dapr

# Install Dataverse plugin
/plugin install dataverse

# Install both
/plugin install dapr dataverse
```

### Update Marketplace

```bash
/plugin marketplace update
```

## Plugin Details

### DAPR Plugin (v2.5.0)

Full support for building distributed applications with DAPR:

- **12 Building Blocks** - State, Pub/Sub, Actors, Workflows, Bindings, Secrets, Config, Locks, Crypto, Jobs, Conversation
- **Multi-Cloud** - Azure, AWS, GCP templates and deployment
- **AI Agents** - DAPR Agents framework for durable AI workflows
- **Security** - TLS by default, secret management, security scanning
- **13 Commands** - `/dapr:init`, `/dapr:run`, `/dapr:deploy`, etc.
- **11 Agents** - Architecture, debugging, deployment experts

[View DAPR Plugin Documentation →](plugins/dapr/README.md)

### Dataverse Plugin (v0.1.0)

Microsoft Dataverse integration for data operations and app development:

- **MCP Server** - 13 tools for direct Dataverse operations
- **Authentication** - Interactive, device code, client secret
- **CRUD Operations** - Create, read, update, delete records
- **Queries** - OData filters and SQL queries
- **Metadata** - Create tables and columns
- **File Handling** - Upload/download with chunking
- **6 Commands** - `/dataverse:setup`, `/dataverse:import`, `/dataverse:export`, etc.
- **6 Skills** - SDK patterns, queries, Power Platform, web apps, schema design
- **2 Agents** - Data operations assistant, architecture guidance

[View Dataverse Plugin Documentation →](plugins/dataverse/README.md)

## For Plugin Developers

### Repository Structure

```
├── .claude-plugin/
│   └── marketplace.json     # Marketplace manifest
├── plugins/
│   ├── dapr/                # DAPR plugin
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   ├── agents/
│   │   ├── commands/
│   │   ├── skills/
│   │   └── ...
│   └── dataverse/           # Dataverse plugin
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── .mcp.json
│       ├── mcp/
│       ├── agents/
│       ├── commands/
│       └── skills/
└── README.md
```

### Adding a New Plugin

1. Create a directory under `plugins/`
2. Add `.claude-plugin/plugin.json` manifest
3. Add plugin components (agents, commands, skills, hooks)
4. Update `marketplace.json` with the new plugin entry
5. Submit a pull request

### Validation

```bash
/plugin validate .
```

## Contributing

Contributions welcome! Please see [CONTRIBUTING.md](plugins/dapr/CONTRIBUTING.md) for guidelines.

## License

MIT License - See [LICENSE](LICENSE) for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/Sahib-Sawhney-WH/sahibs-claude-plugin-marketplace/issues)
- **Dataverse Plugin**: Contact RSM Power Factory
