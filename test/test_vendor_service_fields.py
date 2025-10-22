"""
Test script to check available fields in Erp.BO.VendorSvc
and look for EffectiveDate or pricing-related fields
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

print("=" * 80)
print("🔍 CHECKING Erp.BO.VendorSvc FOR EFFECTIVE DATE FIELDS")
print("=" * 80)

# Test 1: Check main Vendors entity
print("\n" + "=" * 80)
print("📋 TEST 1: Check Vendors Entity")
print("=" * 80)

url = f"{BASE_URL}/{COMPANY_ID}/Erp.BO.VendorSvc/Vendors"
params = {
    "$filter": "VendorID eq 'FAST1'",
    "$top": 1
}

print(f"\n📡 Query: GET {url}")
print(f"Filter: {params['$filter']}")

response = requests.get(url, headers=get_headers(), params=params, timeout=10)

print(f"\nStatus: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    results = data.get("value", [])
    
    if results:
        vendor = results[0]
        print(f"\n✅ Vendor found: {vendor.get('VendorID')} - {vendor.get('Name')}")
        
        # Get all field names
        fields = list(vendor.keys())
        print(f"\n📊 Total fields: {len(fields)}")
        
        # Check for date-related fields
        date_fields = [f for f in fields if 'date' in f.lower() or 'Date' in f]
        print(f"\n📅 Date-related fields ({len(date_fields)}):")
        for field in sorted(date_fields):
            print(f"   - {field}: {vendor.get(field)}")
        
        # Check for price-related fields
        price_fields = [f for f in fields if 'price' in f.lower() or 'Price' in f]
        print(f"\n💰 Price-related fields ({len(price_fields)}):")
        for field in sorted(price_fields):
            print(f"   - {field}: {vendor.get(field)}")
        
        # Check for effective date specifically
        print(f"\n🎯 Checking for EffectiveDate field:")
        if 'EffectiveDate' in fields:
            print(f"   ✅ EffectiveDate EXISTS: {vendor.get('EffectiveDate')}")
        else:
            print(f"   ❌ EffectiveDate NOT FOUND")
        
        # Show all fields
        print(f"\n📋 All available fields:")
        for i, field in enumerate(sorted(fields), 1):
            print(f"   {i:3d}. {field}")
    else:
        print("\n❌ No vendor found with VendorID='FAST1'")
else:
    print(f"\n❌ Error: {response.status_code}")
    print(f"Response: {response.text[:500]}")

# Test 2: Check for child entities (VendorPP, VendorPart, etc.)
print("\n" + "=" * 80)
print("📋 TEST 2: Check for Child Entities in VendorSvc")
print("=" * 80)

# Try to get metadata or check common child entities
child_entities = [
    "VendorPPs",           # Vendor Part Pricing
    "VendorParts",         # Vendor Parts
    "VendorPrices",        # Vendor Prices
    "VendorPriceLists",    # Vendor Price Lists
    "VendorPartPrices",    # Vendor Part Prices
]

print("\nChecking for child entities...")

for entity in child_entities:
    test_url = f"{BASE_URL}/{COMPANY_ID}/Erp.BO.VendorSvc/{entity}"
    test_params = {"$top": 1}
    
    print(f"\n   Testing: {entity}")
    print(f"   URL: {test_url}")
    
    try:
        test_response = requests.get(test_url, headers=get_headers(), params=test_params, timeout=10)
        
        if test_response.status_code == 200:
            test_data = test_response.json()
            test_results = test_data.get("value", [])
            
            print(f"   ✅ EXISTS - Found {len(test_results)} records")
            
            if test_results:
                # Check fields in first record
                first_record = test_results[0]
                entity_fields = list(first_record.keys())
                
                # Check for EffectiveDate
                if 'EffectiveDate' in entity_fields:
                    print(f"   🎯 ✅ HAS EffectiveDate field!")
                    print(f"      Value: {first_record.get('EffectiveDate')}")
                
                # Check for other date fields
                entity_date_fields = [f for f in entity_fields if 'date' in f.lower() or 'Date' in f]
                if entity_date_fields:
                    print(f"   📅 Date fields: {', '.join(entity_date_fields)}")
                
                # Check for price fields
                entity_price_fields = [f for f in entity_fields if 'price' in f.lower() or 'Price' in f]
                if entity_price_fields:
                    print(f"   💰 Price fields: {', '.join(entity_price_fields)}")
                
                # Show all fields
                print(f"   📋 All fields ({len(entity_fields)}): {', '.join(sorted(entity_fields)[:10])}...")
        
        elif test_response.status_code == 404:
            print(f"   ❌ Does not exist (404)")
        else:
            print(f"   ⚠️  Status {test_response.status_code}")
    
    except Exception as e:
        print(f"   ❌ Error: {e}")

# Test 3: Try GetByID to get full dataset structure
print("\n" + "=" * 80)
print("📋 TEST 3: Check GetByID for Full Dataset Structure")
print("=" * 80)

get_by_id_url = f"{BASE_URL}/{COMPANY_ID}/Erp.BO.VendorSvc/GetByID"
get_by_id_payload = {
    "vendorNum": 204  # FAST1's VendorNum
}

print(f"\n📡 Query: POST {get_by_id_url}")
print(f"Payload: {json.dumps(get_by_id_payload, indent=2)}")

try:
    get_by_id_response = requests.post(get_by_id_url, headers=get_headers(), json=get_by_id_payload, timeout=10)
    
    print(f"\nStatus: {get_by_id_response.status_code}")
    
    if get_by_id_response.status_code == 200:
        dataset = get_by_id_response.json()
        
        print(f"\n✅ GetByID successful")
        print(f"\n📊 Dataset structure:")
        
        # Check returnObj structure
        if "returnObj" in dataset:
            return_obj = dataset["returnObj"]
            print(f"\n   returnObj keys: {list(return_obj.keys())}")
            
            # Check each table in the dataset
            for table_name, table_data in return_obj.items():
                if isinstance(table_data, list) and len(table_data) > 0:
                    print(f"\n   📋 Table: {table_name} ({len(table_data)} records)")
                    
                    first_record = table_data[0]
                    fields = list(first_record.keys())
                    
                    # Check for EffectiveDate
                    if 'EffectiveDate' in fields:
                        print(f"      🎯 ✅ HAS EffectiveDate field!")
                    
                    # Show date fields
                    date_fields = [f for f in fields if 'date' in f.lower() or 'Date' in f]
                    if date_fields:
                        print(f"      📅 Date fields: {', '.join(date_fields)}")
                    
                    # Show price fields
                    price_fields = [f for f in fields if 'price' in f.lower() or 'Price' in f]
                    if price_fields:
                        print(f"      💰 Price fields: {', '.join(price_fields)}")
                    
                    print(f"      📋 Total fields: {len(fields)}")
    else:
        print(f"\n❌ Error: {get_by_id_response.status_code}")
        print(f"Response: {get_by_id_response.text[:500]}")

except Exception as e:
    print(f"\n❌ Exception: {e}")

# Summary
print("\n" + "=" * 80)
print("📊 SUMMARY")
print("=" * 80)
print("""
This script checked:
1. ✅ Main Vendors entity for EffectiveDate field
2. ✅ Child entities (VendorPPs, VendorParts, etc.) for pricing with dates
3. ✅ GetByID method for full dataset structure

Look for:
- 🎯 EffectiveDate field in any entity
- 📅 Other date fields (ExpirationDate, StartDate, EndDate, etc.)
- 💰 Price fields combined with date fields
- 📋 Child entities that might contain supplier pricing

If EffectiveDate is found in any child entity, that's the one we should use!
""")

print("\n" + "=" * 80)

