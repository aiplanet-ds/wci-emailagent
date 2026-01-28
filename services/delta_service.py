"""
Delta Query Service for Email Intelligence System

This service replaces webhook functionality with polling-based email monitoring.
It uses Microsoft Graph delta queries to efficiently track email changes for each user.
"""

import asyncio
import json
import os
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Database imports
from database.config import SessionLocal
from database.services.user_service import UserService
from database.services.email_service import EmailService
from database.services.delta_service import DeltaService as DBDeltaService
from database.services.email_state_service import EmailStateService as DBEmailStateService

# Import LLM-powered detection service
from services.llm_detector import llm_is_price_change_email
from utils.processors import process_all_content
from utils.thread_detection import extract_thread_info

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DeltaEmailService:
    """
    Delta query service for polling user emails and processing new/changed messages
    """

    def __init__(self):
        from auth.multi_graph import graph_client
        self.graph_client = graph_client
        self.scheduler = AsyncIOScheduler()
        self.polling_interval = 60  # 1 minute for automated workflow
        self.is_running = False

        # Ensure directories exist
        os.makedirs("delta_cache", exist_ok=True)
        
    async def load_delta_tokens(self) -> Dict[str, str]:
        """Load delta tokens for all users from database"""
        try:
            async with SessionLocal() as db:
                users = await UserService.get_all_users(db, active_only=True)
                tokens = {}
                for user in users:
                    token = await DBDeltaService.get_delta_token(db, user.id)
                    if token:
                        tokens[user.email] = token
                return tokens
        except Exception as e:
            logger.error(f"Error loading delta tokens from database: {e}")
            return {}

    async def save_delta_tokens(self, tokens: Dict[str, str]):
        """Save delta tokens for all users to database"""
        try:
            async with SessionLocal() as db:
                for user_email, token in tokens.items():
                    user = await UserService.get_user_by_email(db, user_email)
                    if user:
                        await DBDeltaService.set_delta_token(db, user.id, token)
                await db.commit()
        except Exception as e:
            logger.error(f"Error saving delta tokens to database: {e}")
    
    async def load_active_users(self) -> List[str]:
        """Load list of active users to monitor from database"""
        try:
            async with SessionLocal() as db:
                users = await UserService.get_all_users(db, active_only=True)
                return [user.email for user in users]
        except Exception as e:
            logger.error(f"Error loading active users from database: {e}")
            return []

    async def save_active_users(self, users: List[str]):
        """Save list of active users to database - deprecated, use activate_user/deactivate_user instead"""
        logger.warning("save_active_users is deprecated - user activation is now managed per-user")
    
    async def add_user_to_monitoring(self, user_email: str):
        """Add a user to email monitoring by activating them in database"""
        try:
            async with SessionLocal() as db:
                user, created = await UserService.get_or_create_user(db, user_email)
                if created:
                    # Commit the newly created user
                    await db.commit()
                    logger.info(f"✅ New user created and added to monitoring: {user_email}")
                elif not user.is_active:
                    await UserService.activate_user(db, user.id)
                    await db.commit()
                    logger.info(f"✅ User reactivated for monitoring: {user_email}")
                else:
                    logger.info(f"ℹ️  User already in monitoring list: {user_email}")

                # Count active users
                active_users = await UserService.get_all_users(db, active_only=True)
                logger.info(f"📊 Total active users: {len(active_users)}")

            # Trigger immediate poll for this user (runs for ALL login cases)
            logger.info(f"🚀 Starting initial email poll for: {user_email}")
            await self.poll_user_emails(user_email)
        except Exception as e:
            logger.error(f"Error adding user to monitoring: {e}")

    async def remove_user_from_monitoring(self, user_email: str):
        """Remove a user from email monitoring by deactivating them in database"""
        try:
            async with SessionLocal() as db:
                user = await UserService.get_user_by_email(db, user_email)
                if user and user.is_active:
                    # Deactivate user
                    await UserService.deactivate_user(db, user.id)

                    # Keep delta token for efficient re-login
                    # Delta tokens persist across sessions to avoid full mailbox sync
                    logger.info(f"   📌 Delta token preserved for {user_email}")

                    await db.commit()

                    # Count remaining active users
                    active_users = await UserService.get_all_users(db, active_only=True)
                    logger.info(f"✅ User removed from monitoring list")
                    logger.info(f"📊 Remaining active users: {len(active_users)}")
        except Exception as e:
            logger.error(f"Error removing user from monitoring: {e}")
    
    async def get_user_delta_messages(self, user_email: str, delta_token: Optional[str] = None) -> Dict[str, Any]:
        """Get delta messages for a user"""
        try:
            return await self.graph_client.get_user_delta_messages(user_email, delta_token)
        except Exception as e:
            logger.error(f"Error getting delta messages for {user_email}: {e}")
            return {"messages": [], "delta_token": delta_token}
    
    async def is_price_change_email(self, user_email: str, message: Dict) -> Dict[str, Any]:
        """
        Determine if an email is a price change notification using LLM-powered detection.

        Args:
            user_email: Email address of the user (for fetching full message)
            message: Email message dict from Microsoft Graph

        Returns:
            Dict with detection results including is_price_change, confidence, reasoning
        """
        try:
            # Extract basic metadata
            subject = message.get('subject', 'No Subject')
            sender_info = message.get('from', {}).get('emailAddress', {})
            sender = sender_info.get('address', '') if sender_info else ''
            date_received = message.get('receivedDateTime', '')
            message_id = message.get('id', '')
            has_attachments = message.get('hasAttachments', False)

            # Prepare metadata for LLM
            metadata = {
                'subject': subject,
                'sender': sender,
                'date': date_received,
                'message_id': message_id,
                'has_attachments': has_attachments
            }

            # Get full message content with attachments
            logger.info(f"   Fetching full email content for LLM analysis...")
            full_message = await self.graph_client.get_user_message_by_id(user_email, message_id)

            # Extract email body
            email_body = ""
            body_data = full_message.get("body", {})
            if body_data:
                email_body = body_data.get("content", "")

            # Process attachments (if any)
            attachment_paths = []  # Empty list if no attachments
            if full_message.get("hasAttachments", False):
                attachments = await self.graph_client.get_user_message_attachments(user_email, message_id)

                # Create user-specific downloads directory for temp attachment storage
                safe_email = user_email.replace("@", "_at_").replace(".", "_dot_")
                user_downloads_dir = os.path.join("downloads", safe_email)
                os.makedirs(user_downloads_dir, exist_ok=True)

                for att in attachments:
                    if att.get("@odata.type", "").endswith("fileAttachment"):
                        filename = att.get("name", "unknown")
                        content_bytes = att.get("contentBytes")

                        if content_bytes:
                            try:
                                # Decode and save attachment
                                if isinstance(content_bytes, str):
                                    decoded_content = base64.b64decode(content_bytes)
                                else:
                                    decoded_content = content_bytes

                                path = os.path.join(user_downloads_dir, filename)
                                with open(path, "wb") as f:
                                    f.write(decoded_content)

                                attachment_paths.append(path)
                                logger.info(f"   Saved attachment for analysis: {filename}")
                            except Exception as e:
                                logger.warning(f"   Could not save attachment {filename}: {e}")

            # Process all content (body + attachments)
            combined_content = process_all_content(email_body, attachment_paths)

            # Call LLM detector (async)
            logger.info(f"   Analyzing with LLM detector...")
            detection_result = await llm_is_price_change_email(combined_content, metadata)

            return detection_result

        except Exception as e:
            logger.error(f"   Error in LLM price change detection: {e}")
            # Return negative result on error to avoid false positives
            return {
                "is_price_change": False,
                "confidence": 0.0,
                "reasoning": f"Detection error: {str(e)}",
                "meets_threshold": False,
                "error": str(e)
            }

    async def process_user_messages(self, user_email: str, messages: List[Dict]):
        """Process new messages for a user with vendor verification and liberal price change filtering"""
        from email_processor import process_user_message
        from services.vendor_verification_service import vendor_verification_service

        processed_count = 0
        skipped_count = 0
        flagged_count = 0

        # Get user from database
        async with SessionLocal() as db:
            user = await UserService.get_user_by_email(db, user_email)
            if not user:
                logger.error(f"User {user_email} not found in database")
                return
            user_id = user.id

        for i, message in enumerate(messages, 1):
            try:
                message_id = message.get('id', '')

                # Check if email already exists in database - skip if it does
                async with SessionLocal() as db:
                    existing_email = await EmailService.get_email_by_message_id(db, message_id)
                    if existing_email:
                        logger.info(f"\n📧 Email {i}/{len(messages)}: Already exists (ID: {message_id[:20]}...) - SKIPPED")
                        skipped_count += 1
                        continue

                # Only NEW emails reach this point
                subject = message.get('subject', 'No Subject')
                sender_info = message.get('from', {}).get('emailAddress', {})
                sender_email = sender_info.get('address', '').lower() if sender_info else ''

                logger.info(f"\n📧 Email {i}/{len(messages)}: {subject} (NEW)")
                logger.info(f"   From: {sender_email}")

                # THREAD INHERITANCE: Check if this is a reply in a verified thread
                # If so, skip verification and LLM detection - go straight to extraction
                thread_info = extract_thread_info(message)

                if thread_info.conversation_id:
                    logger.info(f"   🧵 Thread detected: conversation_id={thread_info.conversation_id[:20]}...")

                    async with SessionLocal() as db:
                        # Query existing emails in this thread
                        thread_emails = await EmailService.get_emails_by_conversation_id(
                            db, thread_info.conversation_id, user_id
                        )

                        # Check if any previous email from the same sender was verified
                        thread_verified = False
                        for prev_email in thread_emails:
                            if prev_email.message_id == message_id:
                                continue  # Skip current email

                            # Check if same sender and verified
                            if prev_email.sender_email and prev_email.sender_email.lower() == sender_email:
                                prev_state = await DBEmailStateService.get_state_by_message_id(db, prev_email.message_id)
                                if prev_state and prev_state.vendor_verified:
                                    logger.info(f"   ✅ VERIFIED THREAD REPLY - Skipping verification & LLM detection")
                                    logger.info(f"   Previous email from this sender was verified in this thread")

                                    # Go straight to extraction
                                    full_message = await self.graph_client.get_user_message_by_id(user_email, message['id'])
                                    await process_user_message(full_message, user_email)

                                    # Mark as verified via thread inheritance
                                    await DBEmailStateService.update_vendor_verification(
                                        db,
                                        message_id,
                                        vendor_verified=True,
                                        verification_status="verified",
                                        verification_method="thread_inheritance"
                                    )
                                    await db.commit()

                                    thread_verified = True
                                    processed_count += 1
                                    break

                        if thread_verified:
                            continue  # Skip to next email - already processed

                # STEP 1: VENDOR VERIFICATION CHECK (before expensive LLM detection)
                verification_enabled = os.getenv("VENDOR_VERIFICATION_ENABLED", "true").lower() == "true"

                if verification_enabled:
                    verification_result = await vendor_verification_service.verify_sender(sender_email)

                    if verification_result['is_verified']:
                        # VERIFIED VENDOR - Proceed with LLM detection
                        method = verification_result['method']
                        logger.info(f"   ✅ VERIFIED VENDOR ({method})")

                        # STEP 2: LLM DETECTION (only for verified vendors)
                        logger.info(f"   Running LLM price change detection...")
                        detection_result = await self.is_price_change_email(user_email, message)

                        if detection_result.get("meets_threshold", False):
                            confidence = detection_result.get("confidence", 0.0)
                            reasoning = detection_result.get("reasoning", "N/A")
                            logger.info(f"   ✅ PRICE CHANGE DETECTED (Confidence: {confidence:.2f})")
                            logger.info(f"   💡 Reasoning: {reasoning}")

                            # Get full message details (we'll need it for processing)
                            full_message = await self.graph_client.get_user_message_by_id(user_email, message['id'])

                            # STEP 3: AI EXTRACTION
                            await process_user_message(full_message, user_email)

                            # Mark as vendor verified and processed
                            async with SessionLocal() as db:
                                # Find vendor if available
                                vendor_id = None
                                if verification_result.get('vendor_info'):
                                    from database.services.vendor_service import VendorService
                                    vendor = await VendorService.get_vendor_by_id(
                                        db, verification_result['vendor_info'].get('vendor_id')
                                    )
                                    if vendor:
                                        vendor_id = vendor.id

                                await DBEmailStateService.update_vendor_verification(
                                    db,
                                    message_id,
                                    vendor_verified=True,
                                    verification_status="verified",
                                    verification_method=verification_result['method'],
                                    vendor_id=vendor_id
                                )
                                await db.commit()

                            processed_count += 1
                        else:
                            # Verified vendor but not a price change email
                            confidence = detection_result.get("confidence", 0.0)
                            reasoning = detection_result.get("reasoning", "N/A")
                            skipped_count += 1
                            logger.info(f"   ⏭️  Not a price change email - SKIPPED (Confidence: {confidence:.2f})")
                            logger.info(f"   💡 Reasoning: {reasoning}")

                    else:
                        # UNVERIFIED SENDER - Flag for manual review WITHOUT running LLM detection
                        logger.warning(f"   ⚠️  UNVERIFIED SENDER - Flagging for manual review")
                        logger.info(f"   💾 Saving basic metadata (LLM detection will run after approval)")
                        logger.info(f"   💰 Token savings: Skipping LLM detection until approved")

                        # Get full message for metadata
                        full_message = await self.graph_client.get_user_message_by_id(user_email, message['id'])

                        # Save minimal email metadata WITHOUT LLM detection or extraction
                        await self._save_flagged_email_metadata(full_message, user_email)

                        # Mark as pending verification (LLM detection not yet performed)
                        async with SessionLocal() as db:
                            # Get the email record to link the state
                            email_record = await EmailService.get_email_by_message_id(db, message_id)

                            state = await DBEmailStateService.get_state_by_message_id(db, message_id)
                            if not state:
                                # Create NEW state and flag for verification
                                state = await DBEmailStateService.create_state(
                                    db,
                                    message_id=message_id,
                                    user_id=user_id,
                                    email_id=email_record.id
                                )

                                await DBEmailStateService.update_vendor_verification(
                                    db,
                                    message_id,
                                    vendor_verified=False,
                                    verification_status="pending_review",
                                    flagged_reason=f"Email from unverified sender: {sender_email}"
                                )

                                # Set LLM detection flags
                                state.awaiting_llm_detection = True
                                state.llm_detection_performed = False
                                await db.commit()
                            else:
                                # State already exists - this shouldn't happen after duplicate check
                                # But if it does (edge case), don't overwrite existing state
                                logger.warning(f"   ⚠️  EmailState already exists for {message_id} - skipping state update")
                                await db.commit()

                        flagged_count += 1

                else:
                    # Verification disabled - run LLM detection and process normally
                    logger.info(f"   Vendor verification disabled")

                    # STEP 2: LLM DETECTION
                    logger.info(f"   Running LLM price change detection...")
                    detection_result = await self.is_price_change_email(user_email, message)

                    if detection_result.get("meets_threshold", False):
                        confidence = detection_result.get("confidence", 0.0)
                        reasoning = detection_result.get("reasoning", "N/A")
                        logger.info(f"   PRICE CHANGE DETECTED (Confidence: {confidence:.2f})")
                        logger.info(f"   Reasoning: {reasoning}")

                        # Get full message details
                        full_message = await self.graph_client.get_user_message_by_id(user_email, message['id'])

                        # STEP 3: AI EXTRACTION
                        await process_user_message(full_message, user_email)
                        processed_count += 1
                    else:
                        # Not a price change email
                        confidence = detection_result.get("confidence", 0.0)
                        reasoning = detection_result.get("reasoning", "N/A")
                        skipped_count += 1
                        logger.info(f"   Not a price change email - SKIPPED (Confidence: {confidence:.2f})")
                        logger.info(f"   Reasoning: {reasoning}")

                # Small delay to avoid overwhelming the system
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"   ❌ ERROR: {e}")

        logger.info("\n" + "="*80)
        logger.info(f"📊 BATCH PROCESSING SUMMARY:")
        logger.info(f"   ✅ Processed: {processed_count}")
        logger.info(f"   ⚠️  Flagged: {flagged_count}")
        logger.info(f"   ⏭️  Skipped: {skipped_count}")
        logger.info(f"   📧 Total: {len(messages)}")
        logger.info("="*80 + "\n")

    async def _save_flagged_email_metadata(self, msg: Dict, user_email: str):
        """Save basic email metadata for flagged emails to database without AI extraction"""
        from datetime import datetime

        message_id = msg.get('id', '')
        subject = msg.get('subject', '(no subject)')
        sender_info = msg.get('from', {}).get('emailAddress', {})
        sender = sender_info.get('address', '(no sender)')
        date_received_str = msg.get('receivedDateTime', '')
        has_attachments = msg.get('hasAttachments', False)

        # Parse date
        try:
            date_received = datetime.fromisoformat(date_received_str.replace('Z', '+00:00'))
            if date_received.tzinfo:
                date_received = date_received.replace(tzinfo=None)
        except:
            date_received = datetime.utcnow()

        # Extract email body
        email_body = ""
        body_data = msg.get("body", {})
        if body_data:
            email_body = body_data.get("content", "")

        # Extract thread information from the message
        thread_info = extract_thread_info(msg)

        # Save minimal email record to database (no AI extraction yet)
        async with SessionLocal() as db:
            # Get user
            user, _ = await UserService.get_or_create_user(db, user_email)

            # Create minimal email record
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
                    # No AI-extracted fields yet - will be populated after approval
                    supplier_info={"contact_email": sender},
                    price_change_summary={"reason": "Awaiting verification and LLM detection"},
                    affected_products=[],
                    additional_details={"notes": "This email requires manual approval. LLM detection and AI extraction will run after approval."},
                    raw_email_data=msg,
                    # Thread information
                    conversation_id=thread_info.conversation_id,
                    conversation_index=thread_info.conversation_index,
                    is_reply=thread_info.is_reply,
                    is_forward=thread_info.is_forward,
                    thread_subject=thread_info.thread_subject,
                    # Folder tracking - explicitly set for inbox emails
                    folder="inbox",
                    is_outgoing=False,
                )
                await db.commit()

        logger.info(f"   💾 Saved flagged email metadata to database (email_id: {email_record.id})")
        if thread_info.conversation_id:
            logger.info(f"   🧵 Thread info: conversation_id={thread_info.conversation_id[:20]}..., is_reply={thread_info.is_reply}, is_forward={thread_info.is_forward}")

    async def poll_user_emails(self, user_email: str):
        """Poll emails for a specific user (both inbox and sent folders)"""
        try:
            # Load current delta tokens for user
            delta_tokens = await self.load_delta_tokens()
            current_inbox_token = delta_tokens.get(user_email)

            logger.info("="*80)
            logger.info(f"🔍 POLLING EMAILS FOR: {user_email}")
            logger.info("="*80)

            # POLL INBOX FOLDER
            logger.info("📥 Polling Inbox folder...")
            result = await self.get_user_delta_messages(user_email, current_inbox_token)
            messages = result.get('messages', [])
            new_inbox_token = result.get('delta_token')

            if messages:
                logger.info(f"📬 NEW INBOX EMAILS: {len(messages)} email(s)")
                logger.info("-"*80)
                await self.process_user_messages(user_email, messages)
            else:
                logger.info(f"📭 No new inbox emails")

            # Update inbox delta token
            if new_inbox_token:
                delta_tokens[user_email] = new_inbox_token
                await self.save_delta_tokens(delta_tokens)

            # POLL SENT FOLDER
            logger.info("📤 Polling Sent folder...")
            await self.poll_user_sent_emails(user_email)

            logger.info("="*80 + "\n")

        except Exception as e:
            logger.error(f"❌ ERROR POLLING EMAILS: {e}")
            logger.error("="*80 + "\n")

    async def poll_user_sent_emails(self, user_email: str):
        """Poll sent folder for a specific user"""
        try:
            # Load sent delta token for this user
            async with SessionLocal() as db:
                user = await UserService.get_user_by_email(db, user_email)
                if not user:
                    return

                current_sent_token = await DBDeltaService.get_sent_delta_token(db, user.id)

                # Get delta messages from sent folder
                result = await self.graph_client.get_user_delta_sent_messages(user_email, current_sent_token)
                messages = result.get('messages', [])
                new_sent_token = result.get('delta_token')

                if messages:
                    logger.info(f"📬 NEW SENT EMAILS: {len(messages)} email(s)")
                    await self.process_sent_messages(user_email, messages)
                else:
                    logger.info(f"📭 No new sent emails")

                # Update sent delta token
                if new_sent_token:
                    await DBDeltaService.set_sent_delta_token(db, user.id, new_sent_token)
                    await db.commit()

        except Exception as e:
            logger.error(f"❌ ERROR POLLING SENT EMAILS: {e}")

    async def process_sent_messages(self, user_email: str, messages: List[Dict]):
        """
        Process sent emails - simplified processing, no LLM detection needed.
        Just stores the sent emails with folder='sent' and is_outgoing=True.
        """
        from datetime import datetime

        async with SessionLocal() as db:
            user = await UserService.get_user_by_email(db, user_email)
            if not user:
                logger.error(f"User {user_email} not found in database")
                return

            processed_count = 0

            for msg in messages:
                try:
                    message_id = msg.get('id', '')

                    # Check if email already exists
                    existing_email = await EmailService.get_email_by_message_id(db, message_id)
                    if existing_email:
                        logger.info(f"   Sent email already exists: {message_id[:20]}...")
                        continue

                    # Extract email metadata
                    subject = msg.get('subject', '(no subject)')
                    sent_datetime_str = msg.get('sentDateTime', '')

                    # Parse sent date
                    try:
                        sent_datetime = datetime.fromisoformat(sent_datetime_str.replace('Z', '+00:00'))
                        if sent_datetime.tzinfo:
                            sent_datetime = sent_datetime.replace(tzinfo=None)
                    except:
                        sent_datetime = datetime.utcnow()

                    # Extract body content
                    body_data = msg.get("body", {})
                    body_html = body_data.get("content", "") if body_data else ""

                    # Extract thread information
                    thread_info = extract_thread_info(msg)

                    # Extract recipients
                    to_recipients = msg.get('toRecipients', [])
                    recipient_emails = [r.get('emailAddress', {}).get('address', '') for r in to_recipients]

                    # Create sent email record
                    email_record = await EmailService.create_email(
                        db,
                        message_id=message_id,
                        user_id=user.id,
                        subject=subject,
                        sender_email=user_email,  # Sent by user
                        received_at=sent_datetime,  # Using sent datetime
                        has_attachments=msg.get('hasAttachments', False),
                        body_html=body_html,
                        raw_email_data=msg,
                        # Thread information
                        conversation_id=thread_info.conversation_id,
                        conversation_index=thread_info.conversation_index,
                        is_reply=thread_info.is_reply,
                        is_forward=thread_info.is_forward,
                        thread_subject=thread_info.thread_subject,
                        # Sent folder tracking
                        folder="sent",
                        is_outgoing=True,
                        # Minimal extracted data for sent emails
                        supplier_info={"contact_email": recipient_emails[0] if recipient_emails else ""},
                        price_change_summary={},
                        affected_products=[],
                        additional_details={"sent_to": recipient_emails},
                    )

                    logger.info(f"   ✅ Saved sent email: {subject[:50]}...")
                    processed_count += 1

                except Exception as e:
                    logger.error(f"   ❌ Error processing sent email: {e}")

            await db.commit()
            logger.info(f"   📊 Processed {processed_count} sent emails")
    
    async def poll_all_users(self):
        """Poll emails for all active users"""
        try:
            active_users = await self.load_active_users()

            if not active_users:
                logger.info("\n" + "="*80)
                logger.info("👥 NO ACTIVE USERS TO MONITOR")
                logger.info("   ℹ️  Waiting for users to authenticate...")
                logger.info("="*80 + "\n")
                return

            logger.info("\n" + "="*80)
            logger.info(f"🔄 AUTOMATED POLLING CYCLE STARTED")
            logger.info(f"👥 Active users: {len(active_users)}")
            logger.info("="*80)

            # Process users concurrently (but with some delay between them)
            for i, user_email in enumerate(active_users):
                # Add small delay between users to avoid rate limiting
                if i > 0:
                    await asyncio.sleep(2)

                # Check if user is still authenticated
                if self.graph_client.is_user_authenticated(user_email):
                    await self.poll_user_emails(user_email)
                else:
                    logger.warning(f"⚠️  User {user_email} not authenticated - SKIPPED")

            logger.info("="*80)
            logger.info("✅ POLLING CYCLE COMPLETE")
            logger.info("⏰ Next poll in 60 seconds...")
            logger.info("="*80 + "\n")

        except Exception as e:
            logger.error(f"❌ ERROR IN POLLING CYCLE: {e}")
            logger.error("="*80 + "\n")
    
    def start_polling(self):
        """Start the background email polling"""
        if self.is_running:
            logger.warning("⚠️  Polling service already running")
            return

        logger.info(f"⚙️  Configuring polling service...")
        logger.info(f"   ⏱️  Interval: {self.polling_interval} seconds")
        logger.info(f"   🔄 Mode: Automated continuous polling")

        # Add the polling job
        self.scheduler.add_job(
            self.poll_all_users,
            IntervalTrigger(seconds=self.polling_interval),
            id='email_polling',
            replace_existing=True,
            max_instances=1  # Prevent overlapping polls
        )

        self.scheduler.start()
        self.is_running = True

        logger.info("✅ Polling service started successfully")
    
    def stop_polling(self):
        """Stop the background email polling"""
        if not self.is_running:
            return
        
        logger.info("🛑 Stopping email polling service")
        
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        
        self.is_running = False
        logger.info("✅ Email polling service stopped")
    
    def get_polling_status(self) -> Dict[str, Any]:
        """Get current polling status"""
        return {
            "is_running": self.is_running,
            "polling_interval": self.polling_interval,
            "next_run": None if not self.scheduler.running else
                       self.scheduler.get_job('email_polling').next_run_time.isoformat() if self.scheduler.get_job('email_polling') else None
        }

    def update_polling_interval(self, seconds: int):
        """
        Update the polling interval at runtime.

        This reschedules the existing job with the new interval.
        The change takes effect immediately.

        Args:
            seconds: New polling interval in seconds
        """
        old_interval = self.polling_interval
        self.polling_interval = seconds

        if self.is_running and self.scheduler.running:
            # Reschedule the job with the new interval
            self.scheduler.reschedule_job(
                'email_polling',
                trigger=IntervalTrigger(seconds=seconds)
            )
            logger.info(f"⏱️  Polling interval updated: {old_interval}s -> {seconds}s")
        else:
            logger.info(f"⏱️  Polling interval set to {seconds}s (will apply when service starts)")
    
    async def get_user_stats(self, user_email: str) -> Dict[str, Any]:
        """Get statistics for a user"""
        try:
            # Check if user is being monitored
            active_users = await self.load_active_users()
            is_monitored = user_email in active_users
            
            # Check if user has delta token (has been polled before)
            delta_tokens = await self.load_delta_tokens()
            has_delta_token = user_email in delta_tokens
            
            # Count processed emails
            safe_email = user_email.replace("@", "_at_").replace(".", "_dot_")
            user_output_dir = f"outputs/{safe_email}"
            processed_count = 0
            if os.path.exists(user_output_dir):
                processed_count = len([f for f in os.listdir(user_output_dir) if f.endswith('.json')])
            
            return {
                "is_monitored": is_monitored,
                "has_delta_token": has_delta_token,
                "processed_emails": processed_count,
                "monitoring_since": None  # Could add timestamp tracking
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats for {user_email}: {e}")
            return {
                "is_monitored": False,
                "has_delta_token": False,
                "processed_emails": 0,
                "monitoring_since": None
            }


# Global instance
delta_service = DeltaEmailService()