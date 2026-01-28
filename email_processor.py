import os, json
import asyncio
import logging
from datetime import datetime
from auth.multi_graph import graph_client
from utils.processors import save_attachment, process_all_content
from utils.thread_detection import extract_thread_info
from services.extractor import extract_price_change_json, extract_reply_email

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
    total_products: int,
    pre_validated_data: dict | None = None
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
            email_metadata=None,
            pre_validated_data=pre_validated_data
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
        # Return error result with pre-validated data for correct validation flags
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
        if pre_validated_data:
            error_result["supplier_part_validated"] = pre_validated_data.get("supplier_part_validated", False)
            error_result["supplier_part_validation_error"] = pre_validated_data.get("supplier_part_error")
            if pre_validated_data.get("part_validated") and pre_validated_data.get("part_data"):
                pd = pre_validated_data["part_data"]
                error_result["component"] = {
                    "part_num": part_num,
                    "description": pd.get("description", ""),
                    "type_code": pd.get("type_code", ""),
                    "uom": pd.get("uom", ""),
                    "current_cost": pd.get("current_cost", 0),
                    "validated": True
                }
            if pre_validated_data.get("supplier_validated") and pre_validated_data.get("supplier_data"):
                sd = pre_validated_data["supplier_data"]
                error_result["supplier"] = {
                    "supplier_id": supplier_id,
                    "vendor_num": sd.get("vendor_num"),
                    "name": sd.get("name", ""),
                    "validated": True
                }
            supplier_part_data = pre_validated_data.get("supplier_part_data", {}) or {}
            supplier_data_pre = pre_validated_data.get("supplier_data", {}) or {}
            vendor_num = supplier_part_data.get("vendor_num") or supplier_data_pre.get("vendor_num")
            if vendor_num:
                error_result["vendor_num"] = vendor_num
        return {
            "idx": idx,
            "part_num": part_num,
            "skipped": False,
            "error": str(e),
            "result": error_result
        }


