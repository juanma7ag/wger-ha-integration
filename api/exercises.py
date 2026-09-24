"""Wger exercises API."""

from __future__ import annotations

from urllib.parse import urlparse

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

    def _normalize_image_url(
        self,
        url: str | None,
    ) -> str | None:
        """Normalize Wger image URLs to the configured public server."""

        if not url:
            return None

        parsed = urlparse(url)

        if parsed.path.startswith("/static/"):
            return (
                f"{self._client._base_url}"
                f"{parsed.path}"
                f"{('?' + parsed.query) if parsed.query else ''}"
            )

        return url

    @staticmethod
    def _normalize_muscle(
        muscle,
    ) -> dict | None:
        """Normalize a Wger muscle entry."""

        if isinstance(
            muscle,
            str,
        ):
            if not muscle.strip():
                return None

            return {
                "id": None,
                "name": muscle.strip(),
                "name_en": None,
                "is_front": None,
                "image_url_main": None,
                "image_url_secondary": None,
            }

        if not isinstance(
            muscle,
            dict,
        ):
            return None

        # Wger normally returns the muscle directly as an object.
        # Keep support for nested representations as well.
        muscle_data = muscle

        nested_muscle = muscle.get(
            "muscle"
        )

        if isinstance(
            nested_muscle,
            dict,
        ):
            muscle_data = nested_muscle

        name = (
            muscle_data.get(
                "name"
            )
            or muscle.get(
                "name"
            )
            or muscle_data.get(
                "name_en"
            )
            or muscle.get(
                "name_en"
            )
        )

        if not name:
            return None

        return {
            "id": (
                muscle_data.get(
                    "id"
                )
                or muscle.get(
                    "id"
                )
            ),
            "name": name,
            "name_en": (
                muscle_data.get(
                    "name_en"
                )
                or muscle.get(
                    "name_en"
                )
            ),
            "is_front": (
                muscle_data.get(
                    "is_front"
                )
                if "is_front" in muscle_data
                else muscle.get(
                    "is_front"
                )
            ),
            "image_url_main": (
                muscle_data.get(
                    "image_url_main"
                )
                or muscle.get(
                    "image_url_main"
                )
            ),
            "image_url_secondary": (
                muscle_data.get(
                    "image_url_secondary"
                )
                or muscle.get(
                    "image_url_secondary"
                )
            ),
        }

    def _normalize_muscles(
        self,
        muscles,
    ) -> list[dict]:
        """Normalize a collection of Wger muscles."""

        if not isinstance(
            muscles,
            list,
        ):
            return []

        normalized = []

        for muscle in muscles:
            normalized_muscle = (
                self._normalize_muscle(
                    muscle
                )
            )

            if not normalized_muscle:
                continue

            normalized_muscle[
                "image_url_main"
            ] = self._normalize_image_url(
                normalized_muscle.get(
                    "image_url_main"
                )
            )

            normalized_muscle[
                "image_url_secondary"
            ] = self._normalize_image_url(
                normalized_muscle.get(
                    "image_url_secondary"
                )
            )

            normalized.append(
                normalized_muscle
            )

        return normalized

    @staticmethod
    def _get_muscle_names(
        muscles: list[dict],
    ) -> list[str]:
        """Extract muscle names from normalized muscles."""

        names = []

        for muscle in muscles:
            name = muscle.get(
                "name"
            )

            if not name:
                continue

            if name not in names:
                names.append(
                    name
                )

        return names

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

        muscles = self._normalize_muscles(
            exercise.get(
                "muscles",
                []
            )
        )

        muscles_secondary = self._normalize_muscles(
            exercise.get(
                "muscles_secondary",
                []
            )
        )

        equipment = exercise.get(
            "equipment",
            []
        )

        images = exercise.get(
            "images",
            []
        )

        translations = exercise.get(
            "translations",
            []
        )

        # Prefer the Spanish translation for the
        # exercise description and notes.
        spanish_translation = None

        for translation in translations:
            if translation.get(
                "language"
            ) == 4:
                spanish_translation = translation
                break

        # Fallback to English if Spanish is not available.
        if spanish_translation is None:
            for translation in translations:
                if translation.get(
                    "language"
                ) == 2:
                    spanish_translation = translation
                    break

        # Final fallback to the first translation
        # containing useful descriptive information.
        if spanish_translation is None:
            for translation in translations:
                if (
                    translation.get(
                        "description"
                    )
                    or translation.get(
                        "notes"
                    )
                ):
                    spanish_translation = translation
                    break

        main_image = None
        thumbnail_small = None
        thumbnail_medium = None

        all_images = []

        for image in images:
            image_data = {
                "id": image.get(
                    "id"
                ),
                "image": image.get(
                    "image"
                ),
                "thumbnail_small": image.get(
                    "thumbnails",
                    {}
                ).get(
                    "small"
                ),
                "thumbnail_medium": image.get(
                    "thumbnails",
                    {}
                ).get(
                    "medium"
                ),
                "is_main": image.get(
                    "is_main",
                    False
                ),
                "style": image.get(
                    "style"
                ),
                "license_author": image.get(
                    "license_author"
                ),
                "is_ai_generated": image.get(
                    "is_ai_generated",
                    False
                ),
            }

            all_images.append(
                image_data
            )

            if image.get(
                "is_main"
            ):
                main_image = image.get(
                    "image"
                )

                thumbnail_small = image.get(
                    "thumbnails",
                    {}
                ).get(
                    "small"
                )

                thumbnail_medium = image.get(
                    "thumbnails",
                    {}
                ).get(
                    "medium"
                )

        # Fallback to the first image if no image
        # is explicitly marked as main.
        if (
            main_image is None
            and images
        ):
            first_image = images[0]

            main_image = first_image.get(
                "image"
            )

            thumbnail_small = first_image.get(
                "thumbnails",
                {}
            ).get(
                "small"
            )

            thumbnail_medium = first_image.get(
                "thumbnails",
                {}
            ).get(
                "medium"
            )

        videos = exercise.get(
            "videos",
            []
        )

        return {
            "id": exercise.get(
                "id"
            ),
            "uuid": exercise.get(
                "uuid"
            ),
            "name": name,
            "category": {
                "id": category.get(
                    "id"
                ),
                "name": category.get(
                    "name"
                ),
            },
            "muscles": muscles,
            "muscles_secondary": muscles_secondary,
            "muscle_names": self._get_muscle_names(
                muscles
            ),
            "muscle_names_secondary": (
                self._get_muscle_names(
                    muscles_secondary
                )
            ),
            "equipment": [
                {
                    "id": item.get(
                        "id"
                    ),
                    "name": item.get(
                        "name"
                    ),
                }
                for item in equipment
                if isinstance(
                    item,
                    dict,
                )
                and item.get(
                    "name"
                )
            ],
            "description": (
                spanish_translation.get(
                    "description_source"
                )
                if spanish_translation
                else None
            ),
            "notes": [
                note.get(
                    "comment"
                )
                for note in (
                    spanish_translation.get(
                        "notes",
                        []
                    )
                    if spanish_translation
                    else []
                )
                if isinstance(
                    note,
                    dict,
                )
                and note.get(
                    "comment"
                )
            ],
            "image": main_image,
            "thumbnail_small": thumbnail_small,
            "thumbnail_medium": thumbnail_medium,
            "images": all_images,
            "videos": videos,
            "variation_group": exercise.get(
                "variation_group"
            ),
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