"""
Test SupplierPartSvc to find the correct field names and filter syntax
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
print("🔍 SUPPLIER PART SERVICE FIELD ANALYSIS")
print("=" * 80)

# Get a few records to see all available fields
url = f"{BASE_URL}/{COMPANY_ID}/Erp.BO.SupplierPartSvc/SupplierParts"
params = {"$top": "3"}

print(f"\n📡 Fetching sample records from SupplierPartSvc...")
print(f"URL: {url}")

try:
    response = requests.get(url, headers=get_headers(), params=params, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        records = data.get("value", [])
        
        print(f"\n✅ SUCCESS - Retrieved {len(records)} sample records")
        
        if records:
            print("\n" + "=" * 80)
            print("📋 AVAILABLE FIELDS IN SupplierParts")
            print("=" * 80)
            
            # Show all fields from first record
            first_record = records[0]
            print(f"\nAll fields: {list(first_record.keys())}")
            
            print("\n" + "=" * 80)
            print("📊 SAMPLE RECORDS")
            print("=" * 80)
            
            for i, record in enumerate(records, 1):
                print(f"\n--- Record {i} ---")
                print(f"Company: {record.get('Company')}")
                print(f"PartNum: {record.get('PartNum')}")
                print(f"VendorNum: {record.get('VendorNum')}")
                print(f"VendPartNum: {record.get('VendPartNum')}")
                print(f"MfgNum: {record.get('MfgNum')}")
                print(f"MfgPartNum: {record.get('MfgPartNum')}")
                print(f"Reference: {record.get('Reference')}")
                print(f"LeadTime: {record.get('LeadTime')}")
                print(f"PurchaseDefault: {record.get('PurchaseDefault')}")
                
                # Check if VendorVendorID exists
                if 'VendorVendorID' in record:
                    print(f"VendorVendorID: {record.get('VendorVendorID')}")
                else:
                    print("VendorVendorID: ❌ NOT FOUND")
                
                # Check if VendorName exists
                if 'VendorName' in record:
                    print(f"VendorName: {record.get('VendorName')}")
                else:
                    print("VendorName: ❌ NOT FOUND")
            
            # Now test if we can get VendorVendorID by expanding Vendor
            print("\n" + "=" * 80)
            print("🔗 TESTING VENDOR EXPANSION")
            print("=" * 80)
            
            # Try to get vendor info by expanding
            test_vendor_num = records[0].get('VendorNum')
            if test_vendor_num:
                print(f"\n📡 Getting vendor info for VendorNum: {test_vendor_num}")
                vendor_url = f"{BASE_URL}/{COMPANY_ID}/Erp.BO.VendorSvc/Vendors({test_vendor_num})"
                
                try:
                    vendor_response = requests.get(vendor_url, headers=get_headers(), timeout=10)
                    if vendor_response.status_code == 200:
                        vendor_data = vendor_response.json()
                        print(f"\n✅ Vendor found:")
                        print(f"   VendorNum: {vendor_data.get('VendorNum')}")
                        print(f"   VendorID: {vendor_data.get('VendorID')}")
                        print(f"   Name: {vendor_data.get('Name')}")
                        
                        print("\n💡 SOLUTION FOUND:")
                        print("   - SupplierParts has VendorNum (internal ID)")
                        print("   - Need to lookup VendorID from VendorSvc using VendorNum")
                        print("   - VendorID is the external supplier ID (like 'FAST1')")
                    else:
                        print(f"   ⚠️  Status {vendor_response.status_code}")
                except Exception as e:
                    print(f"   ❌ Error: {e}")
            
            # Test filtering by VendorNum and PartNum
            print("\n" + "=" * 80)
            print("🧪 TESTING FILTER SYNTAX")
            print("=" * 80)
            
            test_part = records[0].get('PartNum')
            test_vendor_num = records[0].get('VendorNum')
            
            print(f"\nTest data:")
            print(f"  PartNum: {test_part}")
            print(f"  VendorNum: {test_vendor_num}")
            
            # Test filter by VendorNum and PartNum
            filter_query = f"VendorNum eq {test_vendor_num} and PartNum eq '{test_part}'"
            params = {"$filter": filter_query}
            
            print(f"\n📡 Testing filter: {filter_query}")
            
            try:
                filter_response = requests.get(url, headers=get_headers(), params=params, timeout=10)
                print(f"Status: {filter_response.status_code}")
                print(f"URL: {filter_response.url}")
                
                if filter_response.status_code == 200:
                    filter_data = filter_response.json()
                    filter_results = filter_data.get("value", [])
                    print(f"✅ Filter works! Found {len(filter_results)} records")
                elif filter_response.status_code == 400:
                    print(f"❌ Filter syntax error (400)")
                    print(f"Response: {filter_response.text[:300]}")
                else:
                    print(f"⚠️  Status {filter_response.status_code}")
            except Exception as e:
                print(f"❌ Error: {e}")
                
    else:
        print(f"❌ Error: Status {response.status_code}")
        print(f"Response: {response.text[:300]}")
        
except Exception as e:
    print(f"❌ Exception: {e}")

print("\n" + "=" * 80)
print("📋 SUMMARY")
print("=" * 80)
print("""
Based on the analysis above:

1. SupplierPartSvc uses VendorNum (internal ID), not VendorVendorID
2. To match supplier by external ID (like "FAST1"):
   - First lookup VendorNum from VendorSvc using VendorID
   - Then query SupplierPartSvc using VendorNum

RECOMMENDED APPROACH:
Step 1: GET /Erp.BO.VendorSvc/Vendors?$filter=VendorID eq 'FAST1'
        → Returns VendorNum (e.g., 204)

Step 2: GET /Erp.BO.SupplierPartSvc/SupplierParts?$filter=VendorNum eq 204 and PartNum eq 'TEST-001'
        → Returns supplier-part relationship

This is a 2-step process instead of 1-step.
""")

print("=" * 80)

