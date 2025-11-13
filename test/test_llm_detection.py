"""
Test Script for LLM-Powered Price Change Detection

This script demonstrates and tests the new LLM-based price change detection
functionality. It tests various email scenarios to validate detection accuracy.
"""

import os
import json
from dotenv import load_dotenv
from services.llm_detector import llm_is_price_change_email, get_detection_stats

# Load environment variables
load_dotenv()

# Test email scenarios
TEST_EMAILS = [
    {
        "name": "Clear Price Change Notification",
        "content": """
Dear Customer,

We are writing to inform you of an upcoming price change for our products,
effective March 1st, 2024.

Product Details:
- Part #FFH06-12: Old Price $45.00 → New Price $52.00
- Part #ABC-123: Old Price $120.00 → New Price $135.00

Reason: Due to increased raw material costs and supply chain challenges.

Please contact us if you have any questions.

Best regards,
Acme Corporation
Sales Team
sales@acmecorp.com
        """,
        "metadata": {
            "subject": "Important: Price Change Notification - Effective March 1st",
            "sender": "sales@acmecorp.com",
            "date": "2024-02-15T10:00:00Z",
            "has_attachments": False
        },
        "expected": True
    },
    {
        "name": "Invoice (Not a Price Change)",
        "content": """
Dear Customer,

Your invoice for February 2024.

Invoice #: INV-2024-001
Amount Due: $1,245.00
Due Date: March 15, 2024

Items:
- Widget A: $250.00
- Widget B: $995.00

Thank you for your business.
        """,
        "metadata": {
            "subject": "Invoice #INV-2024-001 - February 2024",
            "sender": "billing@acmecorp.com",
            "date": "2024-02-28T15:30:00Z",
            "has_attachments": True
        },
        "expected": False
    },
    {
        "name": "Subtle Price Change (Testing LLM Understanding)",
        "content": """
Hi Team,

Just wanted to give you a heads up that we'll be adjusting our rates starting
next quarter. I've attached the updated catalog with the new figures.

The changes reflect current market conditions. Let me know if you need anything.

Thanks,
John Smith
Regional Sales Manager
        """,
        "metadata": {
            "subject": "Q2 Catalog Update",
            "sender": "j.smith@supplierco.com",
            "date": "2024-03-20T09:15:00Z",
            "has_attachments": True
        },
        "expected": True
    },
    {
        "name": "Order Confirmation (Not a Price Change)",
        "content": """
Order Confirmation

Thank you for your order!

Order #: ORD-2024-12345
Order Date: March 15, 2024

Items Ordered:
1. Product A - Qty: 10 - Unit Price: $50.00 - Total: $500.00
2. Product B - Qty: 5 - Unit Price: $120.00 - Total: $600.00

Subtotal: $1,100.00
Tax: $88.00
Total: $1,188.00

Your order will ship within 2-3 business days.
        """,
        "metadata": {
            "subject": "Order Confirmation - ORD-2024-12345",
            "sender": "orders@vendor.com",
            "date": "2024-03-15T14:20:00Z",
            "has_attachments": False
        },
        "expected": False
    },
    {
        "name": "Marketing Newsletter with Prices (Not a Price Change)",
        "content": """
Check out our Spring Sale!

Save big on these popular items:
- Model X: Now only $99.99! (Regular $129.99)
- Model Y: Just $149.99! (Regular $199.99)
- Model Z: Special price $249.99!

Limited time offer. Shop now at www.example.com

Unsubscribe | Manage Preferences
        """,
        "metadata": {
            "subject": "Spring Sale - Up to 30% Off!",
            "sender": "marketing@retailstore.com",
            "date": "2024-03-10T08:00:00Z",
            "has_attachments": False
        },
        "expected": False
    },
    {
        "name": "Price Increase with Formal Language",
        "content": """
PRICE ADJUSTMENT NOTIFICATION

Dear Valued Customer,

This letter serves as formal notification of price adjustments to our product line,
effective 60 days from the date of this notice.

The revision is necessitated by increased manufacturing costs and regulatory compliance
requirements. Attached please find the amended price schedule.

We appreciate your continued partnership.

Sincerely,
ABC Manufacturing Ltd.
Pricing Department
pricing@abcmfg.com
Phone: (555) 123-4567
        """,
        "metadata": {
            "subject": "FORMAL NOTICE: Price Schedule Revision",
            "sender": "pricing@abcmfg.com",
            "date": "2024-02-20T11:45:00Z",
            "has_attachments": True
        },
        "expected": True
    }
]


