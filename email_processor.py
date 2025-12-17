import os, json
import asyncio
import logging
from auth.multi_graph import graph_client
from utils.processors import save_attachment, process_all_content
from utils.thread_detection import extract_thread_info
from services.extractor import extract_price_change_json

# Database imports
from database.config import SessionLocal
from database.services.user_service import UserService
from database.services.email_service import EmailService
from database.services.email_state_service import EmailStateService
from database.services.bom_impact_service import BomImpactService

logger = logging.getLogger(__name__)

OUTPUT_DIR = "outputs"
DOWNLOADS_DIR = "downloads"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)


async def _process_single_product_bom(
    epicor_service,
    idx: int,
    product: dict,
    supplier_id: str,
    effective_date: str | None,
    total_products: int
) -> dict:
    """
    Process BOM impact analysis for a single product (async).

    Returns a dict with the result or error information.
    """
    part_num = product.get("product_id", "")
    old_price = product.get("old_price") or 0
    new_price = product.get("new_price") or 0

    if not part_num:
        logger.warning(f"   Product {idx}: Missing product_id, skipping")
        return {
            "idx": idx,
            "part_num": part_num,
            "skipped": True,
            "result": None
        }

    logger.info(f"   Starting Product {idx + 1}/{total_products}: {part_num} (${old_price:.4f} -> ${new_price:.4f})")

    try:
        # Run the BOM impact analysis (async Epicor API call)
        impact_result = await epicor_service.process_supplier_price_change(
            part_num=part_num,
            supplier_id=supplier_id,
            old_price=float(old_price) if old_price else 0,
            new_price=float(new_price) if new_price else 0,
            effective_date=effective_date,
            email_metadata=None
        )

        # Log summary
        status = impact_result.get("status", "unknown")
        summary = impact_result.get("bom_impact", {}).get("summary", {})
        total_assemblies = summary.get("total_assemblies_affected", 0)
        risk_summary = summary.get("risk_summary", {})

        logger.info(f"   Product {idx + 1}/{total_products} ({part_num}): {status}, {total_assemblies} assemblies")
        if risk_summary and (risk_summary.get('critical', 0) > 0 or risk_summary.get('high', 0) > 0):
            logger.warning(f"      Risk: Critical={risk_summary.get('critical', 0)}, High={risk_summary.get('high', 0)}")

        return {
            "idx": idx,
            "part_num": part_num,
            "skipped": False,
            "error": None,
            "result": impact_result
        }

    except Exception as e:
        logger.error(f"   Product {idx + 1}/{total_products} ({part_num}): Error - {e}")
        # Return error result
        error_result = {
            "status": "error",
            "processing_errors": [str(e)],
            "component": {"part_num": part_num, "validated": False},
            "supplier": {"supplier_id": supplier_id, "validated": False},
            "price_change": {"part_num": part_num, "old_price": old_price, "new_price": new_price},
            "bom_impact": {"summary": {}, "impact_details": [], "high_risk_assemblies": []},
            "actions_required": [],
            "can_auto_approve": False
        }
        return {
            "idx": idx,
            "part_num": part_num,
            "skipped": False,
            "error": str(e),
            "result": error_result
        }


