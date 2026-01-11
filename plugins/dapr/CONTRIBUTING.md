# Contributing to DAPR Plugin for Claude Code

Thank you for your interest in contributing to the DAPR Plugin! This document provides guidelines and instructions for contributing.

## Getting Started

### Prerequisites

- [Claude Code CLI](https://claude.ai/code) installed
- Git
- Python 3.9+ (for running tests)
- pytest (`pip install pytest`)

### Setup for Development

1. Fork the repository on GitHub
2. Clone your fork locally:

```bash
git clone https://github.com/YOUR-USERNAME/dapr-claude-plugin.git
cd dapr-claude-plugin
```

3. Add as a local marketplace and install:

```bash
claude plugin marketplace add ./
claude plugin install dapr
```

4. Create a new branch for your feature or fix:

```bash
git checkout -b feature/your-feature-name
```

5. After making changes, update and reinstall:

```bash
claude plugin marketplace update sahib-claude-marketplace
claude plugin uninstall dapr
claude plugin install dapr
```

## Project Structure

```
dapr-plugin/
├── .claude-plugin/
│   └── plugin.json          # Plugin configuration
├── agents/                   # Agent definitions
├── commands/                 # Slash command definitions
├── skills/                   # Skill definitions
├── hooks/                    # Hook configurations
├── templates/                # DAPR component templates
│   ├── azure/               # Azure-specific templates
│   ├── aws/                 # AWS-specific templates
│   ├── gcp/                 # GCP-specific templates
│   └── ...
├── examples/                 # Example projects
└── tests/                    # Plugin validation tests
```

## Types of Contributions

### Adding New Templates

1. Create the template YAML file in the appropriate `templates/` subdirectory
2. Follow existing naming conventions: `{type}-{service}.yaml`
3. Include comments explaining configuration options
4. Add usage examples in the template file
5. Update `commands/component.md` if adding a new component type

### Adding New Agents

1. Create a new markdown file in `agents/`
2. Include clear role description and capabilities
3. Define when the agent should be triggered
4. Add relevant tool access

### Adding New Skills

1. Create a new markdown file in `skills/`
2. Document the skill's purpose and usage
3. Include example inputs and outputs

### Improving Documentation

- Fix typos or clarify existing documentation
- Add examples for complex features
- Update README with new features

## Code Guidelines

### Template Standards

- Always use `secretKeyRef` for sensitive values (never plain text)
- Include managed identity as primary auth method for cloud services
- Add local development alternatives where applicable
- Include Python SDK usage examples

### Testing

Run the plugin validation tests before submitting:

```bash
cd tests/
pytest -v
```

### Commit Messages

Use conventional commit format:

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Adding or updating tests

Example:
```
feat: Add Azure Event Hubs binding template
```

## Pull Request Process

1. Update documentation for any new features
2. Ensure all tests pass
3. Update the README if adding significant features
4. Update COMPATIBILITY.md if adding version-specific features
5. Reference any related issues in your PR description

## Reporting Issues

When reporting issues, please include:

- Plugin version
- DAPR version
- Cloud provider (if applicable)
- Steps to reproduce
- Expected vs actual behavior

## Questions?

Feel free to open an issue for questions or discussions about potential contributions.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
