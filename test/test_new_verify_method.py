"""
Test the updated verify_supplier_part method with 2-step approach
"""

from services.epicor_service import epicor_service

print("=" * 80)
print("🧪 TESTING UPDATED verify_supplier_part METHOD")
print("=" * 80)

# Test with known data from previous diagnostic
test_supplier_id = "FAST1"
test_part_num = "#FFH06-12SAE F"

print(f"\nTest data:")
print(f"  Supplier ID: {test_supplier_id}")
print(f"  Part Number: {test_part_num}")
print()

print("=" * 80)
print("🔄 Running verify_supplier_part...")
print("=" * 80)

result = epicor_service.verify_supplier_part(test_supplier_id, test_part_num)

print("\n" + "=" * 80)
print("📋 RESULT")
print("=" * 80)

if result:
    print("\n✅ SUCCESS! Supplier-part relationship verified!")
    print(f"\nReturned data:")
    print(f"  Company: {result.get('Company')}")
    print(f"  PartNum: {result.get('PartNum')}")
    print(f"  VendorNum: {result.get('VendorNum')}")
    print(f"  VendorVendorID: {result.get('VendorVendorID')}")
    print(f"  VendorName: {result.get('VendorName')}")
    print(f"  VendPartNum: {result.get('VendPartNum')}")
    print(f"  LeadTime: {result.get('LeadTime')}")
    print(f"  PurchaseDefault: {result.get('PurchaseDefault')}")
    
    print("\n✅ The 2-step approach works perfectly!")
    print("   Step 1: Looked up VendorNum from VendorID")
    print("   Step 2: Queried SupplierPartSvc with VendorNum")
else:
    print("\n❌ FAILED - Supplier-part relationship not found")
    print("\nPossible reasons:")
    print("  1. Supplier ID doesn't exist in Epicor")
    print("  2. Part is not set up for this supplier")
    print("  3. API permissions issue")

print("\n" + "=" * 80)
print("✅ Test complete!")
print("=" * 80)

