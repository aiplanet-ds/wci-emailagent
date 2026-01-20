"""
Settings API Router
Handles system settings endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Literal
from sqlalchemy.ext.asyncio import AsyncSession

from database.config import get_db
from database.services.settings_service import (
    SettingsService,
    MIN_POLLING_INTERVAL_SECONDS,
    MAX_POLLING_INTERVAL_SECONDS,
    VALID_UNITS,
)
from services.delta_service import delta_service


router = APIRouter(prefix="/api/settings", tags=["settings"])


# Type for time units
TimeUnit = Literal["seconds", "minutes", "hours", "days"]


# Pydantic models
class PollingIntervalRequest(BaseModel):
    value: int = Field(
        ...,
        gt=0,
        description="Polling interval value (must be positive)"
    )
    unit: TimeUnit = Field(
        default="minutes",
        description="Time unit: seconds, minutes, hours, or days"
    )


class PollingIntervalResponse(BaseModel):
    value: int
    unit: str
    total_seconds: int
    next_run: str | None = None
    is_running: bool


class SettingsResponse(BaseModel):
    polling_interval: dict
    polling_status: dict


# Helper function
def get_user_from_session(request: Request) -> str:
    """Get authenticated user email from session"""
    user_email = request.session.get("user_email") or request.session.get("user")
    if not user_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_email


@router.get("", response_model=SettingsResponse)
async def get_settings(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get all system settings"""
    # Verify user is authenticated
    get_user_from_session(request)

    polling_interval = await SettingsService.get_polling_interval(db)
    polling_status = delta_service.get_polling_status()

    return SettingsResponse(
        polling_interval=polling_interval,
        polling_status=polling_status
    )


@router.get("/polling-interval", response_model=PollingIntervalResponse)
async def get_polling_interval(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get the current email polling interval"""
    # Verify user is authenticated
    get_user_from_session(request)

    polling_interval = await SettingsService.get_polling_interval(db)
    status = delta_service.get_polling_status()

    return PollingIntervalResponse(
        value=polling_interval["value"],
        unit=polling_interval["unit"],
        total_seconds=polling_interval["total_seconds"],
        next_run=status.get("next_run"),
        is_running=status.get("is_running", False)
    )


@router.put("/polling-interval", response_model=PollingIntervalResponse)
async def update_polling_interval(
    request: Request,
    body: PollingIntervalRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Update the email polling interval.

    The change takes effect immediately - the scheduler is rescheduled
    with the new interval.

    Supported units: seconds, minutes, hours, days
    Minimum: 10 seconds
    Maximum: 7 days
    """
    # Verify user is authenticated
    get_user_from_session(request)

    try:
        # Save to database (validates and converts to seconds internally)
        result = await SettingsService.set_polling_interval(db, body.value, body.unit)
        await db.commit()

        # Update the running scheduler with total seconds
        delta_service.update_polling_interval(result["total_seconds"])

        status = delta_service.get_polling_status()

        return PollingIntervalResponse(
            value=result["value"],
            unit=result["unit"],
            total_seconds=result["total_seconds"],
            next_run=status.get("next_run"),
            is_running=status.get("is_running", False)
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update polling interval: {str(e)}"
        )
