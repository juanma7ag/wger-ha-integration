"""Wger nutrition API."""

from __future__ import annotations

from .client import WgerApiClient


class WgerNutritionApi:
    """API methods related to Wger nutrition."""

    def __init__(
        self,
        client: WgerApiClient,
    ) -> None:
        """Initialize the nutrition API."""

        self._client = client