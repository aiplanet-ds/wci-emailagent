"""
Vendor Verification Service
Verifies email senders against Epicor vendor list to prevent AI token waste on random emails
"""

import json
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class VendorVerificationService:
    """Service for verifying email senders against Epicor vendor list"""

    def __init__(self, cache_file: str = "data/vendor_email_cache.json"):
        self.cache_file = cache_file
        self.cache_ttl_hours = int(os.getenv("VENDOR_CACHE_TTL_HOURS", "24"))
        self.domain_matching_enabled = os.getenv("VENDOR_DOMAIN_MATCHING_ENABLED", "true").lower() == "true"
        self._ensure_data_directory()

    def _ensure_data_directory(self):
        """Ensure data directory exists"""
        data_dir = os.path.dirname(self.cache_file)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir)

    def _load_cache(self) -> Dict[str, Any]:
        """Load vendor email cache from file"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading vendor cache: {e}")

        return {
            "last_updated": None,
            "ttl_hours": self.cache_ttl_hours,
            "verified_emails": [],
            "verified_domains": [],
            "vendor_lookup": {}
        }

    def _save_cache(self, cache_data: Dict[str, Any]):
        """Save vendor email cache to file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Vendor cache saved: {len(cache_data.get('verified_emails', []))} emails, {len(cache_data.get('verified_domains', []))} domains")
        except Exception as e:
            logger.error(f"Error saving vendor cache: {e}")

    def is_cache_stale(self) -> bool:
        """Check if cache is stale and needs refresh"""
        cache = self._load_cache()

        if not cache.get("last_updated"):
            return True

        try:
            last_updated = datetime.fromisoformat(cache["last_updated"])
            age_hours = (datetime.utcnow() - last_updated).total_seconds() / 3600
            return age_hours > self.cache_ttl_hours
        except Exception:
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

    def build_verified_cache(self) -> Dict[str, Any]:
        """Build verified vendor cache from Epicor data"""
        logger.info("🔄 Building vendor verification cache from Epicor...")

        vendors = self.fetch_vendors_from_epicor()

        if not vendors:
            logger.warning("⚠️ No vendors fetched from Epicor - cache will be empty")
            return {
                "last_updated": datetime.utcnow().isoformat(),
                "ttl_hours": self.cache_ttl_hours,
                "verified_emails": [],
                "verified_domains": [],
                "vendor_lookup": {}
            }

        verified_emails = set()
        verified_domains = set()
        vendor_lookup = {}

        for vendor in vendors:
            vendor_id = vendor.get("vendor_id")
            vendor_name = vendor.get("name")
            email = vendor.get("email")

            if not email or not vendor_id:
                continue

            # Normalize email to lowercase
            email_lower = email.lower().strip()

            # Add exact email
            verified_emails.add(email_lower)

            # Add to lookup
            vendor_lookup[email_lower] = {
                "vendor_id": vendor_id,
                "vendor_name": vendor_name
            }

            # Extract domain for domain-based matching
            if '@' in email_lower:
                domain = email_lower.split('@')[1]
                verified_domains.add(domain)

                # Add domain to lookup with @ prefix
                domain_key = f"@{domain}"
                if domain_key not in vendor_lookup:
                    vendor_lookup[domain_key] = {
                        "vendor_id": vendor_id,
                        "vendor_name": vendor_name
                    }

        cache_data = {
            "last_updated": datetime.utcnow().isoformat(),
            "ttl_hours": self.cache_ttl_hours,
            "verified_emails": sorted(list(verified_emails)),
            "verified_domains": sorted(list(verified_domains)),
            "vendor_lookup": vendor_lookup
        }

        self._save_cache(cache_data)

        logger.info(f"✅ Vendor cache built successfully")
        logger.info(f"   📧 Verified emails: {len(verified_emails)}")
        logger.info(f"   🌐 Verified domains: {len(verified_domains)}")

        return cache_data

    def refresh_cache(self) -> Dict[str, Any]:
        """Refresh vendor cache from Epicor"""
        logger.info("🔄 Refreshing vendor cache from Epicor...")
        return self.build_verified_cache()

    def verify_sender(self, sender_email: str) -> Dict[str, Any]:
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
        # Load cache (refresh if stale)
        if self.is_cache_stale():
            logger.info("⚠️ Vendor cache is stale - refreshing...")
            self.refresh_cache()

        cache = self._load_cache()

        if not sender_email:
            return {
                "is_verified": False,
                "method": None,
                "vendor_info": None
            }

        # Normalize email
        sender_email_lower = sender_email.lower().strip()

        # Check 1: Exact email match
        if sender_email_lower in cache.get("verified_emails", []):
            vendor_info = cache.get("vendor_lookup", {}).get(sender_email_lower)
            logger.info(f"✅ Exact email match: {sender_email_lower}")
            return {
                "is_verified": True,
                "method": "exact_email",
                "vendor_info": vendor_info
            }

        # Check 2: Domain match (if enabled)
        if self.domain_matching_enabled and '@' in sender_email_lower:
            domain = sender_email_lower.split('@')[1]

            if domain in cache.get("verified_domains", []):
                domain_key = f"@{domain}"
                vendor_info = cache.get("vendor_lookup", {}).get(domain_key)
                logger.info(f"✅ Domain match: @{domain}")
                return {
                    "is_verified": True,
                    "method": "domain_match",
                    "vendor_info": vendor_info
                }

        # Not verified
        logger.warning(f"⚠️ Unverified sender: {sender_email_lower}")
        return {
            "is_verified": False,
            "method": None,
            "vendor_info": None
        }

    def get_cache_status(self) -> Dict[str, Any]:
        """Get vendor cache status information"""
        cache = self._load_cache()

        last_updated = cache.get("last_updated")
        is_stale = self.is_cache_stale()

        # Calculate next refresh time
        next_refresh = None
        if last_updated:
            try:
                last_updated_dt = datetime.fromisoformat(last_updated)
                next_refresh_dt = last_updated_dt + timedelta(hours=self.cache_ttl_hours)
                next_refresh = next_refresh_dt.isoformat()
            except Exception:
                pass

        return {
            "last_updated": last_updated,
            "vendor_count": len(set(v.get("vendor_id") for v in cache.get("vendor_lookup", {}).values() if v.get("vendor_id"))),
            "email_count": len(cache.get("verified_emails", [])),
            "domain_count": len(cache.get("verified_domains", [])),
            "is_stale": is_stale,
            "ttl_hours": self.cache_ttl_hours,
            "next_refresh": next_refresh,
            "domain_matching_enabled": self.domain_matching_enabled
        }

    def initialize_cache(self):
        """Initialize cache on startup if needed"""
        if not os.path.exists(self.cache_file) or self.is_cache_stale():
            logger.info("🚀 Initializing vendor verification cache...")
            self.refresh_cache()
        else:
            cache_status = self.get_cache_status()
            logger.info(f"✅ Vendor cache loaded: {cache_status['email_count']} emails, {cache_status['domain_count']} domains")


# Global instance
vendor_verification_service = VendorVerificationService()