async def run_bom_impact_analysis(email_id: int, extraction_result: dict, supplier_info: dict):
    """
    Run BOM impact analysis for all products in an email and store results in database.

    This runs in the background after AI extraction is complete.
    Uses asyncio.gather() for concurrent processing of multiple products.

    Args:
        email_id: Database ID of the email record
        extraction_result: The AI extraction result containing affected_products
        supplier_info: Supplier info from extraction (contains supplier_id)
    """
    from services.epicor_service import EpicorAPIService as EpicorService

    # Configuration for concurrent processing
    MAX_CONCURRENT = 5  # Limit concurrent Epicor API calls to avoid overwhelming the server

    affected_products = extraction_result.get("affected_products", [])
    if not affected_products:
        logger.info("   No affected products to analyze for BOM impact")
        return

    supplier_id = supplier_info.get("supplier_id", "") if supplier_info else ""
    effective_date = extraction_result.get("price_change_summary", {}).get("effective_date")
    total_products = len(affected_products)

    logger.info("STAGE 3: BOM IMPACT ANALYSIS (CONCURRENT)")
    logger.info("-" * 80)
    logger.info(f"   Analyzing {total_products} product(s) for BOM impact...")
    logger.info(f"   Using up to {MAX_CONCURRENT} concurrent tasks")

    try:
        epicor_service = EpicorService()

        # Run concurrent BOM analysis using asyncio
        logger.info("   Starting concurrent BOM analysis...")

        # Use semaphore to limit concurrency
        semaphore = asyncio.Semaphore(MAX_CONCURRENT)

        async def process_with_semaphore(idx: int, product: dict):
            async with semaphore:
                return await _process_single_product_bom(
                    epicor_service,
                    idx,
                    product,
                    supplier_id,
                    effective_date,
                    total_products
                )

        # Create tasks for all products
        tasks = [
            process_with_semaphore(idx, product)
            for idx, product in enumerate(affected_products)
        ]

        # Run all tasks concurrently and collect results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results, handling any exceptions
        processed_results = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"   Unexpected error for product {idx}: {result}")
                product = affected_products[idx]
                processed_results.append({
                    "idx": idx,
                    "part_num": product.get("product_id", ""),
                    "skipped": False,
                    "error": str(result),
                    "result": {
                        "status": "error",
                        "processing_errors": [f"Unexpected error: {str(result)}"],
                        "component": {"part_num": product.get("product_id", ""), "validated": False},
                        "supplier": {"supplier_id": supplier_id, "validated": False},
                        "price_change": {
                            "part_num": product.get("product_id", ""),
                            "old_price": product.get("old_price", 0),
                            "new_price": product.get("new_price", 0)
                        },
                        "bom_impact": {"summary": {}, "impact_details": [], "high_risk_assemblies": []},
                        "actions_required": [],
                        "can_auto_approve": False
                    }
                })
            else:
                processed_results.append(result)

        logger.info(f"   Progress: {len(processed_results)}/{total_products} products processed")
        results = processed_results

        # Store results in database (async context)
        logger.info(f"   Storing {len(results)} results in database...")

        async with SessionLocal() as db:
            # Delete any existing BOM impact results for this email (for re-processing)
            await BomImpactService.delete_by_email_id(db, email_id)

            # Store all results
            success_count = 0
            error_count = 0
            skipped_count = 0

            for result in sorted(results, key=lambda r: r["idx"]):
                if result["skipped"]:
                    skipped_count += 1
                    continue

                await BomImpactService.create(
                    db,
                    email_id=email_id,
                    product_index=result["idx"],
                    impact_data=result["result"]
                )

                if result.get("error"):
                    error_count += 1
                else:
                    success_count += 1

            await db.commit()

        logger.info("   BOM Impact Analysis Complete")
        logger.info(f"      Success: {success_count}, Errors: {error_count}, Skipped: {skipped_count}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"   BOM Impact Analysis failed: {e}")


async def process_user_message(msg, user_email, skip_verification=False):
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

    # Extract thread information from the message
    thread_info = extract_thread_info(msg)

    logger.info("=" * 80)
    logger.info("EMAIL INTELLIGENCE SYSTEM - 3-STAGE WORKFLOW")
    logger.info("=" * 80)
    logger.info(f"Processing email for: {user_email}")
    logger.info(f"Subject: {subject}")
    logger.info(f"From: {sender}")
    logger.info(f"Date: {date_received}")
    logger.info(f"Message ID: {message_id[:20]}...")
    logger.info("=" * 80)
    
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
    logger.info("STAGE 1: EMAIL DETECTION")
    logger.info("-" * 80)

    # Process attachments with user-specific download directory
    attachment_paths = []
    has_attachments = msg.get("hasAttachments", False)

    if has_attachments:
        logger.info("Processing attachments...")
        # Import here to avoid circular import issues
        from auth.multi_graph import graph_client
        attachments = await graph_client.get_user_message_attachments(user_email, message_id)

        for att in attachments:
            if att.get("@odata.type", "").endswith("fileAttachment"):
                filename = att.get("name", "unknown")
                logger.info(f"   Attachment: {filename}")

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

    logger.info("Stage 1 Complete: Content extracted")
    logger.info(f"   Body length: {len(email_body)} characters")
    logger.info(f"   Attachments: {len(attachment_paths)}")
    logger.info("=" * 80)
    
    # Process all content (email body + attachments)
    combined_content = process_all_content(email_body, attachment_paths)

    if not combined_content.strip():
        logger.warning("   No content to process")
        logger.info("=" * 80)
        return

    # ========== PRE-STAGE 2: VENDOR VERIFICATION CHECK ==========
    if not skip_verification:
        # Check email state in database
        async with SessionLocal() as db:
            state = await EmailStateService.get_state_by_message_id(db, message_id)

        if state and state.verification_status == 'pending_review':
            logger.warning("EMAIL FLAGGED FOR VERIFICATION")
            logger.info("-" * 80)
            logger.info("   This email is from an unverified sender")
            logger.info("   AI extraction skipped to save tokens")
            logger.info("   Review this email in the dashboard 'Pending Verification' tab")
            logger.info("   Approve to trigger AI extraction")
            logger.info("=" * 80)
            return

    # ========== STAGE 2: AI ENTITY EXTRACTION ==========
    logger.info("STAGE 2: AI ENTITY EXTRACTION")
    logger.info("-" * 80)
    logger.info("Azure OpenAI GPT-4.1 Processing...")
    logger.info("   Extracting parallel entities:")
    logger.info("   - Supplier ID")
    logger.info("   - Part Name & Number")
    logger.info("   - Effective Date")
    logger.info("   - New Price")
    logger.info("   - Reason for Change")

    try:
        # Note: Email has already been validated as price change by LLM detector in delta_service
        # This extraction focuses solely on extracting structured data
        result = await extract_price_change_json(combined_content, email_metadata)

        # Save to database (JSON file writes removed - database is now the primary storage)
        email_id = None
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
                    raw_email_data=msg,
                    # Thread information
                    conversation_id=thread_info.conversation_id,
                    conversation_index=thread_info.conversation_index,
                    is_reply=thread_info.is_reply,
                    is_forward=thread_info.is_forward,
                    thread_subject=thread_info.thread_subject,
                )
            else:
                # Update existing record
                email_record.supplier_info = result.get("supplier_info")
                email_record.price_change_summary = result.get("price_change_summary")
                email_record.affected_products = result.get("affected_products")
                email_record.additional_details = result.get("additional_details")
                # Update thread info if not already set
                if not email_record.conversation_id and thread_info.conversation_id:
                    email_record.conversation_id = thread_info.conversation_id
                    email_record.conversation_index = thread_info.conversation_index
                    email_record.is_reply = thread_info.is_reply
                    email_record.is_forward = thread_info.is_forward
                    email_record.thread_subject = thread_info.thread_subject

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
            email_id = email_record.id

        logger.info("Stage 2 Complete: Data extracted successfully")
        logger.info("   Saved to database")

        # Print summary of extracted data
        logger.info("Extracted Data Summary:")
        print_extraction_summary(result)
        logger.info("=" * 80)

        # ========== STAGE 3: BOM IMPACT ANALYSIS (Background) ==========
        # Run BOM impact analysis for all products in the email
        if email_id and result.get("affected_products"):
            try:
                await run_bom_impact_analysis(
                    email_id=email_id,
                    extraction_result=result,
                    supplier_info=result.get("supplier_info")
                )
            except Exception as e:
                logger.warning(f"   BOM Impact Analysis error (non-blocking): {e}")

        # Note: Epicor sync will happen when user clicks "Process" button in the UI
        logger.info("Email extracted and ready for processing")
        logger.info("   Epicor sync will occur when you click 'Mark as Processed' in the dashboard")
        logger.info("=" * 80)
        logger.info("EMAIL PROCESSING COMPLETE")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"ERROR PROCESSING EMAIL: {e}")
        logger.info("=" * 80)

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
        
        logger.info(f"Saved user attachment: {filename}")
        return path
    except Exception as e:
        logger.error(f"Error saving user attachment {filename}: {e}")
        return None

