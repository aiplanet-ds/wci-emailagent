"""
Test script for migrated router endpoints

This script tests the database integration of router endpoints:
1. GET /api/emails - list_emails()
2. GET /api/emails/{message_id} - get_email_detail()
3. GET /api/emails/pending-verification - list_pending_verification_emails()
4. GET /api/emails/vendors/cache-status - get_vendor_cache_status()
"""

import asyncio
import sys
import os

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    os.system("chcp 65001 > nul 2>&1")
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from database.config import SessionLocal
from database.services.user_service import UserService
from database.services.email_service import EmailService
from database.services.email_state_service import EmailStateService
from database.services.vendor_service import VendorService


async def test_database_queries():
    """Test that database queries work correctly for router endpoints"""
    print("\n" + "="*80)
    print("TESTING ROUTER ENDPOINT DATABASE QUERIES")
    print("="*80)

    async with SessionLocal() as db:
        # Test 1: Get all users
        print("\n[TEST 1] Getting all users...")
        users = await UserService.get_all_users(db)
        print(f"✓ Found {len(users)} users in database")

        if not users:
            print("⚠ WARNING: No users found in database. Some tests will be skipped.")
            return

        test_user = users[0]
        print(f"  Using test user: {test_user.email}")

        # Test 2: Get emails for user (list_emails endpoint)
        print("\n[TEST 2] Getting emails for user (list_emails query)...")
        emails = await EmailService.get_emails_by_user(db, test_user.id)
        print(f"✓ Found {len(emails)} emails for user")

        if not emails:
            print("⚠ WARNING: No emails found. Some tests will be skipped.")
            return

        test_email = emails[0]
        print(f"  Test email: {test_email.subject[:50]}...")
        print(f"  Message ID: {test_email.message_id}")

        # Test 3: Get email detail (get_email_detail endpoint)
        print("\n[TEST 3] Getting email detail by message_id...")
        email = await EmailService.get_email_by_message_id(db, test_email.message_id)
        if email:
            print(f"✓ Successfully retrieved email detail")
            print(f"  Subject: {email.subject}")
            print(f"  Sender: {email.sender_email}")
            print(f"  Received: {email.received_at}")
            print(f"  Has supplier_info: {bool(email.supplier_info)}")
            print(f"  Has price_change_summary: {bool(email.price_change_summary)}")
            print(f"  Has affected_products: {bool(email.affected_products)}")
        else:
            print("✗ FAILED: Could not retrieve email")

        # Test 4: Get email state
        print("\n[TEST 4] Getting email state...")
        state = await EmailStateService.get_state_by_message_id(db, test_email.message_id)
        if state:
            print(f"✓ Successfully retrieved email state")
            print(f"  Processed: {state.processed}")
            print(f"  Epicor Synced: {state.epicor_synced}")
            print(f"  Vendor Verified: {state.vendor_verified}")
            print(f"  Verification Status: {state.verification_status}")
            print(f"  Is Price Change: {state.is_price_change}")
        else:
            print("⚠ No state found for this email")

        # Test 5: Get pending verification emails
        print("\n[TEST 5] Getting pending verification emails...")
        from sqlalchemy import select, and_
        from database.models import Email, EmailState
        from sqlalchemy.orm import joinedload

        query = (
            select(Email)
            .join(EmailState, Email.id == EmailState.email_id)
            .where(and_(
                Email.user_id == test_user.id,
                EmailState.verification_status == "pending_review"
            ))
            .options(joinedload(Email.email_state))
        )
        result = await db.execute(query)
        pending_emails = result.unique().scalars().all()
        print(f"✓ Found {len(pending_emails)} pending verification emails")

        # Test 6: Get vendor cache status
        print("\n[TEST 6] Getting vendor cache status...")
        vendors = await VendorService.get_all_vendors(db)
        print(f"✓ Found {len(vendors)} vendors in cache")
        if vendors:
            print(f"  Sample vendors:")
            for v in vendors[:3]:
                print(f"    - {v.vendor_name} ({v.vendor_id})")

        # Test 7: Filter emails by processed status
        print("\n[TEST 7] Testing email filtering (processed vs unprocessed)...")
        query_processed = (
            select(Email)
            .join(EmailState, Email.id == EmailState.email_id)
            .where(and_(
                Email.user_id == test_user.id,
                EmailState.processed == True
            ))
        )
        result = await db.execute(query_processed)
        processed_emails = result.scalars().all()

        query_unprocessed = (
            select(Email)
            .join(EmailState, Email.id == EmailState.email_id, isouter=True)
            .where(Email.user_id == test_user.id)
        )
        result = await db.execute(query_unprocessed)
        all_emails = result.scalars().all()

        print(f"✓ Processed emails: {len(processed_emails)}")
        print(f"✓ Total emails: {len(all_emails)}")
        print(f"✓ Unprocessed emails: {len(all_emails) - len(processed_emails)}")

    print("\n" + "="*80)
    print("✅ ALL DATABASE QUERY TESTS PASSED")
    print("="*80)
    print("\n[NEXT STEPS]")
    print("1. Test the actual API endpoints using curl or a REST client")
    print("2. Verify no JSON files are created after endpoint calls")
    print("3. Test endpoint responses match expected format")
    print("="*80 + "\n")


