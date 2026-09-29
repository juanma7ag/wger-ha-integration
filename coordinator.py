"""Data coordinator for Wger."""

from __future__ import annotations

import asyncio
import logging
from copy import deepcopy
from datetime import date, datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from homeassistant.util import dt as dt_util

from .api import WgerApi, WgerApiError, WgerAuthenticationError

from .const import DOMAIN, CONF_WEEKLY_GOAL, DEFAULT_WEEKLY_GOAL
from .api.weekly_goal import build_weekly_goal

_LOGGER = logging.getLogger(__name__)


def _matching_workout_day(
    sequence_entries: list[dict],
    day_id: int,
    workout_date: str | None,
) -> dict | None:
    """Find the recorded session day, preferring its scheduled date."""
    matches = [
        entry for entry in sequence_entries
        if isinstance(entry.get("day"), dict)
        and entry["day"].get("id") == day_id
    ]
    return next(
        (entry for entry in matches if entry.get("date") == workout_date),
        None,
    ) or (
        matches[0] if matches else None
    )


class WgerDataUpdateCoordinator(
    DataUpdateCoordinator[dict]
):
    """Coordinate Wger data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: WgerApi,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""

        self.api = api
        self.entry = entry

        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(
                minutes=30
            ),
        )

    async def _async_update_data(self) -> dict:
        """Translate API failures into Home Assistant lifecycle errors."""
        try:
            return await self._async_fetch_data()
        except WgerAuthenticationError as err:
            raise ConfigEntryAuthFailed("Wger authentication failed") from err
        except WgerApiError as err:
            raise UpdateFailed("Unable to fetch Wger data") from err

    async def _async_fetch_comparison(self, now: datetime) -> dict:
        """Keep optional comparison failures separate from the existing sensors."""
        try:
            return await self.api.comparison.get_comparison(now)
        except WgerAuthenticationError:
            raise
        except (WgerApiError, TimeoutError) as err:
            _LOGGER.warning("Unable to compare Wger sessions: %s", err)
            return {"status": "unavailable"}

    async def _async_fetch_planned_workout(self, now: datetime) -> dict:
        """Keep optional plan matching failures separate from other sensors."""
        try:
            return await self.api.planned_workout.get_planned_workout(now)
        except WgerAuthenticationError:
            raise
        except (WgerApiError, TimeoutError) as err:
            _LOGGER.warning("Unable to match Wger session to plan: %s", err)
            return {"status": "unavailable"}

    async def _async_fetch_data(self) -> dict:
        """Fetch data from Wger."""

        now = dt_util.now()
        weekly_target = self.entry.options.get(CONF_WEEKLY_GOAL, DEFAULT_WEEKLY_GOAL)

        (
            profile,
            routines,
            latest_session,
            weights,
            measurements,
            trainings_this_week,
            current_weight,
            last_workout,
            workout_progress,
            weekly_consistency,
            workout_comparison,
            planned_workout,
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
            self.api.workouts.get_trainings_this_week(now=now),
            self.api.measurements.get_current_weight(),
            self.api.workouts.get_last_workout_analysis(),
            self.api.workouts.get_workout_progress(),
            self.api.workouts.get_weekly_consistency(weekly_target, now),
            self._async_fetch_comparison(now),
            self._async_fetch_planned_workout(now),
        )

        if workout_comparison.get("status") == "ready":
            current = workout_comparison["current"]
            workout_comparison["routine_name"] = next(
                (routine.get("name") for routine in routines.get("results", [])
                 if routine.get("id") == current["routine_id"]),
                None,
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

        # Enrich the last workout with routine and
        # workout sequence information.
        if last_workout:
            last_workout = deepcopy(
                last_workout
            )

            routine_id = last_workout.get(
                "routine_id"
            )

            workout_date = last_workout.get(
                "date"
            )
            day_id = last_workout.get("day_id")

            # Resolve the routine name from the routines
            # already fetched by the coordinator.
            if routine_id is not None:
                for routine in routines.get(
                    "results",
                    [],
                ):
                    if routine.get(
                        "id"
                    ) == routine_id:
                        last_workout[
                            "routine_name"
                        ] = routine.get(
                            "name"
                        )
                        break

            # Resolve the name from the session's recorded day.
            # A scheduled date alone may refer to another day.
            if (
                routine_id is not None
                and day_id is not None
            ):
                try:
                    sequence = (
                        await self.api.routines
                        .get_routine_date_sequence_display(
                            routine_id
                        )
                    )

                    if isinstance(
                        sequence,
                        list,
                    ):
                        sequence_entries = sequence

                    else:
                        sequence_entries = sequence.get(
                            "results",
                            [],
                        )

                    entry = _matching_workout_day(
                        sequence_entries, day_id, workout_date
                    )
                    if entry:
                        day_name = entry["day"].get("name")
                        if day_name:
                            last_workout["workout_name"] = day_name
                        if workout_date and entry.get("date") == workout_date:
                            last_workout["iteration"] = entry.get("iteration")

                except WgerAuthenticationError:
                    raise
                except Exception as err:
                    _LOGGER.warning(
                        "Unable to resolve last workout sequence "
                        "for routine %s: %s",
                        routine_id,
                        err,
                    )

        # Enrich workout progress with routine and
        # workout sequence information.
        if workout_progress:
            workout_progress = deepcopy(
                workout_progress
            )

            routine_sequences = {}

            for progress_entry in workout_progress:
                routine_id = progress_entry.get(
                    "routine_id"
                )

                workout_date = progress_entry.get(
                    "date"
                )

                # Resolve the routine name from the routines
                # already fetched by the coordinator.
                if routine_id is not None:
                    for routine in routines.get(
                        "results",
                        [],
                    ):
                        if routine.get(
                            "id"
                        ) == routine_id:
                            progress_entry[
                                "routine_name"
                            ] = routine.get(
                                "name"
                            )
                            break

                # Resolve the workout/day name and iteration
                # from the routine date sequence.
                if (
                    routine_id is None
                    or not workout_date
                ):
                    continue

                try:
                    if routine_id not in routine_sequences:
                        sequence = (
                            await self.api.routines
                            .get_routine_date_sequence_display(
                                routine_id
                            )
                        )

                        if isinstance(
                            sequence,
                            list,
                        ):
                            routine_sequences[
                                routine_id
                            ] = sequence

                        else:
                            routine_sequences[
                                routine_id
                            ] = sequence.get(
                                "results",
                                [],
                            )

                    sequence_entries = routine_sequences.get(
                        routine_id,
                        [],
                    )

                    for entry in sequence_entries:
                        if entry.get(
                            "date"
                        ) != workout_date:
                            continue

                        progress_entry[
                            "iteration"
                        ] = entry.get(
                            "iteration"
                        )

                        day_data = entry.get(
                            "day",
                            {}
                        )

                        if isinstance(
                            day_data,
                            dict,
                        ):
                            progress_entry[
                                "workout_name"
                            ] = day_data.get(
                                "name"
                            )

                        break

                except WgerAuthenticationError:
                    raise
                except Exception as err:
                    _LOGGER.warning(
                        "Unable to resolve workout progress sequence "
                        "for routine %s: %s",
                        routine_id,
                        err,
                    )

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

        # Calculate next workout planned metrics.
        next_exercises = 0
        next_sets = 0
        next_repetitions = 0

        if next_workout:
            for slot in next_workout.get(
                "slots",
                [],
            ):
                exercise_ids = slot.get(
                    "exercises",
                    []
                )

                next_exercises += len(
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

                    next_sets += sets_value

                    next_repetitions += (
                        sets_value
                        * repetitions_value
                    )

        _LOGGER.debug(
            "Next workout metrics: exercises=%s, sets=%s, repetitions=%s",
            next_exercises,
            next_sets,
            next_repetitions,
        )

        _LOGGER.debug(
            "Last workout analysis: %s",
            last_workout,
        )

        return {
            "profile": profile,
            "routines": routines,
            "active_routine": active_routine,
            "latest_session": latest_session,
            "last_workout": last_workout,
            "workout_progress": workout_progress,
            "weights": weights,
            "measurements": measurements,
            "trainings_this_week": trainings_this_week,
            "weekly_consistency": weekly_consistency,
            "workout_comparison": workout_comparison,
            "planned_workout": planned_workout,
            "weekly_goal": build_weekly_goal(
                trainings_this_week,
                weekly_target,
                now,
            ),
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
            "next_exercises": next_exercises,
            "next_sets": next_sets,
            "next_repetitions": next_repetitions,
        }

    @property
    def workout_progress(
        self,
    ) -> list[dict]:
        if self.data is None:
            return []

        return self.data.get(
            "workout_progress",
            [],
        )

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
    def last_workout(
        self,
    ) -> dict | None:
        if self.data is None:
            return None

        return self.data.get(
            "last_workout"
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

    @property
    def next_exercises(
        self,
    ) -> int:
        if self.data is None:
            return 0

        return self.data.get(
            "next_exercises",
            0,
        )

    @property
    def next_sets(
        self,
    ) -> int:
        if self.data is None:
            return 0

        return self.data.get(
            "next_sets",
            0,
        )

    @property
    def next_repetitions(
        self,
    ) -> int:
        if self.data is None:
            return 0

        return self.data.get(
            "next_repetitions",
            0,
        )
