# Sahib's Claude Plugin Marketplace

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/Sahib-Sawhney-WH/sahibs-claude-plugin-marketplace?style=social)](https://github.com/Sahib-Sawhney-WH/sahibs-claude-plugin-marketplace)

A curated collection of Claude Code plugins for enterprise development, microservices, and Microsoft ecosystem integration.

## Quick Start

```bash
# Add the marketplace
/plugin marketplace add Sahib-Sawhney-WH/sahibs-claude-plugin-marketplace

# Browse and install plugins
/plugin menu
```

## Available Plugins

| Plugin | Description | Version |
|--------|-------------|---------|
| **[dapr](plugins/dapr/)** | Comprehensive DAPR development for Python microservices with multi-cloud support (Azure, AWS, GCP). All 12 DAPR building blocks + AI agents. | 2.5.0 |
| **[dataverse](plugins/dataverse/)** | Microsoft Dataverse integration - CRUD operations, OData/SQL queries, metadata management, and app development assistance. | 0.1.0 |

## Installation

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

---

## Plugin Details

### DAPR Plugin (v2.5.0)

Full support for building distributed applications with DAPR:

| Feature | Details |
|---------|---------|
| **Building Blocks** | All 12: State, Pub/Sub, Actors, Workflows, Bindings, Secrets, Config, Locks, Crypto, Jobs, Conversation |
| **Multi-Cloud** | Azure, AWS, GCP templates and deployment |
| **AI Agents** | DAPR Agents framework for durable AI workflows |
| **Security** | TLS by default, secret management, security scanning |
| **Commands** | 13 commands: `/dapr:init`, `/dapr:run`, `/dapr:deploy`, etc. |
| **Agents** | 11 specialized agents for architecture, debugging, deployment |

[View Full DAPR Documentation →](plugins/dapr/README.md)

---

### Dataverse Plugin (v0.1.0)

Microsoft Dataverse integration for data operations and app development:

| Feature | Details |
|---------|---------|
| **MCP Server** | 14 tools for direct Dataverse operations |
| **Authentication** | Interactive browser, device code, client secret |
| **Operations** | CRUD, bulk operations, OData/SQL queries |
| **Metadata** | Create/modify tables and columns |
| **File Handling** | Upload/download with chunking support |
| **Commands** | 6 commands: `/dataverse:setup`, `/dataverse:import`, `/dataverse:export`, etc. |
| **Skills** | 6 skills: SDK patterns, queries, Power Platform, web apps, schema design |
| **Agents** | 2 agents: Data operations assistant, architecture guidance |

[View Full Dataverse Documentation →](plugins/dataverse/README.md)

---

## Repository Structure

```
sahibs-claude-plugin-marketplace/
├── .claude-plugin/
│   └── marketplace.json        # Marketplace manifest
├── plugins/
│   ├── dapr/                   # DAPR plugin
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json
│   │   ├── agents/
│   │   ├── commands/
│   │   ├── skills/
│   │   ├── hooks/
│   │   ├── templates/
│   │   └── README.md
│   └── dataverse/              # Dataverse plugin
│       ├── .claude-plugin/
│       │   └── plugin.json
│       ├── .mcp.json
│       ├── mcp/
│       ├── agents/
│       ├── commands/
│       ├── skills/
│       └── README.md
├── LICENSE
└── README.md
```

## Adding a New Plugin

1. Create a directory under `plugins/your-plugin-name/`
2. Add `.claude-plugin/plugin.json` manifest
3. Add plugin components (agents, commands, skills, hooks)
4. Update root `marketplace.json` with the new plugin entry
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
- **Contact**: sahibsawhneyprofessional@gmail.com