def process_message_with_locks(message_id):
    """
    Legacy function - now replaced by delta service
    Use process_user_message() instead with proper user context
    """
    logger.warning("process_message_with_locks is legacy - use delta service instead")
    logger.warning(f"   Message {message_id} should be processed via web interface")
    return False

def process_message(msg):
    """
    Legacy function - now replaced by process_user_message() with user context
    This function is deprecated and should not be used in the delta service system
    """
    logger.warning("process_message() is legacy - use process_user_message() instead")
    logger.warning("   Modern email processing requires user context for proper data isolation")

    # Extract basic info for logging
    subject = msg.get("subject", "(no subject)")
    message_id = msg.get("id", "")
    logger.warning(f"   Legacy processing attempted for: {subject} (ID: {message_id})")
    logger.warning("   Use the web interface with delta service for proper processing")

    return False

def print_extraction_summary(data):
    """Print a summary of the extracted price change data"""
    if "error" in data:
        logger.error(f"   Extraction error: {data['error']}")
        return

    # Supplier info
    supplier_info = data.get("supplier_info", {})
    supplier_id = supplier_info.get("supplier_id")
    supplier_name = supplier_info.get("supplier_name")

    if supplier_id:
        logger.info(f"   Supplier ID: {supplier_id}")
    if supplier_name:
        logger.info(f"   Supplier Name: {supplier_name}")

    # Price change details (check both locations for backward compatibility)
    change_details = data.get("price_change_details", {})
    price_change_summary = data.get("price_change_summary", {})

    change_type = change_details.get("change_type") or price_change_summary.get("change_type")
    effective_date = change_details.get("effective_date") or price_change_summary.get("effective_date")

    if change_type:
        logger.info(f"   Change Type: {change_type}")
    if effective_date:
        logger.info(f"   Effective Date: {effective_date}")

    # Products affected
    products = data.get("affected_products", [])
    if products:
        logger.info(f"   Products Affected: {len(products)}")
        for i, product in enumerate(products[:3]):  # Show first 3 products
            name = product.get("product_name", "Unknown")
            old_price = product.get("old_price", "N/A")
            new_price = product.get("new_price", "N/A")
            logger.info(f"      {i+1}. {name}: {old_price} -> {new_price}")

        if len(products) > 3:
            logger.info(f"      ... and {len(products) - 3} more products")

    # Action required
    action = data.get("action_required", {})
    deadline = action.get("response_deadline")
    if deadline:
        logger.info(f"   Response Deadline: {deadline}")

def main():
    """
    Legacy CLI processing function - now replaced by delta service

    For modern usage:
    1. Run: python main.py
    2. Visit: http://localhost:8000
    3. Authenticate with Microsoft OAuth
    4. Emails will be automatically processed via delta queries
    """
    logger.info("Email Intelligence System")
    logger.info("=" * 50)
    logger.warning("This CLI mode is legacy - use the web interface instead:")
    logger.info("   1. Run: python main.py")
    logger.info("   2. Visit: http://localhost:8000")
    logger.info("   3. Authenticate with Microsoft OAuth")
    logger.info("   4. Emails automatically processed via delta queries every 3 minutes")
    logger.info("=" * 50)
    logger.info("For current functionality, use the web interface with delta service")

    return

if __name__ == "__main__":
    main()