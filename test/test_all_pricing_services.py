"""
Test script to check ALL potential pricing-related services in Epicor
and look for ones that support EffectiveDate
"""

import requests
import json
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

BASE_URL = os.getenv("EPICOR_BASE_URL")
COMPANY_ID = os.getenv("EPICOR_COMPANY_ID")
BEARER_TOKEN = os.getenv("EPICOR_BEARER_TOKEN")
API_KEY = os.getenv("EPICOR_API_KEY")

def get_headers():
    """Get request headers with authentication"""
    return {
        "Authorization": f"Bearer {BEARER_TOKEN}",
        "X-API-Key": API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

def test_service(service_name, entity_name, filter_query=None):
    """Test if a service/entity exists and check for EffectiveDate"""
    url = f"{BASE_URL}/{COMPANY_ID}/{service_name}/{entity_name}"
    params = {"$top": 1}
    if filter_query:
        params["$filter"] = filter_query
    
    try:
        response = requests.get(url, headers=get_headers(), params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("value", [])
            
            if results:
                fields = list(results[0].keys())
                has_effective_date = 'EffectiveDate' in fields
                
                # Check for other date fields
                date_fields = [f for f in fields if 'date' in f.lower() or 'Date' in f]
                
                # Check for price fields
                price_fields = [f for f in fields if 'price' in f.lower() or 'Price' in f or 'cost' in f.lower() or 'Cost' in f]
                
                return {
                    "status": "EXISTS_WITH_DATA",
                    "record_count": len(results),
                    "has_effective_date": has_effective_date,
                    "date_fields": date_fields,
                    "price_fields": price_fields,
                    "total_fields": len(fields),
                    "sample_record": results[0]
                }
            else:
                return {
                    "status": "EXISTS_NO_DATA",
                    "record_count": 0
                }
        elif response.status_code == 404:
            return {"status": "NOT_FOUND"}
        else:
            return {"status": f"ERROR_{response.status_code}"}
    except Exception as e:
        return {"status": f"EXCEPTION: {str(e)[:50]}"}

print("=" * 80)
print("🔍 COMPREHENSIVE EPICOR PRICING SERVICES CHECK")
print("=" * 80)

# List of potential services to check
services_to_check = [
    # Purchase-related services
    ("Erp.BO.PartPlantSvc", "PartPlants", "PartNum eq '#FFH06-12SAE F'"),
    ("Erp.BO.PurMiscSvc", "PurMiscs", None),
    ("Erp.BO.PurchaseContractSvc", "PurchaseContracts", "VendorNum eq 204"),
    ("Erp.BO.POSvc", "POHeaders", "VendorNum eq 204"),
    
    # Supplier/Vendor pricing
    ("Erp.BO.SupplierPriceSvc", "SupplierPrices", None),
    ("Erp.BO.VendorPartSvc", "VendorParts", None),
    ("Erp.BO.VendorPriceSvc", "VendorPrices", None),
    
    # Part-related pricing
    ("Erp.BO.PartSvc", "PartCosts", "PartNum eq '#FFH06-12SAE F'"),
    ("Erp.BO.PartSvc", "PartPlants", "PartNum eq '#FFH06-12SAE F'"),
    
    # Price list alternatives
    ("Erp.BO.PriceLstSvc", "PLPartBrks", "PartNum eq '#FFH06-12SAE F'"),
    ("Erp.BO.PriceLstSvc", "PriceLsts", None),
    
    # Customer pricing (for comparison)
    ("Erp.BO.CustPriceLstSvc", "CustPriceLsts", None),
    
    # Quote/RFQ pricing
    ("Erp.BO.RFQEntrySvc", "RFQItems", None),
    ("Erp.BO.QuoteSvc", "QuoteItems", None),
]

results = {}

print("\n🔄 Testing services...")
print("=" * 80)

for service_name, entity_name, filter_query in services_to_check:
    full_name = f"{service_name}/{entity_name}"
    print(f"\n📡 Testing: {full_name}")
    
    result = test_service(service_name, entity_name, filter_query)
    results[full_name] = result
    
    status = result["status"]
    
    if status == "EXISTS_WITH_DATA":
        print(f"   ✅ EXISTS with {result['record_count']} records")
        print(f"   📊 Total fields: {result['total_fields']}")
        
        if result["has_effective_date"]:
            print(f"   🎯 ✅✅✅ HAS EffectiveDate FIELD! ✅✅✅")
        
        if result["date_fields"]:
            print(f"   📅 Date fields: {', '.join(result['date_fields'][:5])}")
        
        if result["price_fields"]:
            print(f"   💰 Price fields: {', '.join(result['price_fields'][:5])}")
    
    elif status == "EXISTS_NO_DATA":
        print(f"   ⚠️  EXISTS but no data")
    
    elif status == "NOT_FOUND":
        print(f"   ❌ Does not exist")
    
    else:
        print(f"   ⚠️  {status}")

# Summary of findings
print("\n" + "=" * 80)
print("📊 SUMMARY OF FINDINGS")
print("=" * 80)

services_with_data = {k: v for k, v in results.items() if v["status"] == "EXISTS_WITH_DATA"}
services_with_effective_date = {k: v for k, v in services_with_data.items() if v.get("has_effective_date")}

print(f"\n✅ Services with data: {len(services_with_data)}")
for service_name in services_with_data.keys():
    print(f"   - {service_name}")

if services_with_effective_date:
    print(f"\n🎯 ✅ SERVICES WITH EffectiveDate FIELD: {len(services_with_effective_date)}")
    for service_name, result in services_with_effective_date.items():
        print(f"\n   🌟 {service_name}")
        print(f"      Records: {result['record_count']}")
        print(f"      Date fields: {', '.join(result['date_fields'])}")
        print(f"      Price fields: {', '.join(result['price_fields'])}")
        
        # Show sample record
        print(f"\n      📋 Sample record:")
        sample = result['sample_record']
        for key in ['PartNum', 'VendorNum', 'VendorID', 'BasePrice', 'UnitCost', 'EffectiveDate', 'ExpirationDate']:
            if key in sample:
                print(f"         {key}: {sample[key]}")
else:
    print(f"\n❌ NO SERVICES FOUND WITH EffectiveDate FIELD")
    print("\nThis means your Epicor instance likely does NOT support effective dates")
    print("for supplier pricing in the standard data model.")
    print("\nOptions:")
    print("1. Use custom UD fields (e.g., EffectiveDate_c)")
    print("2. Store effective dates externally in your application")
    print("3. Contact Epicor support to enable this feature")

# Show services with date fields (even without EffectiveDate)
services_with_dates = {k: v for k, v in services_with_data.items() if v.get("date_fields")}
if services_with_dates and not services_with_effective_date:
    print(f"\n📅 Services with OTHER date fields (not EffectiveDate):")
    for service_name, result in services_with_dates.items():
        print(f"   - {service_name}: {', '.join(result['date_fields'][:3])}")

print("\n" + "=" * 80)

