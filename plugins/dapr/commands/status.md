---
description: Check DAPR runtime status, component health, and Azure deployment state
---

# DAPR Status Check

Check the health and status of your DAPR installation, running applications, and Azure deployments.

## Behavior

When the user runs `/dapr:status`:

1. **Check Local DAPR Installation**
   ```bash
   dapr --version
   dapr status
   ```

   Report:
   - DAPR CLI version
   - DAPR runtime version
   - Control plane status (placement, sentry, operator)
   - Dashboard availability

2. **Check Running Applications**
   ```bash
   dapr list
   ```

   Display table of:
   - App ID
   - HTTP Port
   - gRPC Port
   - App Port
   - Age
   - Status

3. **Validate Local Components**
   - Scan components/ directory
   - Validate each YAML file
   - Check component connectivity (Redis, etc.)
   - Report any configuration issues

4. **Check Azure Status** (if Azure CLI available)
   - Container Apps environment status
   - Deployed DAPR applications
   - Component configurations
   - Managed identity status
   - Recent deployment logs

5. **Health Summary**
   ```
   DAPR Status Report
   ==================

   Local Environment:
   ├── DAPR CLI:        v1.12.0 ✓
   ├── Runtime:         v1.12.0 ✓
   ├── Dashboard:       Running ✓
   └── Components:      3 loaded ✓

   Running Apps:
   ├── order-service:   Running (port 8000)
   └── inventory-svc:   Running (port 8001)

   Azure (Container Apps):
   ├── Environment:     my-env ✓
   ├── Apps:            2 deployed
   └── Last Deploy:     2 hours ago
   ```

## Arguments

- `$ARGUMENTS` - Scope: `local`, `azure`, `all` (default: all)

## Examples

```
/dapr:status
/dapr:status local
/dapr:status azure
```

## Detailed Checks

### Component Health
For each component, verify:
- YAML syntax valid
- Required metadata present
- Connection successful (for state stores, pubsub)
- Secrets accessible (if referenced)

### Azure Integration
If Azure resources detected:
- Check `az` CLI authentication
- Query Container Apps status
- List DAPR components in Azure
- Show resource group details

## Troubleshooting Output

When issues found, provide actionable fixes:

```
Issues Found:
┌─────────────────────────────────────────────────┐
│ ⚠ Redis connection failed                       │
│   Component: statestore                         │
│   Fix: Ensure Redis is running on localhost:6379│
│   Run: docker run -d -p 6379:6379 redis         │
├─────────────────────────────────────────────────┤
│ ⚠ DAPR Dashboard not accessible                 │
│   Expected: http://localhost:8080               │
│   Fix: Run 'dapr dashboard' in another terminal │
└─────────────────────────────────────────────────┘
```

## Quick Actions

After status check, offer relevant actions:
- "Start dashboard" if not running
- "Fix component" if validation failed
- "Deploy to Azure" if local but not deployed
- "View logs" if apps running
