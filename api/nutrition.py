"""Wger nutrition API."""

from __future__ import annotations

import asyncio
from datetime import date

from ..const import (
    ENDPOINT_NUTRITION_DIARY,
    ENDPOINT_NUTRITION_PLANS,
)
from .client import WgerApiClient

NUTRIENT_KEYS = (
    "energy",
    "protein",
    "carbohydrates",
    "fat",
    "fiber",
)


def _to_float(value) -> float | None:
    """Convert an API number (often a decimal string) to float."""

    if value is None or value == "":
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def active_plan(
    plans: list[dict],
    today: date,
) -> dict | None:
    """Return the first plan whose start/end window covers today."""

    today_s = today.isoformat()

    for plan in plans:
        if not isinstance(plan, dict):
            continue

        start = str(plan.get("start") or "")[:10]
        end = str(plan.get("end") or "")[:10]

        if start and start <= today_s and (not end or end >= today_s):
            return plan

    return None


class WgerNutritionApi:
    """API methods related to Wger nutrition."""

    def __init__(
        self,
        client: WgerApiClient,
    ) -> None:
        """Initialize the nutrition API."""

        self._client = client

    async def get_plans(
        self,
        limit: int = 50,
    ) -> list[dict]:
        """Get the user's nutrition plans."""

        data = await self._client._get(
            f"{ENDPOINT_NUTRITION_PLANS}"
            f"?limit={limit}"
        )

        return data.get("results", []) if isinstance(data, dict) else data

    async def get_plan_goals(
        self,
        today: date,
    ) -> dict:
        """Get the goals of the plan active today (None when no plan)."""

        plan = active_plan(
            await self.get_plans(),
            today,
        )

        if plan is None:
            return {
                "plan_id": None,
                "goal_energy": None,
                "goal_protein": None,
            }

        return {
            "plan_id": plan.get("id"),
            "goal_energy": _to_float(plan.get("goal_energy")),
            "goal_protein": _to_float(plan.get("goal_protein")),
        }

    async def get_diary_entries(
        self,
        day: date,
        limit: int = 200,
    ) -> list[dict]:
        """Get nutrition diary entries logged on a day."""

        data = await self._client._get(
            f"{ENDPOINT_NUTRITION_DIARY}"
            f"?datetime__date={day.isoformat()}"
            f"&limit={limit}"
        )

        return data.get("results", []) if isinstance(data, dict) else data

    async def get_diary_entry_values(
        self,
        entry_id,
    ) -> dict:
        """Get the nutritional values of one diary entry."""

        return await self._client._get(
            f"{ENDPOINT_NUTRITION_DIARY}"
            f"{entry_id}/nutritional_values/"
        )

    async def get_daily_totals(
        self,
        day: date,
    ) -> dict:
        """Sum the nutritional values logged on a day.

        An empty diary sums to 0. Any failed request raises, so the
        caller can report the totals as unavailable instead of 0.
        """

        entries = [
            entry
            for entry in await self.get_diary_entries(day)
            if isinstance(entry, dict) and entry.get("id") is not None
        ]

        values = await asyncio.gather(
            *(
                self.get_diary_entry_values(entry["id"])
                for entry in entries
            )
        )

        totals = dict.fromkeys(NUTRIENT_KEYS, 0.0)

        for value in values:
            for key in NUTRIENT_KEYS:
                totals[key] += _to_float(value.get(key)) or 0.0

        result = {key: round(total, 1) for key, total in totals.items()}
        result["entry_count"] = len(entries)

        return result