async def run_epicor_validation(
    email_id: int,
    extraction_result: dict,
    supplier_info: dict
) -> dict:
    """
    Run Epicor validation for all products BEFORE BOM impact analysis.

    This validates:
    1. Part exists in Epicor
    2. Supplier exists in Epicor
    3. Supplier-Part relationship exists (supplier is authorized to supply this part)

    Args:
        email_id: Database ID of the email record
        extraction_result: The AI extraction result containing affected_products
        supplier_info: Supplier info from extraction (contains supplier_id)

    Returns:
        Dictionary with validation results for each product:
        {
            "all_products_valid": bool,
            "any_product_can_proceed": bool,
            "product_validations": [
                {
                    "idx": int,
                    "part_num": str,
                    "validation_result": dict from validate_supplier_part_for_email
                },
                ...
            ],
            "summary": {
                "total_products": int,
                "parts_validated": int,
                "suppliers_validated": int,
                "supplier_parts_validated": int,
                "products_blocked": int
            }
        }
    """
    from services.epicor_service import EpicorAPIService as EpicorService

    affected_products = extraction_result.get("affected_products", [])
    supplier_id = supplier_info.get("supplier_id", "") if supplier_info else ""

    result = {
        "all_products_valid": True,
        "any_product_can_proceed": False,
        "product_validations": [],
        "summary": {
            "total_products": len(affected_products),
            "parts_validated": 0,
            "suppliers_validated": 0,
            "supplier_parts_validated": 0,
            "products_blocked": 0
        }
    }

    if not affected_products:
        logger.info("   No products to validate")
        return result

    if not supplier_id:
        logger.warning("   No supplier ID provided - skipping validation")
        result["all_products_valid"] = False
        return result

    logger.info("STAGE 2.5: EPICOR VALIDATION (PRE-BOM CHECK)")
    logger.info("-" * 80)
    logger.info(f"   Validating {len(affected_products)} product(s) against Epicor...")
    logger.info(f"   Supplier ID: {supplier_id}")

    try:
        epicor_service = EpicorService()

        for idx, product in enumerate(affected_products):
            part_num = product.get("product_id", "")
            if not part_num:
                logger.warning(f"   Product {idx + 1}: Missing product_id, skipping validation")
                result["product_validations"].append({
                    "idx": idx,
                    "part_num": "",
                    "validation_result": {
                        "all_valid": False,
                        "part_validated": False,
                        "supplier_validated": False,
                        "supplier_part_validated": False,
                        "validation_errors": ["Missing product_id"],
                        "can_proceed_with_bom_analysis": False
                    }
                })
                result["summary"]["products_blocked"] += 1
                result["all_products_valid"] = False
                continue

            logger.info(f"\n   Product {idx + 1}/{len(affected_products)}: {part_num}")

            # Run validation for this product
            validation = await epicor_service.validate_supplier_part_for_email(
                part_num=part_num,
                supplier_id=supplier_id
            )

            result["product_validations"].append({
                "idx": idx,
                "part_num": part_num,
                "validation_result": validation
            })

            # Update summary counts
            if validation.get("part_validated"):
                result["summary"]["parts_validated"] += 1
            if validation.get("supplier_validated"):
                result["summary"]["suppliers_validated"] += 1
            if validation.get("supplier_part_validated"):
                result["summary"]["supplier_parts_validated"] += 1

            if not validation.get("all_valid"):
                result["all_products_valid"] = False
                if not validation.get("can_proceed_with_bom_analysis"):
                    result["summary"]["products_blocked"] += 1

            if validation.get("can_proceed_with_bom_analysis"):
                result["any_product_can_proceed"] = True

        # Store validation results in database
        async with SessionLocal() as db:
            from database.services.email_state_service import EmailStateService
            from database.services.email_service import EmailService

            # Get the email record to get message_id
            email = await EmailService.get_email_by_id(db, email_id)
            if email:
                # Store validation summary in email state
                await EmailStateService.update_state(
                    db=db,
                    message_id=email.message_id,
                    epicor_validation_performed=True,
                    epicor_validation_result={
                        "all_products_valid": result["all_products_valid"],
                        "summary": result["summary"],
                        "product_validations": [
                            {
                                "idx": pv["idx"],
                                "part_num": pv["part_num"],
                                "all_valid": pv["validation_result"].get("all_valid"),
                                "part_validated": pv["validation_result"].get("part_validated"),
                                "supplier_validated": pv["validation_result"].get("supplier_validated"),
                                "supplier_part_validated": pv["validation_result"].get("supplier_part_validated"),
                                "validation_errors": pv["validation_result"].get("validation_errors", [])
                            }
                            for pv in result["product_validations"]
                        ]
                    }
                )
                await db.commit()

        logger.info("\n" + "-" * 80)
        logger.info("EPICOR VALIDATION SUMMARY:")
        logger.info(f"   Total Products: {result['summary']['total_products']}")
        logger.info(f"   Parts Validated: {result['summary']['parts_validated']}")
        logger.info(f"   Suppliers Validated: {result['summary']['suppliers_validated']}")
        logger.info(f"   Supplier-Part Links Validated: {result['summary']['supplier_parts_validated']}")
        logger.info(f"   Products Blocked: {result['summary']['products_blocked']}")

        if result["all_products_valid"]:
            logger.info("   ✅ All validations passed - proceeding to BOM analysis")
        elif result["any_product_can_proceed"]:
            logger.warning("   ⚠️  Some validations failed - BOM analysis will proceed for valid products")
        else:
            logger.error("   ❌ All validations failed - BOM analysis blocked")

        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"   Epicor validation error: {e}")
        result["all_products_valid"] = False

    return result


