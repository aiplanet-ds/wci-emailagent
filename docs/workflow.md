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
│  Step 1: Supplier Verification                                  │
│    ├─ VendorSvc: Lookup VendorNum from VendorID               │
│    └─ SupplierPartSvc: Verify supplier-part relationship       │
│                                                                 │
│  Step 2: Price List Management                                  │
│    ├─ PriceLstSvc: Query existing price list entries          │
│    └─ Create entry if not found (GetNewPriceLstParts)         │
│                                                                 │
│  Step 3: Price Update                                           │
│    ├─ Get current entry with all fields                        │
│    ├─ Update BasePrice and EffectiveDate                       │
│    └─ Call Update method with RowMod="U"                       │
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

### 4️⃣ **Price List Management Phase**

```
Query PriceLstSvc for part: "#FFH06-12SAE F"
                         ↓
    ┌─────────────────┴─────────────────┐
    │                                   │
✅ Entry Found                    ❌ Entry Not Found
    │                                   │
    │                          Create New Entry:
    │                          1. GetNewPriceLstParts
    │                          2. Fill template
    │                          3. Call Update (RowMod="A")
    │                                   │
    └─────────────────┬─────────────────┘
                      ↓
            Price list entry ready
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

#### **Price List Entry Creation**

```python
# Step 1: Get template
POST /Erp.BO.PriceLstSvc/GetNewPriceLstParts
Body: {
    "ds": {
        "PriceLst": [{"Company": "165122", "ListCode": "UNA1"}],
        "PriceLstParts": []
    },
    "listCode": "UNA1",
    "partNum": "#FFH06-12SAE F",
    "uomCode": "EA"
}
Response: {"parameters": {"ds": {"PriceLstParts": [template]}}}

# Step 2: Fill template and save
POST /Erp.BO.PriceLstSvc/Update
Body: {
    "ds": {
        "PriceLstParts": [{
            ...template_fields,
            "PartNum": "#FFH06-12SAE F",
            "BasePrice": 130.0,
            "EffectiveDate": "2025-10-20T00:00:00",
            "RowMod": "A"  // A = Add
        }]
    }
}
```

#### **Price Update**

```python
# Step 1: Get current entry
GET /Erp.BO.PriceLstSvc/PriceLstParts?$filter=ListCode eq 'UNA1' and PartNum eq '#FFH06-12SAE F' and UOMCode eq 'EA'
Response: {current_entry with all fields}

# Step 2: Update entry
POST /Erp.BO.PriceLstSvc/Update
Body: {
    "ds": {
        "PriceLstParts": [{
            ...current_entry,
            "BasePrice": 130.0,
            "EffectiveDate": "2025-10-20T00:00:00",
            "RowMod": "U"  // U = Update
        }]
    }
}
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
| Price list not found | Invalid ListCode | Use default list (UNA1) |
| Template creation failed | Missing parameters | Log error, skip product |
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

- **Email Polling Interval**: 60 seconds (configurable in `start.py`)
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
2. **Start the application**: `python start.py`
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

