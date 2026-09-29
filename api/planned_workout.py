"""Match the latest finished workout to its routine plan without guessing links."""

import asyncio
from datetime import datetime
from urllib.parse import urlencode

from .client import WgerApiError, WgerAuthenticationError
from .comparison import _complete_page, _datetime, _number


def select_plan(session: dict, logs: list[dict], sequence: list[dict], now: datetime) -> tuple[dict | None, str]:
    """Prefer a recorded iteration; otherwise require an exact local date/day."""
    candidates = [item for item in sequence if (item.get("day") or {}).get("id") == session["day"]]
    iterations = {log["iteration"] for log in logs if log.get("iteration") is not None}
    if len(iterations) > 1:
        return None, "ambiguous_plan"
    if iterations:
        candidates = [item for item in candidates if item.get("iteration") in iterations]
    else:
        start = _datetime(session.get("datetime_start"))
        local_date = start.astimezone(now.tzinfo).date().isoformat() if start else None
        candidates = [item for item in candidates if item.get("date") == local_date]
    if len(candidates) != 1:
        return None, "ambiguous_plan" if candidates else "no_plan"
    return candidates[0], "ready"


def _measurement(log: dict, key: str, unit: dict) -> dict:
    """Actual and saved target use the same unit in a workout log."""
    actual, target = _number(log.get(key)), _number(log.get(f"{key}_target"))
    return {
        "actual": actual,
        "target": target,
        "delta": round(actual - target, 2) if actual is not None and target is not None and unit else None,
        "unit": unit.get("name"),
    }


def build_planned_workout(session: dict, plan: dict, logs: list[dict], repetition_units: list[dict],
                          weight_units: list[dict], now: datetime) -> dict:
    """Count linked series per slot entry; extra sets cannot fill another entry."""
    reps = {unit["id"]: unit for unit in repetition_units}
    weights = {unit["id"]: unit for unit in weight_units}
    entries = {}
    for slot in plan.get("slots", []):
        for group in slot.get("sets", []):
            entry_id, exercise = group.get("slot_entry_id"), group.get("exercise")
            count = group.get("sets")
            maximum = group.get("max_sets")
            if (entry_id is None or exercise is None or not isinstance(count, int) or count < 0
                    or (maximum is not None and (not isinstance(maximum, int) or maximum < count))):
                return {"status": "invalid_plan"}
            row = entries.setdefault(entry_id, {
                "slot_entry_id": entry_id, "exercise_id": exercise,
                "planned_sets": 0, "max_sets": 0, "plan": [], "logs": [],
            })
            if row["exercise_id"] != exercise:
                return {"status": "invalid_plan"}
            row["planned_sets"] += count
            row["max_sets"] += maximum if maximum is not None else count
            row["plan"].append({
                "sets": count, "max_sets": maximum,
                "repetitions": _number(group.get("repetitions")),
                "max_repetitions": _number(group.get("max_repetitions")),
                "repetitions_unit": reps.get(group.get("repetitions_unit"), {}).get("name"),
                "weight": _number(group.get("weight")),
                "max_weight": _number(group.get("max_weight")),
                "weight_unit": weights.get(group.get("weight_unit"), {}).get("name"),
            })
    if not entries:
        return {"status": "no_plan"}

    unlinked = []
    seen = set()
    for log in logs:
        if log.get("id") is not None:
            if log["id"] in seen:
                continue
            seen.add(log["id"])
        row = entries.get(log.get("slot_entry"))
        compatible = (
            row is not None and row["exercise_id"] == log.get("exercise")
            and log.get("session") == session["id"]
            and log.get("routine") in (None, session["routine"])
            and log.get("iteration") in (None, plan.get("iteration"))
        )
        item = {
            "log_id": log.get("id"), "exercise_id": log.get("exercise"),
            "slot_entry_id": log.get("slot_entry"),
            "repetitions": _measurement(log, "repetitions", reps.get(log.get("repetitions_unit"), {})),
            "weight": _measurement(log, "weight", weights.get(log.get("weight_unit"), {})),
        }
        if compatible:
            row["logs"].append(item)
        else:
            unlinked.append(item)

    for row in entries.values():
        completed = len(row["logs"])
        uncertain = any(
            item["exercise_id"] in (None, row["exercise_id"])
            or item["slot_entry_id"] == row["slot_entry_id"]
            for item in unlinked
        )
        row["recorded_sets"] = completed
        row["covered_sets"] = min(completed, row["planned_sets"])
        row["extra_sets"] = max(0, completed - row["max_sets"])
        row["unverified_sets"] = max(0, row["planned_sets"] - completed) if uncertain else 0
        row["missing_sets"] = None if uncertain else max(0, row["planned_sets"] - completed)
        row["status"] = (
            "uncertain" if uncertain else "extra" if row["extra_sets"] else
            "covered" if completed >= row["planned_sets"] else "partial" if completed else "no_records"
        )
    rows = list(entries.values())
    planned = sum(row["planned_sets"] for row in rows)
    covered = sum(row["covered_sets"] for row in rows)
    start = _datetime(session["datetime_start"])
    return {
        "status": "partial_links" if unlinked else "ready",
        "session_id": session["id"], "routine_id": session["routine"], "day_id": session["day"],
        "date_start": start.astimezone(now.tzinfo).isoformat() if start else None,
        "workout_name": (plan.get("day") or {}).get("name"), "iteration": plan.get("iteration"),
        "planned_sets": planned, "max_sets": sum(row["max_sets"] for row in rows),
        "covered_sets": covered, "recorded_sets": sum(row["recorded_sets"] for row in rows),
        "extra_sets": sum(row["extra_sets"] for row in rows),
        "missing_sets": sum(row["missing_sets"] for row in rows) if not unlinked else None,
        "progress": round(covered / planned * 100, 1) if planned and not unlinked else None,
        "unlinked_count": len(unlinked), "unlinked": unlinked, "exercises": rows,
        "plan_source": "current_routine", "target_source": "saved_log_targets",
    }


