"""Data coordinator for Wger."""

from __future__ import annotations

import asyncio
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)

from .api import WgerApi
from .const import DOMAIN


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
            logger=__import__(
                "logging"
            ).getLogger(__name__),
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

        return {
            "profile": profile,
            "routines": routines,
            "latest_session": latest_session,
            "weights": weights,
            "measurements": measurements,
            "trainings_this_week": trainings_this_week,
            "current_weight": current_weight,
            "last_workout_duration": last_workout_duration,
            "days_since_last_workout": days_since_last_workout,
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
    def last_workout_duration(self) -> float | None:
        """Return the duration of the latest workout."""

        if self.data is None:
            return None

        return self.data.get(
            "last_workout_duration"
        )

    @property
    def days_since_last_workout(self) -> int | None:
        """Return the number of days since the latest workout."""

        if self.data is None:
            return None

        return self.data.get(
            "days_since_last_workout"
        )