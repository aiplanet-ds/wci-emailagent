# Azure Container Apps Deployment Guide

## Prerequisites

- Azure CLI installed (`az --version`)
- Docker installed
- Azure subscription

---

## Step 1: Create Azure Resources

```bash
# Login to Azure
az login

# Create resource group
az group create --name wci-rg --location eastus

# Create Container Registry
az acr create --resource-group wci-rg --name wciregistry --sku Basic
az acr update --name wciregistry --admin-enabled true

# Get ACR credentials
az acr credential show --name wciregistry
```

---

## Step 2: Create Azure PostgreSQL Database

```bash
# Create PostgreSQL server
az postgres flexible-server create \
  --resource-group wci-rg \
  --name wci-postgres-server \
  --admin-user wci_admin \
  --admin-password "YourStrongPassword123!" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 16 \
  --public-access 0.0.0.0

# Create database
az postgres flexible-server db create \
  --resource-group wci-rg \
  --server-name wci-postgres-server \
  --database-name wci_emailagent

# Allow Azure services
az postgres flexible-server firewall-rule create \
  --resource-group wci-rg \
  --name wci-postgres-server \
  --rule-name AllowAzureServices \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

---

## Step 3: Load and Push Docker Images

```bash
# Load images from tar files
docker load -i wci-emailagent-backend.tar
docker load -i wci-emailagent-frontend-aca.tar

# Login to ACR
az acr login --name wciregistry

# Tag images
docker tag wci-emailagent-backend:prod wciregistry.azurecr.io/wci-backend:prod
docker tag wci-emailagent-frontend-aca:prod wciregistry.azurecr.io/wci-frontend:prod

# Push to ACR
docker push wciregistry.azurecr.io/wci-backend:prod
docker push wciregistry.azurecr.io/wci-frontend:prod
```

---

## Step 4: Create Container Apps Environment

```bash
# Install Container Apps extension
az extension add --name containerapp --upgrade

# Register providers
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights

# Create Container Apps environment
az containerapp env create \
  --name wci-environment \
  --resource-group wci-rg \
  --location eastus
```

---

## Step 5: Deploy Backend Container App

```bash
az containerapp create \
  --name wci-backend \
  --resource-group wci-rg \
  --environment wci-environment \
  --image wciregistry.azurecr.io/wci-backend:prod \
  --registry-server wciregistry.azurecr.io \
  --registry-username <acr-username> \
  --registry-password <acr-password> \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 1 \
  --memory 2Gi \
  --env-vars \
    AZ_TENANT_ID=common \
    AZ_CLIENT_ID=<your-azure-client-id> \
    EPICOR_BASE_URL=<your-epicor-url> \
    EPICOR_COMPANY_ID=<your-company-id> \
    EPICOR_DEFAULT_PRICE_LIST=UNA1 \
    EPICOR_TOKEN_URL=https://login.epicor.com/connect/token \
    EPICOR_CLIENT_ID=<your-epicor-client-id> \
    AZURE_OPENAI_API_ENDPOINT=<your-openai-endpoint> \
    AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1 \
    AZURE_OPENAI_API_VERSION=2024-12-01-preview \
    VENDOR_VERIFICATION_ENABLED=true \
    VENDOR_CACHE_TTL_HOURS=24 \
    VENDOR_DOMAIN_MATCHING_ENABLED=true \
    MARGIN_THRESHOLD_CRITICAL=10.0 \
    MARGIN_THRESHOLD_HIGH=15.0 \
    MARGIN_THRESHOLD_MEDIUM=20.0 \
    DB_POOL_SIZE=20 \
    DB_MAX_OVERFLOW=10 \
    DB_ECHO=false \
    HOST=0.0.0.0 \
    PORT=8000 \
    RELOAD=false \
    CORS_ALLOWED_ORIGINS=* \
  --secrets \
    az-client-secret=<your-azure-client-secret> \
    epicor-api-key=<your-epicor-api-key> \
    epicor-client-secret=<your-epicor-client-secret> \
    openai-api-key=<your-openai-key> \
    session-secret=<your-session-secret> \
    database-url="postgresql+asyncpg://wci_admin:<password>@wci-postgres-server.postgres.database.azure.com:5432/wci_emailagent?sslmode=require" \
  --secret-env-vars \
    AZ_CLIENT_SECRET=az-client-secret \
    EPICOR_API_KEY=epicor-api-key \
    EPICOR_CLIENT_SECRET=epicor-client-secret \
    AZURE_OPENAI_API_KEY=openai-api-key \
    SESSION_SECRET=session-secret \
    DATABASE_URL=database-url \
  --command "sh -c 'alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000'"
