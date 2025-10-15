"""
Test the hybrid workflow (NEW with fallback to OLD)
"""

from services.epicor_service import epicor_service

print("=" * 80)
print("🧪 TESTING HYBRID WORKFLOW")
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
    print(f"   Old Price: ${result.get('old_price')}")
    print(f"   New Price: ${result.get('new_price')}")
    print(f"   Effective Date: {result.get('effective_date')}")
    
    if result.get('workflow') == 'PartSvc (fallback)':
        print(f"\n⚠️  NOTE: {result.get('note')}")
        print(f"   To enable effective dates, add this part to a price list in Epicor")
else:
    print(f"\n❌ FAILED")
    print(f"   Error: {result.get('message')}")
    print(f"   Failed at: {result.get('step_failed')}")

print("\n" + "=" * 80)
print("✅ Test complete!")
print("=" * 80)

