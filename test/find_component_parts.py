"""
Script to find component parts from Epicor that are used in assemblies.
This helps identify good test candidates for BOM impact analysis.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.epicor_service import epicor_service
import requests
from dotenv import load_dotenv

load_dotenv()

def find_component_parts():
    """Find parts that are used as components in BOMs"""

    print("="*80)
    print("🔍 SEARCHING FOR COMPONENT PARTS IN EPICOR")
    print("="*80)

    base_url = os.getenv('EPICOR_BASE_URL')
    company_id = os.getenv('EPICOR_COMPANY_ID')
    api_key = os.getenv('EPICOR_API_KEY')

    # Get fresh token
    from services.epicor_auth import epicor_auth
    token = epicor_auth.get_valid_token()

    headers = {
        'Authorization': f'Bearer {token}',
        'X-API-Key': api_key,
        'Content-Type': 'application/json'
    }

    parts_to_check = []

    # Method 1: Query PartMtl (BOM Materials) to find parts that ARE components
    print("\n📋 Method 1: Querying BOM Materials (PartMtl) for component parts...")
    print("-"*80)

    url = f'{base_url}/{company_id}/Erp.BO.EngWorkBenchSvc/PartMtls'
    params = {
        '$top': 50,
        '$select': 'MtlPartNum,PartNum,QtyPer,PartDescription'
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        print(f"   PartMtl query status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            mtl_records = data.get('value', [])
            print(f"   Found {len(mtl_records)} BOM material records")

            # Extract unique component part numbers
            seen = set()
            for mtl in mtl_records:
                mtl_part = mtl.get('MtlPartNum')
                parent_part = mtl.get('PartNum')
                if mtl_part and mtl_part not in seen:
                    seen.add(mtl_part)
                    parts_to_check.append({
                        'PartNum': mtl_part,
                        'PartDescription': mtl.get('PartDescription', 'N/A'),
                        'TypeCode': 'Component',
                        'ParentAssembly': parent_part
                    })
                    print(f"   ✅ {mtl_part} (used in {parent_part})")
        else:
            print(f"   Response: {response.text[:300]}")
    except Exception as e:
        print(f"   ⚠️ Error: {e}")

    # Method 2: Try ECOMtl (Engineering Change BOM)
    if not parts_to_check:
        print("\n📋 Method 2: Trying ECOMtl endpoint...")
        print("-"*80)

        url = f'{base_url}/{company_id}/Erp.BO.ECOMtlSearchSvc/ECOMtlSearches'
        params = {'$top': 30}

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            print(f"   ECOMtl query status: {response.status_code}")
        except Exception as e:
            print(f"   ⚠️ Error: {e}")

    # Method 3: Query PartRev for assemblies, then get their materials
    if not parts_to_check:
        print("\n📋 Method 3: Querying Part Revisions...")
        print("-"*80)

        url = f'{base_url}/{company_id}/Erp.BO.PartSvc/PartRevs'
        params = {
            '$top': 20,
            '$select': 'PartNum,RevisionNum,RevDescription'
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            print(f"   PartRev query status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                revs = data.get('value', [])
                print(f"   Found {len(revs)} part revisions")

                for rev in revs[:10]:
                    part_num = rev.get('PartNum')
                    print(f"   - {part_num} (Rev: {rev.get('RevisionNum')})")

                    # Check if this part is used anywhere
                    parents = epicor_service.get_part_where_used(part_num)
                    if parents:
                        parts_to_check.append({
                            'PartNum': part_num,
                            'PartDescription': rev.get('RevDescription', 'N/A'),
                            'TypeCode': 'HasParents'
                        })
                        print(f"     ✅ Used in {len(parents)} assemblies!")
        except Exception as e:
            print(f"   ⚠️ Error: {e}")

    parts = parts_to_check
    
    print(f"\nFound {len(parts)} parts. Checking which ones are used in BOMs...\n")
    print("-"*80)
    
    components_found = []
    
    for part in parts:
        part_num = part.get('PartNum')
        description = part.get('PartDescription', 'N/A')[:40]
        type_code = part.get('TypeCode', 'N/A')
        
        # Check if this part is used in any assemblies
        parents = epicor_service.get_part_where_used(part_num)
        
        if parents and len(parents) > 0:
            components_found.append({
                'part_num': part_num,
                'description': description,
                'type_code': type_code,
                'parent_count': len(parents),
                'sample_parents': [p.get('PartNum') for p in parents[:3]]
            })
            print(f"✅ {part_num}")
            print(f"   Description: {description}")
            print(f"   Type: {type_code}")
            print(f"   Used in {len(parents)} assemblies: {[p.get('PartNum') for p in parents[:3]]}")
            print()
        else:
            print(f"❌ {part_num} - Not used in any assemblies")
    
    print("\n" + "="*80)
    print("📋 SUMMARY: PARTS THAT ARE USED AS COMPONENTS")
    print("="*80)
    
    if components_found:
        print(f"\nFound {len(components_found)} parts that are used in assemblies:\n")
        for i, comp in enumerate(components_found, 1):
            print(f"{i}. {comp['part_num']}")
            print(f"   Used in {comp['parent_count']} assemblies")
            print(f"   Sample parents: {comp['sample_parents']}")
            print()
        
        # Recommend the best candidate (most parent assemblies)
        best = max(components_found, key=lambda x: x['parent_count'])
        print("-"*80)
        print(f"🎯 RECOMMENDED TEST COMPONENT: {best['part_num']}")
        print(f"   This part is used in {best['parent_count']} assemblies")
        print("-"*80)
    else:
        print("\n⚠️ No component parts found that are used in assemblies.")
        print("   Try adjusting the search criteria.")

if __name__ == "__main__":
    find_component_parts()

