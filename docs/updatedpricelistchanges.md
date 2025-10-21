# Old Process vs New Process - Comparison

## Overview Comparison

| **Aspect** | **OLD PROCESS** | **NEW PROCESS** |
|-------------|----------------|----------------|
| **Price List Strategy** | Single unified list (default "UNA1") | Supplier-specific lists (`SUPPLIER_{id}`) |
| **Effective Date** | Attempted at part level (incorrect) | Header level (correct per Epicor hierarchy) |
| **Part Creation** | Template-based (broken endpoint) | Direct POST with minimal fields |
| **Isolation** | All suppliers share one list | Each supplier has dedicated list |
| **API Approach** | Used non-existent `GetNewPriceLstParts` | Direct POST with `RowMod="A"` |

---

## Detailed Workflow Comparison

### **Step A: Supplier Verification**
✅ **UNCHANGED** – Both processes use the same verification:

1. `GET VendorSvc` to lookup `VendorNum` from `VendorID`
2. `GET SupplierPartSvc` to verify supplier-part relationship

---

### **Step B: Price List Management**

#### **OLD PROCESS (Broken & Inflexible):**
1. Check if part exists in ANY price list  
   ├─ If found → Use that list's `ListCode`  
   └─ If not found → Use default list `"UNA1"`

2. Check if part exists in chosen list  
   ├─ If exists → Skip to Step C  
   └─ If not exists → Create new entry:

   ❌ **PROBLEM:** Call `GetNewPriceLstParts` (**DOESN'T EXIST!**)  
   └─ Fetch template from API  
   └─ Fill template with part details  
   └─ POST template to Update endpoint  

**Result:**  
All suppliers share `"UNA1"` list — cannot set different effective dates per supplier.

#### **NEW PROCESS (Working & Flexible):**
1. Get or create supplier-specific price list  
   ├─ Check for `"SUPPLIER_{supplier_id}"` (e.g., `"SUPPLIER_FAST1"`)  
   ├─ If not exists → Create price list header:

```json
POST /PriceLstSvc/Update
{
  "PriceLst": [{
    "Company": "165122",
    "ListCode": "SUPPLIER_FAST1",
    "ListDescription": "Price List for Faster Inc.",
    "StartDate": "2025-11-01T00:00:00",
    "RowMod": "A"
  }]
}
```

   └─ If exists → Return existing list code  

2. Check if part exists in supplier's list  
   ├─ If exists → Skip to Step C  
   └─ If not exists → Create part entry (DIRECT):

```json
POST /PriceLstSvc/Update
{
  "PriceLstParts": [{
    "Company": "165122",
    "ListCode": "SUPPLIER_FAST1",
    "PartNum": "#FFH06-12SAE F",
    "UOMCode": "EA",
    "BasePrice": 130.0,
    "RowMod": "A"
  }]
}
```

**Result:**  
Each supplier has isolated list; can set different effective dates per supplier.

---

### **Step C: Effective Date Management**

#### **OLD PROCESS (Partially Incorrect):**
❌ Tried to set `EffectiveDate` at part level — Epicor manages dates only at header level.

```json
{
  "PriceLstParts": [{
    "BasePrice": 130.0,
    "EffectiveDate": "2025-11-01T00:00:00",
    "RowMod": "U"
  }]
}
```

**Result:** Dates not properly set; parts don’t inherit correct dates.

#### **NEW PROCESS (Correct):**
✅ Update effective date at **header level**:

```json
POST /PriceLstSvc/Update
{
  "PriceLst": [{
    "ListCode": "SUPPLIER_FAST1",
    "StartDate": "2025-11-01T00:00:00",
    "RowMod": "U"
  }]
}
```

**Result:** All parts in `"SUPPLIER_FAST1"` automatically inherit the correct date.

---

### **Step D: Price Update**

#### **OLD PROCESS:**
1. GET current part entry from list  
2. Update `BasePrice` and attempt `EffectiveDate`:

```json
POST /PriceLstSvc/Update
{
  "PriceLstParts": [{
    "BasePrice": 130.0,
    "EffectiveDate": "2025-11-01",
    "RowMod": "U"
  }]
}
```

❌ **Issues:**
- All suppliers mixed in one list  
- Effective dates not properly managed  
- Hard to track supplier-specific pricing

#### **NEW PROCESS:**
1. GET current part entry from `"SUPPLIER_{id}"` list  
2. Update only `BasePrice`:

```json
POST /PriceLstSvc/Update
{
  "PriceLstParts": [{
    "BasePrice": 130.0,
    "RowMod": "U"
  }]
}
```

✅ **Benefits:**
- Supplier-specific pricing  
- Proper date inheritance  
- Easy to track and audit  
- Independent date control

---

## Data Structure Comparison

### **OLD PROCESS – Single Unified List**
```
Price List: "UNA1"
├── StartDate: 2025-11-01 (affects ALL parts!)
├── Part: "#FFH06-12SAE F" (FAST1)
│   └── BasePrice: 130.0
├── Part: "WIDGET-001" (ACME)
│   └── BasePrice: 25.0
├── Part: "BOLT-123" (FASTENER-CO)
│   └── BasePrice: 5.50
```

❌ **Problems:**
- Shared effective date across suppliers  
- No supplier-specific differentiation  
- Hard to audit or isolate data

### **NEW PROCESS – Supplier-Specific Lists**
```
Price List: "SUPPLIER_FAST1"
├── StartDate: 2025-11-01
├── Description: "Price List for Faster Inc."
├── Part: "#FFH06-12SAE F" → BasePrice: 130.0
├── Part: "BOLT-456" → BasePrice: 2.75

Price List: "SUPPLIER_ACME"
├── StartDate: 2025-12-15
├── Description: "Price List for ACME Corp"
├── Part: "WIDGET-001" → BasePrice: 25.0
```

✅ **Benefits:**
- Independent effective dates  
- Clean supplier isolation  
- Easier updates and audits  
- Follows Epicor best practices

---

## API Endpoint Comparison

### **OLD PROCESS (❌ Broken)**

```json
POST /Erp.BO.PriceLstSvc/GetNewPriceLstParts
{
  "ds": {
    "PriceLst": [{"Company": "165122", "ListCode": "UNA1"}],
    "PriceLstParts": []
  },
  "listCode": "UNA1",
  "partNum": "#FFH06-12SAE F",
  "uomCode": "EA"
}
```

➡️ **Result:** `404 Not Found` – endpoint doesn’t exist.

### **NEW PROCESS (✅ Working)**

```json
POST /Erp.BO.PriceLstSvc/Update
{
  "ds": {
    "PriceLstParts": [{
      "Company": "165122",
      "ListCode": "SUPPLIER_FAST1",
      "PartNum": "#FFH06-12SAE F",
      "UOMCode": "EA",
      "BasePrice": 130.0,
      "RowMod": "A"
    }]
  }
}
```

✅ **Result:** Entry successfully created.

---

## Error Scenarios Comparison

### **Scenario 1: New Part from New Supplier**
- **OLD:** Fails due to missing endpoint  
- **NEW:** Creates list, part, and sets date successfully ✅

### **Scenario 2: Update Effective Date for One Supplier**
- **OLD:** Affects all suppliers ❌  
- **NEW:** Only updates target supplier ✅

---

## Configuration Comparison

```env
# OLD PROCESS
EPICOR_DEFAULT_PRICE_LIST=UNA1

# NEW PROCESS
EPICOR_DEFAULT_PRICE_LIST=UNA1  # Fallback only
# Auto-created supplier lists: SUPPLIER_FAST1, SUPPLIER_ACME, etc.
```

---

## Summary Table

| **Feature** | **OLD** | **NEW** | **Improvement** |
|--------------|----------|----------|----------------|
| **Price List Creation** | Template-based (broken) | Direct POST | ✅ Works |
| **Supplier Isolation** | No | Yes | ✅ Organized |
| **Effective Dates** | Part level (wrong) | Header level (correct) | ✅ Proper hierarchy |
| **Date Flexibility** | Global only | Per-supplier | ✅ Independent |
| **API Compliance** | Non-existent endpoint | Documented APIs | ✅ Future-proof |
| **Auditing** | Difficult | Easy | ✅ Better reporting |
| **Scalability** | Limited | Unlimited | ✅ Infinite |
| **Maintainability** | Complex logic | Simple POST | ✅ Easy to maintain |

---

## Migration Path

Existing data in `"UNA1"` remains untouched.

- **New price changes →** Create/use `SUPPLIER_{id}` lists  
- **Future updates →** Use supplier-specific lists  
- **Old data →** Can be migrated manually if needed  

✅ No breaking changes to existing data.

---

## Conclusion

The **NEW PROCESS** is superior in every way:

✅ Works correctly (no broken endpoints)  
✅ Follows Epicor hierarchy (header-level dates)  
✅ Supplier isolation (independent management)  
✅ Uses documented APIs (future-proof)  
✅ Scalable and maintainable  

The **old process** was broken due to the non-existent `GetNewPriceLstParts` endpoint and incorrect date handling. The new process fixes both while enabling supplier-specific, flexible, and reliable price management.
