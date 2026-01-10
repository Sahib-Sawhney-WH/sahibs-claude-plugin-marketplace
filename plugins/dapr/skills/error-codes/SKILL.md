# DAPR Error Codes Reference

Use this skill to diagnose and troubleshoot DAPR errors. When encountering DAPR error codes, use this reference to understand the cause and apply the appropriate fix.

---

## Actors API Errors

| Error Code | Description | Troubleshooting |
|------------|-------------|-----------------|
| `ERR_ACTOR_INSTANCE_MISSING` | Actor instance not found | Verify actor ID is correct; check if actor was deactivated |
| `ERR_ACTOR_RUNTIME_NOT_FOUND` | Actor runtime not initialized | Ensure actor runtime is configured; check app startup |
| `ERR_ACTOR_REMINDER_CREATE` | Failed to create reminder | Check state store connectivity; verify reminder name |
| `ERR_ACTOR_REMINDER_DELETE` | Failed to delete reminder | Reminder may not exist; check actor ID and reminder name |
| `ERR_ACTOR_REMINDER_GET` | Failed to get reminder | Reminder doesn't exist or state store issue |
| `ERR_ACTOR_TIMER_CREATE` | Failed to create timer | Check timer callback method exists |
| `ERR_ACTOR_TIMER_DELETE` | Failed to delete timer | Timer may not exist; verify timer name |
| `ERR_ACTOR_STATE_GET` | Failed to get actor state | State store connectivity issue; check configuration |
| `ERR_ACTOR_STATE_TRANSACT_SAVE` | Transaction save failed | State store error; check for conflicts |
| `ERR_ACTOR_INVOKE_METHOD` | Method invocation failed | Check method exists; verify method signature |
| `ERR_ACTOR_DEACTIVATE` | Deactivation failed | Check OnDeactivateAsync implementation |
| `ERR_ACTOR_TYPE_INFO` | Actor type metadata error | Verify actor interface registration |
| `ERR_ACTOR_REENTRANCY` | Reentrancy config error | Check reentrancy settings in actor runtime |
| `ERR_ACTOR_DRAIN_ONGOING` | Actor draining in progress | Wait for drain to complete; node is shutting down |
| `ERR_ACTOR_PLACED_ELSEWHERE` | Actor on different host | Retry request; placement will redirect |
| `ERR_ACTOR_NO_HOST` | No host available | Check sidecar connectivity; verify placement service |

### Actor Troubleshooting Steps:
1. Check state store is configured and healthy: `dapr components -k`
2. Verify actor is registered: Check app startup logs for actor registration
3. Confirm placement service is running: `kubectl get pods -l app=dapr-placement`
4. Review actor configuration in `config.yaml`

---

## Workflows API Errors

| Error Code | Description | Troubleshooting |
|------------|-------------|-----------------|
| `ERR_START_WORKFLOW` | Failed to start workflow | Check workflow name; verify workflow registered |
| `ERR_GET_WORKFLOW` | Failed to get workflow status | Instance may not exist; verify instance ID |
| `ERR_TERMINATE_WORKFLOW` | Failed to terminate workflow | Instance may already be completed |
| `ERR_PAUSE_WORKFLOW` | Failed to pause workflow | Workflow may not be running |
| `ERR_RESUME_WORKFLOW` | Failed to resume workflow | Workflow may not be paused |
| `ERR_RAISE_EVENT_WORKFLOW` | Failed to raise event | Check event name; workflow may not be waiting |
| `ERR_PURGE_WORKFLOW` | Failed to purge workflow | Instance may not exist or not completed |
| `ERR_INSTANCE_ID_TOO_LONG` | Instance ID exceeds limit | Use shorter instance IDs (max 64 chars) |
| `ERR_INSTANCE_ID_NOT_FOUND` | Workflow instance missing | Verify instance ID; check if purged |
| `ERR_INSTANCE_ID_INVALID` | Invalid instance ID format | Use alphanumeric with hyphens only |
| `ERR_INSTANCE_ID_PROVIDED_FOR_CRON` | ID not allowed for scheduled | Remove instance_id for cron-triggered workflows |
| `ERR_INSTANCE_DUPLICATE_ID` | Instance already exists | Use unique instance IDs; or purge existing |
| `ERR_WORKFLOW_COMPONENT_NOT_FOUND` | Workflow engine missing | Configure workflow component; check dapr init |
| `ERR_WORKFLOW_NAME_MISSING` | Workflow name required | Provide workflow name in request |

### Workflow Troubleshooting Steps:
1. Check workflow engine is configured: `dapr components -k | grep workflow`
2. Verify workflow is registered in your application
3. Check instance ID format (alphanumeric, hyphens, max 64 chars)
4. Review workflow state: `dapr workflow get <instance-id>`

---

## State Management Errors

