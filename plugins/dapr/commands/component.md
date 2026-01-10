---
description: Generate DAPR component YAML files for state stores, pub/sub, bindings, and secrets across Azure, AWS, and GCP
---

# DAPR Component Generator

Generate properly configured DAPR component YAML files for various backends across multiple cloud providers.

## Behavior

When the user runs `/dapr:component`:

1. **Select Component Type**
   - State Store (Redis, Cosmos DB, DynamoDB, Firestore, PostgreSQL, MongoDB)
   - Pub/Sub (Redis, Service Bus, SNS/SQS, GCP Pub/Sub, Kafka, RabbitMQ)
   - Secret Store (Key Vault, Secrets Manager, GCP Secret Manager, Local File, Kubernetes)
   - Binding (Blob Storage, S3, GCS, Event Grid, Kinesis, Cron, HTTP)

2. **Select Cloud Provider**
   Based on component type, show relevant options:
   - Local development options (Redis, local file, LocalStack, emulators)
   - **Azure** (Cosmos DB, Service Bus, Key Vault, Blob Storage)
   - **AWS** (DynamoDB, SNS/SQS, Secrets Manager, S3, Kinesis, SES)
   - **GCP** (Firestore, Pub/Sub, Secret Manager, Cloud Storage)

3. **Configure Settings**
   - Component name
   - Connection details
   - Authentication method (managed identity vs. connection string)
   - Component-specific settings

4. **Generate YAML**
   Create component file in `./components/` directory with:
   - Proper schema and version
   - All required metadata
   - Secret references (not plain text)
   - Comments explaining settings

5. **Validate**
   Run validation to ensure component is correct

## Arguments

- `$ARGUMENTS` - Component type and backend:

  **Local/Generic:**
  - `state redis` - Redis state store
  - `pubsub redis` - Redis pub/sub
  - `binding cron` - Cron scheduler

  **Azure:**
  - `state cosmos` - Azure Cosmos DB
  - `pubsub servicebus` - Azure Service Bus
  - `secrets keyvault` - Azure Key Vault
  - `binding blob` - Azure Blob Storage
  - `binding eventhubs` - Azure Event Hubs (streaming/IoT)
  - `binding signalr` - Azure SignalR (real-time WebSocket)
  - `binding queuestorage` - Azure Queue Storage (simple queues)

  **AWS:**
  - `state dynamodb` - AWS DynamoDB
  - `pubsub snssqs` - AWS SNS/SQS
  - `secrets awssecrets` - AWS Secrets Manager
  - `binding s3` - AWS S3
  - `binding kinesis` - AWS Kinesis
  - `binding sqs` - AWS SQS
  - `binding ses` - AWS SES (email)

  **GCP:**
  - `state firestore` - GCP Firestore
  - `pubsub gcppubsub` - GCP Pub/Sub
  - `secrets gcpsecrets` - GCP Secret Manager
  - `binding gcs` - GCP Cloud Storage

  **Common Bindings:**
  - `binding http` - HTTP/REST API calls and webhooks
  - `binding kafka` - Apache Kafka messaging
  - `binding rabbitmq` - RabbitMQ queues
  - `binding mqtt` - MQTT for IoT devices
  - `binding postgresql` - PostgreSQL database
  - `binding mysql` - MySQL/MariaDB database
  - `binding redis` - Redis caching/queues
  - `binding smtp` - Email sending
  - `binding influxdb` - InfluxDB time-series
  - `binding localstorage` - Local filesystem
  - `binding graphql` - GraphQL endpoints

## Examples

```
# Local development
/dapr:component state redis
/dapr:component binding cron

# Azure
/dapr:component state cosmos
/dapr:component pubsub servicebus
/dapr:component secrets keyvault
/dapr:component binding eventhubs
/dapr:component binding signalr
/dapr:component binding queuestorage

# AWS
/dapr:component state dynamodb
/dapr:component pubsub snssqs
/dapr:component secrets awssecrets
/dapr:component binding s3

# GCP
/dapr:component state firestore
/dapr:component pubsub gcppubsub
/dapr:component secrets gcpsecrets

# Common Bindings
/dapr:component binding http
/dapr:component binding kafka
/dapr:component binding rabbitmq
/dapr:component binding mqtt
/dapr:component binding postgresql
/dapr:component binding smtp
```

