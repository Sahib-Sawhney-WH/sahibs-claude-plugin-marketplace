# Testing Guide

This guide explains how to run and write tests for the DAPR Claude Code Plugin.

## Prerequisites

Install test dependencies:

```bash
pip install pytest pytest-cov pyyaml
```

## Running Tests

### Run all tests

```bash
pytest tests/ -v
```

### Run with coverage

```bash
pytest tests/ --cov=scripts --cov=tests/validators --cov-report=html --cov-report=term-missing
```

Coverage report will be generated in `htmlcov/` directory.

### Run specific test categories

```bash
# Run only security tests
pytest tests/ -v -m security

# Run only unit tests
pytest tests/ -v -m unit

# Run specific test file
pytest tests/test_component_validation.py -v
```

## Test Structure

```
tests/
├── conftest.py              # Shared pytest fixtures
├── validators.py            # Shared validation functions
├── test_component_validation.py    # Component YAML validation tests
├── test_middleware_validation.py   # Middleware security tests
├── test_binding_validation.py      # Binding configuration tests
└── test_agent_validation.py        # Agent pattern validation tests
```

## Writing Tests

### Using Shared Validators

Import validators from the shared module:

```python
from validators import (
    validate_oauth2,
    validate_bearer,
    validate_database_binding,
    validate_secret_handling,
    SECRET_FIELD_PATTERNS,
)
```

### Using Fixtures

Common fixtures are available from `conftest.py`:

```python
def test_example(temp_dir, valid_component):
    # temp_dir: Temporary directory for test files
    # valid_component: Sample valid component YAML
    pass
```

### Test Markers

Use markers to categorize tests:

```python
import pytest

@pytest.mark.security
def test_secret_not_exposed():
    """Security test for secret handling."""
    pass

@pytest.mark.unit
def test_validation_logic():
    """Unit test for validation function."""
    pass
```

## Validation Testing

Tests validate that hooks will correctly identify issues:

1. **Component Validation**: Checks YAML structure, component types, secret handling
2. **Middleware Validation**: Checks OAuth2, Bearer, OPA, rate limiting configs
3. **Binding Validation**: Checks database, SMTP, Kafka, HTTP binding security
4. **Agent Validation**: Checks tool definitions, async patterns, Pydantic usage

## Adding New Tests

1. Create test functions in appropriate test file
2. Use shared validators from `validators.py`
3. Add appropriate markers (`@pytest.mark.unit`, etc.)
4. Follow naming convention: `test_<what>_<expected_behavior>`

Example:

```python
import pytest
from validators import validate_secret_handling

@pytest.mark.security
def test_secret_in_metadata_detected():
    """Test that secrets in metadata are flagged."""
    metadata = [
        {"name": "password", "value": "secret123"}
    ]
    issues = validate_secret_handling(metadata)
    assert len(issues) > 0
    assert "secret" in issues[0].lower()
```

## Continuous Integration

Tests run automatically on:
- Pull requests
- Pushes to main branch

See `.github/workflows/` for CI configuration.
