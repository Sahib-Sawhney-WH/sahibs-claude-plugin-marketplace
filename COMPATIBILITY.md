# DAPR Plugin Compatibility

This document outlines the compatibility between the DAPR Claude Plugin and various DAPR versions, SDKs, and cloud platforms.

## Version Compatibility Matrix

| Plugin Version | DAPR Runtime | DAPR CLI | Python SDK | Status |
|----------------|--------------|----------|------------|--------|
| v2.4.0 | 1.12 - 1.16 | 1.12+ | 1.12+ | Current |
| v2.3.0 | 1.12 - 1.16 | 1.12+ | 1.12+ | Supported |
| v2.2.0 | 1.12 - 1.15 | 1.12+ | 1.12+ | Supported |
| v2.1.0 | 1.12 - 1.14 | 1.12+ | 1.12+ | Supported |
| v2.0.0 | 1.10 - 1.14 | 1.10+ | 1.10+ | Legacy |

## Feature Availability by DAPR Version

### Building Blocks

| Building Block | DAPR 1.10 | DAPR 1.12 | DAPR 1.14 | DAPR 1.16 |
|----------------|-----------|-----------|-----------|-----------|
| Service Invocation | ✅ | ✅ | ✅ | ✅ |
| State Management | ✅ | ✅ | ✅ | ✅ |
| Pub/Sub | ✅ | ✅ | ✅ | ✅ |
| Bindings | ✅ | ✅ | ✅ | ✅ |
| Secrets | ✅ | ✅ | ✅ | ✅ |
| Actors | ✅ | ✅ | ✅ | ✅ |
| Workflows | ⚠️ Beta | ✅ | ✅ | ✅ |
| Configuration | ⚠️ Beta | ✅ | ✅ | ✅ |
| Distributed Lock | ⚠️ Beta | ✅ | ✅ | ✅ |
| Cryptography | ❌ | ⚠️ Alpha | ✅ | ✅ |
| Jobs/Scheduler | ❌ | ❌ | ⚠️ Alpha | ✅ |
| Conversation (AI) | ❌ | ❌ | ❌ | ⚠️ Alpha |

**Legend:** ✅ Stable | ⚠️ Preview/Beta | ❌ Not Available

### Plugin Features

| Plugin Feature | Min DAPR Version | Notes |
|----------------|------------------|-------|
| Core commands (/dapr:init, run, deploy) | 1.10+ | |
| All 12 building blocks | 1.14+ | Jobs requires 1.14+ |
| DAPR Agents | 1.14+ | Requires workflow support |
| Multi-cloud templates | 1.12+ | |
| HTTP Middleware | 1.12+ | |
| Pluggable components | 1.12+ | |
| Observability (OpenTelemetry) | 1.10+ | |

## SDK Requirements

### Python SDK (dapr)

```bash
# Minimum version
pip install dapr>=1.12.0

# Recommended version
pip install dapr>=1.14.0

# For DAPR Agents (third-party)
pip install dapr-agents>=0.1.0
```

### Version Mapping

| Plugin Version | dapr-python | dapr-ext-workflow | dapr-ext-grpc |
|----------------|-------------|-------------------|---------------|
| v2.4.0 | >=1.12.0 | >=0.3.0 | >=1.12.0 |
| v2.3.0 | >=1.12.0 | >=0.3.0 | >=1.12.0 |
| v2.2.0 | >=1.12.0 | >=0.2.0 | >=1.12.0 |
| v2.1.0 | >=1.10.0 | >=0.1.0 | >=1.10.0 |

## Cloud Platform Compatibility

### Azure

| Service | Plugin Support | Min DAPR Version | Notes |
|---------|----------------|------------------|-------|
| Cosmos DB | ✅ Full | 1.10+ | |
| Service Bus | ✅ Full | 1.10+ | Topics and Queues |
| Key Vault | ✅ Full | 1.10+ | Managed Identity support |
| Blob Storage | ✅ Full | 1.10+ | |
| Event Grid | ✅ Full | 1.10+ | |
| Event Hubs | ✅ Full | 1.10+ | New in v2.4.0 |
| SignalR | ✅ Full | 1.12+ | New in v2.4.0 |
| Queue Storage | ✅ Full | 1.10+ | New in v2.4.0 |
| Container Apps | ✅ Full | 1.12+ | Managed DAPR |
| AKS | ✅ Full | 1.10+ | |

### AWS

| Service | Plugin Support | Min DAPR Version | Notes |
|---------|----------------|------------------|-------|
| DynamoDB | ✅ Full | 1.10+ | |
| SNS/SQS | ✅ Full | 1.10+ | |
| Secrets Manager | ✅ Full | 1.10+ | |
| S3 | ✅ Full | 1.10+ | |
| Kinesis | ✅ Full | 1.12+ | |
| SES | ✅ Full | 1.12+ | |
| EKS | ✅ Full | 1.10+ | |
| ECS Fargate | ✅ Full | 1.12+ | Sidecar pattern |

### GCP

| Service | Plugin Support | Min DAPR Version | Notes |
|---------|----------------|------------------|-------|
| Firestore | ✅ Full | 1.10+ | |
| Pub/Sub | ✅ Full | 1.10+ | |
| Secret Manager | ✅ Full | 1.10+ | |
| Cloud Storage | ✅ Full | 1.10+ | |
| GKE | ✅ Full | 1.10+ | |
| Cloud Run | ✅ Full | 1.12+ | With sidecar |

## Breaking Changes

### DAPR 1.14 → 1.15

- Workflow API stabilized (no breaking changes)
- Scheduler API graduated to stable

### DAPR 1.12 → 1.14

- Cryptography API graduated to stable
- New Jobs/Scheduler building block (alpha)
- Workflow API improvements

### DAPR 1.10 → 1.12

- Configuration API stabilized
- Distributed Lock API stabilized
- Improved gRPC performance

## Checking Your Versions

```bash
# Check DAPR CLI version
dapr --version

# Check DAPR runtime version
dapr version

# Check DAPR runtime on Kubernetes
kubectl get pods -n dapr-system -o jsonpath='{.items[0].spec.containers[0].image}'

# Check Python SDK version
pip show dapr

# Check plugin version
# Look at .claude-plugin/plugin.json
```

## Upgrading DAPR

### Standalone Mode

```bash
# Upgrade CLI
wget -q https://raw.githubusercontent.com/dapr/cli/master/install/install.sh -O - | /bin/bash

# Upgrade runtime
dapr uninstall
dapr init
```

### Kubernetes Mode

```bash
# Upgrade CLI
wget -q https://raw.githubusercontent.com/dapr/cli/master/install/install.sh -O - | /bin/bash

# Upgrade runtime
helm repo update
dapr upgrade -k --runtime-version 1.16.0
```

## Recommended Configuration

For the best experience with this plugin:

```bash
# Recommended versions
DAPR Runtime: 1.14.0 or later
DAPR CLI: 1.14.0 or later
Python: 3.10 or later
dapr-python: 1.14.0 or later
```

## Getting Help

If you encounter compatibility issues:

1. Check versions match the compatibility matrix above
2. Review DAPR release notes for breaking changes
3. Open an issue on the plugin repository with version details

## Resources

- [DAPR Release Notes](https://github.com/dapr/dapr/releases)
- [DAPR Python SDK](https://github.com/dapr/python-sdk)
- [DAPR Component Specs](https://docs.dapr.io/reference/components-reference/)
