"""
Test script to validate the complete OAuth token management flow with database storage.
Tests:
1. Token acquisition via client_credentials
2. Token storage in database
3. Token retrieval from database
4. Token refresh logic
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import os
from dotenv import load_dotenv

load_dotenv(override=True)


async def test_oauth_db_flow():
    """Test the complete OAuth token management flow with database"""
    print("\n" + "="*80)
    print("🔐 EPICOR OAUTH DATABASE FLOW TEST")
    print("="*80)

    # Import after path setup
    from database.config import get_db, init_db, engine
    from database.services.oauth_token_service import OAuthTokenService
    from services.epicor_auth import epicor_auth, SERVICE_NAME
    from sqlalchemy import text

    # Step 1: Initialize database
    print("\n📋 Step 1: Initialize Database")
    print("-"*40)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("✅ Database connection successful")
        
        await init_db()
        print("✅ Database tables initialized")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

    # Step 2: Test token acquisition and storage
    print("\n📋 Step 2: Test Token Acquisition & Storage")
    print("-"*40)
    
    async for db in get_db():
        try:
            # Initialize token (this will acquire and store in DB)
            success = await epicor_auth.initialize_token_async(db)
            
            if success:
                print("✅ Token acquired and stored in database")
            else:
                print("❌ Token acquisition failed")
                return False
            
            # Step 3: Verify token in database
            print("\n📋 Step 3: Verify Token in Database")
            print("-"*40)
            
            token_info = await OAuthTokenService.get_token_info(db, SERVICE_NAME)
            if token_info:
                print("✅ Token found in database:")
                print(f"   Service: {token_info['service_name']}")
                print(f"   Token Type: {token_info['token_type']}")
                print(f"   Expires At: {token_info['expires_at']}")
                print(f"   Is Expired: {token_info['is_expired']}")
                print(f"   Expires Soon: {token_info['expires_soon']}")
                print(f"   Obtained Via: {token_info['obtained_via']}")
                print(f"   Scope: {token_info['scope']}")
            else:
                print("❌ Token not found in database")
                return False
            
            # Step 4: Test get_valid_token_async
            print("\n📋 Step 4: Test get_valid_token_async")
            print("-"*40)
            
            token = await epicor_auth.get_valid_token_async(db)
            if token:
                print(f"✅ Valid token retrieved: {token[:50]}...")
            else:
                print("❌ Failed to get valid token")
                return False
            
            # Step 5: Test API call with token
            print("\n📋 Step 5: Test API Call with Token")
            print("-"*40)
            
            import requests
            base_url = os.getenv("EPICOR_BASE_URL")
            company_id = os.getenv("EPICOR_COMPANY_ID")
            api_key = os.getenv("EPICOR_API_KEY")
            
            test_url = f"{base_url}/{company_id}/Erp.BO.VendorSvc/Vendors"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            if api_key:
                headers["X-api-Key"] = api_key
            
            response = requests.get(
                test_url,
                headers=headers,
                params={"$top": 1, "$select": "VendorID,Name"},
                timeout=30
            )
            
            if response.status_code == 200:
                print("✅ API call successful with database-stored token!")
                result = response.json()
                vendors = result.get("value", [])
                print(f"   Retrieved {len(vendors)} vendor(s)")
            else:
                print(f"❌ API call failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False
            
            await db.commit()
            break
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True


if __name__ == "__main__":
    print("\n" + "="*80)
    print("Starting Epicor OAuth Database Flow Test...")
    print("="*80)
    
    success = asyncio.run(test_oauth_db_flow())
    
    print("\n" + "="*80)
    if success:
        print("✅ OVERALL RESULT: OAuth database flow is working correctly!")
    else:
        print("❌ OVERALL RESULT: OAuth database flow test FAILED")
    print("="*80 + "\n")
    
    exit(0 if success else 1)

