import os, json
from auth.multi_graph import graph_client
from processors import save_attachment, process_all_content
from extractor import extract_price_change_json

OUTPUT_DIR = "outputs"
DOWNLOADS_DIR = "downloads"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

def process_user_message(msg, user_email):
    """Process a single email message for a specific user with data isolation"""
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
    print(f"📧 PROCESSING EMAIL FOR: {user_email}")
    print("="*80)
    print(f"📌 Subject: {subject}")
    print(f"👤 From: {sender}")
    print(f"📅 Date: {date_received}")
    print(f"🆔 Message ID: {message_id[:20]}...")
    print("-"*80)
    
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
    
    # Process attachments with user-specific download directory
    attachment_paths = []
    has_attachments = msg.get("hasAttachments", False)

    if has_attachments:
        print("📎 PROCESSING ATTACHMENTS...")
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

    print(f"\n📊 EMAIL CONTENT SUMMARY:")
    print(f"   📝 Body length: {len(email_body)} characters")
    print(f"   📎 Attachments: {len(attachment_paths)}")
    print("-"*80)
    
    # Process all content (email body + attachments)
    combined_content = process_all_content(email_body, attachment_paths)
    
    if not combined_content.strip():
        print("   ⚠️  No content to process")
        return
    
    # Extract structured data
    print("\n🤖 AZURE OPENAI EXTRACTION:")
    print("   🔄 Analyzing email content with AI...")
    try:
        result = extract_price_change_json(combined_content, email_metadata)

        # Check if email was identified as price change
        if result.get("error") == "Email does not appear to be a price change notification":
            print("   ℹ️  Not a price change email - SKIPPED")
            print("="*80 + "\n")
            return

        # Save results to user-specific directory
        output_filename = f"price_change_{message_id}.json"
        output_path = os.path.join(user_output_dir, output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"   ✅ Extraction successful!")
        print(f"   💾 Saved to: {output_filename}")

        # Print summary of extracted data
        print("\n📋 EXTRACTED DATA SUMMARY:")
        print_extraction_summary(result)
        print("-"*80)

        # 🚀 AUTOMATIC EPICOR UPDATE
        print("\n💼 EPICOR ERP UPDATE:")
        print("   🔄 Initiating automatic price update...")
        try:
            from services.epicor_service import epicor_service

            affected_products = result.get("affected_products", [])
            if affected_products:
                print(f"   📦 Products to update: {len(affected_products)}")

                # Log each product
                for i, product in enumerate(affected_products, 1):
                    product_id = product.get("product_id") or product.get("product_code", "Unknown")
                    new_price = product.get("new_price", "N/A")
                    print(f"      {i}. Part: {product_id} → New Price: ${new_price}")

                print("\n   🔄 Updating prices in Epicor...")
                # Perform batch update
                epicor_results = epicor_service.batch_update_prices(affected_products)

                # Save Epicor update results
                epicor_output_filename = f"epicor_update_{message_id}.json"
                epicor_output_path = os.path.join(user_output_dir, epicor_output_filename)

                with open(epicor_output_path, "w", encoding="utf-8") as f:
                    json.dump(epicor_results, f, indent=2, ensure_ascii=False)

                # Log detailed results
                print(f"\n   ✅ EPICOR UPDATE COMPLETE!")
                print(f"   📊 Results:")
                print(f"      ✅ Successful: {epicor_results['successful']}")
                print(f"      ❌ Failed: {epicor_results['failed']}")
                print(f"      ⏭️  Skipped: {epicor_results['skipped']}")
                print(f"   💾 Results saved to: {epicor_output_filename}")

                # Log individual results
                if epicor_results.get('details'):
                    print("\n   📋 Detailed Results:")
                    for detail in epicor_results['details']:
                        part_num = detail.get('part_num', 'Unknown')
                        status = detail.get('status', 'unknown')
                        if status == 'success':
                            old_price = detail.get('old_price', 'N/A')
                            new_price = detail.get('new_price', 'N/A')
                            print(f"      ✅ {part_num}: ${old_price} → ${new_price}")
                        elif status == 'failed':
                            reason = detail.get('message', 'Unknown error')
                            print(f"      ❌ {part_num}: {reason}")
                        elif status == 'skipped':
                            reason = detail.get('reason', 'Unknown')
                            print(f"      ⏭️  {part_num}: {reason}")
            else:
                print("   ⚠️  No products found in extraction")
                print("   ⏭️  Skipping Epicor update")

        except Exception as epicor_error:
            print(f"\n   ❌ EPICOR UPDATE FAILED!")
            print(f"   ⚠️  Error: {epicor_error}")
            # Save error log
            error_log = {
                "error": str(epicor_error),
                "message_id": message_id,
                "timestamp": email_metadata.get("date")
            }
            error_path = os.path.join(user_output_dir, f"epicor_error_{message_id}.json")
            with open(error_path, "w", encoding="utf-8") as f:
                json.dump(error_log, f, indent=2, ensure_ascii=False)
            print(f"   💾 Error log saved to: epicor_error_{message_id}.json")

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
    supplier_name = data.get("supplier_info", {}).get("supplier_name")
    if supplier_name:
        print(f"   🏢 Supplier: {supplier_name}")
    
    # Price change details
    change_details = data.get("price_change_details", {})
    change_type = change_details.get("change_type")
    effective_date = change_details.get("effective_date")
    
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