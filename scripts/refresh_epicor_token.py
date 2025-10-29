"""
Quick script to refresh Epicor Bearer Token
Run this when you get 401 token expired errors
"""

import sys
from pathlib import Path
# Add parent directory to path to allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv, set_key
from services.epicor_auth import epicor_auth

def refresh_token():
    """Refresh the Epicor Bearer token"""
    print("\n" + "="*80)
    print("🔐 EPICOR TOKEN REFRESH UTILITY")
    print("="*80)
    
    # Load environment
    load_dotenv()
    
    print("\n📋 Current Configuration:")
    print(f"   🌐 Token URL: {epicor_auth.token_url}")
    print(f"   👤 Username: {epicor_auth.username}")
    print(f"   🏢 Company ID: {epicor_auth.company_id}")
    print(f"   🔑 Client ID: {epicor_auth.client_id[:20]}...")
    
    print("\n🔄 Requesting new Bearer token...")
    print("-"*80)
    
    # Get new token
    result = epicor_auth.get_token_with_password()
    
    print("-"*80)
    
    if result["status"] == "success":
        print("\n✅ TOKEN REFRESH SUCCESSFUL!")
        print("="*80)
        print(f"📊 Token Details:")
        print(f"   ⏰ Expires in: {result['expires_in']} seconds ({result['expires_in']//60} minutes)")
        print(f"   🔑 Token type: {result['token_type']}")
        print(f"   💾 Token saved to: .env")
        print("\n🎯 Next Steps:")
        print("   1. Token has been automatically updated in .env file")
        print("   2. Restart your server: python start.py")
        print("   3. Your automated workflow will now work!")
        print("="*80 + "\n")
        
        # Display first/last 20 chars of token for verification
        token = result['access_token']
        print(f"🔍 Token Preview: {token[:30]}...{token[-30:]}")
        print()
        
        return True
    else:
        print("\n❌ TOKEN REFRESH FAILED!")
        print("="*80)
        print(f"⚠️  Error: {result.get('message', 'Unknown error')}")
        print(f"📊 Status Code: {result.get('status_code', 'N/A')}")
        print("\n🔧 Troubleshooting:")
        print("   1. Check your credentials in .env file:")
        print("      - EPICOR_USERNAME")
        print("      - EPICOR_PASSWORD")
        print("      - EPICOR_CLIENT_ID")
        print("      - EPICOR_CLIENT_SECRET (if required)")
        print("   2. Verify Epicor login portal is accessible")
        print("   3. Check if your Epicor account is active")
        print("="*80 + "\n")
        
        return False


if __name__ == "__main__":
    try:
        success = refresh_token()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        print("="*80 + "\n")
        exit(1)

