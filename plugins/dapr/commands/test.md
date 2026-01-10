---
description: Run DAPR-aware tests with mocked clients, Testcontainers integration, or real DAPR sidecar
---

# DAPR Test Runner

Run tests for your DAPR application with proper mocking and integration support.

## Behavior

When the user runs `/dapr:test`:

1. **Detect Test Type**
   - Check for pytest configuration
   - Identify test directories (tests/, test/)
   - Determine test mode based on arguments

2. **Configure Environment**
   - Set up DAPR test fixtures
   - Configure mocking or real sidecar
   - Prepare test components

3. **Run Tests**
   - Execute pytest with DAPR fixtures
   - Capture output and coverage
   - Report results

## Arguments

| Argument | Description |
|----------|-------------|
| `unit` | Run unit tests with mocked DAPR client (default) |
| `integration` | Run integration tests with Testcontainers |
| `e2e` | Run end-to-end tests with real DAPR sidecar |
| `--coverage` | Generate coverage report |
| `--verbose` | Verbose output |
| `--filter` | Filter tests by pattern |

## Test Modes

### Unit Tests (Default)
```
/dapr:test unit
```

Uses mocked DAPR client for fast, isolated tests:
- No external dependencies
- Fastest execution
- Test business logic only

### Integration Tests
```
/dapr:test integration
```

Uses Testcontainers for realistic testing:
- Redis container for state/pubsub
- Real component behavior
- Network isolation

### End-to-End Tests
```
/dapr:test e2e
```

Uses real DAPR sidecar:
- Full DAPR runtime
- Production-like environment
- Slowest but most realistic

## Test Structure

```
tests/
├── conftest.py           # Shared fixtures
├── unit/
│   ├── test_state.py     # State management tests
│   ├── test_pubsub.py    # Pub/sub tests
│   └── test_service.py   # Service invocation tests
├── integration/
│   └── test_e2e.py       # Integration tests
└── docker-compose.test.yaml
```

## Examples

### Run All Unit Tests
```
/dapr:test
```

### Run with Coverage
```
/dapr:test --coverage
```

### Run Specific Test
```
/dapr:test --filter test_order_creation
```

### Integration Tests
```
/dapr:test integration --verbose
```

## Generated Files

When setting up tests, creates:
- `tests/conftest.py` - DAPR fixtures
- `tests/unit/test_example.py` - Example unit tests
- `tests/docker-compose.test.yaml` - Test infrastructure
- `pytest.ini` - Pytest configuration
