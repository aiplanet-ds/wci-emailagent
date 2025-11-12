"""Dashboard service for database operations - replaces JSON-based dashboard statistics"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import select, func, and_, or_, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database.models import Email, EmailState, EpicorSyncResult, User


class DashboardService:
    """Service for generating dashboard statistics from the database"""

    @staticmethod
    async def get_user_stats(
        db: AsyncSession,
        user_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive dashboard statistics for a user

        Args:
            db: Database session
            user_id: User ID
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering

        Returns:
            Dictionary with dashboard statistics matching DashboardStatsResponse format
        """
        # Build date filter conditions
        date_conditions = [Email.user_id == user_id]

        if start_date:
            date_conditions.append(Email.received_at >= start_date)

        if end_date:
            date_conditions.append(Email.received_at <= end_date)

        # Single optimized aggregation query for most statistics
        stats_query = select(
            func.count().label('total_emails'),
            func.count().filter(EmailState.processed == True).label('processed_count'),
            func.count().filter(EmailState.processed == False).label('unprocessed_count'),
            func.count().filter(
                or_(
                    EmailState.needs_info == True,
                    func.jsonb_array_length(EmailState.selected_missing_fields) > 0
                )
            ).label('needs_followup_count'),
            func.count().filter(EmailState.is_price_change == True).label('price_change_count'),
            func.count().filter(
                or_(
                    EmailState.is_price_change == False,
                    EmailState.is_price_change == None
                )
            ).label('non_price_change_count'),
            func.count().filter(
                func.jsonb_array_length(EmailState.selected_missing_fields) > 0
            ).label('emails_with_missing_fields')
        ).select_from(Email).join(
            EmailState,
            Email.message_id == EmailState.message_id
        ).where(
            and_(*date_conditions)
        )

        result = await db.execute(stats_query)
        stats_row = result.one()

        # Extract base statistics
        total_emails = stats_row.total_emails or 0
        processed_count = stats_row.processed_count or 0
        unprocessed_count = stats_row.unprocessed_count or 0
        needs_followup_count = stats_row.needs_followup_count or 0
        price_change_count = stats_row.price_change_count or 0
        non_price_change_count = stats_row.non_price_change_count or 0
        emails_with_missing_fields = stats_row.emails_with_missing_fields or 0

        # Query Epicor sync statistics
        epicor_stats = await DashboardService._get_epicor_stats(
            db, user_id, date_conditions
        )

        # Query recent activity
        recent_activity = await DashboardService._get_recent_activity(
            db, user_id, date_conditions
        )

        # Calculate percentages and rates
        processing_rate = (processed_count / total_emails * 100) if total_emails > 0 else 0.0
        unprocessed_percentage = (unprocessed_count / total_emails * 100) if total_emails > 0 else 0.0
        followup_percentage = (needs_followup_count / total_emails * 100) if total_emails > 0 else 0.0

        total_syncs = epicor_stats['success'] + epicor_stats['failed']
        epicor_success_rate = (epicor_stats['success'] / total_syncs * 100) if total_syncs > 0 else 0.0

        # Return statistics in DashboardStatsResponse format
        return {
            "total_emails": total_emails,
            "processed_count": processed_count,
            "unprocessed_count": unprocessed_count,
            "needs_followup_count": needs_followup_count,
            "price_change_count": price_change_count,
            "non_price_change_count": non_price_change_count,
            "epicor_sync_success": epicor_stats['success'],
            "epicor_sync_failed": epicor_stats['failed'],
            "epicor_sync_pending": epicor_stats['pending'],
            "processing_rate": round(processing_rate, 2),
            "unprocessed_percentage": round(unprocessed_percentage, 2),
            "followup_percentage": round(followup_percentage, 2),
            "epicor_success_rate": round(epicor_success_rate, 2),
            "emails_with_missing_fields": emails_with_missing_fields,
            "recent_activity": recent_activity
        }

    @staticmethod
    async def _get_epicor_stats(
        db: AsyncSession,
        user_id: int,
        date_conditions: List
    ) -> Dict[str, int]:
        """
        Get Epicor sync statistics

        Returns dict with keys: success, failed, pending
        """
        # Query for successful and failed syncs
        sync_stats_query = select(
            func.count().filter(EpicorSyncResult.sync_status == 'success').label('success_count'),
            func.count().filter(EpicorSyncResult.sync_status == 'failed').label('failed_count')
        ).select_from(Email).join(
            EpicorSyncResult,
            Email.id == EpicorSyncResult.email_id,
            isouter=False
        ).where(
            and_(*date_conditions)
        )

        result = await db.execute(sync_stats_query)
        sync_row = result.one()

        # Query for pending syncs (processed but no sync result)
        pending_query = select(
            func.count()
        ).select_from(Email).join(
            EmailState,
            Email.message_id == EmailState.message_id
        ).outerjoin(
            EpicorSyncResult,
            Email.id == EpicorSyncResult.email_id
        ).where(
            and_(
                *date_conditions,
                EmailState.processed == True,
                EpicorSyncResult.id == None
            )
        )

        pending_result = await db.execute(pending_query)
        pending_count = pending_result.scalar() or 0

        return {
            'success': sync_row.success_count or 0,
            'failed': sync_row.failed_count or 0,
            'pending': pending_count
        }

    @staticmethod
    async def _get_recent_activity(
        db: AsyncSession,
        user_id: int,
        date_conditions: List,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get recent activity (processed emails)

        Returns list of recent activity items with message_id, subject, processed_at, processed_by, action
        """
        activity_query = select(
            EmailState.message_id,
            Email.subject,
            EmailState.processed_at,
            User.email.label('processed_by'),
            func.cast('processed', type_=String).label('action')
        ).select_from(EmailState).join(
            Email,
            EmailState.email_id == Email.id
        ).outerjoin(
            User,
            EmailState.processed_by_id == User.id
        ).where(
            and_(
                *date_conditions,
                EmailState.processed_at != None
            )
        ).order_by(
            EmailState.processed_at.desc()
        ).limit(limit)

        result = await db.execute(activity_query)
        activities = result.all()

        # Format activity items
        recent_activity = []
        for activity in activities:
            recent_activity.append({
                "message_id": activity.message_id,
                "subject": activity.subject,
                "processed_at": activity.processed_at.isoformat() if activity.processed_at else None,
                "processed_by": activity.processed_by,
                "action": activity.action
            })

        return recent_activity
