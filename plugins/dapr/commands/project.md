---
description: Initialize a multi-service DAPR project with shared configuration
---

# DAPR Multi-Service Project

Initialize a complete multi-service DAPR project with shared components and configuration.

## Behavior

When the user runs `/dapr:project`:

1. **Create Project Structure**
   - Root project directory
   - Shared components directory
   - Individual service directories
   - Shared infrastructure

2. **Generate Shared Configuration**
   - `dapr.yaml` for multi-app mode
   - Shared component YAML files
   - Resiliency policies
   - Observability configuration

3. **Create Service Templates**
   - FastAPI service template
   - Dockerfile for each service
   - Service-specific components

## Arguments

| Argument | Description |
|----------|-------------|
| `<name>` | Project name (required) |
| `--services` | Comma-separated service names |
| `--template` | Project template (ecommerce, iot, saga) |

## Examples

### Basic Multi-Service Project
```
/dapr:project my-app --services "order-service,inventory-service,payment-service"
```

### E-Commerce Template
```
/dapr:project shop --template ecommerce
```

### IoT Event Processing
```
/dapr:project iot-hub --template iot
```

## Generated Structure

```
my-app/
├── dapr.yaml                      # Multi-app run configuration
├── components/                    # Shared DAPR components
│   ├── statestore.yaml
│   ├── pubsub.yaml
│   ├── secretstore.yaml
│   └── resiliency.yaml
├── services/
│   ├── order-service/
│   │   ├── src/
│   │   │   └── main.py
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── components/            # Service-specific components
│   ├── inventory-service/
│   │   └── ...
│   └── payment-service/
│       └── ...
├── infrastructure/
│   ├── docker-compose.yaml        # Local development
│   ├── bicep/                     # Azure IaC
│   │   └── main.bicep
│   └── kubernetes/                # K8s manifests
│       └── deployment.yaml
├── tests/
│   ├── e2e/
│   └── integration/
└── README.md
```

## dapr.yaml (Multi-App Mode)

```yaml
version: 1
apps:
  - appId: order-service
    appDirPath: ./services/order-service
    appPort: 8001
    command: ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]

  - appId: inventory-service
    appDirPath: ./services/inventory-service
    appPort: 8002
    command: ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8002"]

  - appId: payment-service
    appDirPath: ./services/payment-service
    appPort: 8003
    command: ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8003"]

common:
  resourcesPath: ./components
```

## Running the Project

```bash
# Run all services locally
dapr run -f dapr.yaml

# Run with Docker Compose
docker-compose up

# Deploy to Azure
/dapr:deploy aca
```

## Templates

### E-Commerce Template
- `api-gateway` - BFF pattern gateway
- `order-service` - Order management with workflows
- `inventory-service` - Stock management with actors
- `payment-service` - Payment processing with saga
- `notification-service` - Event-driven notifications

### IoT Template
- `device-gateway` - Device ingestion
- `device-actor` - Per-device state
- `analytics-service` - Stream processing
- `alerting-service` - Threshold alerts

### Saga Template
- `orchestrator` - Saga coordinator
- `service-a` - Participant A
- `service-b` - Participant B
- `service-c` - Participant C
