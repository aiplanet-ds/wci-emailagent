"""Audit service for tracking user actions"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AuditLog


class AuditService:
    """Service for managing audit logs in the database"""

    @staticmethod
    async def log_action(
        db: AsyncSession,
        action_type: str,
        user_id: Optional[int] = None,
        email_id: Optional[int] = None,
        action_details: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Log a user action"""
        audit_log = AuditLog(
            user_id=user_id,
            email_id=email_id,
            action_type=action_type,
            action_details=action_details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(audit_log)
        await db.flush()
        await db.refresh(audit_log)
        return audit_log

    @staticmethod
    async def get_logs_by_user(
        db: AsyncSession,
        user_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """Get audit logs for a specific user"""
        result = await db.execute(
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_logs_by_email(
        db: AsyncSession,
        email_id: int,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Get audit logs for a specific email"""
        result = await db.execute(
            select(AuditLog)
            .where(AuditLog.email_id == email_id)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_logs_by_action_type(
        db: AsyncSession,
        action_type: str,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Get audit logs by action type"""
        result = await db.execute(
            select(AuditLog)
            .where(AuditLog.action_type == action_type)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_recent_logs(
        db: AsyncSession,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """Get recent audit logs"""
        result = await db.execute(
            select(AuditLog)
            .order_by(desc(AuditLog.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    @staticmethod
    async def delete_old_logs(
        db: AsyncSession,
        older_than: datetime,
    ) -> int:
        """Delete audit logs older than specified date. Returns count of deleted logs."""
        result = await db.execute(
            select(AuditLog).where(AuditLog.created_at < older_than)
        )
        logs = result.scalars().all()
        count = len(logs)

        for log in logs:
            await db.delete(log)

        await db.flush()
        return count

    # Convenience methods for common actions
    @staticmethod
    async def log_login(
        db: AsyncSession,
        user_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Log user login"""
        return await AuditService.log_action(
            db=db,
            action_type="login",
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    async def log_email_processed(
        db: AsyncSession,
        user_id: int,
        email_id: int,
        details: Optional[dict] = None,
    ) -> AuditLog:
        """Log email processed"""
        return await AuditService.log_action(
            db=db,
            action_type="email_processed",
            user_id=user_id,
            email_id=email_id,
            action_details=details,
        )

    @staticmethod
    async def log_vendor_approved(
        db: AsyncSession,
        user_id: int,
        email_id: int,
        details: Optional[dict] = None,
    ) -> AuditLog:
        """Log vendor manually approved"""
        return await AuditService.log_action(
            db=db,
            action_type="vendor_approved",
            user_id=user_id,
            email_id=email_id,
            action_details=details,
        )

    @staticmethod
    async def log_epicor_sync(
        db: AsyncSession,
        user_id: int,
        email_id: int,
        success: bool,
        details: Optional[dict] = None,
    ) -> AuditLog:
        """Log Epicor sync"""
        action_details = details or {}
        action_details["success"] = success

        return await AuditService.log_action(
            db=db,
            action_type="epicor_sync",
            user_id=user_id,
            email_id=email_id,
            action_details=action_details,
        )
