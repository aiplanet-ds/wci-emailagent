"""
Delta Query Service for Email Intelligence System

This service replaces webhook functionality with polling-based email monitoring.
It uses Microsoft Graph delta queries to efficiently track email changes for each user.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import aiofiles

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
        self.delta_tokens_file = "delta_tokens.json"
        self.active_users_file = "active_users.json"
        self.polling_interval = 60  # 1 minute for automated workflow
        self.is_running = False

        # Ensure directories exist
        os.makedirs("delta_cache", exist_ok=True)
        
    async def load_delta_tokens(self) -> Dict[str, str]:
        """Load delta tokens for all users"""
        try:
            if os.path.exists(self.delta_tokens_file):
                with open(self.delta_tokens_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading delta tokens: {e}")
        return {}
    
    async def save_delta_tokens(self, tokens: Dict[str, str]):
        """Save delta tokens for all users"""
        try:
            with open(self.delta_tokens_file, 'w') as f:
                json.dump(tokens, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving delta tokens: {e}")
    
    async def load_active_users(self) -> List[str]:
        """Load list of active users to monitor"""
        try:
            if os.path.exists(self.active_users_file):
                with open(self.active_users_file, 'r') as f:
                    data = json.load(f)
                    return data.get('users', [])
        except Exception as e:
            logger.error(f"Error loading active users: {e}")
        return []
    
    async def save_active_users(self, users: List[str]):
        """Save list of active users"""
        try:
            data = {
                'users': users,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.active_users_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving active users: {e}")
    
    async def add_user_to_monitoring(self, user_email: str):
        """Add a user to email monitoring"""
        active_users = await self.load_active_users()
        if user_email not in active_users:
            active_users.append(user_email)
            await self.save_active_users(active_users)
            logger.info(f"✅ User added to monitoring list")
            logger.info(f"📊 Total active users: {len(active_users)}")
        else:
            logger.info(f"ℹ️  User already in monitoring list")
    
    async def remove_user_from_monitoring(self, user_email: str):
        """Remove a user from email monitoring"""
        active_users = await self.load_active_users()
        if user_email in active_users:
            active_users.remove(user_email)
            await self.save_active_users(active_users)

            # Also remove their delta token
            delta_tokens = await self.load_delta_tokens()
            if user_email in delta_tokens:
                del delta_tokens[user_email]
                await self.save_delta_tokens(delta_tokens)

            logger.info(f"✅ User removed from monitoring list")
            logger.info(f"📊 Remaining active users: {len(active_users)}")
    
    async def get_user_delta_messages(self, user_email: str, delta_token: Optional[str] = None) -> Dict[str, Any]:
        """Get delta messages for a user"""
        try:
            return self.graph_client.get_user_delta_messages(user_email, delta_token)
        except Exception as e:
            logger.error(f"Error getting delta messages for {user_email}: {e}")
            return {"messages": [], "delta_token": delta_token}
    
    def is_price_change_email(self, message: Dict) -> bool:
        """Determine if an email is likely about price changes using liberal filtering"""
        subject = message.get('subject', '').lower()
        sender_info = message.get('from', {}).get('emailAddress', {})
        sender = sender_info.get('address', '').lower() if sender_info else ''
        has_attachments = message.get('hasAttachments', False)
        
        # Priority keywords - strong indicators of price changes
        priority_keywords = [
            'price change', 'pricing update', 'cost adjustment', 'rate change',
            'price increase', 'price decrease', 'new pricing', 'pricing effective',
            'cost increase', 'rate adjustment', 'tariff change', 'fee update'
        ]
        
        # General price-related keywords
        price_keywords = [
            'price', 'pricing', 'cost', 'rate', 'rates', 'tariff', 'fee', 'fees',
            'quote', 'quotation', 'invoice', 'bill', 'billing', 'charge', 'charges'
        ]
        
        # Change-related keywords
        change_keywords = [
            'change', 'update', 'revised', 'new', 'effective', 'increase', 'decrease',
            'adjustment', 'modify', 'modified', 'amendment', 'notice', 'notification'
        ]
        
        # Business/supplier keywords
        business_keywords = [
            'supplier', 'vendor', 'contract', 'agreement', 'terms', 'conditions',
            'procurement', 'purchase', 'order', 'catalog', 'catalogue'
        ]
        
        # Financial indicators
        financial_indicators = ['$', '€', '£', '¥', '%', 'usd', 'eur', 'gbp']
        
        # High priority: Strong price change indicators in subject
        if any(keyword in subject for keyword in priority_keywords):
            return True
        
        # Medium-high priority: Has attachments + any price/change keywords
        if has_attachments and (
            any(keyword in subject for keyword in price_keywords) or
            any(keyword in subject for keyword in change_keywords)
        ):
            return True
        
        # Medium priority: Price keywords + change keywords combination
        has_price_keyword = any(keyword in subject for keyword in price_keywords)
        has_change_keyword = any(keyword in subject for keyword in change_keywords)
        if has_price_keyword and has_change_keyword:
            return True
        
        # Medium priority: Financial indicators + business context
        has_financial = any(indicator in subject for indicator in financial_indicators)
        has_business = any(keyword in subject for keyword in business_keywords)
        if has_financial and (has_business or has_change_keyword):
            return True
        
        # Lower priority: Business sender with price/financial keywords
        business_sender_domains = [
            'supplier', 'vendor', 'corp', 'company', 'inc', 'ltd', 'llc',
            'procurement', 'sales', 'billing', 'finance', 'accounting'
        ]
        is_business_sender = any(domain in sender for domain in business_sender_domains)
        if is_business_sender and (has_price_keyword or has_financial):
            return True
        
        # Catch common invoice/billing patterns
        invoice_patterns = [
            'invoice', 'bill', 'billing', 'payment', 'due', 'statement',
            'account', 'balance', 'outstanding', 'remittance'
        ]
        if any(pattern in subject for pattern in invoice_patterns):
            return True
        
        return False

    async def process_user_messages(self, user_email: str, messages: List[Dict]):
        """Process new messages for a user with vendor verification and liberal price change filtering"""
        from main import process_user_message
        from services.vendor_verification_service import vendor_verification_service
        from services.email_state_service import email_state_service

        processed_count = 0
        skipped_count = 0
        flagged_count = 0

        for i, message in enumerate(messages, 1):
            try:
                subject = message.get('subject', 'No Subject')
                message_id = message.get('id', '')
                sender_info = message.get('from', {}).get('emailAddress', {})
                sender_email = sender_info.get('address', '').lower() if sender_info else ''

                logger.info(f"\n📧 Email {i}/{len(messages)}: {subject}")
                logger.info(f"   From: {sender_email}")

                # Use liberal filtering to identify potential price change emails
                if self.is_price_change_email(message):
                    logger.info(f"   ✅ PRICE CHANGE DETECTED")

                    # VENDOR VERIFICATION CHECK (before AI extraction)
                    verification_enabled = os.getenv("VENDOR_VERIFICATION_ENABLED", "true").lower() == "true"

                    if verification_enabled:
                        verification_result = vendor_verification_service.verify_sender(sender_email)

                        if verification_result['is_verified']:
                            # VERIFIED VENDOR - Proceed with AI extraction
                            method = verification_result['method']
                            logger.info(f"   ✅ VERIFIED VENDOR ({method})")

                            # Get full message details
                            full_message = self.graph_client.get_user_message_by_id(user_email, message['id'])

                            # Process the message
                            await asyncio.to_thread(process_user_message, full_message, user_email)

                            # Mark as vendor verified
                            email_state_service.mark_as_vendor_verified(
                                message_id,
                                verification_result['method'],
                                verification_result['vendor_info']
                            )

                            processed_count += 1
                        else:
                            # UNVERIFIED SENDER - Flag for manual review (save AI tokens)
                            logger.warning(f"   ⚠️  FLAGGED - Unverified sender")
                            logger.info(f"   💾 Saving metadata without AI extraction (token savings)")

                            # Get full message for metadata
                            full_message = self.graph_client.get_user_message_by_id(user_email, message['id'])

                            # Save minimal email metadata WITHOUT AI extraction
                            await self._save_flagged_email_metadata(full_message, user_email)

                            # Mark as pending verification
                            email_state_service.update_email_state(message_id, {
                                "vendor_verified": False,
                                "verification_status": "pending_review",
                                "flagged_reason": f"Email from unverified sender: {sender_email}",
                                "is_price_change": True
                            })

                            flagged_count += 1
                    else:
                        # Verification disabled - process normally
                        logger.info(f"   ℹ️  Vendor verification disabled - processing")

                        # Get full message details
                        full_message = self.graph_client.get_user_message_by_id(user_email, message['id'])

                        # Process the message
                        await asyncio.to_thread(process_user_message, full_message, user_email)
                        processed_count += 1

                    # Small delay to avoid overwhelming the system
                    await asyncio.sleep(1)
                else:
                    skipped_count += 1
                    logger.info(f"   ⏭️  Not a price change email - SKIPPED")

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
        """Save basic email metadata for flagged emails without AI extraction"""
        import json
        import os

        safe_email = user_email.replace("@", "_at_").replace(".", "_dot_")
        user_output_dir = os.path.join("outputs", safe_email)
        os.makedirs(user_output_dir, exist_ok=True)

        message_id = msg.get('id', '')
        subject = msg.get('subject', '(no subject)')
        sender_info = msg.get('from', {}).get('emailAddress', {})
        sender = sender_info.get('address', '(no sender)')
        date_received = msg.get('receivedDateTime', '(no date)')

        # Save minimal metadata (no AI extraction)
        flagged_data = {
            "email_metadata": {
                "subject": subject,
                "sender": sender,
                "date": date_received,
                "message_id": message_id
            },
            "flagged": True,
            "flagged_reason": "Unverified vendor email - pending manual approval",
            "supplier_info": {
                "supplier_id": None,
                "supplier_name": None,
                "contact_person": None,
                "contact_email": sender,
                "contact_phone": None
            },
            "price_change_summary": {
                "change_type": None,
                "effective_date": None,
                "notification_date": None,
                "reason": "Awaiting verification",
                "overall_impact": None
            },
            "affected_products": [],
            "additional_details": {
                "terms_and_conditions": None,
                "payment_terms": None,
                "minimum_order_quantity": None,
                "notes": "This email requires manual verification before AI extraction"
            }
        }

        output_filename = f"price_change_{message_id}.json"
        output_path = os.path.join(user_output_dir, output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(flagged_data, f, indent=2, ensure_ascii=False)

        logger.info(f"   💾 Saved flagged email metadata: {output_filename}")

    async def poll_user_emails(self, user_email: str):
        """Poll emails for a specific user"""
        try:
            # Load current delta token for user
            delta_tokens = await self.load_delta_tokens()
            current_token = delta_tokens.get(user_email)

            logger.info("="*80)
            logger.info(f"🔍 POLLING EMAILS FOR: {user_email}")
            logger.info("="*80)

            # Get delta messages
            result = await self.get_user_delta_messages(user_email, current_token)
            messages = result.get('messages', [])
            new_delta_token = result.get('delta_token')

            if messages:
                logger.info(f"📬 NEW EMAILS DETECTED: {len(messages)} email(s)")
                logger.info("-"*80)
                await self.process_user_messages(user_email, messages)
            else:
                logger.info(f"📭 No new emails")
                logger.info("="*80 + "\n")

            # Update delta token
            if new_delta_token:
                delta_tokens[user_email] = new_delta_token
                await self.save_delta_tokens(delta_tokens)

        except Exception as e:
            logger.error(f"❌ ERROR POLLING EMAILS: {e}")
            logger.error("="*80 + "\n")
    
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