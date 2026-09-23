"""Wger analytics API."""

from __future__ import annotations

from .client import WgerApiClient


class WgerAnalyticsApi:
    """API methods related to Wger training analytics."""

    def __init__(
        self,
        client: WgerApiClient,
    ) -> None:
        """Initialize the analytics API."""

        self._client = client