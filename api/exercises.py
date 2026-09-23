"""Wger exercises API."""

from __future__ import annotations

from ..const import (
    DEFAULT_LOG_LIMIT,
    ENDPOINT_EXERCISE_INFO,
)
from .client import WgerApiClient


class WgerExercisesApi:
    """API methods related to Wger exercises."""

    def __init__(
        self,
        client: WgerApiClient,
    ) -> None:
        """Initialize the exercises API."""

        self._client = client

        self._exercise_cache: dict[int, dict] = {}

    async def get_exercises(
        self,
        limit: int = DEFAULT_LOG_LIMIT,
    ) -> dict:
        """Get exercises."""

        return await self._client._get(
            f"{ENDPOINT_EXERCISE_INFO}"
            f"?limit={limit}"
        )

    async def get_exercise(
        self,
        exercise_id: int,
    ) -> dict | None:
        """Get a single exercise by ID."""

        exercise = self._exercise_cache.get(
            exercise_id
        )

        if exercise is not None:
            return exercise

        data = await self._client._get(
            f"{ENDPOINT_EXERCISE_INFO}"
            f"{exercise_id}/"
        )

        return data

    async def build_exercise_cache(
        self,
    ) -> None:
        """Build the exercise cache."""

        data = await self.get_exercises()

        self._exercise_cache = {
            exercise["id"]: exercise
            for exercise in data.get(
                "results",
                []
            )
            if "id" in exercise
        }

    def get_cached_exercise(
        self,
        exercise_id: int,
    ) -> dict | None:
        """Return an exercise from the cache."""

        return self._exercise_cache.get(
            exercise_id
        )

    def clear_exercise_cache(self) -> None:
        """Clear the exercise cache."""

        self._exercise_cache.clear()