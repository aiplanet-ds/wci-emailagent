# Azure Container Instances (ACI) Deployment Guide

## Prerequisites

- Azure CLI installed (`az --version`)
- Docker installed
- Azure subscription with permissions to create resources

## Files Required

- `wci-emailagent-backend.tar` - Backend Docker image
- `wci-emailagent-frontend-aci.tar` - Frontend Docker image (ACI version)
- `aci-deploy.yaml` - ACI deployment template

---

## Step 1: Create Azure Resources

### 1.1 Login to Azure
```bash
az login
```

### 1.2 Create Resource Group
```bash
az group create --name wci-rg --location eastus
```

### 1.3 Create Azure Container Registry (ACR)
```bash
# Create registry
az acr create --resource-group wci-rg --name wciregistry --sku Basic

# Enable admin access
az acr update --name wciregistry --admin-enabled true

# Get credentials (save these for aci-deploy.yaml)
az acr credential show --name wciregistry
```

### 1.4 Create Azure Database for PostgreSQL
```bash
# Create PostgreSQL server
az postgres flexible-server create \
  --resource-group wci-rg \
  --name wci-postgres-server \
  --admin-user wci_admin \
  --admin-password <YOUR-STRONG-PASSWORD> \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 16 \
  --public-access 0.0.0.0

# Create database
az postgres flexible-server db create \
  --resource-group wci-rg \
  --server-name wci-postgres-server \
  --database-name wci_emailagent

# Allow Azure services to connect
az postgres flexible-server firewall-rule create \
  --resource-group wci-rg \
  --name wci-postgres-server \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

---

## Step 2: Load and Push Docker Images

### 2.1 Load Images
```bash
docker load -i wci-emailagent-backend.tar
docker load -i wci-emailagent-frontend-aci.tar
```

### 2.2 Login to ACR
```bash
az acr login --name wciregistry
```

### 2.3 Tag Images for ACR
```bash
docker tag wci-emailagent-backend:prod wciregistry.azurecr.io/wci-backend:prod
docker tag wci-emailagent-frontend-aci:prod wciregistry.azurecr.io/wci-frontend:prod
```

### 2.4 Push Images to ACR
```bash
docker push wciregistry.azurecr.io/wci-backend:prod
docker push wciregistry.azurecr.io/wci-frontend:prod
```

---

## Step 3: Configure Deployment

### 3.1 Edit aci-deploy.yaml

Update all placeholder values in `aci-deploy.yaml`:

| Placeholder | Description |
|-------------|-------------|
| `<your-acr-name>` | Your ACR name (e.g., `wciregistry`) |
| `<acr-username>` | ACR admin username |
| `<acr-password>` | ACR admin password |
| `<your-azure-client-id>` | Azure AD App Registration client ID |
| `<your-azure-client-secret>` | Azure AD App Registration secret |
| `<your-epicor-url>` | Epicor API base URL |
| `<your-epicor-api-key>` | Epicor API key |
| `<your-company-id>` | Epicor company ID |
| `<your-epicor-client-id>` | Epicor OAuth client ID |
| `<your-epicor-client-secret>` | Epicor OAuth client secret |
| `<your-openai-key>` | Azure OpenAI API key |
| `<your-openai-endpoint>` | Azure OpenAI endpoint URL |
| `<db-user>` | PostgreSQL admin username |
| `<db-password>` | PostgreSQL admin password |
| `<server-name>` | PostgreSQL server name |

### 3.2 Generate Session Secret
```bash
openssl rand -hex 32
```

---

## Step 4: Deploy to ACI

```bash
az container create --resource-group wci-rg --file aci-deploy.yaml
```

---

## Step 5: Verify Deployment

### 5.1 Check Container Status
```bash
az container show --resource-group wci-rg --name wci-emailagent --query instanceView.state
```

### 5.2 Get Public URL
```bash
az container show --resource-group wci-rg --name wci-emailagent --query ipAddress.fqdn -o tsv
```

### 5.3 View Logs
```bash
# Backend logs
az container logs --resource-group wci-rg --name wci-emailagent --container-name backend

# Frontend logs
az container logs --resource-group wci-rg --name wci-emailagent --container-name frontend
```

---

## Step 6: Access Application

Your application will be available at:
```
http://wci-emailagent.eastus.azurecontainer.io
```

---

## Common Commands

### Restart Containers
```bash
az container restart --resource-group wci-rg --name wci-emailagent
```

### Stop Containers
```bash
az container stop --resource-group wci-rg --name wci-emailagent
```

### Start Containers
```bash
az container start --resource-group wci-rg --name wci-emailagent
```

### Delete Deployment
```bash
az container delete --resource-group wci-rg --name wci-emailagent --yes
```

### View Real-time Logs
```bash
az container attach --resource-group wci-rg --name wci-emailagent --container-name backend
```

---

## Troubleshooting

### Container Won't Start
```bash
# Check detailed status
az container show --resource-group wci-rg --name wci-emailagent

# Check events
az container show --resource-group wci-rg --name wci-emailagent --query "containers[].instanceView.events"
```

### Database Connection Issues
1. Verify PostgreSQL firewall allows Azure services
2. Check DATABASE_URL format includes `?sslmode=require`
3. Verify server name and credentials

### Image Pull Errors
1. Verify ACR credentials in aci-deploy.yaml
2. Check image names match exactly
3. Ensure ACR admin access is enabled

---

## Cost Optimization

ACI charges per second of container runtime. To reduce costs:
- Stop containers when not in use
- Use appropriate CPU/memory allocations
- Consider Azure App Service for always-on workloads
