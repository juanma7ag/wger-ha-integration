"""Compare completed sessions belonging to the same routine day."""

import asyncio
from datetime import datetime
import math
from urllib.parse import urlencode

from .client import WgerApiClient

def _number(value) -> float | None:
    """Accept only finite, non-negative measurements."""
    try:
        result = float(value)
    except (ValueError, TypeError):
        return None
    return result if math.isfinite(result) and result >= 0 else None


def _datetime(value) -> datetime | None:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError, TypeError):
        return None
    return result if result.tzinfo is not None else None


def _complete_page(data: dict) -> bool:
    return not data.get("next") and data.get("count", len(data.get("results", []))) <= len(data.get("results", []))


def _summary(session: dict, logs: list[dict], repetitions: dict, weights: dict, now: datetime) -> dict:
    """Summarize a full session without mixing incompatible units."""
    start = _datetime(session.get("datetime_start"))
    end = _datetime(session.get("datetime_end"))
    duration = (end - start).total_seconds() / 60 if start and end and end >= start else None
    reps_total = volume = 0.0
    reps_valid = volume_valid = True
    for log in logs:
        unit = repetitions.get(log.get("repetitions_unit"), {})
        reps = _number(log.get("repetitions"))
        if unit.get("unit_type") != "REPETITIONS" or reps is None:
            reps_valid = volume_valid = False
            continue
        reps_total += reps
        weight = _number(log.get("weight"))
        name = weights.get(log.get("weight_unit"), {}).get("name", "").strip().lower()
        factor = {"kg": 1, "lb": 0.45359237}.get(name)
        if factor is None or weight is None:
            volume_valid = False
        else:
            volume += reps * weight * factor

    return {
        "session_id": session["id"],
        "routine_id": session.get("routine"),
        "day_id": session.get("day"),
        "date_start": start.astimezone(now.tzinfo).isoformat() if start else None,
        "date_end": end.astimezone(now.tzinfo).isoformat() if end else None,
        "sets": len(logs),
        "repetitions": reps_total if reps_valid else None,
        "volume": volume if volume_valid else None,
        "duration": duration,
        "exercise_ids": sorted({log["exercise"] for log in logs if log.get("exercise") is not None}),
    }


def build_comparison(current: dict, previous: dict, current_logs: list[dict], previous_logs: list[dict],
                     repetition_units: list[dict], weight_units: list[dict], now: datetime) -> dict:
    """Build values and signed differences; missing measurements stay unknown."""
    repetitions = {unit["id"]: unit for unit in repetition_units}
    weights = {unit["id"]: unit for unit in weight_units}
    latest = _summary(current, current_logs, repetitions, weights, now)
    earlier = _summary(previous, previous_logs, repetitions, weights, now)
    metrics = {}
    for key, unit in (("sets", "series"), ("repetitions", "reps"), ("volume", "kg·reps"), ("duration", "min")):
        value, reference = latest[key], earlier[key]
        comparable = value is not None and reference is not None
        delta = value - reference if comparable else None
        percentage = delta / reference * 100 if comparable and reference != 0 else None
        metrics[key] = {
            "current": round(value, 1) if value is not None else None,
            "previous": round(reference, 1) if reference is not None else None,
            "delta": round(delta, 1) if delta is not None else None,
            "percent": round(percentage, 1) if percentage is not None else None,
            "unit": unit,
        }
    # Totals can change when the routine is edited or exercises are skipped.
    return {
        "status": "ready",
        "current": latest,
        "previous": earlier,
        "metrics": metrics,
        "exercise_selection_changed": latest["exercise_ids"] != earlier["exercise_ids"],
        "repetitions_comparable": metrics["repetitions"]["delta"] is not None,
        "volume_comparable": metrics["volume"]["delta"] is not None,
    }


class WgerComparisonApi:
    """Load two matching completed sessions and their exact logs."""

    def __init__(self, client: WgerApiClient) -> None:
        self._client = client

    async def get_comparison(self, now: datetime) -> dict:
        """Select the latest finished session and its previous routine/day match."""
        params = {"datetime_end__lte": now.isoformat(), "ordering": "-datetime_start", "limit": 1}
        latest_data = await self._client._get(f"/workoutsession/?{urlencode(params)}")
        if not latest_data.get("results"):
            return {"status": "no_sessions"}
        current = latest_data["results"][0]
        start = _datetime(current.get("datetime_start"))
        end = _datetime(current.get("datetime_end"))
        if not start or not end or not start <= end <= now:
            return {"status": "invalid_session"}
        if current.get("routine") is None or current.get("day") is None:
            return {"status": "no_day", "session_id": current.get("id")}

        params.update({"routine": current["routine"], "day": current["day"],
                       "datetime_start__lt": current["datetime_start"]})
        previous_data = await self._client._get(f"/workoutsession/?{urlencode(params)}")
        if not previous_data.get("results"):
            return {"status": "no_previous", "session_id": current.get("id")}
        previous = previous_data["results"][0]
        previous_start = _datetime(previous.get("datetime_start"))
        previous_end = _datetime(previous.get("datetime_end"))
        if (previous.get("routine") != current["routine"] or previous.get("day") != current["day"]
                or not previous_start or not previous_end or not previous_start <= previous_end <= now
                or previous_start >= start):
            return {"status": "invalid_session"}

        current_data, previous_logs_data, reps_data, weights_data = await asyncio.gather(
            self._client._get(f"/workoutlog/?{urlencode({'session': current['id'], 'limit': 999})}"),
            self._client._get(f"/workoutlog/?{urlencode({'session': previous['id'], 'limit': 999})}"),
            self._client._get("/setting-repetitionunit/?limit=999"),
            self._client._get("/setting-weightunit/?limit=999"),
        )
        if not all(_complete_page(data) for data in (current_data, previous_logs_data, reps_data, weights_data)):
            return {"status": "incomplete_history"}
        current_logs = current_data.get("results", [])
        previous_logs = previous_logs_data.get("results", [])
        if not current_logs or not previous_logs:
            return {"status": "no_logs"}
        return build_comparison(current, previous, current_logs, previous_logs,
                                reps_data.get("results", []), weights_data.get("results", []), now)