class WgerPlannedWorkoutApi:
    """Retrieve the plan and logs of the latest finished session."""

    def __init__(self, client, exercises):
        self._client = client
        self._exercises = exercises

    async def get_planned_workout(self, now: datetime) -> dict:
        params = {"datetime_end__lte": now.isoformat(), "ordering": "-datetime_start", "limit": 1}
        data = await self._client._get(f"/workoutsession/?{urlencode(params)}")
        if not data.get("results"):
            return {"status": "no_sessions"}
        session = data["results"][0]
        start, end = _datetime(session.get("datetime_start")), _datetime(session.get("datetime_end"))
        if not start or not end or not start <= end <= now:
            return {"status": "invalid_session"}
        if session.get("routine") is None or session.get("day") is None:
            return {"status": "no_day"}
        logs_data, sequence, reps_data, weights_data = await asyncio.gather(
            self._client._get(f"/workoutlog/?{urlencode({'session': session['id'], 'limit': 999})}"),
            self._client._get(f"/routine/{session['routine']}/date-sequence-display/"),
            self._client._get("/setting-repetitionunit/?limit=999"),
            self._client._get("/setting-weightunit/?limit=999"),
        )
        if not all(_complete_page(page) for page in (logs_data, reps_data, weights_data)):
            return {"status": "incomplete_history"}
        logs = logs_data.get("results", [])
        if not isinstance(sequence, list):
            return {"status": "invalid_plan"}
        plan, status = select_plan(session, logs, sequence, now)
        if plan is None:
            return {"status": status}
        result = build_planned_workout(session, plan, logs, reps_data.get("results", []),
                                       weights_data.get("results", []), now)
        ids = {row["exercise_id"] for row in result.get("exercises", [])}
        ids.update(row["exercise_id"] for row in result.get("unlinked", []) if row["exercise_id"] is not None)
        names = dict(zip(ids, await asyncio.gather(*(self._name(id) for id in ids))))
        for row in result.get("exercises", []) + result.get("unlinked", []):
            row["name"] = names.get(row["exercise_id"]) or f"Ejercicio {row['exercise_id']}"
        return result

    async def _name(self, exercise_id):
        try:
            return await self._exercises.get_exercise_name(exercise_id)
        except WgerAuthenticationError:
            raise
        except (WgerApiError, TimeoutError):
            return None
