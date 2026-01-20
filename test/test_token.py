"""
Test Microsoft Graph API token
"""

import requests
import base64
import json

# Get the token from the cache file
import os
cache_files = [f for f in os.listdir('.') if f.startswith('token_cache_')]

if not cache_files:
    print("❌ No token cache files found!")
    print("Please login first at the application URL configured in your environment")
    exit(1)

cache_file = cache_files[0]
print(f"📁 Reading cache file: {cache_file}")

with open(cache_file, 'r') as f:
    cache_data = json.load(f)

# Extract access token
access_tokens = cache_data.get('AccessToken', {})
if not access_tokens:
    print("❌ No access tokens in cache!")
    exit(1)

# Get the first access token
token_key = list(access_tokens.keys())[0]
token_data = access_tokens[token_key]
access_token = token_data.get('secret')

if not access_token:
    print("❌ No access token found!")
    exit(1)

print(f"✅ Found access token: {access_token[:50]}...")

# Decode the token
try:
    token_parts = access_token.split('.')
    if len(token_parts) >= 2:
        # Decode payload
        payload = token_parts[1]
        payload += '=' * (4 - len(payload) % 4)
        decoded = base64.b64decode(payload)
        token_info = json.loads(decoded)
        
        print("\n📋 Token Information:")
        print(f"   Audience: {token_info.get('aud', 'N/A')}")
        print(f"   Issuer: {token_info.get('iss', 'N/A')}")
        print(f"   Scopes: {token_info.get('scp', 'N/A')}")
        print(f"   App ID: {token_info.get('appid', 'N/A')}")
        print(f"   User: {token_info.get('unique_name', token_info.get('upn', 'N/A'))}")
        
        import time
        exp = token_info.get('exp', 0)
        if exp:
            remaining = exp - time.time()
            print(f"   Expires in: {int(remaining)} seconds ({int(remaining/60)} minutes)")
        
except Exception as e:
    print(f"❌ Could not decode token: {e}")

# Test the token with Graph API
print("\n🧪 Testing token with Graph API...")

headers = {"Authorization": f"Bearer {access_token}"}

# Test 1: Get user profile
print("\n1️⃣ Testing /me endpoint...")
response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    user_data = response.json()
    print(f"   ✅ Success! User: {user_data.get('displayName')} ({user_data.get('mail') or user_data.get('userPrincipalName')})")
else:
    print(f"   ❌ Failed: {response.text[:200]}")

# Test 2: Get messages
print("\n2️⃣ Testing /me/messages endpoint...")
response = requests.get("https://graph.microsoft.com/v1.0/me/messages?$top=1", headers=headers)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    messages = response.json().get('value', [])
    print(f"   ✅ Success! Found {len(messages)} message(s)")
    if messages:
        print(f"   Latest: {messages[0].get('subject', 'No subject')}")
else:
    print(f"   ❌ Failed: {response.text[:500]}")

# Test 3: Get mail folders
print("\n3️⃣ Testing /me/mailFolders endpoint...")
response = requests.get("https://graph.microsoft.com/v1.0/me/mailFolders", headers=headers)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    folders = response.json().get('value', [])
    print(f"   ✅ Success! Found {len(folders)} folder(s)")
else:
    print(f"   ❌ Failed: {response.text[:200]}")

print("\n" + "="*70)
print("🏁 Test Complete")
print("="*70)