| Error Code | Description | Troubleshooting |
|------------|-------------|-----------------|
| `ERR_STATE_STORE_NOT_FOUND` | State store not configured | Check components folder; verify store name |
| `ERR_STATE_STORE_NOT_CONFIGURED` | State store not initialized | Review component YAML; check secrets |
| `ERR_STATE_SAVE` | Failed to save state | Connection issue; check store health |
| `ERR_STATE_GET` | Failed to get state | Key may not exist; connection issue |
| `ERR_STATE_DELETE` | Failed to delete state | Key may not exist; permission issue |
| `ERR_STATE_BULK_GET` | Bulk get operation failed | One or more keys failed; check connection |
| `ERR_STATE_TRANSACTION` | Transaction failed | Concurrency conflict or store limitation |
| `ERR_STATE_QUERY` | Query operation failed | Query syntax error; store may not support queries |
| `ERR_STATE_QUERY_NOT_SUPPORTED` | Store doesn't support queries | Use a query-capable store (Cosmos, MongoDB) |
| `ERR_NOT_SUPPORTED_STATE_OPERATION` | Operation not supported | Check store capabilities |

### State Store Troubleshooting Steps:
1. Verify component configuration: `dapr components -k`
2. Test connection: `dapr invoke --app-id <app> --method <endpoint>`
3. Check secrets are accessible
4. Review store-specific requirements (key format, etc.)

---

## Pub/Sub Errors

| Error Code | Description | Troubleshooting |
|------------|-------------|-----------------|
| `ERR_PUBSUB_NOT_FOUND` | Pub/sub component not found | Check component name; verify configuration |
| `ERR_PUBSUB_NOT_CONFIGURED` | Pub/sub not initialized | Review component YAML; check broker connectivity |
| `ERR_PUBSUB_EMPTY_TOPIC` | Topic name required | Provide topic name in request |
| `ERR_PUBSUB_FORBIDDEN` | Access denied to topic | Check access control policies; verify topic permissions |
| `ERR_PUBSUB_PUBLISH_MESSAGE` | Failed to publish message | Broker connection issue; check credentials |
| `ERR_PUBSUB_REQUEST_METADATA` | Invalid metadata | Check metadata format; verify required fields |
| `ERR_PUBSUB_CLOUD_EVENTS_SER` | CloudEvents serialization error | Check message format; verify content type |
| `ERR_TOPIC_NAME_EMPTY` | Topic name is empty | Provide non-empty topic name |
| `ERR_PUBSUB_SUBSCRIBE` | Subscription failed | Topic may not exist; check permissions |
| `ERR_PUBSUB_EVENTS_SER` | Event serialization failed | Check data format; use valid JSON |
| `ERR_PUBSUB_GET_SUBSCRIPTIONS` | Failed to get subscriptions | App not responding; check /dapr/subscribe endpoint |
| `ERR_BULK_SUBSCRIBE_MESSAGE` | Bulk subscribe failed | Check bulk subscribe configuration |
| `ERR_PUBSUB_OUTBOX` | Outbox pattern failure | State store may be misconfigured |

### Pub/Sub Troubleshooting Steps:
1. Check broker is running and accessible
2. Verify topic exists or auto-creation is enabled
3. Test subscription endpoint: `curl http://localhost:<port>/dapr/subscribe`
4. Check access control policies if using DAPR RBAC

---

## Secrets Errors

| Error Code | Description | Troubleshooting |
|------------|-------------|-----------------|
| `ERR_SECRET_STORE_NOT_FOUND` | Secret store not found | Verify store name; check configuration |
| `ERR_SECRET_STORE_NOT_CONFIGURED` | Store not initialized | Check component YAML; verify credentials |
| `ERR_SECRET_GET` | Failed to get secret | Secret may not exist; check permissions |
| `ERR_SECRET_PERMISSION_DENIED` | Access denied | Check secret scope configuration |

### Secrets Troubleshooting Steps:
1. Verify secret store component is configured
2. Check secret exists in the store
3. Review secret scopes in component configuration

---

## Configuration Errors

| Error Code | Description | Troubleshooting |
|------------|-------------|-----------------|
| `ERR_CONFIGURATION_STORE_NOT_FOUND` | Config store not found | Verify store name; check configuration |
| `ERR_CONFIGURATION_STORE_NOT_CONFIGURED` | Store not initialized | Check component YAML |
| `ERR_CONFIGURATION_GET` | Failed to get config | Key may not exist; check store health |
| `ERR_CONFIGURATION_SUBSCRIBE` | Subscription failed | Store may not support subscriptions |
| `ERR_CONFIGURATION_UNSUBSCRIBE` | Unsubscribe failed | Subscription may not exist |

---

## Crypto Errors

