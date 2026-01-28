"""
Test Reply Email Extraction and Thread Aggregation

This test verifies:
1. The extract_reply_email() function extracts reason from casual reply emails
2. The thread aggregation service correctly merges data from multiple emails
3. The reason field from reply emails appears in the aggregated summary

Test Scenario (from screenshot reference):
- Original email: Price change notification with products but no reason
- Follow-up sent: Asking for reason
- Reply received: "increased labor cost and tariffs"
- Thread Summary should show: all products + reason from reply
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List
from unittest.mock import MagicMock, AsyncMock, patch

# Add parent directory to path for imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_mock_email(
    message_id: str,
    subject: str,
    received_at: datetime,
    is_outgoing: bool = False,
    is_reply: bool = False,
    supplier_info: dict = None,
    price_change_summary: dict = None,
    affected_products: list = None
):
    """Create a mock Email object for testing"""
    email = MagicMock()
    email.message_id = message_id
    email.subject = subject
    email.received_at = received_at
    email.is_outgoing = is_outgoing
    email.is_reply = is_reply
    email.supplier_info = supplier_info
    email.price_change_summary = price_change_summary
    email.affected_products = affected_products
    return email


def test_thread_aggregation_with_reply_reason():
    """
    Test that thread aggregation correctly merges reason from reply email.

    Scenario:
    1. Original email has products and supplier info but NO reason
    2. Reply email has the reason "increased labor cost and tariffs"
    3. Aggregated data should include the reason from the reply
    """
    from services.thread_aggregation_service import aggregate_thread_extractions

    print("\n" + "="*70)
    print("TEST: Thread Aggregation with Reply Reason")
    print("="*70)

    # Create test data based on the screenshot scenario
    now = datetime.utcnow()

    # Email 1: Original price change notification (no reason)
    original_email = create_mock_email(
        message_id="original-msg-123",
        subject="Price Change Notification - Hydraulic Fittings",
        received_at=now - timedelta(days=2),
        is_outgoing=False,
        is_reply=False,
        supplier_info={
            "supplier_name": "Faster Inc. (Indiana)",
            "supplier_id": "FAST1",
            "contact_email": "sales@faster.com"
        },
        price_change_summary={
            "change_type": "decrease",
            "effective_date": "2050-10-20",
            "reason": None,  # No reason in original email
            "overall_impact": None
        },
        affected_products=[
            {
                "product_name": "Hydraulic Fitting SAE Standard",
                "product_id": "#FFH06-12SAE F",
                "old_price": 240.00,
                "new_price": 40.00,
                "currency": "USD"
            }
        ]
    )

    # Email 2: Our follow-up (outgoing - should be excluded from aggregation)
    followup_email = create_mock_email(
        message_id="followup-msg-456",
        subject="RE: Price Change Notification - Hydraulic Fittings",
        received_at=now - timedelta(days=1),
        is_outgoing=True,  # This is our outgoing email
        is_reply=True,
        supplier_info=None,
        price_change_summary=None,
        affected_products=None
    )

    # Email 3: Supplier's reply with the reason
    reply_email = create_mock_email(
        message_id="reply-msg-789",
        subject="RE: Price Change Notification - Hydraulic Fittings",
        received_at=now,
        is_outgoing=False,
        is_reply=True,
        supplier_info=None,  # Might not have supplier info in reply
        price_change_summary={
            "change_type": None,
            "effective_date": None,
            "reason": "increased labor cost and tariffs",  # THE KEY FIELD!
            "overall_impact": None
        },
        affected_products=[]
    )

    # All emails in thread
    thread_emails = [original_email, followup_email, reply_email]

    # Run aggregation
    result = aggregate_thread_extractions(thread_emails, "Price Change Notification - Hydraulic Fittings")

    # Print results
    print("\nThread Summary:")
    print(f"  Total emails: {result['total_emails']}")
    print(f"  Received emails: {result['received_emails_count']}")
    print(f"  Emails with extractions: {result['emails_with_extractions']}")

    print("\nAggregated Supplier Info:")
    supplier_data = result['aggregated_supplier_info']['data']
    print(f"  Supplier Name: {supplier_data.get('supplier_name')}")
    print(f"  Supplier ID: {supplier_data.get('supplier_id')}")

    print("\nAggregated Price Change Summary:")
    summary_data = result['aggregated_price_change_summary']['data']
    summary_sources = result['aggregated_price_change_summary']['sources']
    print(f"  Change Type: {summary_data.get('change_type')}")
    print(f"  Effective Date: {summary_data.get('effective_date')}")
    print(f"  Reason: {summary_data.get('reason')}")
    if 'reason' in summary_sources:
        print(f"    (Source: {summary_sources['reason']['message_id']})")

    print("\nAggregated Products:")
    for p in result['aggregated_affected_products']:
        print(f"  - {p.get('product_name')}: ${p.get('old_price')} -> ${p.get('new_price')}")

    # Assertions
    print("\n" + "-"*70)
    print("ASSERTIONS:")

    # 1. Should have 3 total emails
    assert result['total_emails'] == 3, f"Expected 3 total emails, got {result['total_emails']}"
    print("  [OK] Total emails = 3")

    # 2. Should have 2 received emails (excluding outgoing followup)
    assert result['received_emails_count'] == 2, f"Expected 2 received emails, got {result['received_emails_count']}"
    print("  [OK] Received emails = 2 (outgoing excluded)")

    # 3. Supplier name should come from original email
    assert supplier_data.get('supplier_name') == "Faster Inc. (Indiana)", "Supplier name mismatch"
    print("  [OK] Supplier Name = 'Faster Inc. (Indiana)'")

    # 4. Supplier ID should come from original email
    assert supplier_data.get('supplier_id') == "FAST1", "Supplier ID mismatch"
    print("  [OK] Supplier ID = 'FAST1'")

    # 5. CRITICAL: Reason should come from reply email
    assert summary_data.get('reason') == "increased labor cost and tariffs", \
        f"Expected reason 'increased labor cost and tariffs', got '{summary_data.get('reason')}'"
    print("  [OK] Reason = 'increased labor cost and tariffs' (from reply)")

    # 6. Reason source should be the reply email
    assert 'reason' in summary_sources, "Reason source not tracked"
    assert summary_sources['reason']['message_id'] == "reply-msg-789", "Reason source mismatch"
    print("  [OK] Reason source = reply email")

    # 7. Products should come from original email
    assert len(result['aggregated_affected_products']) == 1, "Expected 1 product"
    print("  [OK] Products aggregated correctly")

    print("\n" + "="*70)
    print("[OK] TEST PASSED: Thread aggregation correctly merges reason from reply")
    print("="*70)

    return True


def test_thread_aggregation_later_overrides_earlier():
    """
    Test that later emails override earlier values for the same field.
    """
    from services.thread_aggregation_service import aggregate_thread_extractions

    print("\n" + "="*70)
    print("TEST: Later Emails Override Earlier Values")
    print("="*70)

    now = datetime.utcnow()

    # Email 1: Has initial reason
    email1 = create_mock_email(
        message_id="email-1",
        subject="Price Change",
        received_at=now - timedelta(days=2),
        is_outgoing=False,
        price_change_summary={
            "reason": "initial reason",
            "effective_date": "2025-01-01"
        }
    )

    # Email 2: Has updated reason (later email - should override)
    email2 = create_mock_email(
        message_id="email-2",
        subject="RE: Price Change",
        received_at=now,
        is_outgoing=False,
        is_reply=True,
        price_change_summary={
            "reason": "updated reason from reply",
            "effective_date": None  # Doesn't override because it's null
        }
    )

    result = aggregate_thread_extractions([email1, email2], "Price Change")
    summary = result['aggregated_price_change_summary']['data']
    sources = result['aggregated_price_change_summary']['sources']

    print(f"\nReason: {summary.get('reason')}")
    print(f"Effective Date: {summary.get('effective_date')}")

    # Later email's reason should override
    assert summary.get('reason') == "updated reason from reply", "Later reason should override"
    print("  [OK] Later reason overrides earlier")

    # Null values don't override - effective_date should remain from email1
    assert summary.get('effective_date') == "2025-01-01", "Null shouldn't override"
    print("  [OK] Null values don't override non-null")

    # Source tracking
    assert sources['reason']['message_id'] == "email-2", "Source should be later email"
    print("  [OK] Source tracking correct")

    print("\n" + "="*70)
    print("[OK] TEST PASSED: Later values correctly override earlier values")
    print("="*70)

    return True


def test_outgoing_emails_excluded():
    """
    Test that outgoing emails are excluded from aggregation.
    """
    from services.thread_aggregation_service import aggregate_thread_extractions

    print("\n" + "="*70)
    print("TEST: Outgoing Emails Excluded from Aggregation")
    print("="*70)

    now = datetime.utcnow()

    # Only outgoing emails
    outgoing1 = create_mock_email(
        message_id="out-1",
        subject="Follow-up",
        received_at=now,
        is_outgoing=True,
        price_change_summary={"reason": "should not appear"}
    )

    outgoing2 = create_mock_email(
        message_id="out-2",
        subject="Another follow-up",
        received_at=now,
        is_outgoing=True,
        supplier_info={"supplier_name": "Should Not Appear"}
    )

    result = aggregate_thread_extractions([outgoing1, outgoing2], "Test")

    print(f"\nTotal emails: {result['total_emails']}")
    print(f"Received emails: {result['received_emails_count']}")

    assert result['total_emails'] == 2, "Should count all emails"
    assert result['received_emails_count'] == 0, "Should have 0 received emails"

    # Aggregated data should be empty
    summary = result['aggregated_price_change_summary']['data']
    assert summary.get('reason') is None, "Outgoing reason should be excluded"
    print("  [OK] Outgoing emails excluded from aggregation")

    print("\n" + "="*70)
    print("[OK] TEST PASSED: Outgoing emails correctly excluded")
    print("="*70)

    return True


async def test_extract_reply_email_function():
    """
    Test the extract_reply_email function with a simulated reply.

    Note: This test requires Azure OpenAI credentials to be configured.
    If credentials are not available, it will be skipped.
    """
    print("\n" + "="*70)
    print("TEST: extract_reply_email Function (Integration)")
    print("="*70)

    try:
        from services.extractor import extract_reply_email
    except ImportError as e:
        print(f"  [SKIP] SKIPPED: Could not import extract_reply_email: {e}")
        return None

    # Check if Azure OpenAI is configured
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    if not api_key:
        print("  [SKIP] SKIPPED: AZURE_OPENAI_API_KEY not configured")
        return None

    # Simulated reply email content
    reply_content = """
