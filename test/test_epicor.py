"""
Test script for Epicor API integration
Run this to verify your Epicor connection and credentials
"""

from services.epicor_service import epicor_service
import json


def test_connection():
    """Test basic connection to Epicor API"""
    print("=" * 60)
    print("🧪 Testing Epicor API Connection")
    print("=" * 60)
    
    result = epicor_service.test_connection()
    
    print(f"\nStatus: {result['status']}")
    print(f"Message: {result['message']}")
    
    if result['status'] == 'success':
        print("\n✅ Connection successful!")
        if 'company_data' in result:
            print("\nCompany Information:")
            print(json.dumps(result['company_data'], indent=2))
    else:
        print("\n❌ Connection failed!")
        print("Please check your .env file configuration:")
        print("  - EPICOR_BASE_URL")
        print("  - EPICOR_API_KEY or EPICOR_USERNAME/PASSWORD")
        print("  - EPICOR_COMPANY_ID")
    
    return result['status'] == 'success'


def test_get_part(part_num: str):
    """Test retrieving a part from Epicor"""
    print("\n" + "=" * 60)
    print(f"🔍 Testing Get Part: {part_num}")
    print("=" * 60)
    
    part_data = epicor_service.get_part(part_num)
    
    if part_data:
        print(f"\n✅ Part found: {part_num}")
        print("\nPart Information:")
        print(f"  Part Number: {part_data.get('PartNum')}")
        print(f"  Description: {part_data.get('PartDescription')}")
        print(f"  Current Price: {part_data.get('UnitPrice')}")
        print(f"  Price Per Code: {part_data.get('PricePerCode')}")
        print(f"  IUM: {part_data.get('IUM')}")
        return True
    else:
        print(f"\n❌ Part not found: {part_num}")
        print("Please provide a valid part number from your Epicor system")
        return False


def test_update_price(part_num: str, new_price: float):
    """Test updating a part price"""
    print("\n" + "=" * 60)
    print(f"💰 Testing Price Update: {part_num} → ${new_price}")
    print("=" * 60)
    
    # First get current price
    part_data = epicor_service.get_part(part_num)
    if not part_data:
        print(f"❌ Cannot update - part {part_num} not found")
        return False
    
    old_price = part_data.get('UnitPrice', 0)
    print(f"\nCurrent Price: ${old_price}")
    print(f"New Price: ${new_price}")
    
    # Confirm update
    confirm = input("\n⚠️  Do you want to proceed with this price update? (yes/no): ")
    if confirm.lower() != 'yes':
        print("❌ Update cancelled")
        return False
    
    # Perform update
    result = epicor_service.update_part_price(part_num, new_price)
    
    print(f"\nStatus: {result['status']}")
    print(f"Message: {result['message']}")
    
    if result['status'] == 'success':
        print(f"\n✅ Price updated successfully!")
        print(f"  Part: {part_num}")
        print(f"  Old Price: ${result.get('old_price')}")
        print(f"  New Price: ${result.get('new_price')}")
        return True
    else:
        print(f"\n❌ Price update failed!")
        return False


def test_batch_update():
    """Test batch price update with sample data"""
    print("\n" + "=" * 60)
    print("📦 Testing Batch Price Update")
    print("=" * 60)
    
    # Sample extracted data (like what comes from email extraction)
    sample_products = [
        {
            "product_id": "1000-0001",
            "product_name": "Sample Product 1",
            "old_price": "100.00",
            "new_price": "110.00"
        },
        {
            "product_id": "1000-0002",
            "product_name": "Sample Product 2",
            "old_price": "200.00",
            "new_price": "220.00"
        }
    ]
    
    print("\nSample products to update:")
    for product in sample_products:
        print(f"  - {product['product_id']}: ${product['old_price']} → ${product['new_price']}")
    
    confirm = input("\n⚠️  Do you want to proceed with batch update? (yes/no): ")
    if confirm.lower() != 'yes':
        print("❌ Batch update cancelled")
        return False
    
    # Perform batch update
    results = epicor_service.batch_update_prices(sample_products)
    
    print("\n📊 Batch Update Results:")
    print(f"  Total: {results['total']}")
    print(f"  Successful: {results['successful']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Skipped: {results['skipped']}")
    
    print("\nDetails:")
    for detail in results['details']:
        status_icon = "✅" if detail['status'] == 'success' else "❌"
        print(f"  {status_icon} {detail['part_num']}: {detail.get('message', detail.get('reason'))}")
    
    return results['successful'] > 0


def main():
    """Main test function"""
    print("\n🚀 Epicor API Integration Test Suite")
    print("=" * 60)
    
    # Test 1: Connection
    if not test_connection():
        print("\n❌ Connection test failed. Please fix configuration before proceeding.")
        return
    
    # Test 2: Get Part (interactive)
    print("\n" + "=" * 60)
    part_num = input("\nEnter a part number to test (or press Enter to skip): ").strip()
    
    if part_num:
        if test_get_part(part_num):
            # Test 3: Update Price (interactive)
            update_test = input("\nDo you want to test price update for this part? (yes/no): ")
            if update_test.lower() == 'yes':
                try:
                    new_price = float(input("Enter new price: "))
                    test_update_price(part_num, new_price)
                except ValueError:
                    print("❌ Invalid price format")
    
    # Test 4: Batch Update (optional)
    print("\n" + "=" * 60)
    batch_test = input("\nDo you want to test batch price update? (yes/no): ")
    if batch_test.lower() == 'yes':
        test_batch_update()
    
    print("\n" + "=" * 60)
    print("✅ Test suite complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

