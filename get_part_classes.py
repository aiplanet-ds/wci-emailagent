"""
Get available Part Classes from Epicor
"""

import requests
from services.epicor_service import epicor_service

print("=" * 70)
print("📋 Get Part Classes from Epicor")
print("=" * 70)

# Get Part Classes
url = f"{epicor_service.base_url}/{epicor_service.company_id}/Erp.BO.PartClassSvc/PartClasses"
headers = epicor_service._get_headers()

print(f"\n🔍 Fetching Part Classes...")
print(f"URL: {url}")
print()

try:
    response = requests.get(url, headers=headers, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        part_classes = data.get("value", [])
        
        if part_classes:
            print(f"✅ Found {len(part_classes)} Part Classes:")
            print("-" * 70)
            
            for i, pc in enumerate(part_classes, 1):
                class_id = pc.get("ClassID", "N/A")
                description = pc.get("Description", "No description")
                active = pc.get("InActive", False)
                status = "❌ Inactive" if active else "✅ Active"
                
                print(f"\n{i}. Class ID: {class_id}")
                print(f"   Description: {description}")
                print(f"   Status: {status}")
            
            print("\n" + "=" * 70)
            print("💡 To create a part with a class, use:")
            print("=" * 70)
            
            # Show first active class as example
            active_classes = [pc for pc in part_classes if not pc.get("InActive", False)]
            if active_classes:
                example_class = active_classes[0].get("ClassID")
                print(f"\nExample:")
                print(f"  python create_test_part.py")
                print(f"  When prompted for Part Class, enter: {example_class}")
            
        else:
            print("⚠️ No Part Classes found")
            print("\n💡 This might mean:")
            print("   1. No Part Classes are configured in Epicor")
            print("   2. You don't have permission to view them")
            print("   3. The endpoint URL is incorrect")
    
    else:
        print(f"❌ Failed to get Part Classes: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        print("\n💡 Alternative: Check Epicor manually")
        print("   1. Open Epicor ERP")
        print("   2. Go to: Product Configuration → Part Class Maintenance")
        print("   3. Note the Class IDs")
        print("   4. Use one when creating a part")

except Exception as e:
    print(f"❌ Error: {e}")
    
    print("\n💡 Manual steps:")
    print("   1. Open Epicor ERP")
    print("   2. Go to: Product Configuration → Part Class Maintenance")
    print("   3. Find an active Part Class")
    print("   4. Note the Class ID")
    print("   5. Use it when creating a part")

print("\n" + "=" * 70)
print("🏁 Done")
print("=" * 70)

