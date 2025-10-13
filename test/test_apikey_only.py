"""
Test Epicor API with ONLY API Key (no username/password)
Try different header formats to find the correct one
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("EPICOR_BASE_URL")
API_KEY = os.getenv("EPICOR_API_KEY")
COMPANY_ID = os.getenv("EPICOR_COMPANY_ID")

print("=" * 70)
print("🔑 Epicor API Key Only Test")
print("=" * 70)
print(f"\nBase URL: {BASE_URL}")
print(f"Company ID: {COMPANY_ID}")
print(f"API Key: {API_KEY[:20]}..." if API_KEY else "API Key: Not set")
print()

# Test endpoints
test_endpoints = [
    f"{BASE_URL}/$metadata",
    f"{BASE_URL}/Erp.BO.PartSvc",
    f"{BASE_URL}/{COMPANY_ID}/Erp.BO.PartSvc/Parts"
]

def test_headers(name, headers, endpoint):
    """Test specific headers"""
    print(f"\n{'='*70}")
    print(f"Testing: {name}")
    print(f"Endpoint: {endpoint}")
    print(f"Headers: {headers}")
    print(f"{'='*70}")
    
    try:
        response = requests.get(endpoint, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS! This works!")
            print(f"Response length: {len(response.text)} bytes")
            if len(response.text) < 1000:
                print(f"Response preview: {response.text[:500]}")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"Response: {response.text[:300]}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

# Test different API key header formats
api_key_formats = [
    # Format 1: x-api-key
    {
        "name": "x-api-key header",
        "headers": {
            "x-api-key": API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    },
    # Format 2: API-Key
    {
        "name": "API-Key header",
        "headers": {
            "API-Key": API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    },
    # Format 3: ApiKey
    {
        "name": "ApiKey header",
        "headers": {
            "ApiKey": API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    },
    # Format 4: Authorization: ApiKey
    {
        "name": "Authorization: ApiKey",
        "headers": {
            "Authorization": f"ApiKey {API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    },
    # Format 5: Authorization: Bearer
    {
        "name": "Authorization: Bearer",
        "headers": {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    },
    # Format 6: Authorization: Token
    {
        "name": "Authorization: Token",
        "headers": {
            "Authorization": f"Token {API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    },
    # Format 7: Ocp-Apim-Subscription-Key (Azure API Management)
    {
        "name": "Ocp-Apim-Subscription-Key",
        "headers": {
            "Ocp-Apim-Subscription-Key": API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    },
    # Format 8: X-API-KEY (uppercase)
    {
        "name": "X-API-KEY header",
        "headers": {
            "X-API-KEY": API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    },
    # Format 9: Multiple headers combined
    {
        "name": "Multiple API key headers",
        "headers": {
            "x-api-key": API_KEY,
            "API-Key": API_KEY,
            "ApiKey": API_KEY,
            "X-API-KEY": API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    },
    # Format 10: Authorization header with API key prefix
    {
        "name": "Authorization: API-Key",
        "headers": {
            "Authorization": f"API-Key {API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    }
]

print("\n" + "="*70)
print("🔍 Testing Different API Key Header Formats")
print("="*70)

success_found = False

for format_config in api_key_formats:
    print(f"\n{'='*70}")
    print(f"FORMAT: {format_config['name']}")
    print(f"{'='*70}")
    
    for endpoint in test_endpoints:
        if test_headers(format_config['name'], format_config['headers'], endpoint):
            print(f"\n🎉 SUCCESS! Found working configuration!")
            print(f"✅ Format: {format_config['name']}")
            print(f"✅ Endpoint: {endpoint}")
            print(f"✅ Headers: {format_config['headers']}")
            success_found = True
            break
    
    if success_found:
        break

if not success_found:
    print("\n" + "="*70)
    print("❌ No working API key format found")
    print("="*70)
    print("\nPossible issues:")
    print("1. API key might be invalid or expired")
    print("2. API key might need to be regenerated in Epicor")
    print("3. Your user might not have REST API access permissions")
    print("4. The API key might need to be used with username/password")
    print("\nNext steps:")
    print("1. Log into Epicor REST API Help in your browser")
    print("2. Open DevTools (F12) → Network tab")
    print("3. Make a test API call")
    print("4. Look at the request headers to see the exact format used")
    print("5. Share a screenshot of the headers with me")

print("\n" + "="*70)
print("🏁 Test Complete")
print("="*70)