```

**Get backend URL:**
```bash
az containerapp show --name wci-backend --resource-group wci-rg --query properties.configuration.ingress.fqdn -o tsv
```

---

## Step 6: Update CORS and Deploy Frontend

First, update backend CORS with the frontend URL (you'll get this after creating frontend):

```bash
# Get backend URL first
BACKEND_URL=$(az containerapp show --name wci-backend --resource-group wci-rg --query properties.configuration.ingress.fqdn -o tsv)
echo "Backend URL: https://$BACKEND_URL"

# Deploy frontend with backend URL
az containerapp create \
  --name wci-frontend \
  --resource-group wci-rg \
  --environment wci-environment \
  --image wciregistry.azurecr.io/wci-frontend:prod \
  --registry-server wciregistry.azurecr.io \
  --registry-username <acr-username> \
  --registry-password <acr-password> \
  --target-port 80 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 0.5 \
  --memory 1Gi \
  --env-vars \
    BACKEND_URL=https://$BACKEND_URL
```

**Get frontend URL:**
```bash
az containerapp show --name wci-frontend --resource-group wci-rg --query properties.configuration.ingress.fqdn -o tsv
```

---

## Step 7: Update Backend CORS (Recommended)

After frontend is deployed, restrict CORS to only allow the frontend URL:

```bash
FRONTEND_URL=$(az containerapp show --name wci-frontend --resource-group wci-rg --query properties.configuration.ingress.fqdn -o tsv)

az containerapp update \
  --name wci-backend \
  --resource-group wci-rg \
  --set-env-vars CORS_ALLOWED_ORIGINS=https://$FRONTEND_URL
```

> **Note:** We initially set `CORS_ALLOWED_ORIGINS=*` in Step 5 to allow the first deployment to work. This step tightens security by restricting CORS to only your frontend URL.

---

## Step 8: Verify Deployment

```bash
# Check backend status
az containerapp show --name wci-backend --resource-group wci-rg --query properties.runningStatus

# Check frontend status
az containerapp show --name wci-frontend --resource-group wci-rg --query properties.runningStatus

# View backend logs
az containerapp logs show --name wci-backend --resource-group wci-rg --follow

# View frontend logs
az containerapp logs show --name wci-frontend --resource-group wci-rg --follow
```

---

## Access Your Application

Frontend URL: `https://wci-frontend.<region>.azurecontainerapps.io`

---

## Common Commands

```bash
# Restart backend
az containerapp revision restart --name wci-backend --resource-group wci-rg

# Restart frontend
az containerapp revision restart --name wci-frontend --resource-group wci-rg

# Scale backend
az containerapp update --name wci-backend --resource-group wci-rg --min-replicas 2 --max-replicas 5

# Delete everything
az group delete --name wci-rg --yes
```

---

## Troubleshooting

### Container Won't Start
```bash
az containerapp logs show --name wci-backend --resource-group wci-rg --type system
```

### Database Connection Issues
1. Verify PostgreSQL firewall allows Azure services
2. Check DATABASE_URL includes `?sslmode=require`
3. Verify server name and credentials

### CORS Errors
1. Verify CORS_ALLOWED_ORIGINS includes frontend URL with `https://`
2. Check no trailing slash in the URL