async def run_bom_impact_analysis(
    email_id: int,
    extraction_result: dict,
    supplier_info: dict,
    validation_results: dict = None
):
    """
    Run BOM impact analysis for all products in an email and store results in database.

    This runs in the background after AI extraction AND Epicor validation is complete.
    Uses asyncio.gather() for concurrent processing of multiple products.

    Args:
        email_id: Database ID of the email record
        extraction_result: The AI extraction result containing affected_products
        supplier_info: Supplier info from extraction (contains supplier_id)
        validation_results: Optional pre-validation results from run_epicor_validation
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

        # Build a lookup map for pre-validated data by product index
        validation_lookup = {}
        if validation_results:
            for pv in validation_results.get("product_validations", []):
                validation_lookup[pv["idx"]] = pv.get("validation_result")

        async def process_with_semaphore(idx: int, product: dict):
            async with semaphore:
                return await _process_single_product_bom(
                    epicor_service,
                    idx,
                    product,
                    supplier_id,
                    effective_date,
                    total_products,
                    pre_validated_data=validation_lookup.get(idx)
                )

        # Build set of product indices that passed validation (using passed-in validation_results)
        # GATE 2: Only run BOM analysis for products where part AND supplier-part are validated
        valid_product_indices = set()
        if validation_results:
            for pv in validation_results.get("product_validations", []):
                vr = pv.get("validation_result", {})
                if vr.get("can_proceed_with_bom_analysis"):
                    valid_product_indices.add(pv["idx"])

        # Create tasks only for validated products, tracking original indices
        tasks = []
        task_indices = []  # Track which original product index each task corresponds to
        skipped_products = []
        for idx, product in enumerate(affected_products):
            if validation_results is None or idx in valid_product_indices:
                tasks.append(process_with_semaphore(idx, product))
                task_indices.append(idx)
            else:
                skipped_products.append(f"{product.get('product_id', 'N/A')}")

        if skipped_products:
            logger.info(f"   Skipping {len(skipped_products)} product(s) - validation failed: {', '.join(skipped_products)}")

        if not tasks:
            logger.warning("   No products passed validation - skipping BOM analysis")
            return

        # Run all tasks concurrently and collect results
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results, handling any exceptions
        # Note: results order matches task_indices order (original product indices)
        processed_results = []
        for task_idx, result in enumerate(results):
            original_idx = task_indices[task_idx]
            if isinstance(result, Exception):
                logger.error(f"   Unexpected error for product {original_idx}: {result}")
                product = affected_products[original_idx]
                part_num = product.get("product_id", "")
                pre_validated = validation_lookup.get(original_idx)
                error_result = {
                    "status": "error",
                    "processing_errors": [f"Unexpected error: {str(result)}"],
                    "component": {"part_num": part_num, "validated": False},
                    "supplier": {"supplier_id": supplier_id, "validated": False},
                    "price_change": {
                        "part_num": part_num,
                        "old_price": product.get("old_price", 0),
                        "new_price": product.get("new_price", 0)
                    },
                    "bom_impact": {"summary": {}, "impact_details": [], "high_risk_assemblies": []},
                    "actions_required": [],
                    "can_auto_approve": False
                }
                # Use pre-validated data for correct validation flags
                if pre_validated:
                    error_result["supplier_part_validated"] = pre_validated.get("supplier_part_validated", False)
                    error_result["supplier_part_validation_error"] = pre_validated.get("supplier_part_error")
                    if pre_validated.get("part_validated") and pre_validated.get("part_data"):
                        pd = pre_validated["part_data"]
                        error_result["component"] = {
                            "part_num": part_num,
                            "description": pd.get("description", ""),
                            "type_code": pd.get("type_code", ""),
                            "uom": pd.get("uom", ""),
                            "current_cost": pd.get("current_cost", 0),
                            "validated": True
                        }
                    if pre_validated.get("supplier_validated") and pre_validated.get("supplier_data"):
                        sd = pre_validated["supplier_data"]
                        error_result["supplier"] = {
                            "supplier_id": supplier_id,
                            "vendor_num": sd.get("vendor_num"),
                            "name": sd.get("name", ""),
                            "validated": True
                        }
                    sp_data = pre_validated.get("supplier_part_data", {}) or {}
                    sd_data = pre_validated.get("supplier_data", {}) or {}
                    vendor_num = sp_data.get("vendor_num") or sd_data.get("vendor_num")
                    if vendor_num:
                        error_result["vendor_num"] = vendor_num
                processed_results.append({
                    "idx": original_idx,
                    "part_num": part_num,
                    "skipped": False,
                    "error": str(result),
                    "result": error_result
                })
            else:
                processed_results.append(result)

        logger.info(f"   Progress: {len(processed_results)}/{len(tasks)} validated products processed ({total_products} total)")
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

                impact_data = result["result"]

                await BomImpactService.create(
                    db,
                    email_id=email_id,
                    product_index=result["idx"],
                    impact_data=impact_data
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
    date_received_str = msg.get("receivedDateTime", "")
    # Parse ISO date string to datetime object (MS Graph API returns ISO 8601 format)
    date_received = None
    if date_received_str:
        try:
            date_received = datetime.fromisoformat(date_received_str.replace('Z', '+00:00'))
            # Strip timezone to make it naive (DB uses TIMESTAMP WITHOUT TIME ZONE)
            if date_received.tzinfo:
                date_received = date_received.replace(tzinfo=None)
        except (ValueError, TypeError):
            logger.warning(f"Could not parse date: {date_received_str}")
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

    try:
        # Use specialized extractor for reply emails (lighter weight, focused on partial info)
        if thread_info.is_reply:
            logger.info("Reply email detected - using reply extractor")
            logger.info("   Extracting: reason, clarifications, additional details")
            result = await extract_reply_email(combined_content, email_metadata)
        else:
            logger.info("Azure OpenAI GPT-4.1 Processing...")
            logger.info("   Extracting parallel entities:")
            logger.info("   - Supplier ID")
            logger.info("   - Part Name & Number")
            logger.info("   - Effective Date")
            logger.info("   - New Price")
            logger.info("   - Reason for Change")
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

        # ========== STAGE 2.5: EPICOR VALIDATION (Before BOM Analysis) ==========
        # Run validation to check part exists, supplier exists, and supplier-part relationship
        validation_results = None
        if email_id and result.get("affected_products") and result.get("supplier_info", {}).get("supplier_id"):
            try:
                validation_results = await run_epicor_validation(
                    email_id=email_id,
                    extraction_result=result,
                    supplier_info=result.get("supplier_info")
                )
            except Exception as e:
                logger.warning(f"   Epicor Validation error (non-blocking): {e}")
                validation_results = None

        # ========== STAGE 3: BOM IMPACT ANALYSIS (Background) ==========
        # Run BOM impact analysis for products that passed validation
        # GATE 1: Supplier must be verified for ANY product to proceed
        # GATE 2: Individual products must have part + supplier-part validated
        if email_id and result.get("affected_products"):
            # GATE 1: Check if supplier is verified (using stored validation results)
            supplier_verified = False
            if validation_results:
                supplier_verified = validation_results.get("summary", {}).get("suppliers_validated", 0) > 0

            if not supplier_verified:
                logger.warning("   ⚠️  Skipping BOM analysis - Supplier ID not verified in Epicor")
            elif validation_results and validation_results.get("any_product_can_proceed"):
                # GATE 2: run_bom_impact_analysis will filter individual products
                try:
                    await run_bom_impact_analysis(
                        email_id=email_id,
                        extraction_result=result,
                        supplier_info=result.get("supplier_info"),
                        validation_results=validation_results
                    )
                except Exception as e:
                    logger.warning(f"   BOM Impact Analysis error (non-blocking): {e}")
            elif validation_results:
                logger.warning("   ⚠️  Skipping BOM analysis - no products passed validation (part + supplier-part required)")

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
    2. Access the web interface at the configured URL
    3. Authenticate with Microsoft OAuth
    4. Emails will be automatically processed via delta queries
    """
    logger.info("Email Intelligence System")
    logger.info("=" * 50)
    logger.warning("This CLI mode is legacy - use the web interface instead:")
    logger.info("   1. Run: python main.py")
    logger.info("   2. Access the web interface at the configured URL")
    logger.info("   3. Authenticate with Microsoft OAuth")
    logger.info("   4. Emails automatically processed via delta queries every 3 minutes")
    logger.info("=" * 50)
    logger.info("For current functionality, use the web interface with delta service")

    return

if __name__ == "__main__":
    main()