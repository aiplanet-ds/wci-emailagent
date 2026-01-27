# Manual Deployment Guide - Azure Container Apps

## Prerequisites

- Azure subscription
- Docker images: `wci-emailagent-backend.tar` and `wci-emailagent-frontend-aca.tar`
- Credentials for: Azure AD, Epicor, Azure OpenAI

---

## Step 1: Create Resource Group

1. Go to [Azure Portal](https://portal.azure.com)
2. Search **"Resource groups"** → Click **"Create"**
3. Fill in:
   - **Subscription:** Your subscription
   - **Resource group:** `wci-rg`
   - **Region:** `East US`
4. Click **"Review + create"** → **"Create"**

---

## Step 2: Create Azure Container Registry (ACR)

1. Search **"Container registries"** → Click **"Create"**
2. Fill in:
   - **Resource group:** `wci-rg`
   - **Registry name:** `wciregistry` (must be globally unique)
   - **Location:** `East US`
   - **SKU:** `Basic`
3. Click **"Review + create"** → **"Create"**
4. After created, go to the registry → **"Access keys"** (left menu)
5. Enable **"Admin user"**
6. **Copy and save:**
   - Login server: `wciregistry.azurecr.io`
   - Username: `wciregistry`
   - Password: (copy one of the passwords)

---

## Step 3: Create Azure Database for PostgreSQL

1. Search **"Azure Database for PostgreSQL flexible servers"** → Click **"Create"**
2. Fill in:
   - **Resource group:** `wci-rg`
   - **Server name:** `wci-postgres-server`
   - **Region:** `East US`
   - **PostgreSQL version:** `16`
   - **Workload type:** `Development` (cheapest)
   - **Compute + storage:** `Burstable, B1ms`
   - **Admin username:** `wci_admin`
   - **Password:** `YourStrongPassword123!`
3. **Networking tab:**
   - Connectivity method: `Public access`
   - Check: **"Allow public access from any Azure service"**
4. Click **"Review + create"** → **"Create"**
5. After created, go to the server → **"Databases"** (left menu)
6. Click **"+ Add"** → Name: `wci_emailagent` → **"Save"**

---

## Step 4: Push Docker Images to ACR

Run these commands on your local machine:

```bash
# Load images
docker load -i wci-emailagent-backend.tar
docker load -i wci-emailagent-frontend-aca.tar

# Login to ACR
docker login wciregistry.azurecr.io -u wciregistry -p <password-from-step-2>

# Tag images
docker tag wci-emailagent-backend:prod wciregistry.azurecr.io/wci-backend:prod
docker tag wci-emailagent-frontend-aca:prod wciregistry.azurecr.io/wci-frontend:prod

# Push images
docker push wciregistry.azurecr.io/wci-backend:prod
docker push wciregistry.azurecr.io/wci-frontend:prod
```

---

## Step 5: Create Container Apps Environment

1. Search **"Container Apps Environments"** → Click **"Create"**
2. Fill in:
   - **Resource group:** `wci-rg`
   - **Environment name:** `wci-environment`
   - **Region:** `East US`
3. **Monitoring tab:** Leave defaults
4. Click **"Review + create"** → **"Create"**

---

## Step 6: Deploy Backend Container App

1. Search **"Container Apps"** → Click **"Create"**

### Basics Tab
| Field | Value |
|-------|-------|
| Resource group | `wci-rg` |
| Container app name | `wci-backend` |
| Container Apps Environment | `wci-environment` |

### Container Tab
| Field | Value |
|-------|-------|
| Use quickstart image | **Uncheck** |
| Image source | `Azure Container Registry` |
| Registry | `wciregistry.azurecr.io` |
| Image | `wci-backend` |
| Image tag | `prod` |
| CPU | `1` |
| Memory | `2 Gi` |
| Command override | `sh -c 'alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000'` |

### Environment Variables (Backend)

**Regular Variables (Source: Manual):**

| Name | Value |
|------|-------|
| AZ_TENANT_ID | `common` |
| AZ_CLIENT_ID | `<your-azure-client-id>` |
| EPICOR_BASE_URL | `<your-epicor-url>` |
| EPICOR_COMPANY_ID | `<your-company-id>` |
| EPICOR_DEFAULT_PRICE_LIST | `UNA1` |
| EPICOR_TOKEN_URL | `https://login.epicor.com/connect/token` |
| EPICOR_CLIENT_ID | `<your-epicor-client-id>` |
| AZURE_OPENAI_API_ENDPOINT | `<your-openai-endpoint>` |
| AZURE_OPENAI_DEPLOYMENT_NAME | `gpt-4.1` |
| AZURE_OPENAI_API_VERSION | `2024-12-01-preview` |
| DB_POOL_SIZE | `20` |
| DB_MAX_OVERFLOW | `10` |
| DB_ECHO | `false` |
| VENDOR_VERIFICATION_ENABLED | `true` |
| VENDOR_CACHE_TTL_HOURS | `24` |
| VENDOR_DOMAIN_MATCHING_ENABLED | `true` |
| MARGIN_THRESHOLD_CRITICAL | `10.0` |
| MARGIN_THRESHOLD_HIGH | `15.0` |
| MARGIN_THRESHOLD_MEDIUM | `20.0` |
| CORS_ALLOWED_ORIGINS | `*` |
| HOST | `0.0.0.0` |
| PORT | `8000` |
| RELOAD | `false` |

**Secret Variables (Source: Secret):**

| Name | Value |
|------|-------|
| AZ_CLIENT_SECRET | `<your-azure-client-secret>` |
| EPICOR_API_KEY | `<your-epicor-api-key>` |
| EPICOR_CLIENT_SECRET | `<your-epicor-client-secret>` |
| AZURE_OPENAI_API_KEY | `<your-openai-key>` |
| SESSION_SECRET | `<generate-with-openssl-rand-hex-32>` |
| DATABASE_URL | `postgresql+asyncpg://wci_admin:YourStrongPassword123!@wci-postgres-server.postgres.database.azure.com:5432/wci_emailagent?ssl=require` |

### Ingress Tab
| Field | Value |
|-------|-------|
| Ingress | `Enabled` |
| Ingress traffic | `Accepting traffic from anywhere` |
| Ingress type | `HTTP` |
| Target port | `8000` |

5. Click **"Review + create"** → **"Create"**
6. **Copy the backend URL** from Overview page (e.g., `https://wci-backend.xxxx.eastus.azurecontainerapps.io`)

---

## Step 7: Deploy Frontend Container App

1. Search **"Container Apps"** → Click **"Create"**

### Basics Tab
| Field | Value |
|-------|-------|
| Resource group | `wci-rg` |
| Container app name | `wci-frontend` |
| Container Apps Environment | `wci-environment` |

### Container Tab
| Field | Value |
|-------|-------|
| Use quickstart image | **Uncheck** |
| Image source | `Azure Container Registry` |
| Registry | `wciregistry.azurecr.io` |
| Image | `wci-frontend` |
| Image tag | `prod` |
| CPU | `0.5` |
| Memory | `1 Gi` |

### Environment Variables (Frontend)

**Only ONE variable needed:**

| Name | Source | Value |
|------|--------|-------|
| BACKEND_URL | Manual | `https://wci-backend.xxxx.eastus.azurecontainerapps.io` (URL from Step 6) |

### Ingress Tab
| Field | Value |
|-------|-------|
| Ingress | `Enabled` |
| Ingress traffic | `Accepting traffic from anywhere` |
| Ingress type | `HTTP` |
| Target port | `80` |

5. Click **"Review + create"** → **"Create"**
6. **Copy the frontend URL** (e.g., `https://wci-frontend.xxxx.eastus.azurecontainerapps.io`)

---

## Step 8: Update Backend CORS

1. Go to **Container Apps** → **wci-backend**
2. Click **"Containers"** (left menu) → **"Edit and deploy"**
3. Click on the container → **"Environment variables"**
4. Find `CORS_ALLOWED_ORIGINS` and change value to:
   ```
   https://wci-frontend.xxxx.eastus.azurecontainerapps.io
   ```
   (Use your actual frontend URL from Step 7)
5. Click **"Save"** → **"Create"**

---

## Step 9: Verify Deployment

1. **Check backend health:**
   ```
   https://wci-backend.xxxx.eastus.azurecontainerapps.io/health
   ```

2. **Access the application:**
   ```
   https://wci-frontend.xxxx.eastus.azurecontainerapps.io
   ```

3. **View logs:** Container Apps → wci-backend → **"Log stream"**

---

## Troubleshooting

### Container Won't Start
- Go to Container Apps → Select app → **"Log stream"**
- Check for error messages

### Database Connection Failed
1. Verify PostgreSQL firewall allows Azure services
2. Check DATABASE_URL includes `?ssl=require`
3. Verify server name and password are correct

### CORS Errors
1. Verify `CORS_ALLOWED_ORIGINS` includes frontend URL with `https://`
2. Make sure there's no trailing slash

### 502 Bad Gateway
- Backend container is still starting
- Wait 1-2 minutes and refresh
- Check backend logs for errors

---

## Quick Reference: Environment Variables Summary

### Backend Container (wci-backend)
- 22 regular environment variables
- 6 secret environment variables
- **Does NOT have BACKEND_URL**

### Frontend Container (wci-frontend)
- Only 1 environment variable: `BACKEND_URL`
- Points to the backend Container App URL

---

## Common Commands

### View Logs
```bash
az containerapp logs show --name wci-backend --resource-group wci-rg --follow
```

### Restart Container
```bash
az containerapp revision restart --name wci-backend --resource-group wci-rg
```

### Delete Everything
```bash
az group delete --name wci-rg --yes
```
