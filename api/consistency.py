"""Weekly consistency derived from completed Wger sessions."""

from datetime import datetime, timedelta

from .weekly_goal import week_bounds

HISTORY_WEEKS = 52
DISPLAY_WEEKS = 12


def build_consistency(sessions: list[dict], target: int, now: datetime) -> dict:
    """Measure recent streaks against the current goal, allowing the open week."""
    current_start, _ = week_bounds(now)
    first_start = current_start - timedelta(weeks=HISTORY_WEEKS - 1)
    counts = {}
    seen = set()
    for session in sessions:
        session_id = session.get("id")
        if not session_id or session_id in seen:
            continue
        try:
            start = datetime.fromisoformat(session["datetime_start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(session["datetime_end"].replace("Z", "+00:00"))
        except (KeyError, AttributeError, TypeError, ValueError):
            continue
        if start.tzinfo is None or end.tzinfo is None or not start <= end <= now:
            continue
        start = start.astimezone(now.tzinfo)
        if start < first_start:
            continue
        seen.add(session_id)
        key = week_bounds(start)[0].date().isoformat()
        counts[key] = counts.get(key, 0) + 1

    weeks = []
    for index in range(HISTORY_WEEKS):
        start = first_start + timedelta(weeks=index)
        key = start.date().isoformat()
        completed = counts.get(key, 0)
        achieved = completed >= target
        is_current = start == current_start
        weeks.append({
            "week_start": key,
            "week_end": (start + timedelta(days=6)).date().isoformat(),
            "completed": completed,
            "target": target,
            "achieved": achieved,
            "is_current": is_current,
            "status": "achieved" if achieved else "in_progress" if is_current else "missed",
        })

    # An unfinished current week has not yet broken the preceding streak.
    candidates = weeks if weeks[-1]["achieved"] else weeks[:-1]
    current_streak = 0
    for week in reversed(candidates):
        if not week["achieved"]:
            break
        current_streak += 1

    best_streak = running = 0
    for week in weeks:
        running = running + 1 if week["achieved"] else 0
        best_streak = max(best_streak, running)

    return {
        "current_streak": current_streak,
        "best_streak": best_streak,
        "streak_at_least": current_streak > 0 and current_streak == len(candidates),
        "target": target,
        "current_week_achieved": weeks[-1]["achieved"],
        "current_week_completed": weeks[-1]["completed"],
        "remaining": max(0, target - weeks[-1]["completed"]),
        "history_weeks": HISTORY_WEEKS,
        "history_start": weeks[0]["week_start"],
        "history_end": weeks[-1]["week_end"],
        "weeks": weeks[-DISPLAY_WEEKS:],
        "history_complete": True,
    }
