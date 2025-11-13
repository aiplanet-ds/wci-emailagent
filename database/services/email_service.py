"""Email service for database operations"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database.models import Email, EmailState


class EmailService:
    """Service for managing emails in the database"""

    @staticmethod
    async def get_email_by_message_id(db: AsyncSession, message_id: str) -> Optional[Email]:
        """Get email by message ID"""
        result = await db.execute(
            select(Email)
            .where(Email.message_id == message_id)
            .options(joinedload(Email.email_state))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_email_by_id(db: AsyncSession, email_id: int) -> Optional[Email]:
        """Get email by ID"""
        result = await db.execute(
            select(Email)
            .where(Email.id == email_id)
            .options(joinedload(Email.email_state))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_emails_by_user(
        db: AsyncSession,
        user_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Email]:
        """Get emails for a specific user"""
        result = await db.execute(
            select(Email)
            .where(Email.user_id == user_id)
            .order_by(desc(Email.received_at))
            .limit(limit)
            .offset(offset)
            .options(joinedload(Email.email_state))
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_emails_by_sender(
        db: AsyncSession,
        sender_email: str,
        limit: int = 100,
    ) -> List[Email]:
        """Get emails from a specific sender"""
        result = await db.execute(
            select(Email)
            .where(Email.sender_email == sender_email)
            .order_by(desc(Email.received_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_email(
        db: AsyncSession,
        message_id: str,
        user_id: int,
        subject: Optional[str] = None,
        sender_email: Optional[str] = None,
        sender_name: Optional[str] = None,
        received_at: Optional[datetime] = None,
        body_text: Optional[str] = None,
        body_html: Optional[str] = None,
        has_attachments: bool = False,
        supplier_info: Optional[dict] = None,
        price_change_summary: Optional[dict] = None,
        affected_products: Optional[list] = None,
        additional_details: Optional[dict] = None,
        raw_email_data: Optional[dict] = None,
    ) -> Email:
        """Create a new email record"""
        email = Email(
            message_id=message_id,
            user_id=user_id,
            subject=subject,
            sender_email=sender_email,
            sender_name=sender_name,
            received_at=received_at or datetime.utcnow(),
            body_text=body_text,
            body_html=body_html,
            has_attachments=has_attachments,
            supplier_info=supplier_info,
            price_change_summary=price_change_summary,
            affected_products=affected_products,
            additional_details=additional_details,
            raw_email_data=raw_email_data,
        )
        db.add(email)
        await db.flush()
        await db.refresh(email)
        return email

    @staticmethod
    async def update_email(
        db: AsyncSession,
        email_id: int,
        subject: Optional[str] = None,
        body_text: Optional[str] = None,
        body_html: Optional[str] = None,
        supplier_info: Optional[dict] = None,
        price_change_summary: Optional[dict] = None,
        affected_products: Optional[list] = None,
        additional_details: Optional[dict] = None,
    ) -> Optional[Email]:
        """Update email information"""
        email = await EmailService.get_email_by_id(db, email_id)
        if not email:
            return None

        if subject is not None:
            email.subject = subject
        if body_text is not None:
            email.body_text = body_text
        if body_html is not None:
            email.body_html = body_html
        if supplier_info is not None:
            email.supplier_info = supplier_info
        if price_change_summary is not None:
            email.price_change_summary = price_change_summary
        if affected_products is not None:
            email.affected_products = affected_products
        if additional_details is not None:
            email.additional_details = additional_details

        email.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(email)
        return email

    @staticmethod
    async def delete_email(db: AsyncSession, email_id: int) -> bool:
        """Delete an email"""
        email = await EmailService.get_email_by_id(db, email_id)
        if not email:
            return False

        await db.delete(email)
        await db.flush()
        return True

    @staticmethod
    async def search_emails(
        db: AsyncSession,
        user_id: int,
        search_term: str,
        limit: int = 50,
    ) -> List[Email]:
        """Search emails by subject or body text"""
        # Simple ILIKE search (can be enhanced with full-text search)
        search_pattern = f"%{search_term}%"
        result = await db.execute(
            select(Email)
            .where(Email.user_id == user_id)
            .where(
                (Email.subject.ilike(search_pattern)) |
                (Email.body_text.ilike(search_pattern))
            )
            .order_by(desc(Email.received_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_price_change_emails(
        db: AsyncSession,
        user_id: int,
        limit: int = 100,
    ) -> List[Email]:
        """Get emails that are identified as price change emails"""
        result = await db.execute(
            select(Email)
            .join(EmailState)
            .where(Email.user_id == user_id)
            .where(EmailState.is_price_change == True)
            .order_by(desc(Email.received_at))
            .limit(limit)
            .options(joinedload(Email.email_state))
        )
        return list(result.scalars().all())
