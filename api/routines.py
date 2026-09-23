"""Wger routines API."""

from __future__ import annotations

from datetime import datetime

from ..const import ENDPOINT_ROUTINES
from .client import WgerApiClient


class WgerRoutinesApi:
    """API methods related to Wger routines."""

    def __init__(
        self,
        client: WgerApiClient,
    ) -> None:
        """Initialize the routines API."""

        self._client = client

    async def get_routines(self) -> dict:
        """Get all routines."""

        return await self._client._get(
            ENDPOINT_ROUTINES
        )

    async def get_routine(
        self,
        routine_id: int,
    ) -> dict:
        """Get a routine by ID."""

        return await self._client._get(
            f"{ENDPOINT_ROUTINES}"
            f"{routine_id}/"
        )

    async def get_routine_structure(
        self,
        routine_id: int,
    ) -> dict:
        """Get the complete structure of a routine."""

        return await self._client._get(
            f"{ENDPOINT_ROUTINES}"
            f"{routine_id}/structure/"
        )

    async def get_routine_stats(
        self,
        routine_id: int,
    ) -> dict:
        """Get statistics for a routine."""

        return await self._client._get(
            f"{ENDPOINT_ROUTINES}"
            f"{routine_id}/stats/"
        )

    async def get_routine_logs(
        self,
        routine_id: int,
    ) -> dict:
        """Get workout logs associated with a routine."""

        return await self._client._get(
            f"{ENDPOINT_ROUTINES}"
            f"{routine_id}/logs/"
        )

    async def get_routine_date_sequence_display(
        self,
        routine_id: int,
    ) -> dict:
        """Get the routine date sequence for display."""

        return await self._client._get(
            f"{ENDPOINT_ROUTINES}"
            f"{routine_id}/date-sequence-display/"
        )

    async def get_routine_date_sequence_gym(
        self,
        routine_id: int,
    ) -> dict:
        """Get the routine date sequence for gym use."""

        return await self._client._get(
            f"{ENDPOINT_ROUTINES}"
            f"{routine_id}/date-sequence-gym/"
        )

    async def get_current_week_stats(
        self,
        routine_id: int,
    ) -> dict:
        """Get statistics for the current ISO week."""

        stats = await self.get_routine_stats(
            routine_id
        )

        current_week = str(
            datetime.now().isocalendar().week
        )

        weekly_stats = {
            "week": current_week,
            "volume": None,
            "sets": None,
            "intensity": None,
        }

        for metric in (
            "volume",
            "sets",
            "intensity",
        ):
            metric_data = stats.get(
                metric,
                {}
            )

            weekly_data = metric_data.get(
                "weekly",
                {}
            )

            current_week_data = weekly_data.get(
                current_week
            )

            if current_week_data is not None:
                weekly_stats[metric] = (
                    current_week_data.get(
                        "total"
                    )
                )

        return weekly_stats

    async def get_current_week_volume(
        self,
        routine_id: int,
    ) -> float | None:
        """Get the training volume for the current week."""

        stats = await self.get_current_week_stats(
            routine_id
        )

        value = stats.get(
            "volume"
        )

        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def get_current_week_sets(
        self,
        routine_id: int,
    ) -> float | None:
        """Get the number of sets for the current week."""

        stats = await self.get_current_week_stats(
            routine_id
        )

        value = stats.get(
            "sets"
        )

        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def get_current_week_intensity(
        self,
        routine_id: int,
    ) -> float | None:
        """Get the average intensity for the current week."""

        stats = await self.get_current_week_stats(
            routine_id
        )

        value = stats.get(
            "intensity"
        )

        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None