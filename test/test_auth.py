"""
Simple authentication test for Epicor API
Tests different authentication methods to find the correct one
"""

import os
import requests
import base64
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("EPICOR_BASE_URL")
API_KEY = os.getenv("EPICOR_API_KEY")
COMPANY_ID = os.getenv("EPICOR_COMPANY_ID")
USERNAME = os.getenv("EPICOR_USERNAME")
PASSWORD = os.getenv("EPICOR_PASSWORD")

print("=" * 70)
print("🔐 Epicor API Authentication Test")
print("=" * 70)
print(f"\nBase URL: {BASE_URL}")
print(f"Company ID: {COMPANY_ID}")
print(f"Username: {USERNAME}")
print(f"API Key: {API_KEY[:20]}..." if API_KEY else "API Key: Not set")
print()

# Test endpoints to try
test_endpoints = [
    f"{BASE_URL}/$metadata",
    f"{BASE_URL}/Erp.BO.PartSvc",
    f"{BASE_URL}/{COMPANY_ID}/Erp.BO.PartSvc"
]

def test_auth_method(name, headers, endpoint):
    """Test a specific authentication method"""
    print(f"\n{'='*70}")
    print(f"Testing: {name}")
    print(f"Endpoint: {endpoint}")
    print(f"Headers: {headers}")
    print(f"{'='*70}")
    
    try:
        response = requests.get(endpoint, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS! This authentication method works!")
            print(f"Response length: {len(response.text)} bytes")
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

# Method 1: API Key as Bearer token
print("\n" + "="*70)
print("METHOD 1: API Key as Bearer Token")
print("="*70)
if API_KEY:
    headers1 = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    for endpoint in test_endpoints:
        if test_auth_method("Bearer Token", headers1, endpoint):
            print("\n🎉 Found working configuration!")
            break
else:
    print("⚠️ API Key not configured, skipping...")

# Method 2: API Key as x-api-key header
print("\n" + "="*70)
print("METHOD 2: API Key as x-api-key Header")
print("="*70)
if API_KEY:
    headers2 = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    for endpoint in test_endpoints:
        if test_auth_method("x-api-key Header", headers2, endpoint):
            print("\n🎉 Found working configuration!")
            break
else:
    print("⚠️ API Key not configured, skipping...")

# Method 3: API Key as API-Key header
print("\n" + "="*70)
print("METHOD 3: API Key as API-Key Header")
print("="*70)
if API_KEY:
    headers3 = {
        "API-Key": API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    for endpoint in test_endpoints:
        if test_auth_method("API-Key Header", headers3, endpoint):
            print("\n🎉 Found working configuration!")
            break
else:
    print("⚠️ API Key not configured, skipping...")

# Method 4: Combined API Key + Basic Authentication
print("\n" + "="*70)
print("METHOD 4: Combined API Key + Basic Authentication (RECOMMENDED)")
print("="*70)
if API_KEY and USERNAME and PASSWORD:
    credentials = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
    headers4 = {
        "x-api-key": API_KEY,
        "API-Key": API_KEY,
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    for endpoint in test_endpoints:
        if test_auth_method("Combined API Key + Basic Auth", headers4, endpoint):
            print("\n🎉 Found working configuration!")
            print("✅ Use BOTH API Key AND Basic Authentication together!")
            break
else:
    print("⚠️ API Key or Username/Password not configured, skipping...")

# Method 5: Basic Authentication only
print("\n" + "="*70)
print("METHOD 5: Basic Authentication Only (Username + Password)")
print("="*70)
if USERNAME and PASSWORD:
    credentials = base64.b64encode(f"{USERNAME}:{PASSWORD}".encode()).decode()
    headers5 = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    for endpoint in test_endpoints:
        if test_auth_method("Basic Auth Only", headers5, endpoint):
            print("\n🎉 Found working configuration!")
            break
else:
    print("⚠️ Username/Password not configured, skipping...")

# Method 6: No authentication (public endpoint test)
print("\n" + "="*70)
print("METHOD 6: No Authentication (Testing if endpoint is public)")
print("="*70)
headers6 = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}
for endpoint in test_endpoints:
    if test_auth_method("No Auth", headers6, endpoint):
        print("\n⚠️ Endpoint is public (no authentication required)")
        break

print("\n" + "="*70)
print("🏁 Authentication Test Complete")
print("="*70)
print("\nIf none of the methods worked, please:")
print("1. Verify your credentials in the .env file")
print("2. Check if your Epicor user has API access permissions")
print("3. Confirm the base URL is correct")
print("4. Contact your Epicor administrator for the correct authentication method")

