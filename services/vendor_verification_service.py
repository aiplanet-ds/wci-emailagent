"""
Vendor Verification Service
Verifies email senders against Epicor vendor list to prevent AI token waste on random emails

MIGRATED TO DATABASE - No longer uses JSON file caching
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import asyncio

# Database imports
from database.config import SessionLocal
from database.services.vendor_service import VendorService

logger = logging.getLogger(__name__)


class VendorVerificationService:
    """Service for verifying email senders against Epicor vendor list"""

    def __init__(self):
        self.cache_ttl_hours = int(os.getenv("VENDOR_CACHE_TTL_HOURS", "24"))
        self.domain_matching_enabled = os.getenv("VENDOR_DOMAIN_MATCHING_ENABLED", "true").lower() == "true"

    async def is_cache_stale(self) -> bool:
        """Check if vendor cache is stale and needs refresh from Epicor"""
        try:
            async with SessionLocal() as db:
                vendors = await VendorService.get_all_vendors(db, verified_only=True, limit=1)

                if not vendors:
                    # No vendors in database - needs refresh
                    return True

                # Check the most recently synced vendor
                from sqlalchemy import select, func
                from database.models import Vendor

                result = await db.execute(
                    select(func.max(Vendor.last_synced_from_epicor))
                )
                last_sync = result.scalar()

                if not last_sync:
                    return True

                # Check if cache is older than TTL
                age_hours = (datetime.utcnow() - last_sync).total_seconds() / 3600
                return age_hours > self.cache_ttl_hours

        except Exception as e:
            logger.error(f"Error checking cache staleness: {e}")
            return True

    def fetch_vendors_from_epicor(self) -> List[Dict[str, Any]]:
        """Fetch vendor emails from Epicor VendorSvc"""
        try:
            from services.epicor_service import EpicorAPIService

            epicor_service = EpicorAPIService()
            vendors = epicor_service.get_all_vendor_emails()

            logger.info(f"✅ Fetched {len(vendors)} vendors from Epicor")
            return vendors

        except Exception as e:
            logger.error(f"❌ Error fetching vendors from Epicor: {e}")
            return []

    async def build_verified_cache(self) -> Dict[str, Any]:
        """Build verified vendor cache in database from Epicor data"""
        logger.info("🔄 Building vendor verification cache from Epicor...")

        vendors = self.fetch_vendors_from_epicor()

        if not vendors:
            logger.warning("⚠️ No vendors fetched from Epicor - database will be empty")
            return {
                "created": 0,
                "updated": 0,
                "total": 0
            }

        # Prepare vendor data for database sync
        vendor_data = []
        for vendor in vendors:
            vendor_id = vendor.get("vendor_id")
            vendor_name = vendor.get("name")
            email = vendor.get("email")

            if not vendor_id or not vendor_name:
                continue

            vendor_entry = {
                "vendor_id": vendor_id,
                "vendor_name": vendor_name,
                "contact_email": email.lower().strip() if email else None,
            }
            vendor_data.append(vendor_entry)

        # Sync to database
        async with SessionLocal() as db:
            created, updated = await VendorService.sync_vendors_from_epicor(db, vendor_data)

            # Now add domain information to vendors
            for vendor_dict in vendor_data:
                email = vendor_dict.get("contact_email")
                if email and '@' in email:
                    domain = email.split('@')[1]
                    vendor_id = vendor_dict.get("vendor_id")

                    # Add domain to verified_domains
                    vendor = await VendorService.get_vendor_by_vendor_id(db, vendor_id)
                    if vendor and domain not in vendor.verified_domains:
                        await VendorService.add_verified_domain(db, vendor_id, domain)

            await db.commit()

        logger.info(f"✅ Vendor cache built successfully")
        logger.info(f"   ➕ Created: {created} vendors")
        logger.info(f"   🔄 Updated: {updated} vendors")
        logger.info(f"   📊 Total: {created + updated} vendors")

        return {
            "created": created,
            "updated": updated,
            "total": created + updated
        }

    async def refresh_cache(self) -> Dict[str, Any]:
        """Refresh vendor cache in database from Epicor"""
        logger.info("🔄 Refreshing vendor cache from Epicor...")
        return await self.build_verified_cache()

    async def verify_sender(self, sender_email: str) -> Dict[str, Any]:
        """
        Verify if sender email is from a verified vendor

        Args:
            sender_email: Email address to verify

        Returns:
            {
                "is_verified": bool,
                "method": "exact_email" | "domain_match" | None,
                "vendor_info": {"vendor_id": str, "vendor_name": str} | None
            }
        """
        # Check if cache is stale and refresh if needed
        if await self.is_cache_stale():
            logger.info("⚠️ Vendor cache is stale - refreshing...")
            await self.refresh_cache()

        if not sender_email:
            return {
                "is_verified": False,
                "method": None,
                "vendor_info": None
            }

        # Normalize email
        sender_email_lower = sender_email.lower().strip()

        try:
            async with SessionLocal() as db:
                # Use the verify_email_against_vendors method
                result = await VendorService.verify_email_against_vendors(db, sender_email_lower)

                if result:
                    vendor, match_type = result
                    vendor_info = {
                        "vendor_id": vendor.vendor_id,
                        "vendor_name": vendor.vendor_name
                    }

                    logger.info(f"✅ {match_type.replace('_', ' ').title()}: {sender_email_lower}")
                    return {
                        "is_verified": True,
                        "method": match_type,
                        "vendor_info": vendor_info
                    }

                # Not verified
                logger.warning(f"⚠️ Unverified sender: {sender_email_lower}")
                return {
                    "is_verified": False,
                    "method": None,
                    "vendor_info": None
                }

        except Exception as e:
            logger.error(f"Error verifying sender: {e}")
            return {
                "is_verified": False,
                "method": None,
                "vendor_info": None
            }

    async def get_cache_status(self) -> Dict[str, Any]:
        """Get vendor cache status information from database"""
        try:
            async with SessionLocal() as db:
                # Get all vendors
                vendors = await VendorService.get_all_vendors(db, verified_only=True)

                # Count unique emails and domains
                emails = set()
                domains = set()
                vendor_ids = set()

                for vendor in vendors:
                    vendor_ids.add(vendor.vendor_id)

                    if vendor.contact_email:
                        emails.add(vendor.contact_email)

                    # Count domains from verified_domains JSONB field
                    if vendor.verified_domains:
                        domains.update(vendor.verified_domains)

                # Get last sync time
                from sqlalchemy import select, func
                from database.models import Vendor

                result = await db.execute(
                    select(func.max(Vendor.last_synced_from_epicor))
                )
                last_updated = result.scalar()

                is_stale = await self.is_cache_stale()

                # Calculate next refresh time
                next_refresh = None
                if last_updated:
                    next_refresh_dt = last_updated + timedelta(hours=self.cache_ttl_hours)
                    next_refresh = next_refresh_dt.isoformat()

                return {
                    "last_updated": last_updated.isoformat() if last_updated else None,
                    "vendor_count": len(vendor_ids),
                    "email_count": len(emails),
                    "domain_count": len(domains),
                    "is_stale": is_stale,
                    "ttl_hours": self.cache_ttl_hours,
                    "next_refresh": next_refresh,
                    "domain_matching_enabled": self.domain_matching_enabled,
                    "storage": "database"  # Indicate we're using database
                }

        except Exception as e:
            logger.error(f"Error getting cache status: {e}")
            return {
                "last_updated": None,
                "vendor_count": 0,
                "email_count": 0,
                "domain_count": 0,
                "is_stale": True,
                "ttl_hours": self.cache_ttl_hours,
                "next_refresh": None,
                "domain_matching_enabled": self.domain_matching_enabled,
                "storage": "database",
                "error": str(e)
            }

    async def initialize_cache(self):
        """Initialize vendor cache on startup if needed"""
        if await self.is_cache_stale():
            logger.info("🚀 Initializing vendor verification cache...")
            await self.refresh_cache()
        else:
            cache_status = await self.get_cache_status()
            logger.info(f"✅ Vendor cache loaded from database: {cache_status['email_count']} emails, {cache_status['domain_count']} domains")


# Global instance
vendor_verification_service = VendorVerificationService()
