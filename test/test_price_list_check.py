"""
Check if parts exist in Epicor price lists
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
print("🔍 CHECKING PRICE LIST ENTRIES")
print("=" * 80)

# Check if the part exists in price lists
part_num = "#FFH06-12SAE F"

url = f"{BASE_URL}/{COMPANY_ID}/Erp.BO.PriceLstSvc/PriceLstParts"
params = {"$filter": f"PartNum eq '{part_num}'"}

print(f"\n📡 Querying price lists for part: {part_num}")
print(f"URL: {url}")
print(f"Filter: {params['$filter']}")

response = requests.get(url, headers=get_headers(), params=params, timeout=10)

print(f"\nStatus: {response.status_code}")
print(f"Full URL: {response.url}")

if response.status_code == 200:
    data = response.json()
    results = data.get("value", [])
    
    print(f"\n✅ Query successful - Found {len(results)} price list entries")
    
    if results:
        print("\n" + "=" * 80)
        print("📋 PRICE LIST ENTRIES")
        print("=" * 80)
        
        for i, entry in enumerate(results, 1):
            print(f"\n--- Entry {i} ---")
            print(f"ListCode: {entry.get('ListCode')}")
            print(f"PartNum: {entry.get('PartNum')}")
            print(f"UOMCode: {entry.get('UOMCode')}")
            print(f"BasePrice: {entry.get('BasePrice')}")
            print(f"EffectiveDate: {entry.get('EffectiveDate')}")
            print(f"Company: {entry.get('Company')}")
    else:
        print("\n❌ NO PRICE LIST ENTRIES FOUND")
        print("\nThis means:")
        print("  1. The part exists in Epicor (PartSvc)")
        print("  2. BUT it's not in any price list (PriceLstSvc)")
        print("  3. You need to add the part to a price list first")
        
        print("\n💡 SOLUTION:")
        print("  Option 1: Add the part to a price list in Epicor manually")
        print("  Option 2: Create a price list entry via API (if supported)")
        print("  Option 3: Use PartSvc to update master part price (no effective date)")
else:
    print(f"\n❌ Error: {response.status_code}")
    print(f"Response: {response.text[:500]}")

# Also check if the part exists at all
print("\n" + "=" * 80)
print("🔍 CHECKING IF PART EXISTS IN PART MASTER")
print("=" * 80)

part_url = f"{BASE_URL}/{COMPANY_ID}/Erp.BO.PartSvc/Parts('{COMPANY_ID}','{part_num}')"
print(f"\n📡 Checking part: {part_num}")
print(f"URL: {part_url}")

part_response = requests.get(part_url, headers=get_headers(), timeout=10)

print(f"\nStatus: {part_response.status_code}")

if part_response.status_code == 200:
    part_data = part_response.json()
    print(f"\n✅ Part exists in Epicor!")
    print(f"   PartNum: {part_data.get('PartNum')}")
    print(f"   PartDescription: {part_data.get('PartDescription')}")
    print(f"   UnitPrice: {part_data.get('UnitPrice')}")
elif part_response.status_code == 404:
    print(f"\n❌ Part does NOT exist in Epicor")
else:
    print(f"\n⚠️  Status {part_response.status_code}")
    print(f"Response: {part_response.text[:300]}")

print("\n" + "=" * 80)
print("📋 SUMMARY")
print("=" * 80)
print("""
If the part exists but has no price list entries:
- The NEW workflow (PriceLstSvc) will fail
- You need to either:
  1. Add the part to a price list in Epicor first
  2. Use the OLD workflow (PartSvc) which updates master price directly

If the part doesn't exist at all:
- You need to create the part in Epicor first
- Then add it to a price list
- Then the workflow will work
""")

print("=" * 80)

