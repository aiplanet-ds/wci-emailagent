"""Settings service for database operations"""

from datetime import datetime
from typing import Optional, Any, Literal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import SystemSettings


# Constants for polling interval
POLLING_INTERVAL_KEY = "polling_interval"
DEFAULT_POLLING_INTERVAL = 60  # Default: 1 minute in seconds
DEFAULT_POLLING_UNIT = "minutes"
MIN_POLLING_INTERVAL_SECONDS = 10  # Minimum: 10 seconds
MAX_POLLING_INTERVAL_SECONDS = 7 * 24 * 60 * 60  # Maximum: 7 days in seconds

# Valid time units
TimeUnit = Literal["seconds", "minutes", "hours", "days"]
VALID_UNITS = ("seconds", "minutes", "hours", "days")

# Conversion factors to seconds
UNIT_TO_SECONDS = {
    "seconds": 1,
    "minutes": 60,
    "hours": 3600,
    "days": 86400,
}


def convert_to_seconds(value: int, unit: TimeUnit) -> int:
    """Convert a value in the given unit to seconds."""
    return value * UNIT_TO_SECONDS[unit]


def convert_from_seconds(seconds: int, unit: TimeUnit) -> int:
    """Convert seconds to the given unit."""
    return seconds // UNIT_TO_SECONDS[unit]


class SettingsService:
    """Service for managing system settings in the database"""

    @staticmethod
    async def get_setting(db: AsyncSession, key: str) -> Optional[Any]:
        """Get a setting by key, returns the value or None if not found"""
        result = await db.execute(
            select(SystemSettings).where(SystemSettings.key == key)
        )
        setting = result.scalar_one_or_none()
        return setting.value if setting else None

    @staticmethod
    async def set_setting(db: AsyncSession, key: str, value: Any) -> SystemSettings:
        """Set or update a setting"""
        result = await db.execute(
            select(SystemSettings).where(SystemSettings.key == key)
        )
        setting = result.scalar_one_or_none()

        if setting:
            setting.value = value
            setting.updated_at = datetime.utcnow()
        else:
            setting = SystemSettings(key=key, value=value)
            db.add(setting)

        await db.flush()
        await db.refresh(setting)
        return setting

    @staticmethod
    async def get_polling_interval(db: AsyncSession) -> dict:
        """
        Get the polling interval with its unit.

        Returns:
            dict with keys: value, unit, total_seconds
        """
        value = await SettingsService.get_setting(db, POLLING_INTERVAL_KEY)
        if value is None:
            return {
                "value": 1,
                "unit": DEFAULT_POLLING_UNIT,
                "total_seconds": DEFAULT_POLLING_INTERVAL,
            }

        # Handle legacy format (just seconds)
        if isinstance(value, dict):
            if "unit" in value:
                # New format with unit
                return {
                    "value": value.get("value", 1),
                    "unit": value.get("unit", DEFAULT_POLLING_UNIT),
                    "total_seconds": value.get("total_seconds", DEFAULT_POLLING_INTERVAL),
                }
            else:
                # Old format with just seconds
                seconds = value.get("seconds", DEFAULT_POLLING_INTERVAL)
                return {
                    "value": seconds,
                    "unit": "seconds",
                    "total_seconds": seconds,
                }

        # Direct int value (legacy)
        return {
            "value": int(value),
            "unit": "seconds",
            "total_seconds": int(value),
        }

    @staticmethod
    async def get_polling_interval_seconds(db: AsyncSession) -> int:
        """Get the polling interval in seconds only (for scheduler)."""
        interval = await SettingsService.get_polling_interval(db)
        return interval["total_seconds"]

    @staticmethod
    async def set_polling_interval(
        db: AsyncSession,
        value: int,
        unit: TimeUnit = "seconds"
    ) -> dict:
        """
        Set the polling interval with a specific time unit.

        Args:
            db: Database session
            value: Polling interval value
            unit: Time unit (seconds, minutes, hours, days)

        Returns:
            dict with keys: value, unit, total_seconds

        Raises:
            ValueError: If the resulting interval is outside valid range or invalid unit
        """
        if unit not in VALID_UNITS:
            raise ValueError(f"Invalid unit. Must be one of: {', '.join(VALID_UNITS)}")

        if value <= 0:
            raise ValueError("Value must be a positive integer")

        total_seconds = convert_to_seconds(value, unit)

        if total_seconds < MIN_POLLING_INTERVAL_SECONDS:
            raise ValueError(
                f"Polling interval must be at least {MIN_POLLING_INTERVAL_SECONDS} seconds"
            )

        if total_seconds > MAX_POLLING_INTERVAL_SECONDS:
            raise ValueError(
                f"Polling interval cannot exceed 7 days ({MAX_POLLING_INTERVAL_SECONDS} seconds)"
            )

        setting_value = {
            "value": value,
            "unit": unit,
            "total_seconds": total_seconds,
        }

        await SettingsService.set_setting(db, POLLING_INTERVAL_KEY, setting_value)
        return setting_value

    @staticmethod
    async def get_all_settings(db: AsyncSession) -> dict:
        """Get all settings as a dictionary"""
        result = await db.execute(select(SystemSettings))
        settings = result.scalars().all()
        return {s.key: s.value for s in settings}
