"""Vendor service for database operations - replaces JSON-based vendor cache"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Vendor


class VendorService:
    """Service for managing vendors in the database"""

    @staticmethod
    async def get_vendor_by_id(db: AsyncSession, vendor_id: int) -> Optional[Vendor]:
        """Get vendor by ID"""
        result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_vendor_by_vendor_id(db: AsyncSession, vendor_id: str) -> Optional[Vendor]:
        """Get vendor by Epicor vendor ID"""
        result = await db.execute(
            select(Vendor).where(Vendor.vendor_id == vendor_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_vendor_by_email(db: AsyncSession, email: str) -> Optional[Vendor]:
        """Get vendor by contact email"""
        result = await db.execute(
            select(Vendor).where(Vendor.contact_email == email)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_vendor_by_domain(db: AsyncSession, domain: str) -> Optional[Vendor]:
        """Get vendor by email domain (checks verified_domains JSONB array)"""
        result = await db.execute(
            select(Vendor).where(
                Vendor.verified_domains.contains([domain])
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def search_vendors(db: AsyncSession, search_term: str, limit: int = 50) -> List[Vendor]:
        """Search vendors by name or vendor ID"""
        search_pattern = f"%{search_term}%"
        result = await db.execute(
            select(Vendor)
            .where(
                or_(
                    Vendor.vendor_name.ilike(search_pattern),
                    Vendor.vendor_id.ilike(search_pattern),
                    Vendor.contact_email.ilike(search_pattern),
                )
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_all_vendors(
        db: AsyncSession,
        verified_only: bool = False,
        limit: int = 1000,
    ) -> List[Vendor]:
        """Get all vendors"""
        query = select(Vendor)
        if verified_only:
            query = query.where(Vendor.verified == True)
        query = query.limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def create_vendor(
        db: AsyncSession,
        vendor_id: str,
        vendor_name: str,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
        verified: bool = True,
        verified_domains: Optional[List[str]] = None,
    ) -> Vendor:
        """Create a new vendor"""
        vendor = Vendor(
            vendor_id=vendor_id,
            vendor_name=vendor_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            verified=verified,
            verified_domains=verified_domains or [],
        )
        db.add(vendor)
        await db.flush()
        await db.refresh(vendor)
        return vendor

    @staticmethod
    async def update_vendor(
        db: AsyncSession,
        vendor_id: str,
        vendor_name: Optional[str] = None,
        contact_email: Optional[str] = None,
        contact_phone: Optional[str] = None,
        verified: Optional[bool] = None,
        verified_domains: Optional[List[str]] = None,
        last_synced_from_epicor: Optional[datetime] = None,
    ) -> Optional[Vendor]:
        """Update vendor information"""
        vendor = await VendorService.get_vendor_by_vendor_id(db, vendor_id)
        if not vendor:
            return None

        if vendor_name is not None:
            vendor.vendor_name = vendor_name
        if contact_email is not None:
            vendor.contact_email = contact_email
        if contact_phone is not None:
            vendor.contact_phone = contact_phone
        if verified is not None:
            vendor.verified = verified
        if verified_domains is not None:
            vendor.verified_domains = verified_domains
        if last_synced_from_epicor is not None:
            vendor.last_synced_from_epicor = last_synced_from_epicor

        vendor.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(vendor)
        return vendor

    @staticmethod
    async def add_verified_domain(
        db: AsyncSession,
        vendor_id: str,
        domain: str,
    ) -> Optional[Vendor]:
        """Add a verified domain to a vendor"""
        vendor = await VendorService.get_vendor_by_vendor_id(db, vendor_id)
        if not vendor:
            return None

        if domain not in vendor.verified_domains:
            vendor.verified_domains = vendor.verified_domains + [domain]
            vendor.updated_at = datetime.utcnow()
            await db.flush()
            await db.refresh(vendor)

        return vendor

    @staticmethod
    async def remove_verified_domain(
        db: AsyncSession,
        vendor_id: str,
        domain: str,
    ) -> Optional[Vendor]:
        """Remove a verified domain from a vendor"""
        vendor = await VendorService.get_vendor_by_vendor_id(db, vendor_id)
        if not vendor:
            return None

        if domain in vendor.verified_domains:
            domains = list(vendor.verified_domains)
            domains.remove(domain)
            vendor.verified_domains = domains
            vendor.updated_at = datetime.utcnow()
            await db.flush()
            await db.refresh(vendor)

        return vendor

    @staticmethod
    async def get_or_create_vendor(
        db: AsyncSession,
        vendor_id: str,
        vendor_name: str,
        contact_email: Optional[str] = None,
    ) -> tuple[Vendor, bool]:
        """Get existing vendor or create new one. Returns (vendor, created)"""
        vendor = await VendorService.get_vendor_by_vendor_id(db, vendor_id)
        if vendor:
            return vendor, False

        vendor = await VendorService.create_vendor(
            db=db,
            vendor_id=vendor_id,
            vendor_name=vendor_name,
            contact_email=contact_email,
        )
        return vendor, True

    @staticmethod
    async def verify_email_against_vendors(
        db: AsyncSession,
        email: str,
    ) -> Optional[tuple[Vendor, str]]:
        """
        Verify if an email belongs to a known vendor.
        Returns (vendor, match_type) where match_type is 'exact_email' or 'domain_match'
        """
        # Try exact email match
        vendor = await VendorService.get_vendor_by_email(db, email)
        if vendor:
            return vendor, "exact_email"

        # Try domain match
        if "@" in email:
            domain = email.split("@")[1].lower()
            vendor = await VendorService.get_vendor_by_domain(db, domain)
            if vendor:
                return vendor, "domain_match"

        return None

    @staticmethod
    async def sync_vendors_from_epicor(
        db: AsyncSession,
        vendor_data: List[dict],
    ) -> tuple[int, int]:
        """
        Sync vendors from Epicor.
        Returns (created_count, updated_count)
        """
        created = 0
        updated = 0
        sync_time = datetime.utcnow()

        for data in vendor_data:
            vendor_id = data.get("vendor_id")
            vendor_name = data.get("vendor_name")

            if not vendor_id or not vendor_name:
                continue

            vendor = await VendorService.get_vendor_by_vendor_id(db, vendor_id)

            if vendor:
                # Update existing vendor
                await VendorService.update_vendor(
                    db=db,
                    vendor_id=vendor_id,
                    vendor_name=vendor_name,
                    contact_email=data.get("contact_email"),
                    contact_phone=data.get("contact_phone"),
                    last_synced_from_epicor=sync_time,
                )
                updated += 1
            else:
                # Create new vendor
                await VendorService.create_vendor(
                    db=db,
                    vendor_id=vendor_id,
                    vendor_name=vendor_name,
                    contact_email=data.get("contact_email"),
                    contact_phone=data.get("contact_phone"),
                )
                created += 1

        return created, updated

    @staticmethod
    async def delete_vendor(db: AsyncSession, vendor_id: str) -> bool:
        """Delete a vendor"""
        vendor = await VendorService.get_vendor_by_vendor_id(db, vendor_id)
        if not vendor:
            return False

        await db.delete(vendor)
        await db.flush()
        return True
