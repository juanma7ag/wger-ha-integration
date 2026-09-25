"""Weekly training goal calculations."""

from datetime import datetime, timedelta


def week_bounds(now: datetime) -> tuple[datetime, datetime]:
    """Return Monday boundaries in the caller's local timezone."""
    start = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return start, start + timedelta(days=7)


def count_completed_sessions(sessions: list[dict], now: datetime) -> int:
    """Count completed sessions by their local start date, once per ID."""
    week_start, week_end = week_bounds(now)
    completed = set()
    for session in sessions:
        try:
            start = datetime.fromisoformat(session["datetime_start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(session["datetime_end"].replace("Z", "+00:00"))
        except (KeyError, AttributeError, TypeError, ValueError):
            continue
        if start.tzinfo is None or end.tzinfo is None:
            continue
        if session.get("id") and week_start <= start < week_end and start <= end <= now:
            completed.add(session["id"])
    return len(completed)


def build_weekly_goal(completed: int, target: int, now: datetime) -> dict:
    """Build one consistent snapshot for entities and the dashboard card."""
    start, end = week_bounds(now)
    return {
        "completed": completed,
        "target": target,
        "remaining": max(0, target - completed),
        "progress": min(100, round(completed / target * 100, 1)),
        "achieved": completed >= target,
        "week_start": start.date().isoformat(),
        "week_end": (end - timedelta(days=1)).date().isoformat(),
    }
