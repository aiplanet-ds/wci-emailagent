# WCI Email Agent - Application Workflow

## 📋 Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Complete Workflow](#complete-workflow)
- [Detailed Process Flow](#detailed-process-flow)
- [Error Handling](#error-handling)
- [Configuration](#configuration)

---

## 🎯 Overview

The WCI Email Agent is an automated system that monitors email inboxes for supplier price change notifications, extracts structured data using AI, and automatically updates prices in Epicor ERP with effective dates.

### Key Features
- ✅ **Automatic Email Monitoring** - Polls email every 60 seconds using Microsoft Graph API
- ✅ **AI-Powered Extraction** - Uses Azure OpenAI GPT-4 to extract structured price data
- ✅ **Supplier Verification** - Validates supplier-part relationships before updates
- ✅ **Automatic Price List Management** - Creates price list entries if they don't exist
- ✅ **Effective Date Support** - Updates prices with future effective dates
- ✅ **Multi-User Support** - OAuth authentication for multiple email accounts
- ✅ **Web Dashboard** - Professional UI for monitoring and management

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                    (FastAPI Web Dashboard)                      │
│                     http://localhost:8000                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AUTHENTICATION LAYER                         │
│              (Microsoft OAuth 2.0 + MSAL)                       │
│          - Token Management                                     │
│          - Multi-Account Support                                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EMAIL MONITORING SERVICE                     │
│              (Microsoft Graph API Delta Queries)                │
│          - Polls every 60 seconds                               │
│          - Detects new price change emails                      │
│          - Extracts email content                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AI EXTRACTION SERVICE                        │
│                  (Azure OpenAI GPT-4.1)                         │
│          - Identifies price change emails                       │
│          - Extracts structured JSON data                        │
│          - Preserves special characters in part numbers         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EPICOR ERP INTEGRATION                       │
│              (Epicor REST API v2 - OData)                       │
│                                                                 │
│  Step A: Supplier Verification                                  │
│    ├─ VendorSvc: Lookup VendorNum from VendorID               │
│    └─ SupplierPartSvc: Verify supplier-part relationship       │
│                                                                 │
│  Step B: Price List Management (SUPPLIER-SPECIFIC)              │
│    ├─ Get or create supplier price list (SUPPLIER_{id})       │
│    ├─ Check if part exists in supplier's price list           │
│    └─ Create part entry if needed (direct POST, RowMod="A")   │
│                                                                 │
│  Step C: Effective Date Management                              │
│    ├─ Update price list header StartDate                      │
│    └─ All parts in list inherit header effective date         │
│                                                                 │
│  Step D: Price Update                                           │
│    ├─ Get current part entry with all fields                  │
│    ├─ Update BasePrice                                         │
│    └─ POST to Update with RowMod="U"                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Complete Workflow

### 1️⃣ **Email Monitoring Phase**

```
User sends email → Microsoft 365 Inbox
                         ↓
            Delta Service polls every 60s
                         ↓
            New email detected via Graph API
                         ↓
            Email content extracted (subject, body, metadata)
```

### 2️⃣ **AI Extraction Phase**

```
Email content → Azure OpenAI GPT-4.1
                         ↓
            AI analyzes content and extracts:
            - Supplier ID (e.g., "FAST1")
            - Supplier Name
            - Part Numbers (with special chars: "#FFH06-12SAE F")
            - Old Prices
            - New Prices
            - Effective Date
            - Change Type
                         ↓
            Returns structured JSON
                         ↓
            Saved to: price_change_{message_id}.json
```

### 3️⃣ **Supplier Verification Phase**

```
For each product in extracted data:
                         ↓
Step 1: Lookup Vendor
    VendorSvc query: VendorID = "FAST1"
    Returns: VendorNum = 204
                         ↓
Step 2: Verify Supplier-Part Link
    SupplierPartSvc query:
    - VendorNum = 204
    - PartNum = "#FFH06-12SAE F"
                         ↓
    ✅ Verified: Supplier can supply this part
    ❌ Failed: Skip this product (log warning)
```

### 4️⃣ **Price List Management Phase (Supplier-Specific)**

```
Step 1: Get or create supplier price list
    Check for SUPPLIER_{supplier_id} (e.g., SUPPLIER_FAST1)
                         ↓
    ┌─────────────────┴─────────────────┐
    │                                   │
✅ List Exists                    ❌ List Not Found
    │                                   │
    │                          Create Price List Header:
    │                          - ListCode: SUPPLIER_FAST1
    │                          - Description: "Price List for..."
    │                          - StartDate: effective_date
    │                          - RowMod: "A"
    │                                   │
    └─────────────────┬─────────────────┘
                      ↓
Step 2: Check if part exists in supplier's price list
                         ↓
    ┌─────────────────┴─────────────────┐
    │                                   │
✅ Part Entry Found              ❌ Part Entry Not Found
    │                                   │
    │                          Create Part Entry (Direct):
    │                          - Company, ListCode, PartNum
    │                          - UOMCode, BasePrice
    │                          - RowMod: "A" (No template needed)
    │                                   │
    └─────────────────┬─────────────────┘
                      ↓
Step 3: Update header effective date (all parts inherit)
                      ↓
            Price list ready for update
```

### 5️⃣ **Price Update Phase**

```
Get current price list entry
    (includes all required fields)
                         ↓
Modify entry:
    - BasePrice = new_price
    - EffectiveDate = "2025-10-20T00:00:00"
    - RowMod = "U" (Update)
                         ↓
Build dataset structure:
    {
        "ds": {
            "PriceLst": [],
            "PriceLstParts": [modified_entry]
        }
    }
                         ↓
Call PriceLstSvc/Update method
                         ↓
    ✅ Success: Price updated with effective date
    ❌ Failed: Log error and continue to next product
```

### 6️⃣ **Results Phase**

```
Batch update complete
                         ↓
Generate summary:
    - ✅ Successful updates
    - ❌ Failed updates
    - ⏭️ Skipped products
                         ↓
Save results to: epicor_update_{message_id}.json
                         ↓
Display in web dashboard
```

---

## 📊 Detailed Process Flow

### Email Processing Flow

```python
# 1. Email Detection
delta_service.check_for_new_emails()
    → Returns list of new emails matching criteria
    → Filters for price change keywords

# 2. Content Extraction
email_content = get_email_body(message_id)
metadata = {
    "subject": "Price Change Notification",
    "from": "supplier@example.com",
    "date": "2025-10-15T08:45:20Z",
    "message_id": "AQMkAD..."
}

# 3. AI Extraction
extracted_data = extract_price_change_json(email_content, metadata)
    → Returns structured JSON with supplier info and products

# 4. Epicor Update
results = epicor_service.update_supplier_part_prices_batch(
    supplier_id="FAST1",
    products=[...],
    effective_date="2025-10-20"
)
```

### Epicor API Workflow

#### **Supplier Verification (2-Step Lookup)**

```python
# Step 1: Get VendorNum from VendorID
GET /Erp.BO.VendorSvc/Vendors?$filter=VendorID eq 'FAST1'
Response: {"VendorNum": 204, "Name": "Faster Inc. (Indiana)"}

# Step 2: Verify Supplier-Part Relationship
GET /Erp.BO.SupplierPartSvc/SupplierParts?$filter=VendorNum eq 204 and PartNum eq '#FFH06-12SAE F'
Response: {"VendorNum": 204, "PartNum": "#FFH06-12SAE F", ...}
```

#### **Supplier-Specific Price List Creation**

```python
# Step 1: Check if supplier price list exists
GET /Erp.BO.PriceLstSvc/PriceLsts?$filter=ListCode eq 'SUPPLIER_FAST1'
Response: {"value": []} or {"value": [price_list_header]}

# Step 2: Create price list header if needed
POST /Erp.BO.PriceLstSvc/Update
Body: {
    "ds": {
        "PriceLst": [{
            "Company": "165122",
            "ListCode": "SUPPLIER_FAST1",
            "ListDescription": "Price List for Faster Inc.",
            "StartDate": "2025-10-20T00:00:00",
            "Active": true,
            "CurrencyCode": "USD",
            "RowMod": "A"  // A = Add (create)
        }]
    }
}

# Step 3: Create part entry (Direct POST - No template needed)
POST /Erp.BO.PriceLstSvc/Update
Body: {
    "ds": {
        "PriceLstParts": [{
            "Company": "165122",
            "ListCode": "SUPPLIER_FAST1",
            "PartNum": "#FFH06-12SAE F",
            "UOMCode": "EA",
            "BasePrice": 130.0,
            "RowMod": "A"  // A = Add (create)
        }]
    }
}
// Note: Effective date inherited from header StartDate
```

#### **Effective Date and Price Update**

```python
# Step 1: Update price list header with effective date (affects all parts)
GET /Erp.BO.PriceLstSvc/PriceLsts?$filter=ListCode eq 'SUPPLIER_FAST1'
Response: {price_list_header}

POST /Erp.BO.PriceLstSvc/Update
Body: {
    "ds": {
        "PriceLst": [{
            ...price_list_header,
            "StartDate": "2025-10-20T00:00:00",
            "RowMod": "U"  // U = Update
        }]
    }
}

# Step 2: Update part price (inherits effective date from header)
GET /Erp.BO.PriceLstSvc/PriceLstParts?$filter=ListCode eq 'SUPPLIER_FAST1' and PartNum eq '#FFH06-12SAE F' and UOMCode eq 'EA'
Response: {current_entry with all fields}

POST /Erp.BO.PriceLstSvc/Update
Body: {
    "ds": {
        "PriceLstParts": [{
            ...current_entry,
            "BasePrice": 130.0,
            "RowMod": "U"  // U = Update
        }]
    }
}
// Note: Effective date managed at header level, not part level
```

---

## ⚠️ Error Handling

### Supplier Verification Errors

| Error | Cause | Action |
|-------|-------|--------|
| Vendor not found | Invalid Supplier ID | Skip product, log warning |
| Supplier-part not linked | Part not set up for supplier | Skip product, log warning |
| API timeout | Network/server issue | Retry with exponential backoff |

### Price List Errors

| Error | Cause | Action |
|-------|-------|--------|
| Price list creation failed | Missing Company ID or invalid data | Log error, skip product |
| Part entry creation failed | Missing required fields | Log error, skip product |
| Header update failed | Invalid date format | Log warning, continue with price update |
| Update failed | Validation error | Log detailed error, continue |

### AI Extraction Errors

| Error | Cause | Action |
|-------|-------|--------|
| JSON parse error | AI returned non-JSON | Strip markdown, retry parse |
| Missing required fields | Incomplete email | Log warning, use defaults |
| Token expired | Azure OpenAI auth issue | Refresh token, retry |

---

## ⚙️ Configuration

### Environment Variables

```env
# Azure OpenAI
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_API_ENDPOINT=https://your-endpoint.openai.azure.com
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4.1
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# Epicor ERP
EPICOR_BASE_URL=https://your-instance.epicorsaas.com/api/v2/odata
EPICOR_COMPANY_ID=165122
EPICOR_API_KEY=your_api_key
EPICOR_BEARER_TOKEN=your_bearer_token
EPICOR_DEFAULT_PRICE_LIST=UNA1

# Microsoft Graph API
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret
AZURE_TENANT_ID=your_tenant_id
REDIRECT_URI=http://localhost:8000/callback
```

### Key Configuration Options

- **Email Polling Interval**: 60 seconds (configurable in `main.py`)
- **Default Price List**: UNA1 (Unassigned Bill-To)
- **Default UOM**: EA (Each)
- **AI Temperature**: 0 (deterministic extraction)
- **Request Timeout**: 10 seconds

---

## 🎯 Success Criteria

A successful price update requires:

1. ✅ Email contains price change keywords
2. ✅ AI successfully extracts structured data
3. ✅ Supplier ID exists in Epicor (VendorSvc)
4. ✅ Supplier-part relationship exists (SupplierPartSvc)
5. ✅ Part exists in price list (or can be created)
6. ✅ Price update succeeds with effective date

---

## 📝 Example Email Format

```
Subject: Price Change Notification - Effective October 2025

SUPPLIER INFORMATION:
Supplier ID: FAST1
Supplier Name: Faster Inc. (Indiana)

PRICE CHANGE DETAILS:

Product #1:
  Product Name: Hydraulic Fitting SAE Standard
  Part Number: #FFH06-12SAE F
  Old Price: $190.00
  New Price: $130.00
  Effective Date: 2025-10-20

EFFECTIVE DATE: October 20, 2025
```

---

## 🚀 Getting Started

1. **Configure environment variables** in `.env`
2. **Start the application**: `python main.py`
3. **Login via OAuth**: Navigate to `http://localhost:8000`
4. **Send test email** to monitored inbox
5. **Monitor dashboard** for automatic processing

---

## 📚 Related Documentation

- [API Documentation](api.md) - Detailed API reference
- [Setup Guide](setup.md) - Installation and configuration
- [Troubleshooting](troubleshooting.md) - Common issues and solutions
- [Epicor Integration](epicor-integration.md) - Epicor API details

---

**Last Updated**: 2025-10-15  
**Version**: 1.0.0

