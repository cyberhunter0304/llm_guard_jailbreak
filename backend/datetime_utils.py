"""
DateTime Utility Module
Provides timezone-aware datetime functions for consistent timestamps
"""
from datetime import datetime, timezone


def get_current_timestamp() -> str:
    """
    Get current timestamp in ISO format with timezone
    
    Returns local timezone-aware timestamp in ISO 8601 format
    Example: "2024-01-29T15:30:45.123456+05:30"
    """
    return datetime.now(timezone.utc).astimezone().isoformat()


def get_utc_timestamp() -> str:
    """
    Get current UTC timestamp in ISO format
    
    Returns UTC timezone-aware timestamp in ISO 8601 format
    Example: "2024-01-29T10:00:45.123456+00:00"
    """
    return datetime.now(timezone.utc).isoformat()


def format_timestamp(dt: datetime) -> str:
    """
    Format a datetime object to ISO string
    
    Args:
        dt: datetime object (timezone-aware or naive)
    
    Returns:
        ISO 8601 formatted string
    """
    if dt.tzinfo is None:
        # If naive datetime, assume it's local time
        dt = dt.astimezone()
    return dt.isoformat()


# Use this function throughout the application for consistency
# It returns local timezone time, which syncs with the user's system clock
now = get_current_timestamp