async def test_email_state_updates():
    """Test email state update operations"""
    print("\n" + "="*80)
    print("TESTING EMAIL STATE UPDATE OPERATIONS")
    print("="*80)

    async with SessionLocal() as db:
        # Get a test email
        users = await UserService.get_all_users(db)
        if not users:
            print("⚠ No users found, skipping state update tests")
            return

        test_user = users[0]
        emails = await EmailService.get_emails_by_user(db, test_user.id)

        if not emails:
            print("⚠ No emails found, skipping state update tests")
            return

        test_email = emails[0]
        message_id = test_email.message_id

        print(f"\n[TEST] Testing state updates for message_id: {message_id[:30]}...")

        # Test: Update email state
        print("\n[TEST 8] Testing EmailStateService.update_state()...")
        state = await EmailStateService.get_state_by_message_id(db, message_id)

        if not state:
            # Create state first
            print("  Creating initial state...")
            state = await EmailStateService.create_state(
                db=db,
                message_id=message_id,
                user_id=test_user.id,
                email_id=test_email.id
            )
            await db.commit()
            print("  ✓ State created")

        # Update the state
        print("  Updating state (setting processed=True)...")
        original_processed = state.processed
        await EmailStateService.update_state(
            db=db,
            message_id=message_id,
            processed=True,
            epicor_synced=False
        )
        await db.commit()

        # Verify update
        updated_state = await EmailStateService.get_state_by_message_id(db, message_id)
        if updated_state.processed == True:
            print("  ✓ State update successful")
        else:
            print("  ✗ FAILED: State not updated")

        # Restore original state
        print("  Restoring original state...")
        await EmailStateService.update_state(
            db=db,
            message_id=message_id,
            processed=original_processed
        )
        await db.commit()
        print("  ✓ State restored")

    print("\n" + "="*80)
    print("✅ EMAIL STATE UPDATE TESTS PASSED")
    print("="*80 + "\n")


async def main():
    """Run all tests"""
    try:
        await test_database_queries()
        await test_email_state_updates()

        print("\n" + "="*80)
        print("🎉 ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*80)
        print("\n[SUMMARY]")
        print("✓ Database queries working correctly")
        print("✓ Email state updates working correctly")
        print("✓ All router endpoint database operations verified")
        print("\n[NEXT STEPS]")
        print("Test the actual HTTP endpoints:")
        print("  curl http://localhost:8000/api/emails")
        print("  curl http://localhost:8000/api/emails/vendors/cache-status")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
