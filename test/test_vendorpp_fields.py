"""
Test script to check ALL fields in VendorPP entity
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
print("🔍 DETAILED CHECK OF VendorPP ENTITY")
print("=" * 80)

# Query VendorPP for vendor 204 (FAST1)
url = f"{BASE_URL}/{COMPANY_ID}/Erp.BO.VendorSvc/VendorPPs"
params = {
    "$filter": "VendorNum eq 204",
    "$top": 5
}

print(f"\n📡 Query: GET {url}")
print(f"Filter: {params['$filter']}")

response = requests.get(url, headers=get_headers(), params=params, timeout=10)

print(f"\nStatus: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    results = data.get("value", [])
    
    print(f"\n✅ Found {len(results)} VendorPP records for VendorNum=204")
    
    if results:
        # Analyze first record
        first_record = results[0]
        all_fields = list(first_record.keys())
        
        print(f"\n📊 Total fields in VendorPP: {len(all_fields)}")
        
        # Check for EffectiveDate
        print(f"\n🎯 Checking for EffectiveDate:")
        if 'EffectiveDate' in all_fields:
            print(f"   ✅ EffectiveDate EXISTS!")
        else:
            print(f"   ❌ EffectiveDate NOT FOUND")
        
        # Show ALL date-related fields
        date_fields = [f for f in all_fields if 'date' in f.lower() or 'Date' in f]
        print(f"\n📅 ALL Date-related fields ({len(date_fields)}):")
        for field in sorted(date_fields):
            value = first_record.get(field)
            print(f"   - {field}: {value}")
        
        # Show ALL price-related fields
        price_fields = [f for f in all_fields if 'price' in f.lower() or 'Price' in f or 'cost' in f.lower() or 'Cost' in f]
        print(f"\n💰 ALL Price/Cost-related fields ({len(price_fields)}):")
        for field in sorted(price_fields):
            value = first_record.get(field)
            print(f"   - {field}: {value}")
        
        # Show part-related fields
        part_fields = [f for f in all_fields if 'part' in f.lower() or 'Part' in f]
        print(f"\n📦 Part-related fields ({len(part_fields)}):")
        for field in sorted(part_fields):
            value = first_record.get(field)
            print(f"   - {field}: {value}")
        
        # Show vendor-related fields
        vendor_fields = [f for f in all_fields if 'vendor' in f.lower() or 'Vendor' in f or 'Vend' in f]
        print(f"\n🏢 Vendor-related fields ({len(vendor_fields)}):")
        for field in sorted(vendor_fields):
            value = first_record.get(field)
            print(f"   - {field}: {value}")
        
        # Show ALL fields with their values
        print(f"\n📋 ALL FIELDS IN VendorPP ({len(all_fields)}):")
        print("=" * 80)
        for i, field in enumerate(sorted(all_fields), 1):
            value = first_record.get(field)
            # Truncate long values
            if isinstance(value, str) and len(value) > 50:
                value = value[:50] + "..."
            print(f"   {i:3d}. {field:40s} = {value}")
        
        # Show all records summary
        print(f"\n📊 ALL RECORDS SUMMARY:")
        print("=" * 80)
        for i, record in enumerate(results, 1):
            print(f"\nRecord {i}:")
            print(f"   VendorNum: {record.get('VendorNum')}")
            print(f"   PurPoint: {record.get('PurPoint')}")
            print(f"   Name: {record.get('Name')}")
            
            # Show any date fields
            for field in date_fields:
                if record.get(field):
                    print(f"   {field}: {record.get(field)}")
            
            # Show any price fields
            for field in price_fields:
                if record.get(field):
                    print(f"   {field}: {record.get(field)}")
    else:
        print("\n❌ No VendorPP records found for VendorNum=204")
else:
    print(f"\n❌ Error: {response.status_code}")
    print(f"Response: {response.text[:500]}")

# Check metadata for VendorPP
print("\n" + "=" * 80)
print("🔍 CHECKING EPICOR METADATA FOR VendorPP")
print("=" * 80)

metadata_url = f"{BASE_URL}/{COMPANY_ID}/$metadata"
print(f"\n📡 Fetching metadata from: {metadata_url}")

try:
    metadata_response = requests.get(metadata_url, headers=get_headers(), timeout=30)
    
    if metadata_response.status_code == 200:
        metadata_xml = metadata_response.text
        
        # Search for VendorPP entity definition
        if 'EntityType Name="VendorPP"' in metadata_xml or 'EntityType Name="Erp.Tablesets.VendorPPRow"' in metadata_xml:
            print("\n✅ Found VendorPP in metadata")
            
            # Extract VendorPP section
            start_marker = 'EntityType Name="VendorPP"'
            if start_marker not in metadata_xml:
                start_marker = 'EntityType Name="Erp.Tablesets.VendorPPRow"'
            
            start_idx = metadata_xml.find(start_marker)
            if start_idx != -1:
                # Find the closing tag
                end_idx = metadata_xml.find('</EntityType>', start_idx)
                vendorpp_section = metadata_xml[start_idx:end_idx + 13]
                
                # Check for EffectiveDate in metadata
                if 'EffectiveDate' in vendorpp_section:
                    print("   🎯 ✅ EffectiveDate found in metadata!")
                    
                    # Extract the property definition
                    eff_date_start = vendorpp_section.find('Property Name="EffectiveDate"')
                    if eff_date_start != -1:
                        eff_date_end = vendorpp_section.find('/>', eff_date_start)
                        eff_date_def = vendorpp_section[eff_date_start:eff_date_end + 2]
                        print(f"   Definition: <{eff_date_def}")
                else:
                    print("   ❌ EffectiveDate NOT in metadata")
                
                # Look for other date properties
                print("\n   📅 Date properties in metadata:")
                for line in vendorpp_section.split('\n'):
                    if 'Property Name=' in line and ('Date' in line or 'date' in line):
                        # Extract property name
                        prop_start = line.find('Property Name="') + 15
                        prop_end = line.find('"', prop_start)
                        prop_name = line[prop_start:prop_end]
                        print(f"      - {prop_name}")
        else:
            print("\n⚠️  VendorPP not found in metadata")
    else:
        print(f"\n⚠️  Could not fetch metadata: {metadata_response.status_code}")
except Exception as e:
    print(f"\n⚠️  Error fetching metadata: {e}")

# Summary
print("\n" + "=" * 80)
print("📊 SUMMARY")
print("=" * 80)
print("""
VendorPP Entity Analysis:
- This entity represents Vendor Purchase Points (shipping/receiving locations)
- It's a child entity of Vendor in the VendorSvc

Key Findings:
1. VendorPP EXISTS in your Epicor instance ✅
2. Check above for EffectiveDate field
3. Check date fields for alternatives (ExpirationDate, StartDate, etc.)
4. Check price fields for pricing information

If EffectiveDate is NOT in VendorPP, we need to look elsewhere:
- Maybe in PartPlant (part-plant supplier info)
- Maybe in PurMisc (purchase miscellaneous)
- Maybe stored externally or not supported
""")

print("\n" + "=" * 80)

