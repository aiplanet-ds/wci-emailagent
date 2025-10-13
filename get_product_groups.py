"""
Get available Product Groups from Epicor
"""

import requests
from services.epicor_service import epicor_service

print("=" * 70)
print("📋 Get Product Groups from Epicor")
print("=" * 70)

# Get Product Groups
url = f"{epicor_service.base_url}/{epicor_service.company_id}/Erp.BO.ProdGrupSvc/ProdGrups"
headers = epicor_service._get_headers()

print(f"\n🔍 Fetching Product Groups...")
print(f"URL: {url}")
print()

try:
    response = requests.get(url, headers=headers, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        prod_groups = data.get("value", [])
        
        if prod_groups:
            print(f"✅ Found {len(prod_groups)} Product Groups:")
            print("-" * 70)
            
            for i, pg in enumerate(prod_groups, 1):
                group_id = pg.get("ProdCode", "N/A")
                description = pg.get("Description", "No description")
                
                print(f"\n{i}. Product Group: {group_id}")
                print(f"   Description: {description}")
            
            print("\n" + "=" * 70)
            print("💡 To create a part with a product group, use:")
            print("=" * 70)
            
            # Show first group as example
            if prod_groups:
                example_group = prod_groups[0].get("ProdCode")
                print(f"\nExample:")
                print(f"  python create_test_part.py")
                print(f"  When prompted for Product Group, enter: {example_group}")
            
        else:
            print("⚠️ No Product Groups found")
            print("\n💡 This might mean:")
            print("   1. No Product Groups are configured in Epicor")
            print("   2. You don't have permission to view them")
            print("   3. The endpoint URL is incorrect")
    
    else:
        print(f"❌ Failed to get Product Groups: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        print("\n💡 Alternative: Check Epicor manually")
        print("   1. Open Epicor ERP")
        print("   2. Go to: Product Configuration → Product Group Maintenance")
        print("   3. Note the Product Group IDs")
        print("   4. Use one when creating a part")

except Exception as e:
    print(f"❌ Error: {e}")
    
    print("\n💡 Manual steps:")
    print("   1. Open Epicor ERP")
    print("   2. Go to: Product Configuration → Product Group Maintenance")
    print("   3. Find an active Product Group")
    print("   4. Note the Product Group ID")
    print("   5. Use it when creating a part")

print("\n" + "=" * 70)
print("🏁 Done")
print("=" * 70)

