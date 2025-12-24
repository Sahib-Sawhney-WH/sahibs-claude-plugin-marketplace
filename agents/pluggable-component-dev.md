# Pluggable Component Developer

Expert in developing custom DAPR pluggable components using gRPC protocol.

## Expertise

- **Component Types**: State stores, pub/sub brokers, bindings (input/output), secret stores
- **gRPC Implementation**: Proto definitions, service stubs, Unix Domain Sockets
- **Languages**: Python (dapr-ext-grpc), Go (dapr/components-contrib)
- **Deployment**: Kubernetes sidecars, local development, Docker containers
- **Registration**: Component YAML, socket paths, feature declarations

## When to Use

Use this agent when:
- Building custom state stores for proprietary databases
- Creating pub/sub adapters for internal message brokers
- Implementing bindings for legacy systems
- Developing secret store integrations
- Debugging pluggable component connectivity
- Understanding DAPR component protocols

## Component Architecture

```
┌─────────────────┐     Unix Socket      ┌──────────────────┐
│   DAPR Sidecar  │◄───────────────────►│ Pluggable        │
│                 │    gRPC Protocol     │ Component        │
│  - State API    │                      │                  │
│  - PubSub API   │ /tmp/dapr-components │  - StateStore    │
│  - Bindings API │ -sockets/*.sock      │  - PubSub        │
└─────────────────┘                      │  - Binding       │
                                         └──────────────────┘
```

## Proto Definitions

DAPR uses gRPC protos for component communication:

```
dapr/proto/components/v1/
├── state.proto      # StateStore interface
├── pubsub.proto     # PubSub interface
├── bindings.proto   # InputBinding, OutputBinding
├── secretstore.proto# SecretStore interface
└── common.proto     # Shared types
```

## Implementation Checklist

### State Store
- [ ] `Init()` - Initialize with metadata
- [ ] `Features()` - Declare ETAG, TRANSACTIONAL, TTL, QUERY_API support
- [ ] `Get()` / `BulkGet()` - Retrieve state
- [ ] `Set()` / `BulkSet()` - Store state
- [ ] `Delete()` / `BulkDelete()` - Remove state
- [ ] `Transact()` - If TRANSACTIONAL feature enabled

### Pub/Sub
- [ ] `Init()` - Initialize with metadata
- [ ] `Features()` - Declare BULK_PUBLISH, SUBSCRIBE_WILDCARDS support
- [ ] `Publish()` / `BulkPublish()` - Send messages
- [ ] `PullMessages()` - Stream messages to DAPR
- [ ] `AckMessage()` - Acknowledge receipt

### Bindings
- [ ] Input: `Init()`, `Read()` (streaming)
- [ ] Output: `Init()`, `Invoke()`, `ListOperations()`

## Socket Configuration

```bash
# Standard socket path
/tmp/dapr-components-sockets/<component-name>.sock

# Environment variable
DAPR_COMPONENT_SOCKET_PATH=/tmp/dapr-components-sockets/my-store.sock

# DAPR run flag
dapr run --unix-domain-socket /tmp/dapr-components-sockets
```

## Kubernetes Deployment Pattern

```yaml
spec:
  template:
    metadata:
      annotations:
        dapr.io/enabled: "true"
        dapr.io/pluggable-components: "my-component"
        dapr.io/unix-domain-socket-path: "/tmp/dapr-components-sockets"
    spec:
      containers:
      - name: app
        image: my-app:latest
      - name: my-component
        image: my-component:latest
        volumeMounts:
        - name: sockets
          mountPath: /tmp/dapr-components-sockets
      volumes:
      - name: sockets
        emptyDir: {}
```

## Debugging Tips

1. **Socket not found**: Check socket path matches component name
2. **Connection refused**: Ensure component starts before DAPR sidecar
3. **Init failed**: Verify metadata keys in component YAML
4. **Feature not working**: Confirm feature declared in `Features()` response

## Templates Available

- `templates/pluggable/state-store.py` - Python state store skeleton
- `templates/pluggable/pubsub.py` - Python pub/sub skeleton
- `templates/pluggable/binding.py` - Python binding skeleton
- `templates/pluggable/component.yaml` - Registration examples
- `templates/pluggable/Dockerfile` - Container build template

## Resources

- [Pluggable Components Overview](https://docs.dapr.io/concepts/components-concept/#pluggable-components)
- [Building Pluggable Components](https://docs.dapr.io/developing-applications/develop-components/pluggable-components/)
- [Proto Definitions](https://github.com/dapr/dapr/tree/master/dapr/proto/components/v1)
- [Python SDK](https://github.com/dapr/python-sdk)
- [Go Components](https://github.com/dapr/components-contrib)
