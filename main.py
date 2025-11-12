import os, json
import asyncio
from auth.multi_graph import graph_client
from utils.processors import save_attachment, process_all_content
from services.extractor import extract_price_change_json

# Database imports
from database.config import SessionLocal
from database.services.user_service import UserService
from database.services.email_service import EmailService
from database.services.email_state_service import EmailStateService

OUTPUT_DIR = "outputs"
DOWNLOADS_DIR = "downloads"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

def process_user_message(msg, user_email, skip_verification=False):
    """Process a single email message for a specific user with data isolation

    Args:
        msg: Email message dict from Microsoft Graph API
        user_email: Email address of the user
        skip_verification: If True, bypass vendor verification check (for manually approved emails)
    """
    # Create user-specific output directory
    safe_email = user_email.replace("@", "_at_").replace(".", "_dot_")
    user_output_dir = os.path.join(OUTPUT_DIR, safe_email)
    user_downloads_dir = os.path.join(DOWNLOADS_DIR, safe_email)
    os.makedirs(user_output_dir, exist_ok=True)
    os.makedirs(user_downloads_dir, exist_ok=True)

    # Extract basic email information
    subject = msg.get("subject", "(no subject)")
    sender_info = msg.get("from", {}).get("emailAddress", {})
    sender = sender_info.get("address", "(no sender)")
    date_received = msg.get("receivedDateTime", "(no date)")
    message_id = msg.get("id", "")

    print("\n" + "="*80)
    print(f"🚀 EMAIL INTELLIGENCE SYSTEM - 3-STAGE WORKFLOW")
    print("="*80)
    print(f"📧 Processing email for: {user_email}")
    print(f"📌 Subject: {subject}")
    print(f"👤 From: {sender}")
    print(f"📅 Date: {date_received}")
    print(f"🆔 Message ID: {message_id[:20]}...")
    print("="*80)
    
    # Prepare metadata
    email_metadata = {
        "subject": subject,
        "from": sender,
        "sender": sender,
        "date": date_received,
        "message_id": message_id,
        "user_email": user_email,
        "attachments": []
    }
    
    # ========== STAGE 1: EMAIL DETECTION ==========
    print("\n📬 STAGE 1: EMAIL DETECTION")
    print("-"*80)

    # Process attachments with user-specific download directory
    attachment_paths = []
    has_attachments = msg.get("hasAttachments", False)

    if has_attachments:
        print("📎 Processing attachments...")
        # Import here to avoid circular import issues
        from auth.multi_graph import graph_client
        attachments = graph_client.get_user_message_attachments(user_email, message_id)

        for att in attachments:
            if att.get("@odata.type", "").endswith("fileAttachment"):
                filename = att.get("name", "unknown")
                print(f"   ✅ Attachment: {filename}")

                # Save to user-specific directory
                att_copy = att.copy()
                path = save_user_attachment(att_copy, user_downloads_dir)
                if path:
                    attachment_paths.append(path)
                    email_metadata["attachments"].append(filename)

    # Get email body content
    email_body = ""
    body_data = msg.get("body", {})
    if body_data:
        email_body = body_data.get("content", "")

    print(f"✅ Stage 1 Complete: Content extracted")
    print(f"   📝 Body length: {len(email_body)} characters")
    print(f"   📎 Attachments: {len(attachment_paths)}")
    print("="*80)
    
    # Process all content (email body + attachments)
    combined_content = process_all_content(email_body, attachment_paths)

    if not combined_content.strip():
        print("   ⚠️  No content to process")
        print("="*80 + "\n")
        return

    # ========== PRE-STAGE 2: VENDOR VERIFICATION CHECK ==========
    if not skip_verification:
        # Check email state in database
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        async def check_verification_status():
            async with SessionLocal() as db:
                state = await EmailStateService.get_state_by_message_id(db, message_id)
                return state

        state = loop.run_until_complete(check_verification_status())

        if state and state.verification_status == 'pending_review':
            print("\n⚠️  EMAIL FLAGGED FOR VERIFICATION")
            print("-"*80)
            print("   This email is from an unverified sender")
            print("   AI extraction skipped to save tokens")
            print("   📋 Review this email in the dashboard 'Pending Verification' tab")
            print("   ✅ Approve to trigger AI extraction")
            print("="*80 + "\n")
            return

    # ========== STAGE 2: AI ENTITY EXTRACTION ==========
    print("\n🤖 STAGE 2: AI ENTITY EXTRACTION")
    print("-"*80)
    print("🔄 Azure OpenAI GPT-4.1 Processing...")
    print("   Extracting parallel entities:")
    print("   • Supplier ID")
    print("   • Part Name & Number")
    print("   • Effective Date")
    print("   • New Price")
    print("   • Reason for Change")

    try:
        # Note: Email has already been validated as price change by LLM detector in delta_service
        # This extraction focuses solely on extracting structured data
        result = extract_price_change_json(combined_content, email_metadata)

        # Save to database (JSON file writes removed - database is now the primary storage)
        async def save_to_database():
            async with SessionLocal() as db:
                # Get or create user
                user, _ = await UserService.get_or_create_user(db, user_email)

                # Create or update email record
                email_record = await EmailService.get_email_by_message_id(db, message_id)
                if not email_record:
                    email_record = await EmailService.create_email(
                        db,
                        message_id=message_id,
                        user_id=user.id,
                        subject=subject,
                        sender_email=sender,
                        received_at=date_received,
                        has_attachments=has_attachments,
                        body_text=email_body,
                        supplier_info=result.get("supplier_info"),
                        price_change_summary=result.get("price_change_summary"),
                        affected_products=result.get("affected_products"),
                        additional_details=result.get("additional_details"),
                        raw_email_data=msg
                    )
                else:
                    # Update existing record
                    email_record.supplier_info = result.get("supplier_info")
                    email_record.price_change_summary = result.get("price_change_summary")
                    email_record.affected_products = result.get("affected_products")
                    email_record.additional_details = result.get("additional_details")

                # Update email state
                state = await EmailStateService.get_state_by_message_id(db, message_id)
                if not state:
                    state = await EmailStateService.create_state(
                        db,
                        message_id=message_id,
                        user_id=user.id,
                        email_id=email_record.id,
                        is_price_change=True
                    )
                else:
                    state.email_id = email_record.id
                    state.is_price_change = True

                await db.commit()

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(save_to_database())

        print(f"✅ Stage 2 Complete: Data extracted successfully")
        print(f"   💾 Saved to: {output_filename}")
        print(f"   💾 Saved to database")

        # Print summary of extracted data
        print("\n📋 Extracted Data Summary:")
        print_extraction_summary(result)
        print("="*80)

        # Note: Epicor sync will happen when user clicks "Process" button in the UI
        print("\n💼 Email extracted and ready for processing")
        print("   ℹ️  Epicor sync will occur when you click 'Mark as Processed' in the dashboard")
        print("="*80)
        print("✅ EMAIL PROCESSING COMPLETE")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n❌ ERROR PROCESSING EMAIL: {e}")
        print("="*80 + "\n")

