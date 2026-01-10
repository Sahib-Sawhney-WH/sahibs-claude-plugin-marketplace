# Sahib's Claude Plugin Marketplace

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/Sahib-Sawhney-WH/sahibs-claude-plugin-marketplace?style=social)](https://github.com/Sahib-Sawhney-WH/sahibs-claude-plugin-marketplace)
[![Plugins](https://img.shields.io/badge/plugins-2-blue)](https://github.com/Sahib-Sawhney-WH/sahibs-claude-plugin-marketplace)

**Enterprise-grade plugins for Claude Code**

Microservices | Microsoft Ecosystem | Multi-Cloud | AI Agents

[Get Started](#quick-start) · [DAPR Plugin](#dapr-plugin) · [Dataverse Plugin](#dataverse-plugin) · [Contributing](#contributing)

</div>

---

## Quick Start

```bash
/plugin marketplace add Sahib-Sawhney-WH/sahibs-claude-plugin-marketplace
/plugin menu
```

---

## Plugins

<table>
<tr>
<td width="50%" valign="top">

### DAPR Plugin
**v2.5.0** | Distributed Application Runtime

Build production-ready microservices with multi-cloud support.

| Capability | Details |
|------------|---------|
| Building Blocks | All 12 supported |
| Cloud Providers | Azure, AWS, GCP |
| Commands | 13 slash commands |
| Agents | 11 specialized experts |
| Templates | 100+ ready to use |

```bash
/plugin install dapr
```

[View Documentation →](plugins/dapr/README.md)

</td>
<td width="50%" valign="top">

### Dataverse Plugin
**v0.1.0** | Microsoft Power Platform

Full Dataverse integration with MCP server for direct data operations.

| Capability | Details |
|------------|---------|
| MCP Tools | 14 operations |
| Auth Methods | Browser, Device Code, Client Secret |
| Commands | 6 slash commands |
| Skills | 6 specialized guides |
| Agents | 2 expert assistants |

```bash
/plugin install dataverse
```

[View Documentation →](plugins/dataverse/README.md)

</td>
</tr>
</table>

---

## Use Cases

| DAPR | Dataverse |
|------|-----------|
| Microservices architecture | CRM/ERP integrations |
| Event-driven systems | Power Platform applications |
| Multi-cloud deployments | Data migration pipelines |
| Actor-based applications | Custom business portals |
| Durable AI agent workflows | Reporting and analytics |

---

## Installation

```bash
# Install both plugins
/plugin install dapr dataverse

# Or install individually
/plugin install dapr
/plugin install dataverse

# Update to latest versions
/plugin marketplace update
```

---

## Repository Structure

```
sahibs-claude-plugin-marketplace/
├── .claude-plugin/
│   └── marketplace.json
├── plugins/
│   ├── dapr/
│   │   ├── agents/           # 11 expert agents
│   │   ├── commands/         # 13 slash commands
│   │   ├── skills/           # 9 skill guides
│   │   ├── hooks/            # Auto-validation
│   │   └── templates/        # 100+ templates
│   └── dataverse/
│       ├── mcp/              # Python MCP server
│       ├── agents/           # 2 agents
│       ├── commands/         # 6 commands
│       └── skills/           # 6 skills
├── LICENSE
└── README.md
```

---

## Contributing

1. Fork the repository
2. Create your plugin in `plugins/your-plugin-name/`
3. Add `.claude-plugin/plugin.json` manifest
4. Update root `marketplace.json`
5. Submit a pull request

See [CONTRIBUTING.md](plugins/dapr/CONTRIBUTING.md) for detailed guidelines.

---

## Support

- **Issues**: [GitHub Issues](https://github.com/Sahib-Sawhney-WH/sahibs-claude-plugin-marketplace/issues)
- **Contact**: sahibsawhneyprofessional@gmail.com

---

<div align="center">

**Sahib Sawhney** · MIT License

</div>
