from django import template
from datetime import timedelta

register = template.Library()


@register.filter
def format_timedelta(value):
    """
    Format a timedelta object into a human-readable string.
    Returns strings like "2 days, 3 hours" or "5 hours, 30 minutes" or "45 minutes"
    """
    if not isinstance(value, timedelta):
        return value
    
    total_seconds = int(value.total_seconds())
    
    if total_seconds < 0:
        return "0 minutes"
    
    days = total_seconds // 86400
    remaining_seconds = total_seconds % 86400
    hours = remaining_seconds // 3600
    remaining_seconds %= 3600
    minutes = remaining_seconds // 60
    
    parts = []
    
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0 and days == 0:  # Only show minutes if less than a day
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    
    if not parts:
        return "Less than a minute"
    
    # Return the first two most significant units
    return ", ".join(parts[:2])
