"""
Test script to validate new Epicor OAuth credentials
Tests both client_credentials and password grant flows
"""

import sys
from pathlib import Path
# Add parent directory to path to allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv
import requests

# Load fresh environment
load_dotenv(override=True)

def test_oauth_credentials():
    """Test the new OAuth credentials for Epicor API"""
    print("\n" + "="*80)
    print("🔐 EPICOR OAUTH CREDENTIALS TEST")
    print("="*80)
    
    # Get credentials from environment
    client_id = os.getenv("EPICOR_CLIENT_ID")
    client_secret = os.getenv("EPICOR_CLIENT_SECRET")
    base_url = os.getenv("EPICOR_BASE_URL")
    company_id = os.getenv("EPICOR_COMPANY_ID")
    api_key = os.getenv("EPICOR_API_KEY")
    
    print("\n📋 Configuration:")
    print(f"   Client ID: {client_id[:20]}..." if client_id else "   Client ID: NOT SET")
    print(f"   Client Secret: {'*' * 20}..." if client_secret else "   Client Secret: NOT SET")
    print(f"   Base URL: {base_url}")
    print(f"   Company ID: {company_id}")
    print(f"   API Key: {api_key[:20]}..." if api_key else "   API Key: NOT SET")
    
    # Token URL for Epicor
    token_url = "https://login.epicor.com/connect/token"

    # Try different scopes
    scopes_to_try = [
        "epicor_erp",  # Just ERP access
        "openid profile epicor_erp",  # OpenID with profile
        "openid",  # Just OpenID
        "",  # Empty scope (let server decide)
    ]

    for scope in scopes_to_try:
        print("\n" + "-"*80)
        print(f"🔄 TEST: Client Credentials Grant Flow with scope: '{scope or '(empty)'}'")
        print("-"*80)

        # Test client_credentials grant
        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
        if scope:
            data["scope"] = scope

        try:
            response = requests.post(
                token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30
            )

            print(f"\n📊 Response Status: {response.status_code}")

            if response.status_code == 200:
                token_data = response.json()
                access_token = token_data.get("access_token", "")
                expires_in = token_data.get("expires_in", 0)
                token_type = token_data.get("token_type", "Unknown")

                print("✅ CLIENT CREDENTIALS AUTHENTICATION SUCCESSFUL!")
                print(f"   Scope: {scope or '(empty)'}")
                print(f"   Token Type: {token_type}")
                print(f"   Expires In: {expires_in} seconds ({expires_in//60} minutes)")
                print(f"   Token Preview: {access_token[:50]}...{access_token[-30:]}" if len(access_token) > 80 else f"   Token: {access_token}")

                # Test the token with an API call
                print("\n" + "-"*80)
                print("🔄 TEST 2: Making API Call with New Token")
                print("-"*80)

                test_url = f"{base_url}/{company_id}/Erp.BO.VendorSvc/Vendors"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
                if api_key:
                    headers["X-api-Key"] = api_key

                api_response = requests.get(
                    test_url,
                    headers=headers,
                    params={"$top": 1, "$select": "VendorID,Name"},
                    timeout=30
                )

                print(f"\n📊 API Response Status: {api_response.status_code}")

                if api_response.status_code == 200:
                    print("✅ API CALL SUCCESSFUL!")
                    result = api_response.json()
                    vendors = result.get("value", [])
                    print(f"   Retrieved {len(vendors)} vendor(s)")
                    if vendors:
                        print(f"   Sample: {vendors[0]}")
                else:
                    print(f"❌ API CALL FAILED: {api_response.status_code}")
                    print(f"   Response: {api_response.text[:500]}")

                return True  # Found working scope, exit

            else:
                print(f"❌ FAILED with scope '{scope or '(empty)'}'")
                # Try to parse error response
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data.get('error', 'Unknown')}")
                    print(f"   Error Description: {error_data.get('error_description', 'None provided')}")
                except:
                    print(f"   Response: {response.text[:200]}")

        except Exception as e:
            print(f"❌ ERROR: {e}")

    # All scopes failed
    print("\n" + "="*80)
    print("❌ ALL SCOPES FAILED - OAuth credentials may be invalid")
    return False


if __name__ == "__main__":
    print("\n" + "="*80)
    print("Starting Epicor OAuth Credentials Test...")
    print("="*80)
    
    success = test_oauth_credentials()
    
    print("\n" + "="*80)
    if success:
        print("✅ OVERALL RESULT: OAuth credentials are VALID and working!")
    else:
        print("❌ OVERALL RESULT: OAuth credentials test FAILED")
        print("\n🔧 Troubleshooting:")
        print("   1. Verify the client_id and client_secret are correct")
        print("   2. Check if the OAuth app has the required scopes")
        print("   3. Ensure the Epicor login portal is accessible")
        print("   4. Confirm the OAuth app is properly configured in Epicor")
    print("="*80 + "\n")
    
    exit(0 if success else 1)