Hi,

Thank you for your email regarding the price change notification.

The reason for the price change is increased labor costs and tariffs. We have seen
significant increases in our raw material costs over the past quarter, and the new
tariff regulations have added additional burden.

The new prices will be effective from October 20, 2050 as previously communicated.

Please let us know if you have any other questions.

Best regards,
John Smith
Faster Inc.
"""

    metadata = {
        "subject": "RE: Price Change Notification - Hydraulic Fittings",
        "from": "john.smith@faster.com",
        "date": datetime.utcnow().isoformat(),
        "message_id": "test-reply-123"
    }

    print("\nCalling extract_reply_email with sample content...")
    print(f"Content preview: {reply_content[:100]}...")

    try:
        result = await extract_reply_email(reply_content, metadata)

        print("\nExtraction Result:")
        print(json.dumps(result, indent=2, default=str))

        # Check if reason was extracted
        price_summary = result.get('price_change_summary', {})
        reason = price_summary.get('reason')

        if reason:
            print(f"\n[OK] Reason extracted: '{reason}'")

            # Check if it contains expected keywords
            reason_lower = reason.lower()
            if 'labor' in reason_lower or 'tariff' in reason_lower or 'cost' in reason_lower:
                print("  [OK] Reason contains expected keywords (labor/tariff/cost)")
            else:
                print("  [WARN] Reason doesn't contain expected keywords but was extracted")
        else:
            print("\n[FAIL] Reason was NOT extracted")
            return False

        print("\n" + "="*70)
        print("[OK] TEST PASSED: extract_reply_email correctly extracts reason")
        print("="*70)
        return True

    except Exception as e:
        print(f"\n[FAIL] Error during extraction: {e}")
        return False


def test_epicor_sync_uses_aggregated_data():
    """
    Test that Epicor sync would receive the aggregated thread data.

    This simulates the email_data dict that would be built for Epicor sync
    when an email is part of a conversation thread.
    """
    from services.thread_aggregation_service import aggregate_thread_extractions

    print("\n" + "="*70)
    print("TEST: Epicor Sync Uses Aggregated Thread Data")
    print("="*70)

    now = datetime.utcnow()

    # Simulate the exact scenario: original email + reply with reason
    original_email = create_mock_email(
        message_id="original-123",
        subject="Price Change Notification",
        received_at=now - timedelta(days=1),
        is_outgoing=False,
        supplier_info={
            "supplier_id": "FAST1",
            "supplier_name": "Faster Inc.",
            "contact_email": "sales@faster.com"
        },
        price_change_summary={
            "change_type": "increase",
            "effective_date": "2025-02-01",
            "reason": None  # NO REASON in original
        },
        affected_products=[
            {"product_id": "PART-001", "new_price": 100.00, "old_price": 90.00}
        ]
    )

    # Outgoing follow-up (excluded)
    followup = create_mock_email(
        message_id="followup-456",
        subject="RE: Price Change Notification",
        received_at=now - timedelta(hours=12),
        is_outgoing=True,
        is_reply=True
    )

    # Reply with reason
    reply = create_mock_email(
        message_id="reply-789",
        subject="RE: Price Change Notification",
        received_at=now,
        is_outgoing=False,
        is_reply=True,
        supplier_info={},  # May not have supplier info
        price_change_summary={
            "reason": "Raw material cost increase due to supply chain issues"
        },
        affected_products=[]
    )

    thread_emails = [original_email, followup, reply]

    # This is EXACTLY what the router now does for Epicor sync
    aggregated = aggregate_thread_extractions(thread_emails, "Price Change Notification")

    # Build email_data like the router does
    email_data = {
        "supplier_info": aggregated["aggregated_supplier_info"]["data"],
        "price_change_summary": aggregated["aggregated_price_change_summary"]["data"],
        "affected_products": [
            {k: v for k, v in p.items() if not k.startswith("source_")}
            for p in aggregated["aggregated_affected_products"]
        ]
    }

    print("\nEmail data that would be sent to Epicor:")
    print(f"  supplier_id: {email_data['supplier_info'].get('supplier_id')}")
    print(f"  supplier_name: {email_data['supplier_info'].get('supplier_name')}")
    print(f"  effective_date: {email_data['price_change_summary'].get('effective_date')}")
    print(f"  reason: {email_data['price_change_summary'].get('reason')}")
    print(f"  products: {len(email_data['affected_products'])}")

    # Assertions
    print("\n" + "-"*70)
    print("ASSERTIONS:")

    # 1. Supplier ID should be present (from original)
    assert email_data['supplier_info'].get('supplier_id') == 'FAST1', "Supplier ID missing"
    print("  [OK] Supplier ID = FAST1 (from original)")

    # 2. CRITICAL: Reason should be present (from reply)
    assert email_data['price_change_summary'].get('reason') is not None, "Reason missing!"
    assert "supply chain" in email_data['price_change_summary']['reason'].lower(), "Wrong reason"
    print("  [OK] Reason from reply included in Epicor data")

    # 3. Effective date should be present (from original)
    assert email_data['price_change_summary'].get('effective_date') == '2025-02-01', "Effective date missing"
    print("  [OK] Effective date = 2025-02-01 (from original)")

    # 4. Products should be present (from original)
    assert len(email_data['affected_products']) == 1, "Products missing"
    print("  [OK] Products included (1 product)")

    print("\n" + "="*70)
    print("[OK] TEST PASSED: Epicor sync correctly uses aggregated thread data")
    print("="*70)

    return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("[TEST] REPLY EXTRACTION & THREAD AGGREGATION TESTS")
    print("="*70)

    results = []

    # Unit tests (no API needed)
    print("\n[UNIT] Unit Tests (No API Required)")
    print("-"*70)

    try:
        results.append(("Thread Aggregation with Reply Reason", test_thread_aggregation_with_reply_reason()))
    except Exception as e:
        print(f"[FAIL] FAILED: {e}")
        results.append(("Thread Aggregation with Reply Reason", False))

    try:
        results.append(("Later Overrides Earlier", test_thread_aggregation_later_overrides_earlier()))
    except Exception as e:
        print(f"[FAIL] FAILED: {e}")
        results.append(("Later Overrides Earlier", False))

    try:
        results.append(("Outgoing Emails Excluded", test_outgoing_emails_excluded()))
    except Exception as e:
        print(f"[FAIL] FAILED: {e}")
        results.append(("Outgoing Emails Excluded", False))

    try:
        results.append(("Epicor Sync Uses Aggregated Data", test_epicor_sync_uses_aggregated_data()))
    except Exception as e:
        print(f"[FAIL] FAILED: {e}")
        results.append(("Epicor Sync Uses Aggregated Data", False))

    # Integration test (requires API)
    print("\n[INTEGRATION] Integration Tests (Requires Azure OpenAI)")
    print("-"*70)

    try:
        result = asyncio.run(test_extract_reply_email_function())
        if result is not None:
            results.append(("extract_reply_email Function", result))
        else:
            results.append(("extract_reply_email Function", "SKIPPED"))
    except Exception as e:
        print(f"[FAIL] FAILED: {e}")
        results.append(("extract_reply_email Function", False))

    # Summary
    print("\n" + "="*70)
    print("[SUMMARY] TEST SUMMARY")
    print("="*70)

    passed = 0
    failed = 0
    skipped = 0

    for name, result in results:
        if result == "SKIPPED":
            status = "[SKIP] SKIPPED"
            skipped += 1
        elif result:
            status = "[PASS] PASSED"
            passed += 1
        else:
            status = "[FAIL] FAILED"
            failed += 1
        print(f"  {status}: {name}")

    print(f"\nTotal: {len(results)} tests")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Skipped: {skipped}")

    if failed == 0:
        print("\n[SUCCESS] All tests passed!")
        return True
    else:
        print(f"\n[WARNING] {failed} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
