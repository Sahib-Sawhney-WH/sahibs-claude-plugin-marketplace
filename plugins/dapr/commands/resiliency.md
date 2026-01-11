---
description: Analyze, apply, and test DAPR resiliency configurations including retry policies, circuit breakers, and timeouts
---

# DAPR Resiliency Manager

Manage resiliency configurations for your DAPR applications to ensure fault tolerance and graceful degradation.

## Behavior

When the user runs `/dapr:resiliency`:

### 1. Analyze Mode (Default)

Analyze the current resiliency configuration:

```
DAPR Resiliency Analysis
=========================

Configuration Files Found:
  ✓ resiliency.yaml (dapr.io/v1alpha1)
  ✓ components/statestore.yaml
  ✓ components/pubsub.yaml

Policy Analysis:
-----------------

Retry Policies (3 defined):
  ✓ serviceRetry
    - Type: exponential
    - Max Retries: 5
    - Max Interval: 30s
    Status: GOOD

  ⚠ stateStoreRetry
    - Type: constant
    - Duration: 500ms
    - Max Retries: 10
    Status: WARNING - Consider exponential backoff for production

  ✗ externalApiRetry
    - Type: constant
    - Duration: 100ms
    - Max Retries: 20
    Status: PROBLEM - Too aggressive, may cause rate limiting

Timeout Policies (2 defined):
  ✓ serviceTimeout: 30s (reasonable)
  ⚠ externalTimeout: 5s (may be too short for external APIs)

Circuit Breaker Policies (1 defined):
  ✓ serviceBreaker
    - Threshold: 5 consecutive failures
    - Recovery: 60s
    Status: GOOD

Missing Policies:
  ⚠ No circuit breaker for state store operations
  ⚠ No timeout policy for pub/sub

Target Coverage:
-----------------
  Apps: 2/3 covered (order-service, payment-service)
  Components: 1/2 covered (statestore)

  Uncovered:
    - notification-service (no resiliency)
    - pubsub (no policies)

Recommendations:
-----------------
1. Add circuit breaker for statestore to prevent cascade failures
2. Increase externalTimeout to 30s for third-party APIs
3. Change externalApiRetry to exponential backoff
4. Add resiliency policies for notification-service
```

### 2. Apply Mode

Apply a resiliency pattern to the project:

```
/dapr:resiliency apply --pattern microservices

Applying 'microservices' resiliency pattern...

Created: resiliency.yaml

Applied policies:
  ✓ serviceRetry (exponential, 5 retries, 30s max)
  ✓ serviceTimeout (30s)
  ✓ serviceCircuitBreaker (5 failures, 60s recovery)

Configured targets:
  ✓ All apps: serviceTimeout + serviceRetry + serviceCircuitBreaker
  ✓ statestore: stateStoreRetry + stateStoreCircuitBreaker
  ✓ pubsub: pubsubRetry

Next steps:
  1. Review resiliency.yaml and customize values
  2. Run 'dapr run' to test locally
  3. Use '/dapr:resiliency test' to validate behavior
```

### 3. Test Mode

Test resiliency policies with chaos injection:

```
/dapr:resiliency test --component statestore

Testing resiliency for 'statestore'...

Test 1: Retry Policy
---------------------
Injecting failures: 3 consecutive errors
Expected behavior: Retry and succeed on 4th attempt
Result: ✓ PASSED
  - Attempts: 4
  - Total time: 2.3s
  - Backoff observed: 500ms, 1s, 2s

Test 2: Circuit Breaker
-----------------------
Injecting failures: 6 consecutive errors
Expected behavior: Circuit opens after 5 failures
Result: ✓ PASSED
  - Failures before open: 5
  - Circuit state: OPEN
  - Rejections: 1

Test 3: Timeout
---------------
Injecting latency: 35s
Expected behavior: Timeout at 30s
Result: ✓ PASSED
  - Actual timeout: 30.1s

Test 4: Recovery
----------------
Waiting for circuit recovery: 60s
Expected behavior: Circuit moves to HALF-OPEN
Result: ✓ PASSED
  - Recovery time: 60s
  - State: HALF-OPEN
  - Test request: SUCCESS
  - Final state: CLOSED

Summary:
---------
All tests passed! Resiliency configuration is working correctly.
```

## Arguments

| Argument | Description |
|----------|-------------|
| `analyze` | Analyze current resiliency configuration (default) |
| `apply` | Apply a resiliency pattern |
| `test` | Test resiliency with chaos injection |
| `--pattern` | Pattern to apply (high-throughput, critical-service, external-api, microservices, event-driven, batch-processing) |
| `--target` | Target platform (local, aca, aks, kubernetes) |
| `--component` | Specific component to test |
| `--app` | Specific app to test |
| `--duration` | Test duration in seconds |
| `--output` | Output format (text, json, yaml) |

## Available Patterns

### 1. High-Throughput
Best for: APIs with high request volume, real-time systems
- Fast timeouts (5s)
- Minimal retries (2 attempts)
- Aggressive circuit breaker (3 failures)

### 2. Critical-Service
Best for: Payment processing, order management
- Long timeouts (120s)
- Aggressive retries (10 attempts)
- Conservative circuit breaker (10 failures)

### 3. External-API
Best for: Third-party integrations
- Extended timeouts (60s)
- Respectful retries with long backoff (5 min max)
- Rate-limit aware circuit breaker

### 4. Microservices (Default)
Best for: General service-to-service communication
- Balanced timeouts (30s)
- Standard retries (5 attempts)
- Standard circuit breaker (5 failures)

### 5. Event-Driven
Best for: Pub/sub, async processing
- At-least-once delivery retries
- Dead letter queue configuration
- Long timeout for handlers

### 6. Batch-Processing
Best for: ETL, data migration
- Very long timeouts (1 hour)
- Many retries (20 attempts)
- Slow circuit recovery (30 min)

## Examples

### Basic Analysis
```
/dapr:resiliency
```

### Apply Microservices Pattern
```
/dapr:resiliency apply --pattern microservices
```

### Apply for Azure Container Apps
```
/dapr:resiliency apply --pattern critical-service --target aca
```

### Test Specific Component
```
/dapr:resiliency test --component statestore --duration 120
```

### Test All Components
```
/dapr:resiliency test --duration 300
```

### Generate JSON Report
```
/dapr:resiliency analyze --output json > resiliency-report.json
```

## Azure Container Apps Integration

When `--target aca` is specified, the command generates ACA-compatible resiliency configuration:

```yaml
# ACA-specific resiliency (applied via az containerapp update)
properties:
  template:
    containers:
      - name: my-app
    scale:
      rules:
        - name: http-scale
          http:
            metadata:
              concurrentRequests: "100"
  configuration:
    dapr:
      enabled: true
      appId: my-app
      # Resiliency via DAPR component
```

## Resiliency Checklist

### Development
- [ ] Basic retry policy configured
- [ ] Reasonable timeouts set
- [ ] Test error scenarios manually

### Staging
- [ ] Circuit breakers enabled
- [ ] Retry policies tuned based on testing
- [ ] Chaos testing performed
- [ ] Monitoring configured

### Production
- [ ] All policies reviewed and approved
- [ ] Circuit breaker recovery tested
- [ ] SLOs defined for each service
- [ ] Alerts configured for circuit breaker trips
- [ ] Runbook for resiliency failures

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success / All tests passed |
| 1 | Analysis found issues |
| 2 | Tests failed |
| 3 | Configuration error |

## Related Commands

- `/dapr:security` - Security scanning
- `/dapr:component` - Component management
- `/dapr:test` - Integration testing
- `/dapr:deploy` - Deployment with resiliency validation
