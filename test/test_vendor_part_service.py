"""
Test VendorPartSvc endpoint to diagnose the 400 error
This script will help identify the correct endpoint and filter syntax
"""

import os
import requests
from dotenv import load_dotenv
import json

load_dotenv()

BASE_URL = os.getenv("EPICOR_BASE_URL")
API_KEY = os.getenv("EPICOR_API_KEY")
BEARER_TOKEN = os.getenv("EPICOR_BEARER_TOKEN")
COMPANY_ID = os.getenv("EPICOR_COMPANY_ID")

def get_headers():
    """Get authentication headers"""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    if BEARER_TOKEN and BEARER_TOKEN != "your-epicor-bearer-token-here":
        headers["Authorization"] = f"Bearer {BEARER_TOKEN}"
    
    if API_KEY:
        headers["X-api-Key"] = API_KEY
    
    return headers

print("=" * 80)
print("🔍 EPICOR VENDOR PART SERVICE DIAGNOSTIC")
print("=" * 80)
print(f"\nBase URL: {BASE_URL}")
print(f"Company ID: {COMPANY_ID}")
print(f"API Key: {'✓ Set' if API_KEY else '✗ Not set'}")
print(f"Bearer Token: {'✓ Set' if BEARER_TOKEN and BEARER_TOKEN != 'your-epicor-bearer-token-here' else '✗ Not set'}")
print()

# Test 1: Check if VendorPartSvc endpoint exists
print("=" * 80)
print("TEST 1: Check VendorPartSvc Endpoint")
print("=" * 80)

test_urls = [
    f"{BASE_URL}/{COMPANY_ID}/Erp.BO.VendorPartSvc/VendorParts",
    f"{BASE_URL}/{COMPANY_ID}/Erp.BO.SupplierPartSvc/SupplierParts",
    f"{BASE_URL}/{COMPANY_ID}/Erp.BO.VendorSvc/Vendors",
]

for test_url in test_urls:
    print(f"\n🔗 Testing: {test_url}")
    try:
        response = requests.get(test_url, headers=get_headers(), timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            count = len(data.get("value", []))
            print(f"   ✅ SUCCESS - Found {count} records")
            if count > 0:
                print(f"   Sample fields: {list(data['value'][0].keys())[:10]}")
        elif response.status_code == 400:
            print(f"   ❌ BAD REQUEST (400)")
            print(f"   Response: {response.text[:200]}")
        elif response.status_code == 404:
            print(f"   ❌ NOT FOUND (404) - Endpoint doesn't exist")
        else:
            print(f"   ⚠️  Status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

# Test 2: Try different filter syntaxes
print("\n" + "=" * 80)
print("TEST 2: Test OData Filter Syntax")
print("=" * 80)

# Use a test supplier ID and part number
test_supplier_id = input("\nEnter a test Supplier ID (VendorVendorID) to test [or press Enter to skip]: ").strip()
test_part_num = input("Enter a test Part Number to test [or press Enter to skip]: ").strip()

if test_supplier_id and test_part_num:
    base_endpoint = f"{BASE_URL}/{COMPANY_ID}/Erp.BO.VendorPartSvc/VendorParts"
    
    # Try different filter formats
    filter_tests = [
        {
            "name": "Standard OData filter",
            "params": {"$filter": f"VendorVendorID eq '{test_supplier_id}' and PartNum eq '{test_part_num}'"}
        },
        {
            "name": "Filter with VendorNum instead",
            "params": {"$filter": f"PartNum eq '{test_part_num}'"}
        },
        {
            "name": "No filter (get all)",
            "params": {"$top": "5"}
        },
        {
            "name": "Filter by PartNum only",
            "params": {"$filter": f"PartNum eq '{test_part_num}'"}
        },
        {
            "name": "Filter by VendorVendorID only",
            "params": {"$filter": f"VendorVendorID eq '{test_supplier_id}'"}
        }
    ]
    
    for test in filter_tests:
        print(f"\n🧪 {test['name']}")
        print(f"   Params: {test['params']}")
        
        try:
            response = requests.get(base_endpoint, headers=get_headers(), params=test['params'], timeout=10)
            print(f"   Status: {response.status_code}")
            print(f"   URL: {response.url}")
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("value", [])
                print(f"   ✅ SUCCESS - Found {len(results)} records")
                
                if results:
                    record = results[0]
                    print(f"   Sample record:")
                    print(f"      PartNum: {record.get('PartNum')}")
                    print(f"      VendorNum: {record.get('VendorNum')}")
                    print(f"      VendorVendorID: {record.get('VendorVendorID')}")
                    print(f"      VendorName: {record.get('VendorName')}")
            elif response.status_code == 400:
                print(f"   ❌ BAD REQUEST (400)")
                print(f"   Response: {response.text[:300]}")
            else:
                print(f"   ⚠️  Status {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
else:
    print("\n⏭️  Skipping filter tests (no test data provided)")

# Test 3: Check metadata to see available fields
print("\n" + "=" * 80)
print("TEST 3: Check Service Metadata")
print("=" * 80)

metadata_urls = [
    f"{BASE_URL}/$metadata",
    f"{BASE_URL}/{COMPANY_ID}/$metadata"
]

for metadata_url in metadata_urls:
    print(f"\n🔗 Checking: {metadata_url}")
    try:
        response = requests.get(metadata_url, headers=get_headers(), timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"   ✅ Metadata available")
            
            # Search for VendorPart in metadata
            if "VendorPart" in response.text:
                print(f"   ✓ Found 'VendorPart' in metadata")
            else:
                print(f"   ✗ 'VendorPart' not found in metadata")
                
            if "SupplierPart" in response.text:
                print(f"   ✓ Found 'SupplierPart' in metadata")
            else:
                print(f"   ✗ 'SupplierPart' not found in metadata")
        else:
            print(f"   ⚠️  Status {response.status_code}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")

# Summary and recommendations
print("\n" + "=" * 80)
print("📋 DIAGNOSTIC SUMMARY")
print("=" * 80)
print("""
Based on the test results above:

1. If VendorPartSvc returns 200 with records:
   ✅ The endpoint exists and is accessible
   → Check which filter syntax worked
   → Update the code to use that syntax

2. If VendorPartSvc returns 404:
   ❌ The endpoint doesn't exist in your Epicor instance
   → You may need to use a different service
   → Contact your Epicor admin about Vendor Part Cross Reference API

3. If VendorPartSvc returns 400 with all filter attempts:
   ❌ The endpoint exists but doesn't accept OData filters
   → May need to use a different approach
   → Check Epicor documentation for your version

4. If SupplierPartSvc works instead:
   ✅ Use SupplierPartSvc instead of VendorPartSvc
   → Update the code to use the correct service name

NEXT STEPS:
- Review the test results above
- Identify which endpoint and filter syntax works
- Update services/epicor_service.py accordingly
- Or disable supplier verification if the service is not available
""")

print("=" * 80)
print("✅ Diagnostic complete!")
print("=" * 80)

