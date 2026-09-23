"""Data coordinator for Wger."""

from __future__ import annotations

import asyncio
import logging
from copy import deepcopy
from datetime import date, datetime, timedelta

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
        )

        # Calculate workout metrics from the already
        # fetched latest session.
        last_workout_duration = None
        days_since_last_workout = None

        if latest_session:
            start = latest_session.get(
                "datetime_start"
            )

            end = latest_session.get(
                "datetime_end"
            )

            if start and end:
                try:
                    start_dt = datetime.fromisoformat(
                        start.replace(
                            "Z",
                            "+00:00",
                        )
                    )

                    end_dt = datetime.fromisoformat(
                        end.replace(
                            "Z",
                            "+00:00",
                        )
                    )

                    last_workout_duration = round(
                        (
                            end_dt - start_dt
                        ).total_seconds()
                        / 60,
                        1,
                    )

                except ValueError:
                    _LOGGER.warning(
                        "Invalid workout session dates: %s - %s",
                        start,
                        end,
                    )

            if start:
                try:
                    workout_dt = datetime.fromisoformat(
                        start.replace(
                            "Z",
                            "+00:00",
                        )
                    )

                    now = datetime.now().astimezone()

                    days_since_last_workout = (
                        now.date()
                        - workout_dt.date()
                    ).days

                except ValueError:
                    _LOGGER.warning(
                        "Invalid workout session date: %s",
                        start,
                    )

        # Find the currently active routine based on
        # its date range.
        active_routine = None
        today = date.today()

        for routine in routines.get(
            "results",
            [],
        ):
            if routine.get(
                "is_template",
                False,
            ):
                continue

            if routine.get(
                "is_public",
                False,
            ):
                continue

            start = routine.get(
                "start"
            )

            end = routine.get(
                "end"
            )

            if not start or not end:
                continue

            try:
                start_date = date.fromisoformat(
                    start
                )

                end_date = date.fromisoformat(
                    end
                )

            except ValueError:
                _LOGGER.warning(
                    "Invalid routine dates: %s - %s",
                    start,
                    end,
                )

                continue

            if (
                start_date
                <= today
                <= end_date
            ):
                active_routine = routine
                break

        # Get statistics and workout sequence
        # for the active routine.
        routine_stats = None
        weekly_repetitions = None
        todays_workout = None
        next_workout = None

        if active_routine:
            routine_id = active_routine[
                "id"
            ]

            (
                routine_stats,
                weekly_repetitions,
                todays_workout,
                next_workout,
            ) = await asyncio.gather(
                self.api.routines.get_current_week_stats(
                    routine_id
                ),
                self.api.workouts.get_repetitions_this_week(
                    routine_id
                ),
                self.api.routines.get_todays_workout(
                    routine_id
                ),
                self.api.routines.get_next_workout(
                    routine_id
                ),
            )

            _LOGGER.debug(
                "Active Wger routine: %s",
                active_routine,
            )

            _LOGGER.debug(
                "Current week routine stats: %s",
                routine_stats,
            )

            _LOGGER.debug(
                "Current week repetitions: %s",
                weekly_repetitions,
            )

            _LOGGER.debug(
                "Today's Wger workout: %s",
                todays_workout,
            )

            _LOGGER.debug(
                "Next Wger workout: %s",
                next_workout,
            )

        # Resolve exercise IDs to detailed exercise
        # information.
        exercise_ids: set[int] = set()

        for workout in (
            todays_workout,
            next_workout,
        ):
            if not workout:
                continue

            for slot in workout.get(
                "slots",
                [],
            ):
                for exercise_id in slot.get(
                    "exercises",
                    [],
                ):
                    try:
                        exercise_ids.add(
                            int(exercise_id)
                        )

                    except (
                        TypeError,
                        ValueError,
                    ):
                        _LOGGER.warning(
                            "Invalid Wger exercise ID: %s",
                            exercise_id,
                        )

        exercise_details: dict[
            int,
            dict,
        ] = {}

        if exercise_ids:
            exercise_details_results = (
                await asyncio.gather(
                    *(
                        self.api.exercises.get_exercise_details(
                            exercise_id
                        )
                        for exercise_id in exercise_ids
                    )
                )
            )

            for (
                exercise_id,
                details,
            ) in zip(
                exercise_ids,
                exercise_details_results,
                strict=False,
            ):
                if details:
                    exercise_details[
                        exercise_id
                    ] = details

        _LOGGER.debug(
            "Resolved Wger exercise details: %s",
            exercise_details,
        )

        # Enrich today's workout with exercise details.
        if todays_workout:
            todays_workout = deepcopy(
                todays_workout
            )

            todays_workout[
                "exercise_details"
            ] = {
                str(exercise_id): details
                for (
                    exercise_id,
                    details,
                ) in exercise_details.items()
            }

        # Enrich next workout with exercise details.
        if next_workout:
            next_workout = deepcopy(
                next_workout
            )

            next_workout[
                "exercise_details"
            ] = {
                str(exercise_id): details
                for (
                    exercise_id,
                    details,
                ) in exercise_details.items()
            }

        # Calculate today's planned workout metrics.
        todays_exercises = 0
        todays_sets = 0
        todays_repetitions = 0

        if todays_workout:
            for slot in todays_workout.get(
                "slots",
                [],
            ):
                exercise_ids = slot.get(
                    "exercises",
                    []
                )

                todays_exercises += len(
                    exercise_ids
                )

                for workout_set in slot.get(
                    "sets",
                    [],
                ):
                    sets = workout_set.get(
                        "sets"
                    )

                    repetitions = workout_set.get(
                        "repetitions"
                    )

                    try:
                        sets_value = int(
                            sets or 0
                        )

                    except (
                        TypeError,
                        ValueError,
                    ):
                        sets_value = 0

                    try:
                        repetitions_value = int(
                            repetitions or 0
                        )

                    except (
                        TypeError,
                        ValueError,
                    ):
                        repetitions_value = 0

                    todays_sets += sets_value

                    todays_repetitions += (
                        sets_value
                        * repetitions_value
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
            "todays_workout": todays_workout,
            "next_workout": next_workout,
            "todays_exercises": todays_exercises,
            "todays_sets": todays_sets,
            "todays_repetitions": todays_repetitions,
        }

    @property
    def current_weight(
        self,
    ) -> float | None:
        if self.data is None:
            return None

        return self.data.get(
            "current_weight"
        )

    @property
    def trainings_this_week(
        self,
    ) -> int:
        if self.data is None:
            return 0

        return self.data.get(
            "trainings_this_week",
            0,
        )

    @property
    def latest_session(
        self,
    ) -> dict | None:
        if self.data is None:
            return None

        return self.data.get(
            "latest_session"
        )

    @property
    def last_workout_duration(
        self,
    ) -> float | None:
        if self.data is None:
            return None

        return self.data.get(
            "last_workout_duration"
        )

    @property
    def days_since_last_workout(
        self,
    ) -> int | None:
        if self.data is None:
            return None

        return self.data.get(
            "days_since_last_workout"
        )

    @property
    def active_routine(
        self,
    ) -> dict | None:
        if self.data is None:
            return None

        return self.data.get(
            "active_routine"
        )

    @property
    def weekly_volume(
        self,
    ) -> float | None:
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
    def weekly_sets(
        self,
    ) -> float | None:
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
    def weekly_intensity(
        self,
    ) -> float | None:
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
    def weekly_repetitions(
        self,
    ) -> float | None:
        if self.data is None:
            return None

        return self.data.get(
            "weekly_repetitions"
        )

    @property
    def todays_workout(
        self,
    ) -> dict | None:
        if self.data is None:
            return None

        return self.data.get(
            "todays_workout"
        )

    @property
    def next_workout(
        self,
    ) -> dict | None:
        if self.data is None:
            return None

        return self.data.get(
            "next_workout"
        )

    @property
    def todays_exercises(
        self,
    ) -> int:
        if self.data is None:
            return 0

        return self.data.get(
            "todays_exercises",
            0,
        )

    @property
    def todays_sets(
        self,
    ) -> int:
        if self.data is None:
            return 0

        return self.data.get(
            "todays_sets",
            0,
        )

    @property
    def todays_repetitions(
        self,
    ) -> int:
        if self.data is None:
            return 0

        return self.data.get(
            "todays_repetitions",
            0,
        )