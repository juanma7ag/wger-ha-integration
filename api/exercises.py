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

        if data:
            self._exercise_cache[
                exercise_id
            ] = data

        return data

    async def get_exercise_name(
        self,
        exercise_id: int,
    ) -> str | None:
        """Get the preferred name of an exercise."""

        exercise = await self.get_exercise(
            exercise_id
        )

        if not exercise:
            return None

        translations = exercise.get(
            "translations",
            []
        )

        # Prefer Spanish.
        for translation in translations:
            if translation.get(
                "language"
            ) == 4:
                name = translation.get(
                    "name"
                )

                if name:
                    return name

        # Fallback to English.
        for translation in translations:
            if translation.get(
                "language"
            ) == 2:
                name = translation.get(
                    "name"
                )

                if name:
                    return name

        # Final fallback: first available
        # translation with a valid name.
        for translation in translations:
            name = translation.get(
                "name"
            )

            if name:
                return name

        return None

    async def get_exercise_details(
        self,
        exercise_id: int,
    ) -> dict | None:
        """Get useful display details for an exercise."""

        exercise = await self.get_exercise(
            exercise_id
        )

        if not exercise:
            return None

        name = await self.get_exercise_name(
            exercise_id
        )

        category = exercise.get(
            "category",
            {}
        )

        muscles = exercise.get(
            "muscles",
            []
        )

        muscles_secondary = exercise.get(
            "muscles_secondary",
            []
        )

        equipment = exercise.get(
            "equipment",
            []
        )

        images = exercise.get(
            "images",
            []
        )

        main_image = None

        for image in images:
            if image.get(
                "is_main"
            ):
                main_image = image.get(
                    "image"
                )
                break

        # Fallback to the first image if
        # no image is explicitly marked as main.
        if (
            main_image is None
            and images
        ):
            main_image = images[0].get(
                "image"
            )

        return {
            "name": name,
            "category": category.get(
                "name"
            ),
            "muscles": [
                muscle.get("name")
                for muscle in muscles
                if muscle.get("name")
            ],
            "muscles_secondary": [
                muscle.get("name")
                for muscle in muscles_secondary
                if muscle.get("name")
            ],
            "equipment": [
                item.get("name")
                for item in equipment
                if item.get("name")
            ],
            "image": main_image,
        }

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

    def clear_exercise_cache(
        self,
    ) -> None:
        """Clear the exercise cache."""

        self._exercise_cache.clear()