"""
Test automatic Bearer token generation
"""

from services.epicor_auth import epicor_auth
from services.epicor_service import epicor_service
import json

print("=" * 70)
print("🔐 Testing Automatic Bearer Token Generation")
print("=" * 70)

# Test 1: Get token with username/password
print("\n📝 Test 1: Get Bearer Token with Username/Password")
print("-" * 70)

result = epicor_auth.get_token_with_password()

if result["status"] == "success":
    print("✅ Token obtained successfully!")
    print(f"   Access Token: {result['access_token'][:50]}...")
    print(f"   Expires In: {result['expires_in']} seconds ({result['expires_in']//60} minutes)")
    print(f"   Token Type: {result['token_type']}")
    if result.get('refresh_token'):
        print(f"   Refresh Token: {result['refresh_token'][:50]}...")
else:
    print(f"❌ Failed to get token: {result['message']}")
    print("\n⚠️ This might be because:")
    print("   1. Epicor doesn't allow password grant for your client")
    print("   2. Client secret is required but not provided")
    print("   3. Username/password is incorrect")
    print("   4. OAuth endpoint URL is incorrect")
    print("\nTrying with Epicor service anyway...")

# Test 2: Get token info
print("\n📊 Test 2: Token Information")
print("-" * 70)

token_info = epicor_auth.get_token_info()
print(f"Status: {token_info['status']}")
if token_info['status'] != 'no_token':
    print(f"Expires In: {token_info['expires_in']} seconds")
    print(f"Has Refresh Token: {token_info['has_refresh_token']}")

# Test 3: Test Epicor API connection with auto token
print("\n🔌 Test 3: Test Epicor API Connection (with auto token)")
print("-" * 70)

connection_result = epicor_service.test_connection()

if connection_result["status"] == "success":
    print("✅ Epicor API connection successful!")
    print("   The automatic token generation is working!")
else:
    print(f"❌ Connection failed: {connection_result['message']}")

# Test 4: Get valid token
print("\n🎫 Test 4: Get Valid Token (auto-refresh if needed)")
print("-" * 70)

valid_token = epicor_auth.get_valid_token()

if valid_token:
    print(f"✅ Valid token obtained: {valid_token[:50]}...")
    print("   This token will be automatically refreshed when it expires!")
else:
    print("❌ Could not obtain valid token")

print("\n" + "=" * 70)
print("🏁 Test Complete")
print("=" * 70)

print("\n📋 Summary:")
print("-" * 70)

if result["status"] == "success":
    print("✅ Automatic token generation: WORKING")
    print("✅ Token will be automatically refreshed every hour")
    print("✅ No manual token copying needed!")
    print("\n🎉 You're all set! The system will handle tokens automatically.")
else:
    print("⚠️ Automatic token generation: NOT WORKING")
    print("\n📝 Possible reasons:")
    print("   1. Epicor OAuth endpoint might be different")
    print("   2. Client credentials might be needed")
    print("   3. Password grant might not be enabled")
    print("\n💡 Next steps:")
    print("   1. Contact Epicor administrator")
    print("   2. Ask for OAuth configuration details:")
    print("      - Token endpoint URL")
    print("      - Client ID")
    print("      - Client Secret (if required)")
    print("      - Supported grant types")
    print("\n📌 For now, you can continue using manual token refresh")
    print("   See: TOKEN_REFRESH_GUIDE.md")