| Error Code | Description | Troubleshooting |
|------------|-------------|-----------------|
| `ERR_CRYPTO_PROVIDER_NOT_FOUND` | Crypto provider not found | Configure crypto component |
| `ERR_CRYPTO_KEY` | Key operation failed | Check key name; verify key exists |
| `ERR_CRYPTO_ENCRYPT` | Encryption failed | Check key permissions; verify algorithm |
| `ERR_CRYPTO_DECRYPT` | Decryption failed | Wrong key; data may be corrupted |

---

## Bindings Errors

| Error Code | Description | Troubleshooting |
|------------|-------------|-----------------|
| `ERR_INVOKE_OUTPUT_BINDING` | Output binding failed | Check binding configuration; verify connection |

### Bindings Troubleshooting Steps:
1. Verify binding component is configured correctly
2. Check target service is accessible
3. Review operation name matches binding capabilities

---

## Distributed Locks Errors

| Error Code | Description | Troubleshooting |
|------------|-------------|-----------------|
| `ERR_LOCK_STORE_NOT_CONFIGURED` | Lock store not configured | Configure lock component |
| `ERR_TRY_LOCK` | Failed to acquire lock | Lock held by another owner; retry |
| `ERR_UNLOCK` | Failed to release lock | Not lock owner; lock may have expired |
| `ERR_LOCK_STORE_NOT_FOUND` | Lock store not found | Verify component name |

---

## Health Check Errors

| Error Code | Description | Troubleshooting |
|------------|-------------|-----------------|
| `ERR_HEALTH_NOT_READY` | Sidecar not ready | Wait for initialization; check dependencies |
| `ERR_HEALTH_OUTBOUND_NOT_READY` | Outbound not ready | External dependencies not available |
| `ERR_HEALTH_APPHEALTH_NOT_READY` | App health check failed | App is unhealthy; check app logs |

---

## Scheduler/Jobs Errors

| Error Code | Description | Troubleshooting |
|------------|-------------|-----------------|
| `DAPR_SCHEDULER_CREATE_ERROR` | Failed to create job | Check job configuration; verify scheduler running |
| `DAPR_SCHEDULER_GET_ERROR` | Failed to get job | Job may not exist; check job name |
| `DAPR_SCHEDULER_LIST_ERROR` | Failed to list jobs | Scheduler connectivity issue |
| `DAPR_SCHEDULER_DELETE_ERROR` | Failed to delete job | Job may not exist |
| `DAPR_SCHEDULER_NOT_FOUND` | Job not found | Verify job name |
| `DAPR_SCHEDULER_ALREADY_EXISTS` | Job already exists | Use unique job names or delete existing |
| `DAPR_SCHEDULER_NOT_CONNECTED` | Not connected to scheduler | Check scheduler service is running |
| `DAPR_SCHEDULER_NOT_ENABLED` | Scheduler not enabled | Enable scheduler in DAPR configuration |

---

## Common/API Errors

| Error Code | Description | Troubleshooting |
|------------|-------------|-----------------|
| `ERR_API_UNIMPLEMENTED` | API not implemented | Feature not available in this version |
| `ERR_API_CHANNEL` | Channel/connection error | Check sidecar connectivity |
| `ERR_MALFORMED_REQUEST` | Invalid request format | Check request body; verify JSON format |
| `ERR_MALFORMED_REQUEST_DATA` | Invalid request data | Check data field format |
| `ERR_BAD_REQUEST` | Bad request | Review request parameters |
| `ERR_INTERNAL` | Internal error | Check DAPR sidecar logs |
| `ERR_NOT_FOUND` | Resource not found | Verify resource exists |
| `ERR_METHOD_NOT_ALLOWED` | HTTP method not allowed | Use correct HTTP method |

---

## Quick Diagnostic Commands

```bash
# Check DAPR sidecar status
dapr list

# View component status
dapr components -k

# Check sidecar logs
kubectl logs <pod-name> -c daprd

# Test sidecar health
curl http://localhost:3500/v1.0/healthz

# View actor placement
dapr placement -k

# Debug workflow instance
dapr workflow get --instance-id <id>
```

---

## Common Resolution Patterns

### Connection Issues
1. Verify sidecar is running: `dapr list`
2. Check network policies allow sidecar communication
3. Verify DNS resolution for external services
4. Check TLS/mTLS configuration

### Configuration Issues
1. Validate component YAML syntax
2. Check secret references are correct
3. Verify namespace matches deployment
4. Review component scopes

### Permission Issues
1. Check DAPR access control policies
2. Verify RBAC configuration
3. Review service account permissions
4. Check secret access scopes

---

## Error Severity Levels

| Level | Action |
|-------|--------|
| **Transient** | Retry with exponential backoff |
| **Configuration** | Fix component configuration, restart |
| **Permission** | Update RBAC/access policies |
| **Fatal** | Check logs, may require DAPR restart |
