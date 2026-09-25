"""Wger API package."""

from __future__ import annotations

from aiohttp import ClientSession

from .analytics import WgerAnalyticsApi
from .client import (
    WgerApiClient,
    WgerApiError,
    WgerAuthenticationError,
    WgerConnectionError,
)
from .comparison import WgerComparisonApi
from .exercises import WgerExercisesApi
from .measurements import WgerMeasurementsApi
from .nutrition import WgerNutritionApi
from .profile import WgerProfileApi
from .routines import WgerRoutinesApi
from .workouts import WgerWorkoutsApi


class WgerApi:
    """High-level Wger API."""

    def __init__(
        self,
        session: ClientSession,
        base_url: str,
        token: str,
    ) -> None:
        """Initialize the Wger API."""

        self._client = WgerApiClient(
            session=session,
            base_url=base_url,
            token=token,
        )

        self.comparison = WgerComparisonApi(self._client)

        self.profile = WgerProfileApi(
            self._client
        )

        self.workouts = WgerWorkoutsApi(
            self._client
        )

        self.routines = WgerRoutinesApi(
            self._client
        )

        self.exercises = WgerExercisesApi(
            self._client
        )

        self.measurements = WgerMeasurementsApi(
            self._client
        )

        self.nutrition = WgerNutritionApi(
            self._client
        )

        self.analytics = WgerAnalyticsApi(
            self._client
        )

    async def validate_connection(self) -> bool:
        """Validate the Wger API connection."""

        try:
            await self.profile.get_profile()

            return True

        except WgerApiError:
            return False


__all__ = [
    "WgerApi",
    "WgerApiClient",
    "WgerApiError",
    "WgerAuthenticationError",
    "WgerConnectionError",
]