"""Wger profile API."""

from __future__ import annotations

from ..const import ENDPOINT_PROFILE
from .client import WgerApiClient


class WgerProfileApi:
    """API methods related to the Wger user profile."""

    def __init__(
        self,
        client: WgerApiClient,
    ) -> None:
        """Initialize the profile API."""

        self._client = client

    async def get_profile(self) -> dict:
        """Get the current user's profile."""

        return await self._client._get(
            ENDPOINT_PROFILE
        )