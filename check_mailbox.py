"""
Check if the user has a Microsoft mailbox
"""

import requests
import json
import os

# Get the token from the cache file
cache_files = [f for f in os.listdir('.') if f.startswith('token_cache_')]

if not cache_files:
    print("❌ No token cache files found!")
    print("Please login first at http://localhost:8000")
    exit(1)

cache_file = cache_files[0]
with open(cache_file, 'r') as f:
    cache_data = json.load(f)

# Extract access token
access_tokens = cache_data.get('AccessToken', {})
token_key = list(access_tokens.keys())[0]
token_data = access_tokens[token_key]
access_token = token_data.get('secret')

headers = {"Authorization": f"Bearer {access_token}"}

print("="*70)
print("🔍 Checking Microsoft Mailbox Status")
print("="*70)

# Test 1: Get user info
print("\n1️⃣ Getting user information...")
response = requests.get("https://graph.microsoft.com/v1.0/me", headers=headers)
if response.status_code == 200:
    user = response.json()
    print(f"   ✅ User: {user.get('displayName')}")
    print(f"   📧 Email: {user.get('mail') or user.get('userPrincipalName')}")
    print(f"   🏢 User Type: {user.get('userType', 'N/A')}")
    
    # Check if it's a guest
    upn = user.get('userPrincipalName', '')
    if '#EXT#' in upn:
        print(f"   ⚠️  This is a GUEST account")
    
    # Check mail property
    if not user.get('mail'):
        print(f"   ⚠️  No 'mail' property - might not have a mailbox")
else:
    print(f"   ❌ Failed: {response.status_code}")
    exit(1)

# Test 2: Check mailbox settings
print("\n2️⃣ Checking mailbox settings...")
response = requests.get("https://graph.microsoft.com/v1.0/me/mailboxSettings", headers=headers)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    settings = response.json()
    print(f"   ✅ Mailbox exists!")
    print(f"   Time zone: {settings.get('timeZone', 'N/A')}")
    print(f"   Language: {settings.get('language', {}).get('displayName', 'N/A')}")
elif response.status_code == 401:
    print(f"   ❌ Unauthorized - No mailbox access")
    print(f"   Response: {response.text[:200]}")
elif response.status_code == 404:
    print(f"   ❌ Mailbox not found - This account doesn't have an Exchange mailbox")
else:
    print(f"   ❌ Error: {response.text[:200]}")

# Test 3: Try to get inbox folder
print("\n3️⃣ Checking inbox folder...")
response = requests.get("https://graph.microsoft.com/v1.0/me/mailFolders/inbox", headers=headers)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    inbox = response.json()
    print(f"   ✅ Inbox exists!")
    print(f"   Total items: {inbox.get('totalItemCount', 'N/A')}")
    print(f"   Unread: {inbox.get('unreadItemCount', 'N/A')}")
elif response.status_code == 401:
    print(f"   ❌ Unauthorized")
    error_data = response.json() if response.text else {}
    error_msg = error_data.get('error', {}).get('message', 'No error message')
    print(f"   Error: {error_msg}")
elif response.status_code == 404:
    print(f"   ❌ Inbox not found - No mailbox")
else:
    print(f"   ❌ Error: {response.text[:200]}")

# Test 4: Check user's licenses
print("\n4️⃣ Checking user licenses...")
response = requests.get("https://graph.microsoft.com/v1.0/me/licenseDetails", headers=headers)
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    licenses = response.json().get('value', [])
    if licenses:
        print(f"   ✅ Found {len(licenses)} license(s):")
        for lic in licenses:
            print(f"      - {lic.get('skuPartNumber', 'Unknown')}")
    else:
        print(f"   ⚠️  No licenses found")
        print(f"   This might be why there's no mailbox!")
else:
    print(f"   ⚠️  Could not check licenses: {response.status_code}")

print("\n" + "="*70)
print("📋 Summary")
print("="*70)

print("\n🎯 Diagnosis:")
print("   If you see 'No mailbox' or 'Unauthorized' errors above,")
print("   it means this account doesn't have a Microsoft Exchange mailbox.")
print()
print("💡 Solution:")
print("   1. Use an Outlook.com or Hotmail.com account")
print("   2. OR use an Office 365 work/school account")
print("   3. Gmail accounts don't work with Microsoft Graph Mail API")
print()
print("🔗 Create a free Outlook account:")
print("   https://outlook.com")

