"""
Discover available price lists in Epicor
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
print("🔍 DISCOVERING AVAILABLE PRICE LISTS")
print("=" * 80)

# Query all price lists
url = f"{BASE_URL}/{COMPANY_ID}/Erp.BO.PriceLstSvc/PriceLsts"
params = {"$top": "50"}  # Get up to 50 price lists

print(f"\n📡 Querying price lists...")
print(f"URL: {url}")

response = requests.get(url, headers=get_headers(), params=params, timeout=10)

print(f"\nStatus: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    price_lists = data.get("value", [])
    
    print(f"\n✅ Found {len(price_lists)} price lists")
    
    if price_lists:
        print("\n" + "=" * 80)
        print("📋 AVAILABLE PRICE LISTS")
        print("=" * 80)
        
        for i, pl in enumerate(price_lists, 1):
            print(f"\n--- Price List {i} ---")
            print(f"ListCode: {pl.get('ListCode')}")
            print(f"ListDescription: {pl.get('ListDescription')}")
            print(f"Company: {pl.get('Company')}")
            print(f"StartDate: {pl.get('StartDate')}")
            print(f"EndDate: {pl.get('EndDate')}")
            print(f"Active: {pl.get('Active', True)}")
        
        print("\n" + "=" * 80)
        print("💡 RECOMMENDATION")
        print("=" * 80)
        
        # Find the first active price list
        active_lists = [pl for pl in price_lists if pl.get('Active', True)]
        
        if active_lists:
            recommended = active_lists[0]
            list_code = recommended.get('ListCode')
            print(f"\n✅ Use this price list code: {list_code}")
            print(f"   Description: {recommended.get('ListDescription')}")
            print(f"\nUpdate your code to use:")
            print(f'   list_code = "{list_code}"')
        else:
            print(f"\n⚠️  No active price lists found")
            print(f"   You may need to create a price list in Epicor first")
    else:
        print("\n❌ NO PRICE LISTS FOUND")
        print("\nThis means:")
        print("  1. No price lists exist in your Epicor system")
        print("  2. You need to create a price list in Epicor first")
        print("\nSteps to create a price list:")
        print("  1. Log into Epicor ERP")
        print("  2. Go to: Sales Management → Price List Maintenance")
        print("  3. Create a new price list (e.g., 'SUPPLIER' or 'VENDOR')")
        print("  4. Then run this script again")
else:
    print(f"\n❌ Error: {response.status_code}")
    print(f"Response: {response.text[:500]}")

print("\n" + "=" * 80)
print("✅ Discovery complete!")
print("=" * 80)

