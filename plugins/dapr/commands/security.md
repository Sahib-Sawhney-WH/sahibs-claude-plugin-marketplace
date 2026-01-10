---
description: Scan DAPR project for security vulnerabilities, plain-text secrets, missing ACLs, and configuration issues
---

# DAPR Security Scanner

Scan your DAPR project for security issues and best practice violations.

## Behavior

When the user runs `/dapr:security`:

1. **Locate Configuration Files**
   - Find all component YAML files in `components/`
   - Find `dapr.yaml` if present
   - Find any Configuration or Resiliency resources

2. **Run Security Checks**

   ### Critical Checks (Fail deployment)
   - Plain-text secrets in component files
   - Hardcoded connection strings with passwords
   - API keys or tokens in plain text
   - Missing `secretKeyRef` for sensitive fields

   ### High Severity Checks
   - Secret stores without scope restrictions
   - mTLS disabled in production config
   - No access control policies defined
   - Missing resiliency policies for external services

   ### Medium Severity Checks
   - Components without scope restrictions
   - Using connection strings instead of managed identity
   - Missing circuit breakers for service invocation
   - No timeout policies defined

   ### Low Severity Checks
   - Missing metadata fields
   - Non-optimal retry configurations
   - Missing tracing configuration

3. **Generate Report**
   ```
   DAPR Security Scan Results
   ==========================

   Files Scanned: 5

   CRITICAL Issues (1):
   ✗ components/statestore.yaml:15
     Plain-text password in 'redisPassword'
     → Use secretKeyRef instead of value

   HIGH Issues (0): None

   MEDIUM Issues (2):
   ⚠ components/pubsub.yaml
     No scope restrictions defined
     → Add scopes to limit access

   ⚠ dapr.yaml
     No resiliency policy referenced
     → Create resiliency.yaml for production

   LOW Issues (1):
   ○ components/secretstore.yaml
     Using connectionString instead of managed identity
     → Consider azureClientId for managed identity auth

   Summary: 1 critical, 0 high, 2 medium, 1 low
   Status: FAILED (critical issues found)
   ```

4. **Suggest Fixes**
   For each issue, provide:
   - The problematic configuration
   - The recommended fix
   - Code snippet showing the correction

## Arguments

| Argument | Description |
|----------|-------------|
| `--path` | Path to scan (default: current directory) |
| `--fix` | Attempt to auto-fix issues |
| `--report` | Generate JSON report file |
| `--fail-on` | Fail on severity level (critical, high, medium, low) |

## Examples

### Basic Scan
```
/dapr:security
```

### Scan Specific Directory
```
/dapr:security --path ./services/order-service
```

### Generate Report
```
/dapr:security --report security-report.json
```

### CI/CD Mode (Fail on Critical)
```
/dapr:security --fail-on critical
```

### Auto-Fix Mode
```
/dapr:security --fix
```

## Security Best Practices Enforced

### Secrets Management
- ✓ Use `secretKeyRef` for all sensitive values
- ✓ Never commit plain-text secrets
- ✓ Use Azure Key Vault or similar for production
- ✓ Enable secret rotation

### Access Control
- ✓ Define `scopes` on all components
- ✓ Use `accessControl` with `defaultAction: deny`
- ✓ Apply least-privilege principle
- ✓ Enable mTLS for service-to-service

### Resiliency
- ✓ Configure circuit breakers for external services
- ✓ Set appropriate timeouts
- ✓ Use exponential backoff for retries
- ✓ Limit retry attempts

### Observability
- ✓ Enable distributed tracing
- ✓ Configure structured logging
- ✓ Set up metrics collection
- ✓ Use correlation IDs

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No issues or only LOW severity |
| 1 | MEDIUM or HIGH issues found |
| 2 | CRITICAL issues found |
