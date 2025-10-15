# Verification Guide - Epicor Swagger Documentation

## 📋 Table of Contents
- [Overview](#overview)
- [Accessing Swagger Documentation](#accessing-swagger-documentation)
- [Complete Verification Workflow](#complete-verification-workflow)
- [Query Examples](#query-examples)
- [Troubleshooting](#troubleshooting)
- [Quick Reference](#quick-reference)

---

## 🎯 Overview

This guide explains how to verify that price changes have been successfully applied in Epicor ERP using the Swagger API documentation. You'll learn how to check:

- ✅ **Supplier Information** - Verify supplier exists and details are correct
- ✅ **Supplier-Part Relationships** - Confirm supplier can supply the part
- ✅ **Price Changes** - Check that prices were updated correctly
- ✅ **Effective Dates** - Verify effective dates are set properly

---

## 🌐 Accessing Swagger Documentation

### **Swagger UI URL**

```
https://centralusdtadtl26.epicorsaas.com/saas5393third/api/v2/swagger/ui/index
```

Replace with your Epicor instance URL if different.

### **Authentication Setup**

1. Click the **"Authorize"** button (🔒 icon) in Swagger UI
2. Enter your credentials:
   - **API Key**: Your `X-API-Key` value
   - **Bearer Token**: Your authentication token
3. Click **"Authorize"** then **"Close"**

### **OData Metadata (Optional)**

To explore all available fields and entities:
```
https://centralusdtadtl26.epicorsaas.com/saas5393third/api/v2/odata/165122/$metadata
```

---

## 🔄 Complete Verification Workflow

### **Step 1: Verify Supplier Information** 🏢

**Purpose**: Confirm the supplier exists in Epicor and get their internal VendorNum.

#### **Endpoint**
```
GET /Erp.BO.VendorSvc/Vendors
```

#### **Filter Query**
```
VendorID eq 'FAST1'
```

#### **In Swagger UI:**
1. Navigate to: **`Erp.BO.VendorSvc`** section
2. Find: **`GET /Vendors`** endpoint
3. Click **"Try it out"**
4. In the **`$filter`** parameter field, enter:
   ```
   VendorID eq 'FAST1'
   ```
5. Click **"Execute"**

#### **Expected Response:**
```json
{
  "value": [
    {
      "Company": "165122",
      "VendorNum": 204,                    // ✅ Internal vendor number
      "VendorID": "FAST1",                 // ✅ External supplier ID
      "Name": "Faster Inc. (Indiana)",     // ✅ Supplier name
      "Address1": "123 Main St",
      "City": "Indianapolis",
      "State": "IN",
      "Country": "USA",
      "EmailAddress": "contact@faster.com",
      "PhoneNum": "555-1234",
      "VendorNumVendorID": "FAST1",
      "Active": true
    }
  ]
}
```

#### **What to Verify:**
- ✅ `VendorID` matches your supplier ID (e.g., "FAST1")
- ✅ `VendorNum` is returned (you'll need this for next step)
- ✅ `Name` matches expected supplier name
- ✅ `Active` is `true`

---

### **Step 2: Verify Supplier-Part Relationship** 🔗

**Purpose**: Confirm the supplier is authorized to supply this specific part.

#### **Endpoint**
```
GET /Erp.BO.SupplierPartSvc/SupplierParts
```

#### **Filter Query**
```
VendorNum eq 204 and PartNum eq '#FFH06-12SAE F'
```

#### **In Swagger UI:**
1. Navigate to: **`Erp.BO.SupplierPartSvc`** section
2. Find: **`GET /SupplierParts`** endpoint
3. Click **"Try it out"**
4. In the **`$filter`** parameter field, enter:
   ```
   VendorNum eq 204 and PartNum eq '#FFH06-12SAE F'
   ```
   *(Replace `204` with the VendorNum from Step 1)*
5. Click **"Execute"**

#### **Expected Response:**
```json
{
  "value": [
    {
      "Company": "165122",
      "VendorNum": 204,                    // ✅ Matches supplier
      "PartNum": "#FFH06-12SAE F",         // ✅ Part number
      "VendorVendorID": "FAST1",           // ✅ Supplier ID
      "VendorName": "Faster Inc. (Indiana)",
      "OpCode": "BUY",
      "PurchasingFactor": 1,
      "LeadTime": 5,
      "MinimumPrice": 0,
      "SysRowID": "..."
    }
  ]
}
```

#### **What to Verify:**
- ✅ `VendorNum` matches the supplier's internal number
- ✅ `PartNum` matches exactly (including special characters like `#`)
- ✅ `VendorVendorID` matches the external supplier ID
- ✅ Record exists (not empty array)

---

### **Step 3: Check Price List Entry** 💰

**Purpose**: Verify the price was updated with the correct value and effective date.

#### **Endpoint**
```
GET /Erp.BO.PriceLstSvc/PriceLstParts
```

#### **Filter Query**
```
ListCode eq 'UNA1' and PartNum eq '#FFH06-12SAE F' and UOMCode eq 'EA'
```

#### **In Swagger UI:**
1. Navigate to: **`Erp.BO.PriceLstSvc`** section
2. Find: **`GET /PriceLstParts`** endpoint
3. Click **"Try it out"**
4. In the **`$filter`** parameter field, enter:
   ```
   ListCode eq 'UNA1' and PartNum eq '#FFH06-12SAE F' and UOMCode eq 'EA'
   ```
5. Click **"Execute"**

#### **Expected Response:**
```json
{
  "value": [
    {
      "Company": "165122",
      "ListCode": "UNA1",                  // ✅ Price list code
      "PartNum": "#FFH06-12SAE F",         // ✅ Part number
      "UOMCode": "EA",                     // ✅ Unit of measure
      "BasePrice": 130.0,                  // ✅ NEW PRICE (was 190.0)
      "EffectiveDate": "2025-10-20T00:00:00",  // ✅ EFFECTIVE DATE
      "EndDate": null,
      "LastUpdated": "2025-10-15T08:50:23",    // ✅ Recent timestamp
      "PricePer": 1,
      "DiscountPercent": 0,
      "SysRevID": 123456,
      "SysRowID": "..."
    }
  ]
}
```

#### **What to Verify:**
- ✅ `BasePrice` matches your new price (e.g., 130.0)
- ✅ `EffectiveDate` matches your target date (e.g., "2025-10-20T00:00:00")
- ✅ `LastUpdated` shows a recent timestamp
- ✅ `ListCode` is correct (default: "UNA1")
- ✅ `UOMCode` is correct (default: "EA")

---

### **Step 4: View All Price Lists for Part** 📊

**Purpose**: See the part across all price lists and check for multiple entries.

#### **Filter Query**
```
PartNum eq '#FFH06-12SAE F'
```

#### **In Swagger UI:**
1. Same endpoint: **`GET /Erp.BO.PriceLstSvc/PriceLstParts`**
2. In the **`$filter`** parameter field, enter:
   ```
   PartNum eq '#FFH06-12SAE F'
   ```
3. Optionally add **`$orderby`**: `EffectiveDate desc`
4. Click **"Execute"**

#### **Expected Response:**
```json
{
  "value": [
    {
      "ListCode": "UNA1",
      "PartNum": "#FFH06-12SAE F",
      "BasePrice": 130.0,
      "EffectiveDate": "2025-10-20T00:00:00"
    },
    {
      "ListCode": "AMV",
      "PartNum": "#FFH06-12SAE F",
      "BasePrice": 125.0,
      "EffectiveDate": "2025-09-01T00:00:00"
    }
  ]
}
```

This shows the part in **all price lists** with their respective prices and dates.

---

## 📝 Query Examples

### **Example 1: Clean Output with $select**

Get only the fields you need:

```
GET /Erp.BO.PriceLstSvc/PriceLstParts?$filter=PartNum eq '#FFH06-12SAE F'&$select=ListCode,PartNum,UOMCode,BasePrice,EffectiveDate,LastUpdated
```

**Response:**
```json
{
  "value": [
    {
      "ListCode": "UNA1",
      "PartNum": "#FFH06-12SAE F",
      "UOMCode": "EA",
      "BasePrice": 130.0,
      "EffectiveDate": "2025-10-20T00:00:00",
      "LastUpdated": "2025-10-15T08:50:23"
    }
  ]
}
```

---

### **Example 2: Sort by Effective Date**

See price changes in chronological order:

```
GET /Erp.BO.PriceLstSvc/PriceLstParts?$filter=PartNum eq '#FFH06-12SAE F'&$orderby=EffectiveDate desc
```

Shows most recent effective date first.

---

### **Example 3: Limit Results with $top**

Get only the first 10 results:

```
GET /Erp.BO.PriceLstSvc/PriceLstParts?$filter=PartNum eq '#FFH06-12SAE F'&$top=10
```

---

### **Example 4: Expand Related Data**

Get supplier-part info with vendor details:

```
GET /Erp.BO.SupplierPartSvc/SupplierParts?$filter=VendorNum eq 204&$expand=Vendor
```

Includes full vendor record in the response.

---

## ⚠️ Troubleshooting

### **Issue: Empty Response (No Results)**

**Possible Causes:**
1. Part number doesn't match exactly (check special characters like `#`, spaces)
2. Wrong price list code (try querying without `ListCode` filter)
3. Part not in any price list yet
4. Wrong company ID in the URL

**Solution:**
- Try broader query: `$filter=PartNum eq '#FFH06-12SAE F'` (without ListCode)
- Check part number spelling and special characters
- Verify you're using the correct company ID (165122)

---

### **Issue: 400 Bad Request Error**

**Possible Causes:**
1. Invalid OData syntax in filter
2. Special characters not properly handled
3. Field name typo

**Solution:**
- Check filter syntax: `Field eq 'Value'` (use single quotes for strings)
- For special characters, Swagger UI handles encoding automatically
- Verify field names match exactly (case-sensitive)

---

### **Issue: 401 Unauthorized Error**

**Possible Causes:**
1. Bearer token expired
2. API key missing or invalid
3. Not authorized in Swagger UI

**Solution:**
- Click "Authorize" button and re-enter credentials
- Refresh your bearer token (tokens typically expire after a few hours)
- Verify API key is correct in `.env` file

---

### **Issue: Part Number with Special Characters**

**Example:** `#FFH06-12SAE F` (contains `#` and space)

**Solution:**
- Swagger UI automatically URL-encodes special characters
- Use the exact part number as it appears in Epicor
- Don't manually encode (e.g., don't use `%23` for `#`)

---

## 📚 Quick Reference

### **Common OData Operators**

| Operator | Example | Description |
|----------|---------|-------------|
| `eq` | `VendorID eq 'FAST1'` | Equals |
| `ne` | `BasePrice ne 0` | Not equals |
| `gt` | `BasePrice gt 100` | Greater than |
| `lt` | `BasePrice lt 200` | Less than |
| `ge` | `BasePrice ge 100` | Greater than or equal |
| `le` | `BasePrice le 200` | Less than or equal |
| `and` | `VendorNum eq 204 and PartNum eq 'TEST'` | Logical AND |
| `or` | `ListCode eq 'UNA1' or ListCode eq 'AMV'` | Logical OR |

### **Common OData Query Options**

| Option | Example | Description |
|--------|---------|-------------|
| `$filter` | `$filter=PartNum eq 'TEST'` | Filter results |
| `$select` | `$select=PartNum,BasePrice` | Select specific fields |
| `$orderby` | `$orderby=EffectiveDate desc` | Sort results |
| `$top` | `$top=10` | Limit number of results |
| `$skip` | `$skip=20` | Skip first N results |
| `$expand` | `$expand=Vendor` | Include related entities |

### **Key Epicor Services**

| Service | Purpose | Key Entities |
|---------|---------|--------------|
| `VendorSvc` | Supplier master data | Vendors |
| `SupplierPartSvc` | Supplier-part relationships | SupplierParts |
| `PriceLstSvc` | Price list management | PriceLsts, PriceLstParts |
| `PartSvc` | Part master data | Parts |

### **Important Fields**

| Field | Description | Example |
|-------|-------------|---------|
| `VendorID` | External supplier identifier | "FAST1" |
| `VendorNum` | Internal vendor number | 204 |
| `PartNum` | Part number (with special chars) | "#FFH06-12SAE F" |
| `ListCode` | Price list code | "UNA1" |
| `BasePrice` | Base price for the part | 130.0 |
| `EffectiveDate` | When price becomes effective | "2025-10-20T00:00:00" |
| `UOMCode` | Unit of measure | "EA" (Each) |

---

## ✅ Verification Checklist

Use this checklist after running a price update:

- [ ] **Step 1**: Supplier exists in VendorSvc
  - [ ] VendorID matches (e.g., "FAST1")
  - [ ] VendorNum retrieved (e.g., 204)
  - [ ] Supplier is active

- [ ] **Step 2**: Supplier-part link exists in SupplierPartSvc
  - [ ] VendorNum matches
  - [ ] PartNum matches exactly
  - [ ] Record found (not empty)

- [ ] **Step 3**: Price list entry updated in PriceLstSvc
  - [ ] BasePrice matches new price
  - [ ] EffectiveDate matches target date
  - [ ] LastUpdated is recent
  - [ ] ListCode is correct

- [ ] **Step 4**: All price lists checked (if applicable)
  - [ ] Part appears in expected price lists
  - [ ] No duplicate entries with conflicting dates

---

## 🎯 Example: Complete Verification

### **Scenario:**
- Supplier: FAST1 (Faster Inc.)
- Part: #FFH06-12SAE F
- New Price: $130.00
- Effective Date: 2025-10-20

### **Verification Steps:**

```
1. GET /Erp.BO.VendorSvc/Vendors?$filter=VendorID eq 'FAST1'
   ✅ Result: VendorNum = 204, Name = "Faster Inc. (Indiana)"

2. GET /Erp.BO.SupplierPartSvc/SupplierParts?$filter=VendorNum eq 204 and PartNum eq '#FFH06-12SAE F'
   ✅ Result: Link exists

3. GET /Erp.BO.PriceLstSvc/PriceLstParts?$filter=ListCode eq 'UNA1' and PartNum eq '#FFH06-12SAE F' and UOMCode eq 'EA'
   ✅ Result: BasePrice = 130.0, EffectiveDate = 2025-10-20T00:00:00

4. GET /Erp.BO.PriceLstSvc/PriceLstParts?$filter=PartNum eq '#FFH06-12SAE F'
   ✅ Result: Part in 1 price list (UNA1)
```

**Conclusion:** ✅ Price change verified successfully!

---

## 📞 Support

If you encounter issues not covered in this guide:

1. Check the [Workflow Documentation](workflow.md) for system architecture
2. Review Epicor API logs for detailed error messages
3. Verify your `.env` configuration matches your Epicor instance
4. Contact your Epicor administrator for API access issues

---

**Last Updated**: 2025-10-15  
**Version**: 1.0.0

