"""
Test automatic price list entry creation
"""

from services.epicor_service import epicor_service

print("=" * 80)
print("🧪 TESTING AUTOMATIC PRICE LIST ENTRY CREATION")
print("=" * 80)

# Test with the part that's NOT in price list
test_supplier_id = "FAST1"
test_part_num = "#FFH06-12SAE F"
test_price = 130.0
test_effective_date = "2025-10-20"

print(f"\nTest data:")
print(f"  Supplier ID: {test_supplier_id}")
print(f"  Part Number: {test_part_num}")
print(f"  New Price: ${test_price}")
print(f"  Effective Date: {test_effective_date}")
print()

print("=" * 80)
print("🔄 Running update_supplier_part_price...")
print("=" * 80)
print("\nExpected flow:")
print("  1. ✅ Verify supplier-part relationship")
print("  2. ⚠️  Find no price list entries")
print("  3. 📝 Create new price list entry")
print("  4. ✅ Return success with new entry")
print()

result = epicor_service.update_supplier_part_price(
    supplier_id=test_supplier_id,
    part_num=test_part_num,
    new_price=test_price,
    effective_date=test_effective_date
)

print("\n" + "=" * 80)
print("📋 RESULT")
print("=" * 80)

print(f"\nStatus: {result.get('status')}")
print(f"Message: {result.get('message')}")
print(f"Workflow: {result.get('workflow')}")

if result.get('status') == 'success':
    print(f"\n✅ SUCCESS!")
    print(f"   Part: {result.get('part_num')}")
    print(f"   Supplier: {result.get('supplier_id')} ({result.get('vendor_name')})")
    print(f"   New Price: ${result.get('new_price')}")
    print(f"   Effective Date: {result.get('effective_date')}")
    print(f"   List Code: {result.get('list_code')}")
    
    if result.get('workflow') == 'PriceLstSvc (created new entry)':
        print(f"\n🎉 Price list entry was automatically created!")
        print(f"   The part is now in the price list and can be updated in the future")
else:
    print(f"\n❌ FAILED")
    print(f"   Error: {result.get('message')}")
    print(f"   Failed at: {result.get('step_failed')}")
    
    if 'create_price_list_entry' in result.get('step_failed', ''):
        print(f"\n💡 TROUBLESHOOTING:")
        print(f"   - Check if the 'BASE' price list exists in Epicor")
        print(f"   - Check if API user has POST permissions for PriceLstSvc")
        print(f"   - Check if the part exists in Epicor (PartSvc)")
        print(f"   - Review the error message above for details")

print("\n" + "=" * 80)
print("✅ Test complete!")
print("=" * 80)

