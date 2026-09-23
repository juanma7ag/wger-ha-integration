"""Wger measurements API."""

from __future__ import annotations

from ..const import (
    DEFAULT_PAGE_LIMIT,
    ENDPOINT_MEASUREMENTS,
    ENDPOINT_WEIGHT_ENTRIES,
)
from .client import WgerApiClient


class WgerMeasurementsApi:
    """API methods related to Wger measurements."""

    def __init__(
        self,
        client: WgerApiClient,
    ) -> None:
        """Initialize the measurements API."""

        self._client = client

    async def get_measurements(
        self,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> dict:
        """Get body measurements."""

        return await self._client._get(
            f"{ENDPOINT_MEASUREMENTS}"
            f"?limit={limit}"
        )

    async def get_weight_entries(
        self,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> dict:
        """Get weight history."""

        return await self._client._get(
            f"{ENDPOINT_WEIGHT_ENTRIES}"
            f"?ordering=-date"
            f"&limit={limit}"
        )

    async def get_current_weight(
        self,
    ) -> float | None:
        """Get the latest body weight."""

        data = await self.get_weight_entries(
            limit=1
        )

        results = data.get(
            "results",
            []
        )

        if not results:
            return None

        weight = results[0].get(
            "weight"
        )

        if weight is None:
            return None

        try:
            return float(weight)
        except (TypeError, ValueError):
            return None