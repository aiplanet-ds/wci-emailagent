"""
Dashboard API Router
Handles dashboard statistics endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from database.config import get_db
from database.services.user_service import UserService
from database.services.dashboard_service import DashboardService


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# Pydantic models
class DashboardStatsResponse(BaseModel):
    total_emails: int
    processed_count: int
    unprocessed_count: int
    needs_followup_count: int
    price_change_count: int
    non_price_change_count: int
    epicor_sync_success: int
    epicor_sync_failed: int
    epicor_sync_pending: int
    processing_rate: float
    unprocessed_percentage: float
    followup_percentage: float
    epicor_success_rate: float
    emails_with_missing_fields: int
    recent_activity: list


# Helper function
def get_user_from_session(request: Request) -> str:
    """Get authenticated user email from session"""
    user_email = request.session.get("user_email") or request.session.get("user")
    if not user_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_email


@router.get("/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    request: Request,
    db: AsyncSession = Depends(get_db),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Get dashboard statistics for the authenticated user

    Query params:
    - start_date: Optional ISO format start date (e.g., 2025-01-01T00:00:00Z)
    - end_date: Optional ISO format end date (e.g., 2025-01-31T23:59:59Z)

    Returns comprehensive statistics including:
    - Email counts (total, processed, unprocessed)
    - Follow-up needs
    - Price change classification
    - Epicor sync results
    - Processing rates and percentages
    - Recent activity
    """
    user_email = get_user_from_session(request)

    try:
        # Get user from database
        user = await UserService.get_user_by_email(db, user_email)
        if not user:
            raise HTTPException(status_code=404, detail=f"User not found: {user_email}")

        # Parse date strings to datetime objects
        start_dt = None
        end_dt = None

        if start_date:
            try:
                # Handle ISO format with Z or timezone
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                # Strip timezone for PostgreSQL TIMESTAMP WITHOUT TIME ZONE
                if start_dt.tzinfo:
                    start_dt = start_dt.replace(tzinfo=None)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid start_date format: {str(e)}")

        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                if end_dt.tzinfo:
                    end_dt = end_dt.replace(tzinfo=None)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid end_date format: {str(e)}")

        # Get stats from database
        stats = await DashboardService.get_user_stats(
            db=db,
            user_id=user.id,
            start_date=start_dt,
            end_date=end_dt
        )

        return DashboardStatsResponse(**stats)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve dashboard statistics: {str(e)}"
        )
