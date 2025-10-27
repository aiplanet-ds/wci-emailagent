"""
Test script to verify the ListType fix for price list creation
"""

from services.epicor_service import epicor_service

print("=" * 80)
print("TESTING LISTTYPE FIX - PRICE LIST CREATION")
print("=" * 80)

# Test with the FAST1 supplier that was failing before
test_supplier_id = "FAST1"
test_supplier_name = "Faster Inc. (Indiana)"
test_effective_date = "2025-10-28"

print(f"\nTest Parameters:")
print(f"  Supplier ID: {test_supplier_id}")
print(f"  Supplier Name: {test_supplier_name}")
print(f"  Effective Date: {test_effective_date}")

print("\n" + "=" * 80)
print("TEST: Get or Create Supplier Price List")
print("=" * 80)

print("\nExpected behavior:")
print("  1. Search for existing price list for FAST1")
print("  2. If not found, create new price list with:")
print("     - ListCode: FAST1 (5 chars, within 10-char limit)")
print("     - ListDescription: PL: Faster Inc. (Indiana) (25 chars, within 30-char limit)")
print("     - ListType: 'B' (FIXED - was missing before)")
print("     - StartDate: 2025-10-28T00:00:00")

print("\nCalling get_or_create_supplier_price_list...")
print("-" * 80)

result = epicor_service.get_or_create_supplier_price_list(
    supplier_id=test_supplier_id,
    supplier_name=test_supplier_name,
    effective_date=test_effective_date
)

print("-" * 80)
print("\n" + "=" * 80)
print("RESULT")
print("=" * 80)

status = result.get("status")
print(f"\nStatus: {status}")
print(f"Message: {result.get('message')}")
print(f"List Code: {result.get('list_code')}")
print(f"Created: {result.get('created', False)}")

if status == "success":
    print("\n" + "=" * 80)
    print("SUCCESS!")
    print("=" * 80)

    if result.get('created'):
        print("\nA new price list was created successfully!")
        print("\nKey fixes applied:")
        print("  1. ListCode length: <= 10 chars")
        print("  2. Description length: <= 30 chars")
        print("  3. ListType field: 'B' (NOW INCLUDED)")
        print("  4. Search before create: Checked for existing lists first")
    else:
        print("\nAn existing price list was found and will be reused!")
        print(f"Using existing list: {result.get('list_code')}")

    print(f"\nYou can now use this price list to add parts:")
    print(f"  List Code: {result.get('list_code')}")

else:
    print("\n" + "=" * 80)
    print("FAILED")
    print("=" * 80)

    print(f"\nError: {result.get('message')}")
    print(f"Status Code: {result.get('status_code', 'N/A')}")

    if "ListType" in result.get('message', ''):
        print("\nThe ListType error is still occurring!")
        print("This may indicate:")
        print("  1. The 'B' value is not valid for your Epicor instance")
        print("  2. Additional fields may be required")
        print("  3. Authentication or permission issues")
    elif "10" in result.get('message', '') or "30" in result.get('message', ''):
        print("\nField length error still occurring!")
        print("Check the ListCode or ListDescription length")
    else:
        print("\nUnexpected error - check the error message above")

print("\n" + "=" * 80)
print("Test complete!")
print("=" * 80)
