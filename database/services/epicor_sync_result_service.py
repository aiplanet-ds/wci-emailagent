"""Epicor sync result service for database operations"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import EpicorSyncResult


class EpicorSyncResultService:
    """Service for managing Epicor sync results in the database"""

    @staticmethod
    async def create_sync_result(
        db: AsyncSession,
        email_id: int,
        user_id: Optional[int],
        sync_status: str,
        total_products: int = 0,
        successful_updates: int = 0,
        failed_updates: int = 0,
        results_summary: Optional[dict] = None,
        error_message: Optional[str] = None,
    ) -> EpicorSyncResult:
        """
        Create a new Epicor sync result record

        Args:
            db: Database session
            email_id: ID of the email being synced
            user_id: ID of the user performing the sync
            sync_status: Status of sync ('success', 'partial', 'failed')
            total_products: Total number of products in sync
            successful_updates: Number of successful updates
            failed_updates: Number of failed updates
            results_summary: Detailed results as JSON
            error_message: Error message if sync failed

        Returns:
            Created EpicorSyncResult object
        """
        sync_result = EpicorSyncResult(
            email_id=email_id,
            user_id=user_id,
            sync_status=sync_status,
            total_products=total_products,
            successful_updates=successful_updates,
            failed_updates=failed_updates,
            results_summary=results_summary or {},
            error_message=error_message,
            synced_at=datetime.utcnow(),
        )
        db.add(sync_result)
        await db.flush()
        await db.refresh(sync_result)
        return sync_result

    @staticmethod
    async def get_sync_result_by_id(
        db: AsyncSession,
        sync_result_id: int
    ) -> Optional[EpicorSyncResult]:
        """Get Epicor sync result by ID"""
        result = await db.execute(
            select(EpicorSyncResult).where(EpicorSyncResult.id == sync_result_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_sync_result_by_email_id(
        db: AsyncSession,
        email_id: int
    ) -> Optional[EpicorSyncResult]:
        """
        Get the most recent Epicor sync result for an email

        Args:
            db: Database session
            email_id: ID of the email

        Returns:
            Most recent EpicorSyncResult or None
        """
        result = await db.execute(
            select(EpicorSyncResult)
            .where(EpicorSyncResult.email_id == email_id)
            .order_by(desc(EpicorSyncResult.synced_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_sync_results_by_email_id(
        db: AsyncSession,
        email_id: int,
        limit: int = 10
    ) -> List[EpicorSyncResult]:
        """
        Get all Epicor sync results for an email (most recent first)

        Args:
            db: Database session
            email_id: ID of the email
            limit: Maximum number of results to return

        Returns:
            List of EpicorSyncResult objects
        """
        result = await db.execute(
            select(EpicorSyncResult)
            .where(EpicorSyncResult.email_id == email_id)
            .order_by(desc(EpicorSyncResult.synced_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_all_sync_results_by_user(
        db: AsyncSession,
        user_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> List[EpicorSyncResult]:
        """
        Get all Epicor sync results for a user

        Args:
            db: Database session
            user_id: ID of the user
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of EpicorSyncResult objects
        """
        result = await db.execute(
            select(EpicorSyncResult)
            .where(EpicorSyncResult.user_id == user_id)
            .order_by(desc(EpicorSyncResult.synced_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_failed_syncs(
        db: AsyncSession,
        user_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[EpicorSyncResult]:
        """
        Get failed Epicor sync results

        Args:
            db: Database session
            user_id: Optional user ID to filter by
            limit: Maximum number of results to return

        Returns:
            List of failed EpicorSyncResult objects
        """
        query = select(EpicorSyncResult).where(
            EpicorSyncResult.sync_status == 'failed'
        )

        if user_id:
            query = query.where(EpicorSyncResult.user_id == user_id)

        query = query.order_by(desc(EpicorSyncResult.synced_at)).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_recent_syncs(
        db: AsyncSession,
        user_id: Optional[int] = None,
        hours: int = 24,
        limit: int = 100,
    ) -> List[EpicorSyncResult]:
        """
        Get recent Epicor sync results within specified hours

        Args:
            db: Database session
            user_id: Optional user ID to filter by
            hours: Number of hours to look back
            limit: Maximum number of results to return

        Returns:
            List of recent EpicorSyncResult objects
        """
        from datetime import timedelta
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        query = select(EpicorSyncResult).where(
            EpicorSyncResult.synced_at >= cutoff_time
        )

        if user_id:
            query = query.where(EpicorSyncResult.user_id == user_id)

        query = query.order_by(desc(EpicorSyncResult.synced_at)).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def delete_sync_result(
        db: AsyncSession,
        sync_result_id: int
    ) -> bool:
        """
        Delete an Epicor sync result

        Args:
            db: Database session
            sync_result_id: ID of the sync result to delete

        Returns:
            True if deleted, False if not found
        """
        sync_result = await EpicorSyncResultService.get_sync_result_by_id(
            db, sync_result_id
        )
        if not sync_result:
            return False

        await db.delete(sync_result)
        await db.flush()
        return True

    @staticmethod
    async def get_sync_statistics(
        db: AsyncSession,
        user_id: Optional[int] = None
    ) -> dict:
        """
        Get aggregated statistics for Epicor syncs

        Args:
            db: Database session
            user_id: Optional user ID to filter by

        Returns:
            Dictionary with sync statistics
        """
        from sqlalchemy import func

        query = select(
            func.count(EpicorSyncResult.id).label('total_syncs'),
            func.sum(
                func.cast(
                    EpicorSyncResult.sync_status == 'success',
                    db.bind.dialect.name == 'postgresql' and db.bind.dialect.name or None
                )
            ).label('successful_syncs'),
            func.sum(
                func.cast(
                    EpicorSyncResult.sync_status == 'failed',
                    db.bind.dialect.name == 'postgresql' and db.bind.dialect.name or None
                )
            ).label('failed_syncs'),
            func.sum(EpicorSyncResult.total_products).label('total_products_processed'),
            func.sum(EpicorSyncResult.successful_updates).label('total_successful_updates'),
            func.sum(EpicorSyncResult.failed_updates).label('total_failed_updates'),
        )

        if user_id:
            query = query.where(EpicorSyncResult.user_id == user_id)

        result = await db.execute(query)
        row = result.first()

        return {
            'total_syncs': row.total_syncs or 0,
            'successful_syncs': row.successful_syncs or 0,
            'failed_syncs': row.failed_syncs or 0,
            'total_products_processed': row.total_products_processed or 0,
            'total_successful_updates': row.total_successful_updates or 0,
            'total_failed_updates': row.total_failed_updates or 0,
        }
