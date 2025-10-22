"""
Test if we can filter SupplierPartSvc directly by VendorVendorID
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("EPICOR_BASE_URL")
API_KEY = os.getenv("EPICOR_API_KEY")
BEARER_TOKEN = os.getenv("EPICOR_BEARER_TOKEN")
COMPANY_ID = os.getenv("EPICOR_COMPANY_ID")

def get_headers():
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
print("🧪 TESTING VendorVendorID FILTER")
print("=" * 80)

url = f"{BASE_URL}/{COMPANY_ID}/Erp.BO.SupplierPartSvc/SupplierParts"

# Test 1: Filter by VendorVendorID only
print("\n--- Test 1: Filter by VendorVendorID only ---")
filter1 = "VendorVendorID eq 'FAST1'"
params1 = {"$filter": filter1}

print(f"Filter: {filter1}")
response1 = requests.get(url, headers=get_headers(), params=params1, timeout=10)
print(f"Status: {response1.status_code}")
print(f"URL: {response1.url}")

if response1.status_code == 200:
    data1 = response1.json()
    results1 = data1.get("value", [])
    print(f"✅ SUCCESS - Found {len(results1)} records")
    if results1:
        print(f"Sample: PartNum={results1[0].get('PartNum')}, VendorVendorID={results1[0].get('VendorVendorID')}")
elif response1.status_code == 400:
    print(f"❌ BAD REQUEST (400)")
    print(f"Response: {response1.text[:300]}")
else:
    print(f"⚠️  Status {response1.status_code}")

# Test 2: Filter by VendorVendorID AND PartNum
print("\n--- Test 2: Filter by VendorVendorID AND PartNum ---")
filter2 = "VendorVendorID eq 'FAST1' and PartNum eq '#FFH06-12SAE F'"
params2 = {"$filter": filter2}

print(f"Filter: {filter2}")
response2 = requests.get(url, headers=get_headers(), params=params2, timeout=10)
print(f"Status: {response2.status_code}")
print(f"URL: {response2.url}")

if response2.status_code == 200:
    data2 = response2.json()
    results2 = data2.get("value", [])
    print(f"✅ SUCCESS - Found {len(results2)} records")
    if results2:
        record = results2[0]
        print(f"\nRecord details:")
        print(f"  PartNum: {record.get('PartNum')}")
        print(f"  VendorNum: {record.get('VendorNum')}")
        print(f"  VendorVendorID: {record.get('VendorVendorID')}")
        print(f"  VendorName: {record.get('VendorName')}")
elif response2.status_code == 400:
    print(f"❌ BAD REQUEST (400)")
    print(f"Response: {response2.text[:500]}")
else:
    print(f"⚠️  Status {response2.status_code}")

print("\n" + "=" * 80)
print("📋 CONCLUSION")
print("=" * 80)

if response2.status_code == 200:
    print("""
✅ PERFECT! We CAN filter directly by VendorVendorID!

The correct approach is:
- Endpoint: /Erp.BO.SupplierPartSvc/SupplierParts
- Filter: VendorVendorID eq 'FAST1' and PartNum eq '#FFH06-12SAE F'

This is a 1-step process - no need for 2-step lookup!

ACTION: Update services/epicor_service.py to use SupplierPartSvc instead of VendorPartSvc
""")
elif response2.status_code == 400:
    print("""
❌ Cannot filter by VendorVendorID directly (400 error)

Need to use 2-step approach:
Step 1: Lookup VendorNum from VendorSvc using VendorID
Step 2: Query SupplierPartSvc using VendorNum

ACTION: Update services/epicor_service.py to implement 2-step lookup
""")

print("=" * 80)

