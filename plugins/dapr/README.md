# DAPR Plugin for Claude Code v2.6

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-2.6.0-blue.svg)](https://github.com/Sahib-Sawhney-WH/dapr-claude-plugin/releases/tag/v2.6.0)
[![GitHub stars](https://img.shields.io/github/stars/Sahib-Sawhney-WH/dapr-claude-plugin?style=social)](https://github.com/Sahib-Sawhney-WH/dapr-claude-plugin)

A comprehensive Claude Code plugin for developing, deploying, and debugging DAPR (Distributed Application Runtime) applications with Python across Azure, AWS, and GCP.

## What's New in v2.6

### Cross-Platform Robustness
- **Cross-Platform Environment Detection** - New Python-based environment checker replaces Windows-specific commands
- **Cloud CLI Validators** - Pre-deployment validation for Azure CLI, AWS CLI, and gcloud authentication
- **Dependency Analysis** - Circular dependency detection across component configurations

### Enhanced Validation
- **8 New Validation Functions** - Service dependencies, secret references, resource quotas, port conflicts, managed identity, mTLS, and resiliency policy validation
- **12 New Hooks** - ACL policies, configurations, subscriptions, deployments, observability, workflows, and actors

### Resiliency & Reliability
- **Resiliency Command** - New `/dapr:resiliency` command for analyze/apply/test operations
- **8 Pre-defined Patterns** - High-throughput, critical-service, external-api, microservices, event-driven, batch-processing, edge-computing, state-intensive
- **Azure Container Apps Templates** - ACA-specific resiliency configuration

### SDK Error Handling
- **RetryPolicy & CircuitBreaker** - Production-ready error handling utilities
- **@with_dapr_retry Decorator** - Automatic retry with exponential backoff
- **Error Classification** - DaprError with category-based handling

### Observability
- **Trace Analyzer** - Analyze distributed traces from Zipkin/Jaeger/Azure Monitor
- **Health Check Framework** - Liveness, readiness, and detailed health endpoints
- **DAPR Sidecar Connectivity** - Automatic sidecar health verification

### Chaos Testing
- **@chaos_monkey Decorator** - Configurable failure injection for testing
- **ResiliencyTester** - Validate retry policies, circuit breakers, and timeouts
- **DAPR-Specific Patterns** - Component failure simulation

## What's New in v2.5

### Security Improvements
- **Safe Expression Evaluation** - Replaced unsafe `eval()` with `simpleeval` library in agent templates
- **Secure Redis Defaults** - Redis templates now use `secretKeyRef` instead of empty passwords
- **TLS by Default** - All Redis component templates enable TLS encryption
- **Localhost Binding** - Templates default to `127.0.0.1` instead of `0.0.0.0` (configurable via `HOST` env var)
- **Authorization Examples** - Added commented auth middleware patterns to service templates

### Testing Improvements
- **Shared Validators Module** - New `tests/validators.py` with 12+ reusable validation functions
- **Pytest Configuration** - Added `pytest.ini` with markers for unit, integration, and security tests
- **Testing Guide** - New `TESTING.md` documentation for running and writing tests

### Documentation
- **Code of Conduct** - Added contributor code of conduct with enforcement contact

## v2.4 Features

- **Dedicated Azure Templates** - Consolidated `templates/azure/` directory with 10 templates matching AWS/GCP structure
- **New Azure Bindings** - Event Hubs (streaming/IoT), SignalR (real-time WebSocket), Queue Storage (simple queues)
- **Version Compatibility Matrix** - `COMPATIBILITY.md` documenting DAPR 1.10-1.16 support
- **Plugin Self-Tests** - Pytest test suite validating hook logic for components, middleware, bindings, and agents
- **Azure Template Validation Hook** - Automatic validation for Azure templates

## v2.3 Features

- **12 Binding Templates** - HTTP, Kafka, RabbitMQ, MQTT, PostgreSQL, MySQL, Redis, SMTP, InfluxDB, LocalStorage, GraphQL, Cron
- **Error Codes Reference** - 80+ DAPR error codes with troubleshooting steps
- **Pluggable Components** - Build custom state stores, pub/sub, and bindings with gRPC

## v2.2 Features

- **Multi-Cloud Support** - AWS (DynamoDB, SNS/SQS, S3) and GCP (Firestore, Pub/Sub, GCS)
- **HTTP Middleware** - OAuth2, Bearer/OIDC, OPA, Rate Limiting, Circuit Breakers, WASM
- **Cloud Deployment** - EKS, ECS, GKE, Cloud Run templates

## v2.1 Features

- **DAPR Agents AI Framework** - Build intelligent, durable AI agents
- **Agentic Patterns** - Prompt chaining, parallelization, routing, evaluator-optimizer, human-in-the-loop
- **Multi-Agent Orchestration** - Workflow-based agent coordination
- **CrewAI/OpenAI Integration** - Framework integrations with DAPR persistence

## Features

### Multi-Cloud Support

| Cloud | State Store | Pub/Sub | Secrets | Bindings | Deployment |
|-------|-------------|---------|---------|----------|------------|
| **Azure** | Cosmos DB | Service Bus | Key Vault | Blob, Event Grid, Event Hubs, SignalR, Queue Storage | Container Apps, AKS |
| **AWS** | DynamoDB | SNS/SQS | Secrets Manager | S3, SQS, Kinesis, SES | EKS, ECS Fargate |
| **GCP** | Firestore | Pub/Sub | Secret Manager | Cloud Storage | GKE, Cloud Run |

### All 12 DAPR Building Blocks

| Building Block | Description | Component Template |
|----------------|-------------|-------------------|
| Service Invocation | Service-to-service calls | Built-in |
| State Management | Key-value storage | `statestore.yaml` |
| Pub/Sub | Event-driven messaging | `pubsub.yaml` |
| Bindings | External system triggers | 12+ templates |
| Secrets | Secure credential storage | `secretstore.yaml` |
| Actors | Virtual actor pattern | `statestore.yaml` (with actors) |
| Workflows | Durable orchestration | Built-in |
| Configuration | Dynamic app configuration | `configuration.yaml` |
| Distributed Lock | Mutex across services | `lock.yaml` |
| Cryptography | Encrypt/decrypt operations | `crypto.yaml` |
| Jobs | Scheduled task execution | `job.yaml` |
| Conversation | LLM/AI integration | `conversation.yaml` |

### Binding Templates (v2.3)

| Binding | Type | Use Case |
|---------|------|----------|
| HTTP | `bindings.http` | REST APIs, webhooks |
| Cron | `bindings.cron` | Scheduled tasks |
| Kafka | `bindings.kafka` | High-throughput streaming |
| RabbitMQ | `bindings.rabbitmq` | Message queuing |
| MQTT | `bindings.mqtt3` | IoT devices |
| PostgreSQL | `bindings.postgresql` | SQL database |
| MySQL | `bindings.mysql` | SQL database |
| Redis | `bindings.redis` | Caching, queues |
| SMTP | `bindings.smtp` | Email sending |
| InfluxDB | `bindings.influxdb` | Time-series data |
| LocalStorage | `bindings.localstorage` | File system |
| GraphQL | `bindings.graphql` | GraphQL endpoints |

### HTTP Middleware (v2.2)

| Middleware | Use Case |
|------------|----------|
| OAuth2 | Authorization code flow |
| OAuth2 Client Credentials | Service-to-service auth |
| Bearer/OIDC | JWT token validation |
| OPA | Policy-based authorization |
| Rate Limit | Request throttling |
| Sentinel | Circuit breaker |
| WASM | Custom WebAssembly middleware |
| Router Alias | Route rewriting |
| Router Checker | Route validation |

### Pluggable Components (v2.3)

Build custom DAPR components using gRPC:

| Template | Description |
|----------|-------------|
| `state-store.py` | Python state store with gRPC |
| `pubsub.py` | Python pub/sub with streaming |
| `binding.py` | Python input/output binding |
| `component.yaml` | Registration examples |
| `Dockerfile` | Container build template |

## Installation

### Option 1: From GitHub Marketplace (Recommended)

```bash
# Add the plugin marketplace
claude plugin marketplace add Sahib-Sawhney-WH/dapr-claude-plugin

# Install the plugin
claude plugin install dapr
```

### Option 2: One-Line Install

```bash
# Add marketplace and install in one command
claude plugin marketplace add Sahib-Sawhney-WH/dapr-claude-plugin && claude plugin install dapr
```

### Option 3: Local Development

```bash
# Clone the repository
git clone https://github.com/Sahib-Sawhney-WH/dapr-claude-plugin.git

# Add as local marketplace and install
claude plugin marketplace add ./dapr-claude-plugin
claude plugin install dapr
```

### Updating the Plugin

```bash
# Update to the latest version
claude plugin marketplace update sahib-claude-marketplace
claude plugin update dapr
```

## Commands

| Command | Description |
|---------|-------------|
| `/dapr:init` | Initialize a new DAPR project with templates |
| `/dapr:run` | Run DAPR application locally with sidecar |
| `/dapr:deploy` | Deploy to Azure/AWS/GCP |
| `/dapr:logs` | View and filter DAPR service logs |
| `/dapr:status` | Check DAPR runtime status |
| `/dapr:component` | Generate component YAML files |
| `/dapr:workflow` | Scaffold a new DAPR workflow |
| `/dapr:test` | Run unit, integration, or E2E tests |
| `/dapr:security` | Scan for security issues |
| `/dapr:resiliency` | Analyze, apply, and test resiliency policies |
| `/dapr:cicd` | Generate CI/CD pipelines |
| `/dapr:project` | Initialize multi-service projects |
| `/dapr:agent` | Create DAPR AI agents |
| `/dapr:middleware` | Generate middleware configuration |

## Agents

Specialized AI agents automatically invoked when relevant:

| Agent | When Used |
|-------|-----------|
| `dapr-architect` | Designing distributed systems |
| `microservices-expert` | Writing service code |
| `dapr-debugger` | Diagnosing runtime errors |
| `azure-deployer` | Azure Container Apps/AKS deployment |
| `cloud-deployer` | Multi-cloud deployment (AWS/GCP) |
| `workflow-expert` | Creating durable workflows |
| `config-specialist` | Configuring components |
| `multi-service-expert` | Cross-service debugging |
| `ai-agent-expert` | Building AI agents |
| `middleware-expert` | HTTP middleware configuration |
| `pluggable-component-dev` | Custom component development |

## Skills

| Skill | Purpose |
|-------|---------|
| `dapr-validation` | Validates component YAML files |
| `dapr-code-generation` | Generates Python code |
| `dapr-troubleshooting` | Diagnoses errors |
| `security-scanner` | Detects secrets and issues |
| `observability-setup` | Configures OpenTelemetry |
| `agent-builder` | Validates AI agent configs |
| `middleware-validator` | Security checks for middleware |
| `error-codes` | DAPR error code reference |

## Quick Start

### 1. Create a New Project

```
/dapr:init my-service
```

### 2. Add Components

```bash
# Azure
/dapr:component state cosmos
/dapr:component pubsub servicebus

# AWS
/dapr:component state dynamodb
/dapr:component pubsub snssqs

# GCP
/dapr:component state firestore
/dapr:component pubsub gcppubsub

# Common Bindings
/dapr:component binding kafka
/dapr:component binding postgresql
```

### 3. Run Locally

```
/dapr:run
```

### 4. Deploy

```bash
# Azure Container Apps
/dapr:deploy aca

# AWS EKS
/dapr:deploy eks

# GCP GKE
/dapr:deploy gke
```

## Error Codes Reference (v2.3)

Use the error codes skill to diagnose DAPR issues:

| Category | Error Prefix | Count |
|----------|--------------|-------|
| Actors | `ERR_ACTOR_*` | 16 |
| Workflows | `ERR_*_WORKFLOW` | 14 |
| State | `ERR_STATE_*` | 10 |
| Pub/Sub | `ERR_PUBSUB_*` | 13 |
| Secrets | `ERR_SECRET_*` | 4 |
| Configuration | `ERR_CONFIGURATION_*` | 5 |
| Crypto | `ERR_CRYPTO_*` | 4 |
| Locks | `ERR_LOCK_*` | 4 |
| Health | `ERR_HEALTH_*` | 3 |
| Scheduler | `DAPR_SCHEDULER_*` | 8 |

## DAPR Agents

### Basic Agent

```python
from dapr_agents import AssistantAgent, tool

@tool
async def search(query: str) -> str:
    """Search for information."""
    return f"Results for: {query}"

agent = AssistantAgent(
    name="assistant",
    role="Helpful Assistant",
    instructions="Help users find information.",
    tools=[search],
    model="gpt-4o"
)

await agent.run("Search for DAPR documentation")
```

### Durable Agent (Workflow-Backed)

```python
from dapr.ext.workflow import workflow, activity
from dapr_agents import AssistantAgent

@activity
async def research_activity(ctx, topic: str) -> str:
    agent = AssistantAgent(name="researcher", ...)
    return await agent.run(f"Research: {topic}")

@workflow
def research_workflow(ctx, topic: str):
    result = yield ctx.call_activity(research_activity, input=topic)
    return result
```

## Pluggable Components

### Custom State Store

```python
from dapr.proto.components.v1 import state_pb2_grpc

class CustomStateStore(state_pb2_grpc.StateStoreServicer):
    def Init(self, request, context):
        # Initialize with metadata from component.yaml
        return state_pb2.InitResponse()

    def Get(self, request, context):
        # Retrieve state by key
        return state_pb2.GetResponse(data=...)

    def Set(self, request, context):
        # Store state
        return state_pb2.SetResponse()
```

### Registration

```yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: my-state-store
spec:
  type: state.my-custom-store
  version: v1
  metadata:
  - name: connectionString
    secretKeyRef:
      name: my-secrets
      key: connection-string
```

## Template Structure

```
templates/
├── azure/           # Azure templates (12 files) - Cosmos DB, Service Bus, Key Vault,
│                    # Blob Storage, Event Grid, Event Hubs, SignalR, Queue Storage,
│                    # Container Apps, AKS deployment, resiliency-aca, resiliency-patterns
├── aws/             # AWS components (DynamoDB, SNS/SQS, S3, EKS, ECS)
├── gcp/             # GCP components (Firestore, Pub/Sub, GCS, GKE, Cloud Run)
├── bindings/        # 12 binding templates
├── middleware/      # HTTP middleware (OAuth2, OPA, etc.)
├── pluggable/       # Custom component templates
├── agents/          # DAPR Agents templates
├── workflows/       # Workflow patterns
├── testing/         # Test fixtures, mocks, and chaos testing
├── observability/   # Tracing, trace analyzer, and health checks
└── utils/           # Error handling utilities (RetryPolicy, CircuitBreaker)

scripts/             # Validation and environment scripts
├── check-environment.py    # Cross-platform environment detection
├── check-azure-auth.py     # Azure CLI validation
├── check-aws-auth.py       # AWS CLI validation
├── check-gcp-auth.py       # GCP CLI validation
└── dependency-analyzer.py  # Circular dependency detection

tests/               # Plugin self-tests for validation logic
├── conftest.py      # Pytest fixtures
├── validators.py    # Shared validation functions (20+ functions)
├── test_component_validation.py
├── test_middleware_validation.py
├── test_binding_validation.py
└── test_agent_validation.py
```

## Hooks (Auto-Validation)

The plugin automatically validates:
- Component YAML files (`components/*.yaml`)
- Middleware configurations (`middleware/*.yaml`)
- Binding configurations (`bindings/*.yaml`)
- Pluggable components (`pluggable/*.py`)
- Agent configurations (`*_agent.py`, `*agent*.py`)
- Tool definitions (`tools/*.py`)
- Resiliency policies (`resiliency*.yaml`)
- ACL policies (`acl*.yaml`)
- Configuration components (`configuration*.yaml`)
- Subscriptions (`subscription*.yaml`)
- Deployments (`deploy*.yaml`)
- Workflow implementations (`workflow*.py`)
- Actor implementations (`actor*.py`)
- Observability code (`observability/**/*.py`)
- GitHub Actions workflows
- Dockerfiles
- Secret files

### Pre-Deployment Hooks
- Cloud CLI authentication (Azure, AWS, GCP)
- `dapr run` port conflict detection
- Kubernetes deployment validation
- Docker Compose DAPR validation

## Requirements

- Python 3.9+
- DAPR CLI (`dapr init`)
- Docker (for local development)
- Cloud CLI (Azure CLI, AWS CLI, or gcloud)
- OpenAI API key (for AI agents)

## Environment Variables

```bash
# LLM Configuration
OPENAI_API_KEY=sk-...
AZURE_OPENAI_API_KEY=...
LLM_MODEL=gpt-4o

# DAPR Configuration
DAPR_HTTP_PORT=3500
DAPR_GRPC_PORT=50001

# AWS (for AWS components)
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1

# GCP (for GCP components)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
GCP_PROJECT_ID=my-project
```

## Version Compatibility

See \ for detailed version matrix.

| Plugin Version | DAPR Runtime | Python SDK | Notes |
|----------------|--------------|------------|-------|
| v2.6.x | 1.12 - 1.16 | >=1.12.0 | Robustness & resiliency enhancements |
| v2.5.x | 1.12 - 1.16 | >=1.12.0 | Security hardened defaults |
| v2.4.x | 1.12 - 1.16 | >=1.12.0 | Full feature support |
| v2.3.x | 1.12 - 1.15 | >=1.12.0 | All 12 building blocks |
| v2.1.x - v2.2.x | 1.12+ | >=1.12.0 | DAPR Agents requires 1.14+ |

## Changelog

### v2.6.0
- Cross-Platform: Replaced Windows-specific SessionStart hook with Python-based environment detection
- Cross-Platform: Added cloud CLI authentication validators (Azure, AWS, GCP)
- Validation: Added dependency-analyzer.py for circular dependency detection
- Validation: Added 8 new validation functions (service dependencies, secret references, resource quotas, port conflicts, managed identity, mTLS, resiliency policies)
- Validation: Added 12 new hooks for ACL, configuration, subscription, deployment, observability, workflow, and actor files
- Resiliency: New `/dapr:resiliency` command for analyze/apply/test operations
- Resiliency: Added resiliency-aca.yaml with Azure Container Apps configuration
- Resiliency: Added resiliency-patterns.yaml with 8 pre-defined patterns
- Error Handling: Added templates/utils/error_handling.py with RetryPolicy, CircuitBreaker, @with_dapr_retry decorator
- Observability: Added trace_analyzer.py for Zipkin/Jaeger/Azure Monitor trace analysis
- Observability: Added health_checks.py with liveness/readiness probe framework
- Testing: Added chaos_testing.py with @chaos_monkey decorator and ResiliencyTester
- Hooks: Added pre-deployment hooks for dapr run, kubectl, docker-compose, and dapr init

### v2.5.0
- Security: Replaced `eval()` with `simpleeval` library in agent templates
- Security: Redis templates use `secretKeyRef` instead of empty passwords
- Security: Enabled TLS by default in Redis component templates
- Security: Changed default host binding from `0.0.0.0` to `127.0.0.1`
- Security: Added authorization middleware examples to service templates
- Testing: Created shared `tests/validators.py` module with 12+ validation functions
- Testing: Added `pytest.ini` configuration with test markers
- Docs: Added `TESTING.md` guide for running and writing tests
- Docs: Added `CODE_OF_CONDUCT.md` with enforcement contact

### v2.4.0
- Dedicated \ directory with 10 templates (Cosmos DB, Service Bus, Key Vault, Blob Storage, Event Grid, Event Hubs, SignalR, Queue Storage, Container Apps, AKS)
- Version compatibility matrix (\)
- Plugin self-tests for hook validation logic (5 test files)
- Azure template validation hook
- Updated component command with Event Hubs, SignalR, Queue Storage

### v2.3.0
- 12 binding templates (HTTP, Kafka, RabbitMQ, MQTT, databases, email)
- 80+ error codes reference with troubleshooting
- Pluggable component development support
- Binding and pluggable component validation hooks

### v2.2.0
- AWS templates (DynamoDB, SNS/SQS, S3, EKS, ECS)
- GCP templates (Firestore, Pub/Sub, GCS, GKE, Cloud Run)
- HTTP middleware (OAuth2, Bearer, OPA, Rate Limit, Sentinel, WASM)
- Cloud deployer agent

### v2.1.0
- DAPR Agents AI framework support
- Agentic patterns (prompt chaining, parallelization, routing)
- Multi-agent orchestration
- CrewAI and OpenAI Agents integration

### v2.0.0
- All 12 DAPR building blocks
- Testing support with mocked clients
- CI/CD integration
- Observability with OpenTelemetry

## License

MIT

## Support

For issues and feature requests, please open an issue on the [plugin repository](https://github.com/Sahib-Sawhney-WH/dapr-claude-plugin).
