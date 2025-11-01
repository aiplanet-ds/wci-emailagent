"""Email state service for database operations - replaces JSON-based state management"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database.models import EmailState


class EmailStateService:
    """Service for managing email states in the database"""

    @staticmethod
    async def get_state_by_message_id(db: AsyncSession, message_id: str) -> Optional[EmailState]:
        """Get email state by message ID"""
        result = await db.execute(
            select(EmailState)
            .where(EmailState.message_id == message_id)
            .options(
                joinedload(EmailState.email),
                joinedload(EmailState.vendor),
                joinedload(EmailState.processed_by_user),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_state_by_id(db: AsyncSession, state_id: int) -> Optional[EmailState]:
        """Get email state by ID"""
        result = await db.execute(
            select(EmailState).where(EmailState.id == state_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_state(
        db: AsyncSession,
        message_id: str,
        user_id: int,
        email_id: Optional[int] = None,
        is_price_change: Optional[bool] = None,
        llm_confidence: Optional[float] = None,
        llm_reasoning: Optional[str] = None,
    ) -> EmailState:
        """Create a new email state"""
        state = EmailState(
            message_id=message_id,
            user_id=user_id,
            email_id=email_id,
            is_price_change=is_price_change,
            llm_confidence=llm_confidence,
            llm_reasoning=llm_reasoning,
        )
        db.add(state)
        await db.flush()
        await db.refresh(state)
        return state

    @staticmethod
    async def mark_as_processed(
        db: AsyncSession,
        message_id: str,
        processed_by_id: int,
    ) -> Optional[EmailState]:
        """Mark email as processed"""
        state = await EmailStateService.get_state_by_message_id(db, message_id)
        if not state:
            return None

        state.processed = True
        state.processed_at = datetime.utcnow()
        state.processed_by_id = processed_by_id
        state.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(state)
        return state

    @staticmethod
    async def mark_as_unprocessed(
        db: AsyncSession,
        message_id: str,
    ) -> Optional[EmailState]:
        """Mark email as unprocessed"""
        state = await EmailStateService.get_state_by_message_id(db, message_id)
        if not state:
            return None

        state.processed = False
        state.processed_at = None
        state.processed_by_id = None
        state.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(state)
        return state

    @staticmethod
    async def mark_epicor_synced(
        db: AsyncSession,
        message_id: str,
        success: bool = True,
    ) -> Optional[EmailState]:
        """Mark email as synced with Epicor"""
        state = await EmailStateService.get_state_by_message_id(db, message_id)
        if not state:
            return None

        state.epicor_synced = success
        if success:
            state.epicor_synced_at = datetime.utcnow()
        state.epicor_sync_attempts += 1
        state.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(state)
        return state

    @staticmethod
    async def update_vendor_verification(
        db: AsyncSession,
        message_id: str,
        vendor_verified: bool,
        verification_status: str,
        verification_method: Optional[str] = None,
        vendor_id: Optional[int] = None,
        flagged_reason: Optional[str] = None,
    ) -> Optional[EmailState]:
        """Update vendor verification status"""
        state = await EmailStateService.get_state_by_message_id(db, message_id)
        if not state:
            return None

        state.vendor_verified = vendor_verified
        state.verification_status = verification_status
        state.verification_method = verification_method
        state.vendor_id = vendor_id
        state.flagged_reason = flagged_reason
        state.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(state)
        return state

    @staticmethod
    async def manually_approve(
        db: AsyncSession,
        message_id: str,
        approved_by_id: int,
    ) -> Optional[EmailState]:
        """Manually approve an email"""
        state = await EmailStateService.get_state_by_message_id(db, message_id)
        if not state:
            return None

        state.vendor_verified = True
        state.verification_status = "manually_approved"
        state.verification_method = "manual_approval"
        state.manually_approved_by_id = approved_by_id
        state.manually_approved_at = datetime.utcnow()
        state.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(state)
        return state

    @staticmethod
    async def set_followup_info(
        db: AsyncSession,
        message_id: str,
        needs_info: bool,
        selected_missing_fields: Optional[List[str]] = None,
        followup_draft: Optional[str] = None,
    ) -> Optional[EmailState]:
        """Set follow-up information"""
        state = await EmailStateService.get_state_by_message_id(db, message_id)
        if not state:
            return None

        state.needs_info = needs_info
        state.selected_missing_fields = selected_missing_fields or []
        state.followup_draft = followup_draft
        state.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(state)
        return state

    @staticmethod
    async def get_pending_verification(
        db: AsyncSession,
        user_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[EmailState]:
        """Get emails pending verification"""
        query = select(EmailState).where(
            EmailState.verification_status == "pending_review"
        )
        if user_id:
            query = query.where(EmailState.user_id == user_id)

        query = query.order_by(EmailState.created_at.desc()).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_unprocessed_emails(
        db: AsyncSession,
        user_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[EmailState]:
        """Get unprocessed emails"""
        query = select(EmailState).where(EmailState.processed == False)
        if user_id:
            query = query.where(EmailState.user_id == user_id)

        query = query.order_by(EmailState.created_at.desc()).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_price_change_emails(
        db: AsyncSession,
        user_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[EmailState]:
        """Get emails identified as price changes"""
        query = select(EmailState).where(EmailState.is_price_change == True)
        if user_id:
            query = query.where(EmailState.user_id == user_id)

        query = query.order_by(EmailState.created_at.desc()).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_unsynced_emails(
        db: AsyncSession,
        user_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[EmailState]:
        """Get emails that need to be synced with Epicor"""
        query = select(EmailState).where(
            and_(
                EmailState.is_price_change == True,
                EmailState.vendor_verified == True,
                EmailState.epicor_synced == False,
            )
        )
        if user_id:
            query = query.where(EmailState.user_id == user_id)

        query = query.order_by(EmailState.created_at.desc()).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update_llm_detection(
        db: AsyncSession,
        message_id: str,
        is_price_change: bool,
        llm_confidence: float,
        llm_reasoning: Optional[str] = None,
    ) -> Optional[EmailState]:
        """Update LLM detection results"""
        state = await EmailStateService.get_state_by_message_id(db, message_id)
        if not state:
            return None

        state.is_price_change = is_price_change
        state.llm_confidence = llm_confidence
        state.llm_reasoning = llm_reasoning
        state.llm_detection_performed = True
        state.awaiting_llm_detection = False
        state.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(state)
        return state

    @staticmethod
    async def update_state(
        db: AsyncSession,
        message_id: str,
        **kwargs
    ) -> Optional[EmailState]:
        """
        Update email state with arbitrary fields

        This is a general-purpose update method used by router endpoints.
        Accepts any EmailState field as keyword argument.
        """
        state = await EmailStateService.get_state_by_message_id(db, message_id)
        if not state:
            return None

        # Update provided fields
        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)

        state.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(state)
        return state

    @staticmethod
    async def delete_state(db: AsyncSession, message_id: str) -> bool:
        """Delete an email state"""
        state = await EmailStateService.get_state_by_message_id(db, message_id)
        if not state:
            return False

        await db.delete(state)
        await db.flush()
        return True
