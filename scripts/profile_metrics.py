"""Pure helpers for calculating GitHub contribution streaks."""

from datetime import date, timedelta
from typing import Any


def calculate_streaks(items: list[dict[str, Any]], today: date) -> tuple[int, int]:
    """Return the current and longest consecutive contribution-day streaks."""
    active_dates = {
        date.fromisoformat(item["date"])
        for item in items
        if item["contributionCount"] > 0
    }
    if not active_dates:
        return 0, 0

    best = current = 0
    cursor = min(active_dates)
    while cursor <= max(active_dates):
        if cursor in active_dates:
            current += 1
            best = max(best, current)
        else:
            current = 0
        cursor += timedelta(days=1)

    # A current streak can include today or yesterday; do not surface an old one.
    anchor = today if today in active_dates else today - timedelta(days=1)
    current_streak = 0
    cursor = anchor
    while cursor in active_dates:
        current_streak += 1
        cursor -= timedelta(days=1)

    return current_streak, best
