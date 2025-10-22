# Epicor Kinetic Pricing Hierarchy

In **Epicor Kinetic**, *Price List*, *Price List Parts*, and *Price List Breaks* work together in a clear hierarchy to control pricing for parts and customers. Their relationship can be summarized as follows.

---

## Hierarchy Overview

### **Price List (PriceLst)**

The **top-level** object. Each price list holds key information like list code, description, currency, start date (effective date), and optional end date.

**Example fields:**
- `ListCode`
- `Description`
- `StartDate`
- `EndDate`
- `CurrencyCode`

**Purpose:**
Sets the date range during which associated pricing is valid for all linked parts.

---

### **Price List Part (PriceLstParts)**

**Child of a Price List.**  
Each record links a part (and UOM) to a specific price list and sets a base price for that part/list pairing.

**Example fields:**
- `ListCode`
- `PartNum`
- `UnitPrice`
- `UOMCode`

**Notes:**
- Inherits effective/expiration dates from the parent price list.
- No individual part-level effective date.

---

### **Price List Breaks (PLPartBrks or PriceLstBrk)**

**Child of a Price List Part.**  
Each break record specifies quantity-based discounting, where different unit prices or discounts apply at specified quantity thresholds.

**Example fields:**
- `ListCode`
- `PartNum`
- `Quantity`
- `UnitPrice`
- `DiscountPercent`

**Purpose:**
Allows for advanced pricing structures such as “Buy 10+, get a lower unit price” for the specific part in that price list.

---

## Visual Hierarchy

```
Price List (ListCode)
│
├── Price List Part (PartNum, ListCode)
│   ├── Price List Break (Quantity, UnitPrice/Discount)
│   ├── Price List Break (Quantity, UnitPrice/Discount)
│   └── ...
├── Price List Part (PartNum, ListCode)
│   ├── Price List Break (Quantity, UnitPrice/Discount)
│   └── ...
└── ...
```

---

## Detailed Explanation

The **Price List** defines:
- Which customers or suppliers see special pricing  
- The overall validity dates for those prices  
- The currency and global options  

**Price List Parts** are entries for each included part, attaching explicit prices (and UOM, etc.).

**Price List Breaks** define the quantity thresholds (*breakpoints*) for each part in the list—these can specify tiered pricing or quantity discounts.

---

## Key Points

- The hierarchy is **Price List → Price List Parts → Price List Breaks**.
- All effective dates and overall inclusion are controlled by the header level (**Price List**).
- Price breaks only exist in relation to a specific part/list combination, not standalone.
- This relationship allows Epicor to provide flexible and scalable pricing schedules, covering custom pricing by part, customer, quantity break, and time period — all structured logically from the top down.

---


