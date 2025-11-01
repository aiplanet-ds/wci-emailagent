"""Delta service for managing Microsoft Graph delta tokens"""

from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import DeltaToken


class DeltaService:
    """Service for managing delta tokens in the database"""

    @staticmethod
    async def get_delta_token(db: AsyncSession, user_id: int) -> Optional[str]:
        """Get delta token for a user"""
        result = await db.execute(
            select(DeltaToken).where(DeltaToken.user_id == user_id)
        )
        delta_token = result.scalar_one_or_none()
        return delta_token.delta_token if delta_token else None

    @staticmethod
    async def set_delta_token(
        db: AsyncSession,
        user_id: int,
        token: str,
    ) -> DeltaToken:
        """Set or update delta token for a user"""
        result = await db.execute(
            select(DeltaToken).where(DeltaToken.user_id == user_id)
        )
        delta_token = result.scalar_one_or_none()

        if delta_token:
            # Update existing token
            delta_token.delta_token = token
            delta_token.updated_at = datetime.utcnow()
        else:
            # Create new token
            delta_token = DeltaToken(
                user_id=user_id,
                delta_token=token,
            )
            db.add(delta_token)

        await db.flush()
        await db.refresh(delta_token)
        return delta_token

    @staticmethod
    async def delete_delta_token(db: AsyncSession, user_id: int) -> bool:
        """Delete delta token for a user"""
        result = await db.execute(
            select(DeltaToken).where(DeltaToken.user_id == user_id)
        )
        delta_token = result.scalar_one_or_none()

        if not delta_token:
            return False

        await db.delete(delta_token)
        await db.flush()
        return True

    @staticmethod
    async def clear_all_delta_tokens(db: AsyncSession) -> int:
        """Clear all delta tokens (useful for full resync). Returns count of deleted tokens."""
        result = await db.execute(select(DeltaToken))
        tokens = result.scalars().all()
        count = len(tokens)

        for token in tokens:
            await db.delete(token)

        await db.flush()
        return count
