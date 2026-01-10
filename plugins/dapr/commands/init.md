---
description: Initialize a new DAPR project with Python SDK, components, and Azure-ready configuration
---

# DAPR Project Initialization

Initialize a new DAPR-enabled Python microservices project with best practices configuration.

## Behavior

When the user runs `/dapr:init`:

1. **Gather Project Info**
   - Ask for project name if not provided in $ARGUMENTS
   - Ask for project type: microservice, workflow, or actor
   - Ask for Azure integration preferences (Container Apps, AKS, or local only)

2. **Create Project Structure**
   ```
   {project_name}/
   ├── src/
   │   └── main.py              # Main application entry
   ├── components/
   │   ├── statestore.yaml      # State management component
   │   ├── pubsub.yaml          # Pub/Sub component
   │   └── secrets.yaml         # Secrets component
   ├── dapr.yaml                # DAPR configuration
   ├── requirements.txt         # Python dependencies
   ├── Dockerfile               # Container image
   └── README.md                # Project documentation
   ```

3. **Install Dependencies**
   - dapr (core SDK)
   - dapr-ext-fastapi or dapr-ext-grpc (based on choice)
   - dapr-ext-workflow (if workflow project)

4. **Configure Components**
   - Set up local Redis for state/pubsub (development)
   - Prepare Azure component templates (production)
   - Configure secrets management

5. **Validate Setup**
   - Check DAPR CLI is installed (`dapr --version`)
   - Verify Python environment
   - Run initial health check

## Arguments

- `$ARGUMENTS` - Project name (optional, will prompt if not provided)

## Examples

```
/dapr:init my-order-service
/dapr:init payment-workflow --type workflow
/dapr:init inventory-actor --type actor --azure
```

## Best Practices Applied

- Uses FastAPI for HTTP endpoints (modern async Python)
- Configures health endpoints for Kubernetes readiness/liveness
- Sets up structured logging with correlation IDs
- Includes OpenTelemetry tracing setup
- Prepares multi-stage Dockerfile for optimized images
- Includes .env.example for local development

## Post-Initialization

After initialization, suggest:
1. Run `dapr init` if DAPR runtime not installed
2. Start with `dapr run --app-id {app_name} -- python src/main.py`
3. Review component configurations for production
