---
description: Deploy DAPR application to Azure Container Apps or AKS with automatic configuration
---

# DAPR Azure Deployment

Deploy your DAPR application to Azure with production-ready configuration.

## Behavior

When the user runs `/dapr:deploy`:

1. **Select Deployment Target**
   - Azure Container Apps (recommended for most cases)
   - Azure Kubernetes Service (for advanced control)
   - Ask user preference if $ARGUMENTS doesn't specify

2. **Pre-Deployment Validation**
   - Verify Azure CLI is installed and logged in
   - Check DAPR configuration is valid
   - Validate Docker/container image exists
   - Ensure required Azure resources exist

3. **Container Apps Deployment**
   ```bash
   # Create environment if needed
   az containerapp env create \
     --name {env-name} \
     --resource-group {rg} \
     --dapr-instrumentation-key {key}

   # Deploy DAPR components
   az containerapp env dapr-component set \
     --name {env-name} \
     --resource-group {rg} \
     --dapr-component-name statestore \
     --yaml ./components/statestore.yaml

   # Deploy application
   az containerapp create \
     --name {app-name} \
     --resource-group {rg} \
     --environment {env-name} \
     --image {image} \
     --dapr-enabled \
     --dapr-app-id {app-id} \
     --dapr-app-port {port}
   ```

4. **AKS Deployment**
   ```bash
   # Ensure DAPR is installed on cluster
   dapr init -k

   # Apply components
   kubectl apply -f ./components/

   # Deploy application
   kubectl apply -f ./k8s/deployment.yaml
   ```

5. **Post-Deployment**
   - Verify deployment succeeded
   - Check DAPR sidecar is running
   - Test health endpoint
   - Display access URL

## Arguments

- `$ARGUMENTS` - Target and options:
  - `aca` or `container-apps` - Deploy to Azure Container Apps
  - `aks` or `kubernetes` - Deploy to AKS
  - `--rg {name}` - Resource group name
  - `--env {name}` - Container Apps environment name

## Examples

```
/dapr:deploy aca
/dapr:deploy aks --rg myapp-rg
/dapr:deploy container-apps --env production-env
```

## Prerequisites Checked

- [ ] Azure CLI installed (`az --version`)
- [ ] Logged into Azure (`az account show`)
- [ ] Docker image built and pushed to registry
- [ ] Azure resources exist (resource group, ACR, etc.)
- [ ] DAPR components configured

## Deployment Artifacts Generated

For Container Apps:
- Component YAML adapted for Container Apps format
- Managed identity configuration
- Scaling rules (KEDA)

For AKS:
- Kubernetes deployment YAML
- Service and ingress configuration
- DAPR component resources

## Error Handling

- Missing Azure CLI: Provide installation instructions
- Not logged in: Run `az login`
- Image not found: Prompt to build and push
- Resource group missing: Offer to create
- Component errors: Validate and fix YAML

## Post-Deployment Output

```
Deployment Complete!
=====================

Target:       Azure Container Apps
App Name:     order-service
App ID:       order-service
Environment:  production-env
Resource Group: myapp-rg

Endpoints:
  Application: https://order-service.bluewater-123.eastus.azurecontainerapps.io
  Health:      https://order-service.bluewater-123.eastus.azurecontainerapps.io/health

DAPR Components:
  ✓ statestore (Azure Cosmos DB)
  ✓ pubsub (Azure Service Bus)
  ✓ secretstore (Azure Key Vault)

Next Steps:
  - Monitor logs: az containerapp logs show -n order-service -g myapp-rg
  - Scale app: az containerapp update -n order-service --min-replicas 2 --max-replicas 10
  - Add custom domain: az containerapp hostname add ...
```
