"""Data coordinator for Wger."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)

from .api import WgerApi
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class WgerDataUpdateCoordinator(
    DataUpdateCoordinator[dict]
):
    """Coordinate Wger data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: WgerApi,
    ) -> None:
        """Initialize the coordinator."""

        self.api = api

        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                minutes=30
            ),
        )

    async def _async_update_data(self) -> dict:
        """Fetch data from Wger."""

        (
            profile,
            routines,
            latest_session,
            weights,
            measurements,
            trainings_this_week,
            current_weight,
            last_workout_duration,
            days_since_last_workout,
        ) = await asyncio.gather(
            self.api.profile.get_profile(),
            self.api.routines.get_routines(),
            self.api.workouts.get_latest_session(),
            self.api.measurements.get_weight_entries(
                limit=50
            ),
            self.api.measurements.get_measurements(
                limit=100
            ),
            self.api.workouts.get_trainings_this_week(),
            self.api.measurements.get_current_weight(),
            self.api.workouts.get_last_workout_duration(),
            self.api.workouts.get_days_since_last_workout(),
        )

        # Find the currently active routine.
        active_routine = None

        for routine in routines.get(
            "results",
            [],
        ):
            if routine.get(
                "is_template",
                False,
            ):
                continue

            if not routine.get(
                "is_public",
                False,
            ):
                active_routine = routine
                break

        # Get statistics for the active routine.
        routine_stats = None
        weekly_repetitions = None

        if active_routine:
            routine_id = active_routine["id"]

            routine_stats = (
                await self.api.routines.get_current_week_stats(
                    routine_id
                )
            )

            weekly_repetitions = (
                await self.api.workouts.get_repetitions_this_week(
                    routine_id
                )
            )

        return {
            "profile": profile,
            "routines": routines,
            "active_routine": active_routine,
            "latest_session": latest_session,
            "weights": weights,
            "measurements": measurements,
            "trainings_this_week": trainings_this_week,
            "current_weight": current_weight,
            "last_workout_duration": last_workout_duration,
            "days_since_last_workout": days_since_last_workout,
            "routine_stats": routine_stats,
            "weekly_repetitions": weekly_repetitions,
        }

    @property
    def current_weight(self) -> float | None:
        """Return current body weight."""

        if self.data is None:
            return None

        return self.data.get(
            "current_weight"
        )

    @property
    def trainings_this_week(self) -> int:
        """Return the number of trainings this week."""

        if self.data is None:
            return 0

        return self.data.get(
            "trainings_this_week",
            0,
        )

    @property
    def latest_session(self) -> dict | None:
        """Return the latest workout session."""

        if self.data is None:
            return None

        return self.data.get(
            "latest_session"
        )

    @property
    def last_workout_duration(
        self,
    ) -> float | None:
        """Return the duration of the latest workout."""

        if self.data is None:
            return None

        return self.data.get(
            "last_workout_duration"
        )

    @property
    def days_since_last_workout(
        self,
    ) -> int | None:
        """Return the number of days since the latest workout."""

        if self.data is None:
            return None

        return self.data.get(
            "days_since_last_workout"
        )

    @property
    def active_routine(self) -> dict | None:
        """Return the active routine."""

        if self.data is None:
            return None

        return self.data.get(
            "active_routine"
        )

    @property
    def weekly_volume(self) -> float | None:
        """Return the current week's training volume."""

        if self.data is None:
            return None

        stats = self.data.get(
            "routine_stats"
        )

        if not stats:
            return None

        return stats.get(
            "volume"
        )

    @property
    def weekly_sets(self) -> float | None:
        """Return the current week's number of sets."""

        if self.data is None:
            return None

        stats = self.data.get(
            "routine_stats"
        )

        if not stats:
            return None

        return stats.get(
            "sets"
        )

    @property
    def weekly_intensity(self) -> float | None:
        """Return the current week's average intensity."""

        if self.data is None:
            return None

        stats = self.data.get(
            "routine_stats"
        )

        if not stats:
            return None

        return stats.get(
            "intensity"
        )

    @property
    def weekly_repetitions(self) -> float | None:
        """Return the current week's repetitions."""

        if self.data is None:
            return None

        return self.data.get(
            "weekly_repetitions"
        )