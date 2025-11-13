"""User service for database operations"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User


class UserService:
    """Service for managing users in the database"""

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email address"""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        """Get user by ID"""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_users(db: AsyncSession, active_only: bool = False) -> List[User]:
        """Get all users, optionally filter by active status"""
        query = select(User)
        if active_only:
            query = query.where(User.is_active == True)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def create_user(
        db: AsyncSession,
        email: str,
        display_name: Optional[str] = None,
        msal_account_id: Optional[str] = None,
        preferences: Optional[dict] = None,
    ) -> User:
        """Create a new user"""
        user = User(
            email=email,
            display_name=display_name,
            msal_account_id=msal_account_id,
            preferences=preferences or {},
            is_active=True,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def update_user(
        db: AsyncSession,
        user_id: int,
        display_name: Optional[str] = None,
        is_active: Optional[bool] = None,
        token_expires_at: Optional[datetime] = None,
        preferences: Optional[dict] = None,
    ) -> Optional[User]:
        """Update user information"""
        user = await UserService.get_user_by_id(db, user_id)
        if not user:
            return None

        if display_name is not None:
            user.display_name = display_name
        if is_active is not None:
            user.is_active = is_active
        if token_expires_at is not None:
            user.token_expires_at = token_expires_at
        if preferences is not None:
            user.preferences = preferences

        user.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def update_last_login(db: AsyncSession, user_id: int) -> Optional[User]:
        """Update user's last login timestamp"""
        user = await UserService.get_user_by_id(db, user_id)
        if not user:
            return None

        user.last_login_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def get_or_create_user(
        db: AsyncSession,
        email: str,
        display_name: Optional[str] = None,
        msal_account_id: Optional[str] = None,
    ) -> tuple[User, bool]:
        """Get existing user or create new one. Returns (user, created)"""
        user = await UserService.get_user_by_email(db, email)
        if user:
            # Update last login
            await UserService.update_last_login(db, user.id)
            return user, False

        # Create new user
        user = await UserService.create_user(
            db=db,
            email=email,
            display_name=display_name,
            msal_account_id=msal_account_id,
        )
        return user, True

    @staticmethod
    async def deactivate_user(db: AsyncSession, user_id: int) -> Optional[User]:
        """Deactivate a user"""
        return await UserService.update_user(db, user_id, is_active=False)

    @staticmethod
    async def activate_user(db: AsyncSession, user_id: int) -> Optional[User]:
        """Activate a user"""
        return await UserService.update_user(db, user_id, is_active=True)

    @staticmethod
    async def delete_user(db: AsyncSession, user_id: int) -> bool:
        """Delete a user (hard delete)"""
        user = await UserService.get_user_by_id(db, user_id)
        if not user:
            return False

        await db.delete(user)
        await db.flush()
        return True
