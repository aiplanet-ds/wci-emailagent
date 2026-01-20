"""
End-to-End Async Testing Script for WCI Email Agent

Tests the synchronous-to-asynchronous code changes:
1. Email polling mechanism
2. Epicor API operations
3. LLM detection and extraction
4. Complete workflow
"""

import asyncio
import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import httpx
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8000"


async def test_api_health():
    """Test 1: Basic API health check"""
    print("\n" + "=" * 80)
    print("TEST 1: API Health Check")
    print("=" * 80)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{BASE_URL}/api/user")
            print(f"   Status Code: {response.status_code}")
            print(f"   Response: {response.json()}")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            print("   ✅ API is responding")
            return True
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return False


async def test_epicor_connection():
    """Test 2: Epicor API connection (async)"""
    print("\n" + "=" * 80)
    print("TEST 2: Epicor API Connection (Async)")
    print("=" * 80)
    
    try:
        from services.epicor_service import EpicorAPIService
        epicor = EpicorAPIService()
        
        print("   Testing Epicor connection...")
        result = await epicor.test_connection()
        
        print(f"   Status: {result.get('status')}")
        print(f"   Message: {result.get('message')}")
        
        if result.get("status") == "success":
            print("   ✅ Epicor connection successful")
            return True
        else:
            print(f"   ⚠️ Epicor connection issue: {result.get('message')}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


async def test_epicor_part_lookup():
    """Test 3: Epicor part lookup (async)"""
    print("\n" + "=" * 80)
    print("TEST 3: Epicor Part Lookup (Async)")
    print("=" * 80)
    
    try:
        from services.epicor_service import EpicorAPIService
        epicor = EpicorAPIService()
        
        # Test with a known part
        test_part = "#FFH06-12SAE F"
        print(f"   Looking up part: {test_part}")
        
        result = await epicor.get_part_where_used(test_part)
        
        print(f"   Parent assemblies found: {len(result) if result else 0}")
        if result:
            print(f"   First parent: {result[0].get('PartNum', 'N/A')}")
        print("   ✅ Part lookup working")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


async def test_llm_detection():
    """Test 4: LLM Detection (async)"""
    print("\n" + "=" * 80)
    print("TEST 4: LLM Price Change Detection (Async)")
    print("=" * 80)
    
    try:
        from services.llm_detector import llm_is_price_change_email
        
        test_content = """
        Dear Customer,
        We are writing to inform you of an upcoming price change for our products.
        Part #ABC-123: Old Price $45.00 → New Price $52.00
        Effective Date: January 1, 2025
        Best regards, Acme Corp
        """
        
        test_metadata = {
            "subject": "Price Change Notification",
            "sender": "sales@acmecorp.com",
            "date": "2024-12-15T10:00:00Z"
        }
        
        print("   Running LLM detection on test email...")
        result = await llm_is_price_change_email(test_content, test_metadata)
        
        print(f"   Is Price Change: {result.get('is_price_change')}")
        print(f"   Confidence: {result.get('confidence', 0):.2%}")
        print(f"   Meets Threshold: {result.get('meets_threshold')}")
        print(f"   Reasoning: {result.get('reasoning', 'N/A')[:100]}...")
        print("   ✅ LLM detection working")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_extractor():
    """Test 5: AI Extraction (async)"""
    print("\n" + "=" * 80)
    print("TEST 5: AI Entity Extraction (Async)")
    print("=" * 80)
    
    try:
        from services.extractor import extract_price_change_json
        
        test_content = """
        Price Change Notification
        
        Supplier: Acme Corporation (Vendor ID: ACME001)
        
        Effective Date: January 15, 2025
        
        Products Affected:
        - Part #FFH06-12SAE F: $45.00 → $52.00
        - Part #ABC-123: $120.00 → $135.00
        
        Reason: Raw material cost increase
        """
        
        test_metadata = {
            "subject": "Price Change - Acme Corp",
            "from": "sales@acmecorp.com",
            "date": "2024-12-15"
        }
        
        print("   Running AI extraction...")
        result = await extract_price_change_json(test_content, test_metadata)
        
        if "error" not in result:
            supplier_info = result.get("supplier_info", {})
            products = result.get("affected_products", [])
            print(f"   Supplier ID: {supplier_info.get('supplier_id', 'N/A')}")
            print(f"   Products extracted: {len(products)}")
            if products:
                print(f"   First product: {products[0].get('product_id', 'N/A')}")
            print("   ✅ AI extraction working")
            return True
        else:
            print(f"   ⚠️ Extraction error: {result.get('error')}")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all async tests"""
    print("\n" + "=" * 80)
    print("🚀 WCI EMAIL AGENT - ASYNC E2E TEST SUITE")
    print("=" * 80)
    print("Testing synchronous-to-asynchronous code changes...")
    
    results = {}
    
    # Run tests
    results["API Health"] = await test_api_health()
    results["Epicor Connection"] = await test_epicor_connection()
    results["Epicor Part Lookup"] = await test_epicor_part_lookup()
    results["LLM Detection"] = await test_llm_detection()
    results["AI Extraction"] = await test_extractor()
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    print(f"\n   Total: {passed}/{total} tests passed")
    print("=" * 80)
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