def run_detection_tests():
    """Run detection tests on all test email scenarios"""
    print("="*80)
    print("🤖 LLM PRICE CHANGE DETECTION - TEST SUITE")
    print("="*80)
    print(f"Testing {len(TEST_EMAILS)} email scenarios...\n")

    results = []
    correct_count = 0

    for i, test_email in enumerate(TEST_EMAILS, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}/{len(TEST_EMAILS)}: {test_email['name']}")
        print(f"{'='*80}")
        print(f"📧 Subject: {test_email['metadata']['subject']}")
        print(f"👤 From: {test_email['metadata']['sender']}")
        print(f"📎 Has Attachments: {test_email['metadata']['has_attachments']}")
        print(f"🎯 Expected: {'PRICE CHANGE' if test_email['expected'] else 'NOT PRICE CHANGE'}")
        print(f"\n📄 Email Content Preview:")
        print(f"{test_email['content'][:200]}...")
        print(f"\n🤖 Running LLM Detection...")

        # Run detection
        detection_result = llm_is_price_change_email(
            test_email['content'],
            test_email['metadata']
        )

        # Display results
        is_price_change = detection_result.get('is_price_change', False)
        confidence = detection_result.get('confidence', 0.0)
        reasoning = detection_result.get('reasoning', 'N/A')
        meets_threshold = detection_result.get('meets_threshold', False)

        print(f"\n📊 DETECTION RESULT:")
        print(f"   • Is Price Change: {is_price_change}")
        print(f"   • Confidence: {confidence:.2%}")
        print(f"   • Meets Threshold: {meets_threshold}")
        print(f"   • Reasoning: {reasoning}")

        # Check if result matches expectation
        is_correct = (meets_threshold == test_email['expected'])
        if is_correct:
            correct_count += 1
            print(f"\n✅ CORRECT DETECTION")
        else:
            print(f"\n❌ INCORRECT DETECTION")
            print(f"   Expected: {test_email['expected']}, Got: {meets_threshold}")

        results.append({
            "test_name": test_email['name'],
            "expected": test_email['expected'],
            "detected": meets_threshold,
            "confidence": confidence,
            "correct": is_correct,
            "reasoning": reasoning
        })

    # Print summary
    print(f"\n\n{'='*80}")
    print("📊 TEST SUMMARY")
    print(f"{'='*80}")
    print(f"Total Tests: {len(TEST_EMAILS)}")
    print(f"Correct Detections: {correct_count}/{len(TEST_EMAILS)}")
    print(f"Accuracy: {(correct_count/len(TEST_EMAILS))*100:.1f}%")
    print(f"{'='*80}")

    # Detailed results
    print(f"\n📋 DETAILED RESULTS:")
    for i, result in enumerate(results, 1):
        status = "✅" if result['correct'] else "❌"
        print(f"\n{i}. {status} {result['test_name']}")
        print(f"   Expected: {result['expected']}, Detected: {result['detected']}, Confidence: {result['confidence']:.2%}")
        print(f"   Reasoning: {result['reasoning']}")

    # Calculate statistics
    stats = get_detection_stats(
        [{"meets_threshold": r["detected"], "confidence": r["confidence"]} for r in results]
    )
    print(f"\n📈 DETECTION STATISTICS:")
    print(f"   • Average Confidence: {stats['average_confidence']:.2%}")
    print(f"   • Max Confidence: {stats['max_confidence']:.2%}")
    print(f"   • Min Confidence: {stats['min_confidence']:.2%}")
    print(f"   • Detection Rate: {stats['detection_rate']:.1%}")

    print(f"\n{'='*80}")
    print("✅ TEST SUITE COMPLETE")
    print(f"{'='*80}\n")

    return results


def test_single_email():
    """Interactive test for a single custom email"""
    print("\n" + "="*80)
    print("🧪 SINGLE EMAIL TEST MODE")
    print("="*80)
    print("Enter email details for testing:\n")

    subject = input("Subject: ").strip()
    sender = input("Sender email: ").strip()
    has_attachments = input("Has attachments? (y/n): ").strip().lower() == 'y'

    print("\nEnter email content (press Ctrl+D or Ctrl+Z when done):")
    print("-"*80)

    try:
        content_lines = []
        while True:
            try:
                line = input()
                content_lines.append(line)
            except EOFError:
                break
    except KeyboardInterrupt:
        print("\n\nTest cancelled.")
        return

    content = "\n".join(content_lines)

    metadata = {
        "subject": subject,
        "sender": sender,
        "date": "2024-03-15T10:00:00Z",
        "has_attachments": has_attachments
    }

    print(f"\n🤖 Running LLM Detection...")
    result = llm_is_price_change_email(content, metadata)

    print(f"\n📊 DETECTION RESULT:")
    print(f"   • Is Price Change: {result.get('is_price_change', False)}")
    print(f"   • Confidence: {result.get('confidence', 0.0):.2%}")
    print(f"   • Meets Threshold: {result.get('meets_threshold', False)}")
    print(f"   • Reasoning: {result.get('reasoning', 'N/A')}")
    print("="*80 + "\n")


def main():
    """Main test function"""
    print("\n🤖 LLM Price Change Detection - Test Suite\n")
    print("Options:")
    print("1. Run full test suite (recommended)")
    print("2. Test a single custom email")
    print("3. Exit")

    try:
        choice = input("\nEnter your choice (1-3): ").strip()

        if choice == "1":
            run_detection_tests()
        elif choice == "2":
            test_single_email()
        elif choice == "3":
            print("Exiting...")
        else:
            print("Invalid choice. Please run again.")
    except KeyboardInterrupt:
        print("\n\nTest cancelled.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
