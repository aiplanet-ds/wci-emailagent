"""
Test script to update a part price in Epicor
Simulates the email extraction → price update workflow
"""

from services.epicor_service import epicor_service
import json

print("=" * 70)
print("🧪 Test Price Update Workflow")
print("=" * 70)

# Step 1: Get part number from user
print("\n📝 Step 1: Enter Part Information")
print("-" * 70)

part_num = input("Enter Part Number (e.g., TEST-001): ").strip()

if not part_num:
    print("❌ Part number is required!")
    exit(1)

# Step 2: Get current part info from Epicor
print(f"\n🔍 Step 2: Retrieving current info for {part_num}...")
print("-" * 70)

current_part = epicor_service.get_part(part_num)

if not current_part:
    print(f"❌ Part {part_num} not found in Epicor!")
    print("\n💡 Please create this part in Epicor first:")
    print("   1. Open Epicor → Part Maintenance")
    print(f"   2. Create part: {part_num}")
    print("   3. Set initial price (e.g., 100.00)")
    print("   4. Save and run this script again")
    exit(1)

print(f"✅ Part found!")
print(f"   Part Number: {current_part.get('PartNum')}")
print(f"   Description: {current_part.get('PartDescription')}")
print(f"   Current Price: ${current_part.get('UnitPrice', 0):.2f}")
print(f"   Price Per Code: {current_part.get('PricePerCode')}")

# Step 3: Get new price from user
print(f"\n💰 Step 3: Enter New Price")
print("-" * 70)

current_price = current_part.get('UnitPrice', 0)
print(f"Current Price: ${current_price:.2f}")

try:
    new_price_input = input("Enter New Price (e.g., 125.00): ").strip()
    new_price = float(new_price_input.replace("$", "").replace(",", ""))
except ValueError:
    print("❌ Invalid price format!")
    exit(1)

if new_price == current_price:
    print("⚠️ New price is the same as current price!")
    confirm = input("Continue anyway? (yes/no): ").strip().lower()
    if confirm != 'yes':
        print("❌ Update cancelled")
        exit(0)

# Step 4: Simulate extracted data (like from email)
print(f"\n📊 Step 4: Simulating Email Extraction Data")
print("-" * 70)

extracted_data = {
    "affected_products": [
        {
            "product_id": part_num,
            "product_name": current_part.get('PartDescription', 'Test Part'),
            "old_price": str(current_price),
            "new_price": str(new_price),
            "price_change_amount": str(new_price - current_price),
            "price_change_percentage": str(((new_price - current_price) / current_price * 100) if current_price > 0 else 0),
            "unit": "EA",
            "effective_date": "Immediate"
        }
    ]
}

print("Extracted Data:")
print(json.dumps(extracted_data, indent=2))

# Step 5: Confirm update
print(f"\n⚠️  Step 5: Confirm Price Update")
print("-" * 70)
print(f"Part Number: {part_num}")
print(f"Old Price: ${current_price:.2f}")
print(f"New Price: ${new_price:.2f}")
print(f"Change: ${new_price - current_price:.2f} ({((new_price - current_price) / current_price * 100):.1f}%)")

confirm = input("\n🔄 Update price in Epicor? (yes/no): ").strip().lower()

if confirm != 'yes':
    print("❌ Update cancelled")
    exit(0)

# Step 6: Update price in Epicor
print(f"\n🔄 Step 6: Updating Price in Epicor...")
print("-" * 70)

result = epicor_service.update_part_price(
    part_num=part_num,
    new_price=new_price,
    price_per_code="E"
)

if result["status"] == "success":
    print("✅ Price updated successfully!")
    print(f"   Part: {result['part_num']}")
    print(f"   Old Price: ${result.get('old_price', 0):.2f}")
    print(f"   New Price: ${result.get('new_price', 0):.2f}")
    print(f"   Message: {result['message']}")
else:
    print("❌ Price update failed!")
    print(f"   Error: {result['message']}")
    exit(1)

# Step 7: Verify the update
print(f"\n✅ Step 7: Verifying Update...")
print("-" * 70)

updated_part = epicor_service.get_part(part_num)

if updated_part:
    updated_price = updated_part.get('UnitPrice', 0)
    print(f"✅ Verification successful!")
    print(f"   Current Price in Epicor: ${updated_price:.2f}")
    
    if abs(updated_price - new_price) < 0.01:  # Allow for floating point precision
        print(f"   ✅ Price matches expected value!")
    else:
        print(f"   ⚠️ Price mismatch! Expected: ${new_price:.2f}, Got: ${updated_price:.2f}")
else:
    print("⚠️ Could not verify update (part not found)")

# Step 8: Summary
print("\n" + "=" * 70)
print("🎉 Test Complete!")
print("=" * 70)

print("\n📊 Summary:")
print(f"   Part Number: {part_num}")
print(f"   Old Price: ${current_price:.2f}")
print(f"   New Price: ${new_price:.2f}")
print(f"   Status: ✅ Updated Successfully")

print("\n💡 Next Steps:")
print("   1. Verify the price in Epicor ERP")
print("   2. Test with a real email using the web interface")
print("   3. Process multiple parts in batch")

print("\n📝 To test with real email:")
print("   1. Run: python start.py")
print("   2. Go to the application URL configured in your environment")
print("   3. Process an email with price changes")
print("   4. Click 'Update Prices in Epicor ERP'")

