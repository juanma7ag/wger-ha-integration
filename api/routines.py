"""Wger routines API."""

from __future__ import annotations

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