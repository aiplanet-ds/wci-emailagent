"""
Test script to check PriceLsts (price list header) for StartDate and EndDate
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
print("🔍 CHECKING PriceLsts (Price List Headers) FOR DATE FIELDS")
print("=" * 80)

# Query PriceLsts
url = f"{BASE_URL}/{COMPANY_ID}/Erp.BO.PriceLstSvc/PriceLsts"
params = {
    "$top": 10,
    "$orderby": "ListCode"
}

print(f"\n📡 Query: GET {url}")

response = requests.get(url, headers=get_headers(), params=params, timeout=10)

print(f"\nStatus: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    results = data.get("value", [])
    
    print(f"\n✅ Found {len(results)} price lists")
    
    if results:
        # Check first record for all fields
        first_record = results[0]
        all_fields = list(first_record.keys())
        
        print(f"\n📊 Total fields in PriceLsts: {len(all_fields)}")
        
        # Check for date fields
        date_fields = [f for f in all_fields if 'date' in f.lower() or 'Date' in f]
        print(f"\n📅 Date-related fields ({len(date_fields)}):")
        for field in sorted(date_fields):
            print(f"   - {field}")
        
        # Check specifically for StartDate and EndDate
        print(f"\n🎯 Key Date Fields:")
        print(f"   StartDate exists: {'StartDate' in all_fields}")
        print(f"   EndDate exists: {'EndDate' in all_fields}")
        print(f"   EffectiveDate exists: {'EffectiveDate' in all_fields}")
        
        # Show all price lists with their dates
        print(f"\n📋 ALL PRICE LISTS WITH DATES:")
        print("=" * 80)
        
        for i, record in enumerate(results, 1):
            print(f"\n{i}. ListCode: {record.get('ListCode')}")
            print(f"   Description: {record.get('ListDescription')}")
            print(f"   StartDate: {record.get('StartDate')}")
            print(f"   EndDate: {record.get('EndDate')}")
            print(f"   Active: {record.get('Active', 'N/A')}")
            
            # Show any other date fields
            for field in date_fields:
                if field not in ['StartDate', 'EndDate'] and record.get(field):
                    print(f"   {field}: {record.get(field)}")
        
        # Check UNA1 specifically
        print(f"\n🎯 CHECKING YOUR CURRENT PRICE LIST (UNA1):")
        print("=" * 80)
        
        una1_url = f"{BASE_URL}/{COMPANY_ID}/Erp.BO.PriceLstSvc/PriceLsts"
        una1_params = {"$filter": "ListCode eq 'UNA1'"}
        
        una1_response = requests.get(una1_url, headers=get_headers(), params=una1_params, timeout=10)
        
        if una1_response.status_code == 200:
            una1_data = una1_response.json()
            una1_results = una1_data.get("value", [])
            
            if una1_results:
                una1 = una1_results[0]
                print(f"\n✅ Found UNA1 price list")
                print(f"   ListCode: {una1.get('ListCode')}")
                print(f"   Description: {una1.get('ListDescription')}")
                print(f"   StartDate: {una1.get('StartDate')}")
                print(f"   EndDate: {una1.get('EndDate')}")
                
                # Show ALL fields
                print(f"\n   📋 All fields in UNA1:")
                for key, value in sorted(una1.items()):
                    if value and key not in ['SysRowID', 'SysRevID', 'RowMod']:
                        print(f"      {key}: {value}")
            else:
                print("\n❌ UNA1 not found")
        
        # Show all fields
        print(f"\n📋 ALL FIELDS IN PriceLsts:")
        print("=" * 80)
        for i, field in enumerate(sorted(all_fields), 1):
            print(f"   {i:3d}. {field}")
    
    else:
        print("\n❌ No price lists found")
else:
    print(f"\n❌ Error: {response.status_code}")
    print(f"Response: {response.text[:500]}")

# Summary
print("\n" + "=" * 80)
print("📊 ANALYSIS")
print("=" * 80)
print("""
PriceLsts Entity (Price List Headers):
- This is the HEADER table for price lists
- Contains StartDate and EndDate for the ENTIRE price list
- Individual parts (PriceLstParts) inherit these dates

How Epicor Handles Effective Dates:
1. Price List Level (PriceLsts):
   - StartDate: When the entire price list becomes active
   - EndDate: When the entire price list expires
   
2. Part Level (PriceLstParts):
   - NO individual effective dates (as we discovered)
   - Uses the price list's StartDate/EndDate

Implications for Your Use Case:
❌ You CANNOT set different effective dates for individual parts
❌ All parts in a price list share the same StartDate/EndDate
❌ To have different effective dates, you'd need MULTIPLE price lists

Possible Solutions:
1. Create date-based price lists (e.g., "UNA1-2025-10-20")
2. Use custom UD fields on PriceLstParts (EffectiveDate_c)
3. Store effective dates externally in your application
4. Update prices immediately without effective dates

Recommendation:
→ Store effective dates in your application database
→ Update Epicor prices immediately (no future dating)
→ Track intended effective dates for audit/reporting
""")

print("\n" + "=" * 80)

