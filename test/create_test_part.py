"""
Create a test part in Epicor using REST API v2
"""

from services.epicor_service import epicor_service
import json

print("=" * 70)
print("🔧 Create Test Part in Epicor")
print("=" * 70)

# Default values (USA standards)
DEFAULT_PART_NUM = "TEST-001"
DEFAULT_DESCRIPTION = "Test Part for Email Integration"
DEFAULT_PART_TYPE = "P"  # P = Purchased
DEFAULT_PRICE = 100.00
DEFAULT_IUM = "EA"  # Each
DEFAULT_PUM = "EA"  # Each
DEFAULT_PRICE_PER_CODE = "E"  # Each
DEFAULT_PART_CLASS = "R150"  # OTHER (generic class)
DEFAULT_PRODUCT_GROUP = "CF030025"  # CF - UNASSIGNED

print("\n📝 Part Configuration")
print("-" * 70)
print("Press Enter to use default values shown in [brackets]")
print()

# Get part details from user
part_num = input(f"Part Number [{DEFAULT_PART_NUM}]: ").strip() or DEFAULT_PART_NUM
description = input(f"Description [{DEFAULT_DESCRIPTION}]: ").strip() or DEFAULT_DESCRIPTION

print("\nPart Type Options:")
print("  P = Purchased (default)")
print("  M = Manufactured")
print("  S = Sales Kit")
print("  O = Other")
part_type = input(f"Part Type [{DEFAULT_PART_TYPE}]: ").strip().upper() or DEFAULT_PART_TYPE

price_input = input(f"Initial Unit Price [{DEFAULT_PRICE}]: ").strip()
try:
    unit_price = float(price_input.replace("$", "").replace(",", "")) if price_input else DEFAULT_PRICE
except ValueError:
    print(f"⚠️ Invalid price, using default: ${DEFAULT_PRICE}")
    unit_price = DEFAULT_PRICE

print("\nUnit of Measure Options:")
print("  EA = Each (default)")
print("  LB = Pound")
print("  KG = Kilogram")
print("  FT = Foot")
print("  M = Meter")
ium = input(f"Inventory Unit of Measure [{DEFAULT_IUM}]: ").strip().upper() or DEFAULT_IUM
pum = input(f"Purchasing Unit of Measure [{DEFAULT_PUM}]: ").strip().upper() or DEFAULT_PUM

print("\nPrice Per Code Options:")
print("  E = Each (default)")
print("  C = Per 100")
print("  M = Per 1000")
print("  T = Per Ton")
price_per_code = input(f"Price Per Code [{DEFAULT_PRICE_PER_CODE}]: ").strip().upper() or DEFAULT_PRICE_PER_CODE

print("\nPart Class (REQUIRED by Epicor):")
print("  Common options:")
print("  R150 = OTHER (default)")
print("  R050 = HARDWARE")
print("  R110 = PLASTIC")
print("  R130 = METAL")
print("  R080 = INDIRECT")
print("  (Run 'python get_part_classes.py' to see all 87 classes)")
part_class = input(f"Part Class [{DEFAULT_PART_CLASS}]: ").strip().upper() or DEFAULT_PART_CLASS

print("\nProduct Group (REQUIRED by Epicor):")
print("  Common options:")
print("  CF030025 = CF - UNASSIGNED (default)")
print("  AH010013 = AUG - Unassigned")
print("  DM010057 = DM - N/A")
print("  (Run 'python get_product_groups.py' to see all 100 groups)")
product_group = input(f"Product Group [{DEFAULT_PRODUCT_GROUP}]: ").strip().upper() or DEFAULT_PRODUCT_GROUP

# Summary
print("\n" + "=" * 70)
print("📋 Part Summary")
print("=" * 70)
print(f"Part Number:        {part_num}")
print(f"Description:        {description}")
print(f"Part Type:          {part_type}")
print(f"Part Class:         {part_class}")
print(f"Product Group:      {product_group}")
print(f"Unit Price:         ${unit_price:.2f}")
print(f"Inventory UOM:      {ium}")
print(f"Purchasing UOM:     {pum}")
print(f"Price Per Code:     {price_per_code}")
print(f"Company ID:         {epicor_service.company_id}")

# Confirm
print("\n" + "-" * 70)
confirm = input("Create this part in Epicor? (yes/no): ").strip().lower()

if confirm != 'yes':
    print("❌ Part creation cancelled")
    exit(0)

# Create the part
print("\n" + "=" * 70)
print("🔄 Creating Part in Epicor...")
print("=" * 70)

result = epicor_service.create_part(
    part_num=part_num,
    description=description,
    part_type=part_type,
    unit_price=unit_price,
    ium=ium,
    pum=pum,
    price_per_code=price_per_code,
    part_class=part_class,
    product_group=product_group
)

if result["status"] == "success":
    print("\n✅ Part created successfully!")
    print(f"   Part Number: {result['part_num']}")
    print(f"   Message: {result['message']}")
    
    # Verify by retrieving the part
    print("\n🔍 Verifying part creation...")
    part_data = epicor_service.get_part(part_num)
    
    if part_data:
        print("✅ Verification successful!")
        print(f"   Part Number: {part_data.get('PartNum')}")
        print(f"   Description: {part_data.get('PartDescription')}")
        print(f"   Type: {part_data.get('TypeCode')}")
        print(f"   Unit Price: ${part_data.get('UnitPrice', 0):.2f}")
        print(f"   IUM: {part_data.get('IUM')}")
        print(f"   Price Per Code: {part_data.get('PricePerCode')}")
    else:
        print("⚠️ Could not verify part (might still be created)")
    
    # Next steps
    print("\n" + "=" * 70)
    print("🎉 Success! Next Steps:")
    print("=" * 70)
    print(f"\n1. Test price update with this part:")
    print(f"   python test_price_update.py")
    print(f"   Enter part number: {part_num}")
    print(f"   Enter new price: 125.00")
    
    print(f"\n2. Or test with email:")
    print(f"   - Send email with part number: {part_num}")
    print(f"   - Old price: ${unit_price:.2f}")
    print(f"   - New price: $125.00")
    print(f"   - Run: python start.py")
    print(f"   - Process email in web interface")
    
    print(f"\n3. Verify in Epicor ERP:")
    print(f"   - Open Part Maintenance")
    print(f"   - Search for: {part_num}")
    print(f"   - Check the details")
    
else:
    print("\n❌ Part creation failed!")
    print(f"   Error: {result['message']}")
    
    if "already exists" in result['message']:
        print("\n💡 This part already exists in Epicor.")
        print("   Options:")
        print("   1. Use a different part number")
        print("   2. Delete the existing part in Epicor")
        print("   3. Use the existing part for testing")
    else:
        print("\n💡 Possible issues:")
        print("   1. Missing required fields")
        print("   2. Invalid part type or UOM")
        print("   3. Insufficient permissions")
        print("   4. Bearer token expired (refresh it)")
        
        print("\n🔧 Troubleshooting:")
        print("   1. Check if Bearer token is valid")
        print("   2. Verify you have Part Maintenance permissions")
        print("   3. Check Epicor logs for details")
        print("   4. Try creating the part manually in Epicor first")

print("\n" + "=" * 70)
print("🏁 Done")
print("=" * 70)