def save_user_attachment(attachment, user_downloads_dir):
    """Save email attachment to user-specific downloads directory"""
    filename = attachment["name"]
    content_bytes = attachment.get("contentBytes")
    if not content_bytes:
        return None
    
    try:
        # Handle base64 encoded content
        if isinstance(content_bytes, str):
            try:
                import base64
                decoded_content = base64.b64decode(content_bytes)
            except:
                decoded_content = content_bytes.encode('utf-8')
        else:
            decoded_content = content_bytes
            
        path = os.path.join(user_downloads_dir, filename)
        with open(path, "wb") as f:
            f.write(decoded_content)
        
        print(f"✅ Saved user attachment: {filename}")
        return path
    except Exception as e:
        print(f"❌ Error saving user attachment {filename}: {e}")
        return None

def process_message_with_locks(message_id):
    """
    Legacy function - now replaced by delta service
    Use process_user_message() instead with proper user context
    """
    print(f"⚠️  process_message_with_locks is legacy - use delta service instead")
    print(f"   Message {message_id} should be processed via web interface")
    return False

def process_message(msg):
    """
    Legacy function - now replaced by process_user_message() with user context
    This function is deprecated and should not be used in the delta service system
    """
    print("⚠️  process_message() is legacy - use process_user_message() instead")
    print("   Modern email processing requires user context for proper data isolation")
    
    # Extract basic info for logging
    subject = msg.get("subject", "(no subject)")
    message_id = msg.get("id", "")
    print(f"   📧 Legacy processing attempted for: {subject} (ID: {message_id})")
    print("   ➡️  Use the web interface with delta service for proper processing")
    
    return False

def print_extraction_summary(data):
    """Print a summary of the extracted price change data"""
    if "error" in data:
        print(f"   ❌ Extraction error: {data['error']}")
        return

    # Supplier info
    supplier_info = data.get("supplier_info", {})
    supplier_id = supplier_info.get("supplier_id")
    supplier_name = supplier_info.get("supplier_name")

    if supplier_id:
        print(f"   🏢 Supplier ID: {supplier_id}")
    if supplier_name:
        print(f"   🏢 Supplier Name: {supplier_name}")

    # Price change details (check both locations for backward compatibility)
    change_details = data.get("price_change_details", {})
    price_change_summary = data.get("price_change_summary", {})

    change_type = change_details.get("change_type") or price_change_summary.get("change_type")
    effective_date = change_details.get("effective_date") or price_change_summary.get("effective_date")
    
    if change_type:
        print(f"   📈 Change Type: {change_type}")
    if effective_date:
        print(f"   📅 Effective Date: {effective_date}")
    
    # Products affected
    products = data.get("affected_products", [])
    if products:
        print(f"   📦 Products Affected: {len(products)}")
        for i, product in enumerate(products[:3]):  # Show first 3 products
            name = product.get("product_name", "Unknown")
            old_price = product.get("old_price", "N/A")
            new_price = product.get("new_price", "N/A")
            print(f"      {i+1}. {name}: {old_price} → {new_price}")
        
        if len(products) > 3:
            print(f"      ... and {len(products) - 3} more products")
    
    # Action required
    action = data.get("action_required", {})
    deadline = action.get("response_deadline")
    if deadline:
        print(f"   ⏰ Response Deadline: {deadline}")

def main():
    """
    Legacy CLI processing function - now replaced by delta service
    
    For modern usage:
    1. Run: python webhook.py
    2. Visit: http://localhost:8000
    3. Authenticate with Microsoft OAuth
    4. Emails will be automatically processed via delta queries
    """
    print("🚀 Email Intelligence System")
    print("=" * 50)
    print("⚠️  This CLI mode is legacy - use the web interface instead:")
    print("   1. Run: python webhook.py")
    print("   2. Visit: http://localhost:8000")
    print("   3. Authenticate with Microsoft OAuth")
    print("   4. Emails automatically processed via delta queries every 3 minutes")
    print("=" * 50)
    print("✅ For current functionality, use the web interface with delta service")
    
    return

if __name__ == "__main__":
    main()