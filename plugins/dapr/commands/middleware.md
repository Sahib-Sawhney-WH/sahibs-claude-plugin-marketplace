# /dapr:middleware

Generate DAPR HTTP middleware components for API security and request processing.

## Description

Creates middleware component YAML and pipeline configuration for securing and processing HTTP requests. Supports OAuth2, OpenID Connect, OPA policies, rate limiting, WebAssembly, and circuit breakers.

## Usage

```
/dapr:middleware <type> <name> [options]
```

## Middleware Types

| Type | Description |
|------|-------------|
| `oauth2` | OAuth2 Authorization Code flow |
| `oauth2cc` | OAuth2 Client Credentials (service-to-service) |
| `bearer` | OpenID Connect Bearer Token validation |
| `opa` | Open Policy Agent policy enforcement |
| `ratelimit` | Rate limiting per second by IP |
| `wasm` | WebAssembly custom logic |
| `sentinel` | Circuit breaker and fault tolerance |
| `routeralias` | HTTP route aliasing |
| `routerchecker` | Route validation with regex |

## Arguments

| Argument | Description |
|----------|-------------|
| `<type>` | Middleware type (see table above) |
| `<name>` | Component name (lowercase, alphanumeric, hyphens) |

## Options

### OAuth2/Bearer Options
| Option | Description |
|--------|-------------|
| `--provider` | OAuth provider preset: `google`, `azure`, `auth0` |
| `--issuer` | Token issuer URL |
| `--audience` | Token audience (client ID) |
| `--scopes` | OAuth scopes (space-separated) |

### Rate Limiting Options
| Option | Description |
|--------|-------------|
| `--rate` | Max requests per second (default: 10) |

### OPA Options
| Option | Description |
|--------|-------------|
| `--policy` | Path to .rego policy file |
| `--default-status` | HTTP status on denial (default: 403) |

### WASM Options
| Option | Description |
|--------|-------------|
| `--url` | WASM binary URL (file://, http://, https://) |

### Pipeline Options
| Option | Description |
|--------|-------------|
| `--pipeline` | Pipeline type: `http` (incoming) or `app` (outgoing) |

## Examples

### OAuth2 with Google

```
/dapr:middleware oauth2 google-auth --provider google
```

Creates:
```yaml
# components/google-auth.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: google-auth
spec:
  type: middleware.http.oauth2
  version: v1
  metadata:
  - name: clientId
    secretKeyRef:
      name: oauth-secrets
      key: google-client-id
  - name: clientSecret
    secretKeyRef:
      name: oauth-secrets
      key: google-client-secret
  - name: scopes
    value: "openid profile email"
  - name: authURL
    value: "https://accounts.google.com/o/oauth2/v2/auth"
  - name: tokenURL
    value: "https://accounts.google.com/o/oauth2/token"
  - name: redirectURL
    value: "http://localhost:8080/callback"
  - name: authHeaderName
    value: "authorization"
```

### Bearer Token with Azure AD

```
/dapr:middleware bearer azure-auth --provider azure --audience my-api
```

Creates:
```yaml
# components/azure-auth.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: azure-auth
spec:
  type: middleware.http.bearer
  version: v1
  metadata:
  - name: audience
    value: "my-api"
  - name: issuer
    value: "https://login.microsoftonline.com/{tenant}/v2.0"
```

### Rate Limiting

```
/dapr:middleware ratelimit api-ratelimit --rate 100
```

Creates:
```yaml
# components/api-ratelimit.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: api-ratelimit
spec:
  type: middleware.http.ratelimit
  version: v1
  metadata:
  - name: maxRequestsPerSecond
    value: "100"
```

### OPA Policy

```
/dapr:middleware opa access-policy --policy policies/rbac.rego
```

Creates:
```yaml
# components/access-policy.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: access-policy
spec:
  type: middleware.http.opa
  version: v1
  metadata:
  - name: defaultStatus
    value: "403"
  - name: includedHeaders
    value: "Authorization, X-User-Role"
  - name: rego
    value: |
      package http
      default allow = false
      # Policy loaded from policies/rbac.rego
```

### Circuit Breaker (Sentinel)

```
/dapr:middleware sentinel circuit-breaker
```

Creates:
```yaml
# components/circuit-breaker.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: circuit-breaker
spec:
  type: middleware.http.sentinel
  version: v1
  metadata:
  - name: appName
    value: "my-app"
  - name: logDir
    value: "/var/log/sentinel"
  - name: flowRules
    value: |
      [
        {
          "resource": "POST:/api/orders",
          "threshold": 100,
          "tokenCalculateStrategy": 0,
          "controlBehavior": 0
        }
      ]
```

### Full Pipeline Configuration

After creating middleware components, configure the pipeline:

```
/dapr:middleware pipeline --http ratelimit,oauth2 --app bearer
```

Creates:
```yaml
# config/appconfig.yaml
apiVersion: dapr.io/v1alpha1
kind: Configuration
metadata:
  name: appconfig
spec:
  httpPipeline:
    handlers:
    - name: ratelimit
      type: middleware.http.ratelimit
    - name: oauth2
      type: middleware.http.oauth2
  appHttpPipeline:
    handlers:
    - name: bearer
      type: middleware.http.bearer
```

## Behavior

1. **Validate Input**
   - Check middleware type is valid
   - Validate name follows naming conventions
   - Verify required options for type

2. **Load Provider Preset** (if applicable)
   - Apply provider-specific URLs and settings
   - Configure recommended scopes

3. **Generate Component YAML**
   - Create component file in `components/` directory
   - Use secret references for sensitive values
   - Apply best practices for security

4. **Generate Pipeline Config** (if requested)
   - Create or update Configuration YAML
   - Add handlers in specified order

5. **Security Recommendations**
   - Remind about secret management
   - Suggest HTTPS enforcement
   - Recommend rate limiting

## Middleware Pipeline Flow

```
Request → Rate Limit → OAuth2/Bearer → OPA → User Code
Response ← Rate Limit ← OAuth2/Bearer ← OPA ← User Code
```

Middleware executes in order for requests, reverse order for responses.

## Best Practices

1. **Order Matters**: Rate limiting first, then authentication, then authorization
2. **Use Secrets**: Never store credentials in plain text
3. **HTTPS**: Enable `forceHTTPS: true` in production
4. **Path Filtering**: Use regex patterns to scope middleware to specific routes
5. **Rate Limits**: Consider per-sidecar limits (not cluster-wide)

## OAuth Provider Presets

### Google
- Auth URL: `https://accounts.google.com/o/oauth2/v2/auth`
- Token URL: `https://accounts.google.com/o/oauth2/token`
- Scopes: `openid profile email`

### Azure AD (Entra ID)
- Issuer: `https://login.microsoftonline.com/{tenant}/v2.0`
- Token URL: `https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token`

### Auth0
- Issuer: `https://{domain}.auth0.com/`
- Auth URL: `https://{domain}.auth0.com/authorize`
- Token URL: `https://{domain}.auth0.com/oauth/token`

## Related Commands

- `/dapr:component` - Generate other DAPR components
- `/dapr:security` - Scan for security issues in middleware configs
- `/dapr:status` - Check DAPR runtime status

## See Also

- [DAPR Middleware Documentation](https://docs.dapr.io/operations/components/middleware/)
- [OAuth2 Middleware](https://docs.dapr.io/reference/components-reference/supported-middleware/middleware-oauth2/)
- [OPA Middleware](https://docs.dapr.io/reference/components-reference/supported-middleware/middleware-opa/)
- [Rate Limit Middleware](https://docs.dapr.io/reference/components-reference/supported-middleware/middleware-rate-limit/)
