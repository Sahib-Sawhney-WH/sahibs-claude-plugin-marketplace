---
description: Generate CI/CD pipelines for DAPR applications (GitHub Actions, Azure DevOps)
---

# DAPR CI/CD Generator

Generate production-ready CI/CD pipelines for your DAPR application.

## Behavior

When the user runs `/dapr:cicd`:

1. **Detect Project Structure**
   - Identify main application file
   - Find test directories
   - Locate component YAML files
   - Detect Dockerfile

2. **Generate CI Pipeline**
   - Linting and type checking
   - Unit tests with coverage
   - DAPR configuration validation
   - Security scanning
   - Container build

3. **Generate CD Pipeline**
   - Staging deployment
   - Health checks
   - Production deployment (blue-green)
   - Rollback on failure

## Arguments

| Argument | Description |
|----------|-------------|
| `github` | Generate GitHub Actions workflows (default) |
| `azure-devops` | Generate Azure DevOps pipelines |
| `--target aca` | Target Azure Container Apps |
| `--target aks` | Target Azure Kubernetes Service |

## Examples

### GitHub Actions for Container Apps
```
/dapr:cicd github --target aca
```

### Azure DevOps for AKS
```
/dapr:cicd azure-devops --target aks
```

## Generated Files

### GitHub Actions
```
.github/
└── workflows/
    ├── ci.yml           # Build, test, validate
    ├── cd-aca.yml       # Deploy to Container Apps
    └── cd-aks.yml       # Deploy to AKS
```

### Azure DevOps
```
azure-pipelines/
├── azure-pipelines.yml  # Main pipeline
├── templates/
│   ├── build.yml        # Build template
│   ├── test.yml         # Test template
│   └── deploy.yml       # Deploy template
└── variables/
    ├── staging.yml      # Staging variables
    └── production.yml   # Production variables
```

## Pipeline Features

### CI Pipeline
- Ruff linting and MyPy type checking
- Unit tests with pytest and coverage
- DAPR configuration validation
- Security scanning with Trivy
- Container image build and push

### CD Pipeline
- Environment-based deployments
- Blue-green deployment strategy
- Health check verification
- Automatic rollback on failure
- DAPR component updates

## Required Secrets

### GitHub Actions
| Secret | Description |
|--------|-------------|
| `AZURE_CREDENTIALS` | Azure service principal JSON |
| `AZURE_RESOURCE_GROUP` | Resource group name |
| `AZURE_CONTAINER_REGISTRY` | ACR name |
| `CONTAINER_APP_NAME` | Container Apps name |

### Azure DevOps
| Variable | Description |
|----------|-------------|
| `azureSubscription` | Azure service connection |
| `resourceGroup` | Resource group name |
| `containerRegistry` | ACR name |
| `appName` | Application name |
