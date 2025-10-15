"""
Test script for the new Epicor Price Update Workflow
Tests the complete workflow as described in Epicor_Price_Update_Workflow.md
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.epicor_service import epicor_service
import json

def test_supplier_part_verification():
    """Test Step 3: Verify Supplier-Part Link"""
    print("\n" + "="*80)
    print("TEST 1: Supplier-Part Verification")
    print("="*80)
    
    # Test data from workflow document
    supplier_id = "FAST1"
    part_num = "#FFH06-12SAE F"
    
    print(f"\n🔍 Testing supplier-part verification...")
    print(f"   Supplier ID: {supplier_id}")
    print(f"   Part Number: {part_num}")
    
    result = epicor_service.verify_supplier_part(supplier_id, part_num)
    
    if result:
        print(f"\n✅ SUCCESS: Supplier-part relationship verified")
        print(f"   VendorNum: {result.get('VendorNum')}")
        print(f"   VendorName: {result.get('VendorName')}")
        print(f"   VendorVendorID: {result.get('VendorVendorID')}")
        print(f"   PartNum: {result.get('PartNum')}")
        return True
    else:
        print(f"\n❌ FAILED: Supplier-part relationship not found")
        print(f"   This could mean:")
        print(f"   - The supplier-part mapping doesn't exist in Epicor")
        print(f"   - The supplier ID or part number is incorrect")
        print(f"   - API permissions are insufficient")
        return False

def test_price_list_query():
    """Test Step 4: Query Price List"""
    print("\n" + "="*80)
    print("TEST 2: Price List Query")
    print("="*80)
    
    part_num = "#FFH06-12SAE F"
    
    print(f"\n🔍 Testing price list query...")
    print(f"   Part Number: {part_num}")
    
    result = epicor_service.get_price_list_parts(part_num)
    
    if result:
        print(f"\n✅ SUCCESS: Found {len(result)} price list entries")
        for i, entry in enumerate(result, 1):
            print(f"\n   Entry {i}:")
            print(f"      ListCode: {entry.get('ListCode')}")
            print(f"      PartNum: {entry.get('PartNum')}")
            print(f"      UOMCode: {entry.get('UOMCode')}")
            print(f"      BasePrice: {entry.get('BasePrice')}")
            print(f"      EffectiveDate: {entry.get('EffectiveDate')}")
        return True
    else:
        print(f"\n❌ FAILED: No price list entries found")
        return False

def test_price_list_update():
    """Test Step 4: Update Price List with Effective Date"""
    print("\n" + "="*80)
    print("TEST 3: Price List Update with Effective Date")
    print("="*80)
    
    # Test data from workflow document
    list_code = "SUPPLIER001"  # You'll need to use actual ListCode from your system
    part_num = "TEST-001"
    new_price = 130.00
    effective_date = "2025-10-20"
    uom_code = "EA"
    
    print(f"\n🔍 Testing price list update...")
    print(f"   ListCode: {list_code}")
    print(f"   Part Number: {part_num}")
    print(f"   New Price: ${new_price}")
    print(f"   Effective Date: {effective_date}")
    print(f"   UOM Code: {uom_code}")
    
    print(f"\n⚠️  NOTE: This test will attempt to update actual data in Epicor")
    print(f"   Make sure you're using a test part or test environment!")
    
    response = input("\n   Continue with update? (yes/no): ")
    if response.lower() != 'yes':
        print("   ⏭️  Test skipped by user")
        return None
    
    result = epicor_service.update_price_list(
        list_code=list_code,
        part_num=part_num,
        new_price=new_price,
        effective_date=effective_date,
        uom_code=uom_code
    )
    
    if result["status"] == "success":
        print(f"\n✅ SUCCESS: Price list updated")
        print(f"   Old Price: ${result.get('old_price')}")
        print(f"   New Price: ${result.get('new_price')}")
        print(f"   Effective Date: {result.get('effective_date')}")
        return True
    else:
        print(f"\n❌ FAILED: {result.get('message')}")
        return False

def test_complete_workflow():
    """Test Complete Workflow: Supplier Verification → Price Update"""
    print("\n" + "="*80)
    print("TEST 4: Complete Workflow")
    print("="*80)
    
    # Test data
    supplier_id = "FAST1"
    part_num = "#FFH06-12SAE F"
    new_price = 130.00
    effective_date = "2025-10-20"
    
    print(f"\n🚀 Testing complete workflow...")
    print(f"   Supplier ID: {supplier_id}")
    print(f"   Part Number: {part_num}")
    print(f"   New Price: ${new_price}")
    print(f"   Effective Date: {effective_date}")
    
    print(f"\n⚠️  NOTE: This test will attempt to update actual data in Epicor")
    print(f"   Make sure you're using a test part or test environment!")
    
    response = input("\n   Continue with complete workflow test? (yes/no): ")
    if response.lower() != 'yes':
        print("   ⏭️  Test skipped by user")
        return None
    
    result = epicor_service.update_supplier_part_price(
        supplier_id=supplier_id,
        part_num=part_num,
        new_price=new_price,
        effective_date=effective_date
    )
    
    if result["status"] == "success":
        print(f"\n✅ SUCCESS: Complete workflow executed successfully")
        print(f"\n   📋 Results:")
        print(f"      Supplier ID: {result.get('supplier_id')}")
        print(f"      Vendor Num: {result.get('vendor_num')}")
        print(f"      Vendor Name: {result.get('vendor_name')}")
        print(f"      Part Number: {result.get('part_num')}")
        print(f"      List Code: {result.get('list_code')}")
        print(f"      Old Price: ${result.get('old_price')}")
        print(f"      New Price: ${result.get('new_price')}")
        print(f"      Effective Date: {result.get('effective_date')}")
        return True
    else:
        print(f"\n❌ FAILED: {result.get('message')}")
        print(f"   Step Failed: {result.get('step_failed', 'Unknown')}")
        return False

def test_extraction_schema():
    """Test that extraction includes supplier_id"""
    print("\n" + "="*80)
    print("TEST 5: Extraction Schema Validation")
    print("="*80)
    
    print(f"\n🔍 Checking extraction prompt schema...")
    
    # Read extractor.py to verify schema
    try:
        with open('extractor.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
        checks = {
            "supplier_id in schema": '"supplier_id": string' in content,
            "supplier_id instruction": 'SUPPLIER ID' in content or 'supplier_id' in content,
            "effective_date in schema": '"effective_date": string' in content
        }
        
        print(f"\n   Schema Checks:")
        all_passed = True
        for check_name, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"      {status} {check_name}")
            if not passed:
                all_passed = False
        
        if all_passed:
            print(f"\n✅ SUCCESS: Extraction schema is correctly configured")
            return True
        else:
            print(f"\n❌ FAILED: Some schema checks failed")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: Could not read extractor.py: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("EPICOR PRICE UPDATE WORKFLOW - TEST SUITE")
    print("Testing implementation against Epicor_Price_Update_Workflow.md")
    print("="*80)
    
    # Test connection first
    print("\n🔌 Testing Epicor API connection...")
    connection_result = epicor_service.test_connection()
    
    if connection_result["status"] != "success":
        print(f"❌ Connection failed: {connection_result.get('message')}")
        print(f"\n⚠️  Cannot proceed with tests without API connection")
        return
    
    print(f"✅ Connection successful")
    
    # Run tests
    results = {}
    
    # Test 5: Extraction schema (non-API test)
    results["extraction_schema"] = test_extraction_schema()
    
    # Test 1: Supplier-part verification
    results["supplier_verification"] = test_supplier_part_verification()
    
    # Test 2: Price list query
    results["price_list_query"] = test_price_list_query()
    
    # Test 3: Price list update (requires user confirmation)
    results["price_list_update"] = test_price_list_update()
    
    # Test 4: Complete workflow (requires user confirmation)
    results["complete_workflow"] = test_complete_workflow()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, result in results.items():
        if result is True:
            status = "✅ PASSED"
        elif result is False:
            status = "❌ FAILED"
        else:
            status = "⏭️  SKIPPED"
        print(f"   {status}: {test_name}")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    main()