## Generated Components

### State Store - Redis (Local)
```yaml
# components/statestore.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: statestore
spec:
  type: state.redis
  version: v1
  metadata:
  - name: redisHost
    value: localhost:6379
  - name: actorStateStore
    value: "true"
```

### State Store - Cosmos DB (Azure)
```yaml
# components/statestore.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: statestore
spec:
  type: state.azure.cosmosdb
  version: v1
  metadata:
  - name: url
    value: https://{account}.documents.azure.com:443/
  - name: database
    value: daprdb
  - name: collection
    value: state
  - name: azureClientId
    value: "{managed-identity-client-id}"
```

### Pub/Sub - Service Bus (Azure)
```yaml
# components/pubsub.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: pubsub
spec:
  type: pubsub.azure.servicebus.topics
  version: v1
  metadata:
  - name: namespaceName
    value: "{namespace}.servicebus.windows.net"
  - name: azureClientId
    value: "{managed-identity-client-id}"
  - name: consumerID
    value: "{app-id}"
```

### Secret Store - Key Vault (Azure)
```yaml
# components/secretstore.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: secretstore
spec:
  type: secretstores.azure.keyvault
  version: v1
  metadata:
  - name: vaultName
    value: "{vault-name}"
  - name: azureClientId
    value: "{managed-identity-client-id}"
```

### Binding - Cron (Scheduled)
```yaml
# components/scheduled-job.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: scheduled-job
spec:
  type: bindings.cron
  version: v1
  metadata:
  - name: schedule
    value: "@every 5m"
```

### State Store - DynamoDB (AWS)
```yaml
# components/statestore.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: statestore
spec:
  type: state.aws.dynamodb
  version: v1
  metadata:
  - name: table
    value: "dapr-state"
  - name: region
    value: "us-east-1"
  # Use IRSA on EKS - omit accessKey/secretKey
  - name: accessKey
    secretKeyRef:
      name: aws-credentials
      key: access-key
  - name: secretKey
    secretKeyRef:
      name: aws-credentials
      key: secret-key
```

### Pub/Sub - SNS/SQS (AWS)
```yaml
# components/pubsub.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: pubsub
spec:
  type: pubsub.aws.snssqs
  version: v1
  metadata:
  - name: region
    value: "us-east-1"
  - name: accessKey
    secretKeyRef:
      name: aws-credentials
      key: access-key
  - name: secretKey
    secretKeyRef:
      name: aws-credentials
      key: secret-key
```

### State Store - Firestore (GCP)
```yaml
# components/statestore.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: statestore
spec:
  type: state.gcp.firestore
  version: v1
  metadata:
  - name: project_id
    value: "my-gcp-project"
  - name: type
    value: "service_account"
  # Use Workload Identity on GKE - omit credentials
```

### Pub/Sub - GCP Pub/Sub
```yaml
# components/pubsub.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: pubsub
spec:
  type: pubsub.gcp.pubsub
  version: v1
  metadata:
  - name: projectId
    value: "my-gcp-project"
  # Use Workload Identity on GKE
```

### Binding - S3 (AWS)
```yaml
# components/s3-storage.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: s3-storage
spec:
  type: bindings.aws.s3
  version: v1
  metadata:
  - name: bucket
    value: "my-bucket"
  - name: region
    value: "us-east-1"
  - name: accessKey
    secretKeyRef:
      name: aws-credentials
      key: access-key
  - name: secretKey
    secretKeyRef:
      name: aws-credentials
      key: secret-key
```

## Interactive Prompts

When running without arguments, prompt for:
1. Component type (state/pubsub/secrets/binding)
2. Backend service
3. Environment (local/azure/other)
4. Component name
5. Connection details based on backend

## Best Practices Applied

- Uses managed identity for Azure services
- Separates dev/prod configurations
- Includes comments for customization
- Sets appropriate defaults
- Validates before saving
