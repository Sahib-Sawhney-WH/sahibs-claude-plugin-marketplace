---
description: View and filter DAPR application and sidecar logs for debugging
---

# DAPR Log Viewer

Stream and filter logs from DAPR applications and sidecars.

## Behavior

When the user runs `/dapr:logs`:

1. **Detect Environment**
   - Local development (dapr run)
   - Docker containers
   - Kubernetes (AKS, etc.)
   - Azure Container Apps

2. **Identify Applications**
   - List running DAPR apps: `dapr list`
   - Get app-id from $ARGUMENTS or prompt

3. **Stream Logs**

   **Local Development:**
   ```bash
   dapr logs --app-id {app-id}
   ```

   **Kubernetes:**
   ```bash
   # Application logs
   kubectl logs deployment/{app} -c {app}

   # Sidecar logs
   kubectl logs deployment/{app} -c daprd
   ```

   **Azure Container Apps:**
   ```bash
   az containerapp logs show \
     --name {app} \
     --resource-group {rg} \
     --follow
   ```

4. **Filter and Format**
   - Filter by log level (debug, info, warn, error)
   - Filter by time range
   - Search for specific patterns
   - Colorize output by level

## Arguments

- `$ARGUMENTS` - App and filter options:
  - `{app-id}` - Application to view logs for
  - `--level {error|warn|info|debug}` - Filter by level
  - `--since {time}` - Logs since (e.g., "5m", "1h")
  - `--tail {n}` - Last n lines
  - `--sidecar` - Show sidecar logs instead
  - `--follow` or `-f` - Stream live logs

## Examples

```
/dapr:logs order-service
/dapr:logs order-service --level error
/dapr:logs order-service --since 5m --follow
/dapr:logs order-service --sidecar
/dapr:logs --tail 100
```

## Log Output Format

```
DAPR Logs: order-service
==========================

[2024-01-15 10:23:45] INFO  Starting application...
[2024-01-15 10:23:46] INFO  DAPR sidecar connected on port 3500
[2024-01-15 10:23:46] INFO  Components loaded: statestore, pubsub
[2024-01-15 10:23:47] INFO  Listening on port 8000
[2024-01-15 10:24:01] DEBUG Processing order: ORD-123
[2024-01-15 10:24:02] INFO  Order saved to state store
[2024-01-15 10:24:02] INFO  Event published: order.created
[2024-01-15 10:25:15] WARN  Retry attempt 1 for inventory service
[2024-01-15 10:25:16] ERROR Failed to invoke inventory-service: timeout

Press Ctrl+C to stop streaming
```

## Log Analysis

When viewing logs, automatically:

1. **Detect Errors**
   - Highlight error patterns
   - Suggest possible causes
   - Link to troubleshooting docs

2. **Track Request Flow**
   - Correlate requests across services
   - Show trace IDs
   - Display timing information

3. **Identify Patterns**
   - Repeated errors
   - Performance issues
   - Resource constraints

## Error Detection Example

```
ERROR DETECTED
==============

[10:25:16] ERROR Failed to invoke inventory-service: timeout

Possible Causes:
1. inventory-service is not running
2. Network connectivity issue
3. Service is overloaded

Suggested Actions:
- Check if inventory-service is running: dapr list
- Verify network connectivity
- Check inventory-service logs: /dapr:logs inventory-service

Related Logs:
[10:25:15] WARN  Retry attempt 1 for inventory service
[10:25:15] WARN  Retry attempt 2 for inventory service
```

## Environment-Specific Commands

### Local (dapr run)
```bash
# View app logs
dapr logs --app-id order-service

# View with level filter
dapr logs --app-id order-service --log-level warn
```

### Kubernetes
```bash
# App container logs
kubectl logs -l app=order-service -c order-service --tail=100 -f

# Sidecar logs
kubectl logs -l app=order-service -c daprd --tail=100 -f

# Combined
kubectl logs -l app=order-service --all-containers --tail=100 -f
```

### Azure Container Apps
```bash
# Stream logs
az containerapp logs show \
  --name order-service \
  --resource-group myapp-rg \
  --follow

# Query logs (Log Analytics)
az monitor log-analytics query \
  --workspace {workspace-id} \
  --analytics-query "ContainerAppConsoleLogs | where ContainerAppName == 'order-service'"
```

## Structured Logging Support

When structured logging (JSON) is detected:

```json
{"timestamp":"2024-01-15T10:24:01Z","level":"info","message":"Processing order","orderId":"ORD-123","traceId":"abc123"}
```

Format output:
```
[10:24:01] INFO  Processing order
           orderId: ORD-123
           traceId: abc123
```

## Quick Actions

After viewing logs, offer:
- "Filter errors only" - Show only error logs
- "Search for pattern" - Search specific text
- "View sidecar logs" - Switch to DAPR sidecar
- "Open in dashboard" - Open DAPR dashboard
- "Debug this error" - Use dapr-debugger agent
