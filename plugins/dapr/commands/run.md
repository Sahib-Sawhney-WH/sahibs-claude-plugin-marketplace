---
description: Run a DAPR application locally with sidecar injection and component loading
---

# DAPR Local Run

Run your DAPR application locally with the DAPR sidecar for development and testing.

## Behavior

When the user runs `/dapr:run`:

1. **Detect Application**
   - Find dapr.yaml in current directory or $ARGUMENTS path
   - Identify application entry point (main.py, app.py, etc.)
   - Detect framework (FastAPI, Flask, gRPC)

2. **Validate Environment**
   - Check DAPR CLI installation
   - Verify DAPR runtime is initialized (`dapr init`)
   - Ensure components/ directory exists
   - Validate component YAML files

3. **Configure Run**
   - Set app-id from dapr.yaml or directory name
   - Configure app-port based on framework detection
   - Load components from local directory
   - Enable debug logging if requested

4. **Execute DAPR Run**
   ```bash
   dapr run \
     --app-id {app_id} \
     --app-port {port} \
     --dapr-http-port 3500 \
     --components-path ./components \
     --log-level debug \
     -- python src/main.py
   ```

5. **Monitor Output**
   - Stream application logs
   - Show DAPR sidecar logs
   - Display service endpoints
   - Watch for errors and suggest fixes

## Arguments

- `$ARGUMENTS` - Optional path to application or specific run options

## Options Detection

Parse $ARGUMENTS for:
- `--debug` - Enable verbose logging
- `--port {n}` - Override application port
- `--config {path}` - Use specific config file
- `--hot-reload` - Enable file watching (if supported)

## Examples

```
/dapr:run
/dapr:run ./services/order-service
/dapr:run --debug --port 8080
```

## Troubleshooting

If the run fails, automatically check:
1. Is DAPR installed? → Suggest `dapr init`
2. Port conflict? → Find available port
3. Component error? → Validate YAML syntax
4. Python error? → Check requirements installed
5. Missing dependencies? → Run `pip install -r requirements.txt`

## Multi-Service Support

For multi-service projects (detected via dapr.yaml services section):
- Offer to run specific service or all services
- Use `dapr run -f dapr.yaml` for multi-app mode
- Display all service endpoints

## Output

Show clear status:
```
DAPR Application Started
========================
App ID:       order-service
App Port:     8000
DAPR Port:    3500
Dashboard:    http://localhost:8080

Endpoints:
  HTTP:   http://localhost:8000
  DAPR:   http://localhost:3500/v1.0/invoke/order-service/method/

Press Ctrl+C to stop
```
