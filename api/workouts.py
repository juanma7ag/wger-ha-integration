"""Wger workouts API."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode

from .client import WgerApiClient, WgerAuthenticationError
from ..const import (
    DEFAULT_LOG_LIMIT,
    DEFAULT_PAGE_LIMIT,
    ENDPOINT_WORKOUT_LOGS,
    ENDPOINT_WORKOUT_SESSIONS,
)
from .weekly_goal import count_completed_sessions, week_bounds
from .consistency import HISTORY_WEEKS, build_consistency

_LOGGER = logging.getLogger(__name__)


class WgerWorkoutsApi:
    """API methods related to workouts and workout sessions."""

    def __init__(
            self,
            client: WgerApiClient,
    ) -> None:
        """Initialize the workouts API."""

        self._client = client

    async def get_workout_sessions(
            self,
            limit: int = DEFAULT_PAGE_LIMIT,
    ) -> dict:
        """Get workout sessions."""

        return await self._client._get(
            f"{ENDPOINT_WORKOUT_SESSIONS}"
            f"?limit={limit}"
        )

    async def get_latest_session(self) -> dict | None:
        """Get the latest workout session."""

        data = await self._client._get(
            f"{ENDPOINT_WORKOUT_SESSIONS}"
            f"?ordering=-datetime_start"
            f"&limit=1"
        )

        results = data.get(
            "results",
            [],
        )

        return results[0] if results else None

    async def get_trainings_this_week(self, now: datetime | None = None) -> int:
        """Count completed sessions starting this week in the supplied timezone."""
        now = now or datetime.now().astimezone()
        start, end = week_bounds(now)
        query = urlencode({
            "datetime_start__gte": start.isoformat(),
            "datetime_start__lt": end.isoformat(),
            "ordering": "-datetime_start",
            "limit": 250,
        })
        data = await self._client._get(f"{ENDPOINT_WORKOUT_SESSIONS}?{query}")
        return count_completed_sessions(data.get("results", []), now)

    async def get_weekly_consistency(self, target: int, now: datetime) -> dict:
        """Fetch a bounded history without following pagination links."""
        start, end = week_bounds(now)
        query = urlencode({
            "datetime_start__gte": (start - timedelta(weeks=HISTORY_WEEKS - 1)).isoformat(),
            "datetime_start__lt": end.isoformat(),
            "ordering": "-datetime_start",
            "limit": 999,
        })
        data = await self._client._get(f"{ENDPOINT_WORKOUT_SESSIONS}?{query}")
        sessions = data.get("results", [])
        if data.get("next") or data.get("count", len(sessions)) > len(sessions):
            # Partial history must not look like missed weeks or a broken streak.
            return {"history_complete": False, "target": target, "weeks": []}
        return build_consistency(sessions, target, now)

    async def get_last_workout_duration(
            self,
    ) -> float | None:
        """Return duration of the latest workout in minutes."""

        session = await self.get_latest_session()

        if not session:
            return None

        start = session.get(
            "datetime_start"
        )

        end = session.get(
            "datetime_end"
        )

        if not start or not end:
            return None

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

            duration = (
                               end_dt - start_dt
                       ).total_seconds() / 60

            return round(
                duration,
                1,
            )

        except ValueError:
            _LOGGER.warning(
                "Invalid workout session dates: %s - %s",
                start,
                end,
            )

            return None

    async def get_days_since_last_workout(
            self,
    ) -> int | None:
        """Return number of days since the latest workout."""

        session = await self.get_latest_session()

        if not session:
            return None

        start = session.get(
            "datetime_start"
        )

        if not start:
            return None

        try:
            workout_dt = datetime.fromisoformat(
                start.replace(
                    "Z",
                    "+00:00",
                )
            )

            now = datetime.now().astimezone()

            return (
                    now.date()
                    - workout_dt.date()
            ).days

        except ValueError:
            _LOGGER.warning(
                "Invalid workout session date: %s",
                start,
            )

            return None

    async def get_workout_logs(
            self,
            limit: int = DEFAULT_LOG_LIMIT,
    ) -> dict:
        """Get workout logs."""

        return await self._client._get(
            f"{ENDPOINT_WORKOUT_LOGS}"
            f"?limit={limit}"
        )

    async def get_workout_progress(
            self,
            limit: int = DEFAULT_LOG_LIMIT,
    ) -> list[dict]:
        """Return aggregated workout progress by session."""

        sessions_data = await self.get_workout_sessions(
            limit=250
        )

        sessions = sessions_data.get(
            "results",
            [],
        )

        logs_data = await self.get_workout_logs(
            limit=limit
        )

        logs = logs_data.get(
            "results",
            [],
        )

        logs_by_session = {}

        for log in logs:
            session_id = log.get(
                "session"
            )

            if not session_id:
                continue

            if session_id not in logs_by_session:
                logs_by_session[session_id] = []

            logs_by_session[session_id].append(
                log
            )

        progress = []

        for session in sessions:
            session_id = session.get(
                "id"
            )

            if not session_id:
                continue

            session_logs = logs_by_session.get(
                session_id,
                [],
            )

            if not session_logs:
                continue

            total_sets = len(session_logs)
            total_repetitions = 0.0
            total_volume = 0.0
            rir_values = []
            exercise_ids = set()

            for log in session_logs:
                exercise_id = log.get(
                    "exercise"
                )

                if exercise_id is not None:
                    exercise_ids.add(
                        exercise_id
                    )

                repetitions = log.get(
                    "repetitions"
                )

                weight = log.get(
                    "weight"
                )

                rir = log.get(
                    "rir"
                )

                try:
                    if repetitions is not None:
                        total_repetitions += float(
                            repetitions
                        )
                except (
                        TypeError,
                        ValueError,
                ):
                    pass

                try:
                    if (
                            weight is not None
                            and repetitions is not None
                    ):
                        total_volume += (
                                float(weight)
                                * float(repetitions)
                        )
                except (
                        TypeError,
                        ValueError,
                ):
                    pass

                try:
                    if rir is not None:
                        rir_values.append(
                            float(rir)
                        )
                except (
                        TypeError,
                        ValueError,
                ):
                    pass

            start = session.get(
                "datetime_start"
            )

            end = session.get(
                "datetime_end"
            )

            session_date = self._parse_datetime(
                start
            )

            progress.append({
                "session_id": session_id,
                "date": (
                    session_date.date().isoformat()
                    if session_date
                    else ""
                ),
                "date_start": start,
                "date_end": end,
                "iteration": session.get(
                    "iteration"
                ),
                "workout_name": session.get(
                    "name"
                ),
                "routine_id": session.get(
                    "routine"
                ),
                "routine_name": session.get(
                    "routine_name"
                ),
                "total_exercises": len(
                    exercise_ids
                ),
                "total_sets": total_sets,
                "total_repetitions": round(
                    total_repetitions,
                    1,
                ),
                "total_volume": round(
                    total_volume,
                    1,
                ),
                "average_rir": self._calculate_average_rir(
                    rir_values
                ),
            })

        progress.sort(
            key=lambda item: item.get(
                "date_start"
            ) or "",
            reverse=True,
        )

        return progress

    async def get_repetitions_this_week(
            self,
            routine_id: int | None = None,
    ) -> float:
        """Count repetitions performed during the current ISO week."""

        data = await self.get_workout_logs(
            limit=250
        )

        logs = data.get(
            "results",
            [],
        )

        today = datetime.now().astimezone()

        current_year, current_week, _ = (
            today.isocalendar()
        )

        total_repetitions = 0.0

        for log in logs:
            if (
                    routine_id is not None
                    and log.get("routine") != routine_id
            ):
                continue

            date_value = log.get(
                "date"
            )

            repetitions = log.get(
                "repetitions"
            )

            if not date_value or repetitions is None:
                continue

            try:
                log_date = datetime.fromisoformat(
                    date_value.replace(
                        "Z",
                        "+00:00",
                    )
                )

            except ValueError:
                _LOGGER.warning(
                    "Invalid workout log date: %s",
                    date_value,
                )

                continue

            (
                log_year,
                log_week,
                _,
            ) = log_date.isocalendar()

            if (
                    log_year != current_year
                    or log_week != current_week
            ):
                continue

            try:
                total_repetitions += float(
                    repetitions
                )

            except (TypeError, ValueError):
                _LOGGER.warning(
                    "Invalid repetitions value: %s",
                    repetitions,
                )

        return total_repetitions

    @staticmethod
    def _parse_datetime(
            value: str | None,
    ) -> datetime | None:
        """Parse an ISO datetime value."""

        if not value:
            return None

        try:
            return datetime.fromisoformat(
                value.replace(
                    "Z",
                    "+00:00",
                )
            )
        except ValueError:
            return None

    @staticmethod
    def _calculate_average_rir(
            values: list,
    ) -> float | None:
        """Calculate the average RIR from numeric values."""

        numeric_values = []

        for value in values:
            try:
                if value is not None:
                    numeric_values.append(
                        float(value)
                    )
            except (TypeError, ValueError):
                continue

        if not numeric_values:
            return None

        return round(
            sum(numeric_values) / len(numeric_values),
            2,
        )

    @staticmethod
    def _build_muscle_distribution(
            exercises: list[dict],
    ) -> list[dict]:
        """Build an estimated muscle volume distribution."""

        muscle_data = {}

        for exercise in exercises:
            volume = exercise.get(
                "total_volume"
            )

            try:
                volume = float(volume)
            except (TypeError, ValueError):
                continue

            if volume <= 0:
                continue

            primary = [
                muscle
                for muscle in exercise.get(
                    "muscle_names",
                    [],
                )
                if muscle
            ]

            secondary = [
                muscle
                for muscle in exercise.get(
                    "muscle_names_secondary",
                    [],
                )
                if muscle
            ]

            if not primary and not secondary:
                continue

            if primary:
                primary_volume = volume
                secondary_volume = 0.0

                if secondary:
                    primary_volume = volume * 0.70
                    secondary_volume = volume * 0.30

                primary_share = (
                        primary_volume / len(primary)
                )

                for muscle in primary:
                    if muscle not in muscle_data:
                        muscle_data[muscle] = {
                            "estimated_volume": 0.0,
                            "exercises": set(),
                        }

                    muscle_data[muscle][
                        "estimated_volume"
                    ] += primary_share

                    muscle_data[muscle][
                        "exercises"
                    ].add(
                        exercise.get(
                            "exercise_id"
                        )
                    )

                if secondary:
                    secondary_share = (
                            secondary_volume
                            / len(secondary)
                    )

                    for muscle in secondary:
                        if muscle not in muscle_data:
                            muscle_data[muscle] = {
                                "estimated_volume": 0.0,
                                "exercises": set(),
                            }

                        muscle_data[muscle][
                            "estimated_volume"
                        ] += secondary_share

                        muscle_data[muscle][
                            "exercises"
                        ].add(
                            exercise.get(
                                "exercise_id"
                            )
                        )

            else:
                secondary_share = (
                        volume / len(secondary)
                )

                for muscle in secondary:
                    if muscle not in muscle_data:
                        muscle_data[muscle] = {
                            "estimated_volume": 0.0,
                            "exercises": set(),
                        }

                    muscle_data[muscle][
                        "estimated_volume"
                    ] += secondary_share

                    muscle_data[muscle][
                        "exercises"
                    ].add(
                        exercise.get(
                            "exercise_id"
                        )
                    )

        total_volume = sum(
            item["estimated_volume"]
            for item in muscle_data.values()
        )

        if total_volume <= 0:
            return []

        distribution = []

        for muscle, data in muscle_data.items():
            estimated_volume = data[
                "estimated_volume"
            ]

            distribution.append({
                "muscle": muscle,
                "percentage": round(
                    (
                            estimated_volume
                            / total_volume
                    )
                    * 100,
                    1,
                ),
                "estimated_volume": round(
                    estimated_volume,
                    1,
                ),
                "exercises": sorted(
                    exercise_id
                    for exercise_id in data[
                        "exercises"
                    ]
                    if exercise_id is not None
                ),
            })

        distribution.sort(
            key=lambda item: item[
                "estimated_volume"
            ],
            reverse=True,
        )

        return distribution

    async def get_last_workout_analysis(
            self,
    ) -> dict | None:
        """Return a detailed analysis of the latest workout session."""

        latest_session = await self.get_latest_session()

        if not latest_session:
            return None

        session_id = latest_session.get(
            "id"
        )

        if not session_id:
            return None

        routine_id = latest_session.get(
            "routine"
        )

        data = await self.get_workout_logs(
            limit=250
        )

        logs = [
            log
            for log in data.get(
                "results",
                [],
            )
            if log.get("session") == session_id
        ]

        muscle_distribution_note = (
            "Estimación basada en el volumen de los ejercicios "
            "y los músculos asociados a cada movimiento. "
            "No representa una carga muscular medida directamente."
        )

        if not logs:
            return {
                "session_id": session_id,
                "routine_id": routine_id,
                "iteration": latest_session.get(
                    "iteration"
                ),
                "date": latest_session.get(
                    "datetime_start",
                    "",
                )[:10],
                "date_start": latest_session.get(
                    "datetime_start"
                ),
                "date_end": latest_session.get(
                    "datetime_end"
                ),
                "duration": None,
                "workout_name": latest_session.get(
                    "name"
                ),
                "routine_name": latest_session.get(
                    "routine_name"
                ),
                "totals": {
                    "total_exercises": 0,
                    "total_sets": 0,
                    "total_repetitions": 0,
                    "total_volume": 0.0,
                },
                "average_rir": None,
                "exercises": [],
                "muscle_distribution": [],
                "muscle_distribution_note": (
                    muscle_distribution_note
                ),
            }

        from .exercises import WgerExercisesApi

        exercises_api = WgerExercisesApi(
            self._client
        )

        grouped_logs = {}

        for log in logs:
            exercise_id = log.get(
                "exercise"
            )

            if exercise_id is None:
                continue

            if exercise_id not in grouped_logs:
                grouped_logs[exercise_id] = []

            grouped_logs[exercise_id].append(
                log
            )

        exercises = []

        for exercise_id, exercise_logs in grouped_logs.items():
            try:
                details = await exercises_api.get_exercise_details(
                    exercise_id
                )
            except WgerAuthenticationError:
                raise
            except Exception as err:
                _LOGGER.warning(
                    "Unable to load exercise %s for last workout: %s",
                    exercise_id,
                    err,
                )
                details = {}

            exercise_name = details.get(
                "name"
            ) or f"Ejercicio {exercise_id}"

            primary_muscles = details.get(
                "muscle_names",
                [],
            )

            secondary_muscles = details.get(
                "muscle_names_secondary",
                [],
            )

            if not isinstance(
                    primary_muscles,
                    list,
            ):
                primary_muscles = []

            if not isinstance(
                    secondary_muscles,
                    list,
            ):
                secondary_muscles = []

            sets = []
            total_repetitions = 0.0
            total_volume = 0.0
            max_weight = None
            rir_values = []
            weight_unit = None

            for log in exercise_logs:
                repetitions = log.get(
                    "repetitions"
                )

                weight = log.get(
                    "weight"
                )

                rir = log.get(
                    "rir"
                )

                try:
                    if repetitions is not None:
                        total_repetitions += float(
                            repetitions
                        )
                except (
                        TypeError,
                        ValueError,
                ):
                    pass

                try:
                    if (
                            weight is not None
                            and repetitions is not None
                    ):
                        total_volume += (
                                float(weight)
                                * float(repetitions)
                        )
                except (
                        TypeError,
                        ValueError,
                ):
                    pass

                try:
                    if weight is not None:
                        weight_value = float(
                            weight
                        )

                        if (
                                max_weight is None
                                or weight_value > max_weight
                        ):
                            max_weight = weight_value

                except (
                        TypeError,
                        ValueError,
                ):
                    pass

                try:
                    if rir is not None:
                        rir_values.append(
                            float(rir)
                        )
                except (
                        TypeError,
                        ValueError,
                ):
                    pass

                if log.get(
                        "weight_unit"
                ):
                    weight_unit = log.get(
                        "weight_unit"
                    )

                sets.append({
                    "log_id": log.get(
                        "id"
                    ),
                    "date": log.get(
                        "date"
                    ),
                    "repetitions": repetitions,
                    "repetitions_target": log.get(
                        "repetitions_target"
                    ),
                    "weight": weight,
                    "weight_target": log.get(
                        "weight_target"
                    ),
                    "weight_unit": log.get(
                        "weight_unit"
                    ),
                    "rir": rir,
                    "rir_target": log.get(
                        "rir_target"
                    ),
                    "rest": log.get(
                        "rest"
                    ),
                    "rest_target": log.get(
                        "rest_target"
                    ),
                })

            exercises.append({
                "exercise_id": exercise_id,
                "name": exercise_name,
                "image": details.get(
                    "image"
                ),
                "thumbnail_small": details.get(
                    "thumbnail_small"
                ),
                "thumbnail_medium": details.get(
                    "thumbnail_medium"
                ),
                "muscle_names": primary_muscles,
                "muscle_names_secondary": secondary_muscles,
                "weight_unit": weight_unit,
                "sets": sets,
                "total_repetitions": round(
                    total_repetitions,
                    1,
                ),
                "total_volume": round(
                    total_volume,
                    1,
                ),
                "max_weight": max_weight,
                "average_rir": self._calculate_average_rir(
                    rir_values
                ),
            })

        total_exercises = len(
            exercises
        )

        total_sets = sum(
            len(exercise["sets"])
            for exercise in exercises
        )

        total_repetitions = sum(
            exercise["total_repetitions"]
            for exercise in exercises
        )

        total_volume = sum(
            exercise["total_volume"]
            for exercise in exercises
        )

        average_rir = self._calculate_average_rir(
            [
                log.get("rir")
                for log in logs
            ]
        )

        log_dates = [
            self._parse_datetime(
                log.get("date")
            )
            for log in logs
            if log.get("date")
        ]

        log_dates = [
            value
            for value in log_dates
            if value is not None
        ]

        session_start = (
            min(log_dates)
            if log_dates
            else self._parse_datetime(
                latest_session.get(
                    "datetime_start"
                )
            )
        )

        session_end = (
            max(log_dates)
            if log_dates
            else self._parse_datetime(
                latest_session.get(
                    "datetime_end"
                )
            )
        )

        duration = None

        latest_session_start = self._parse_datetime(
            latest_session.get(
                "datetime_start"
            )
        )

        latest_session_end = self._parse_datetime(
            latest_session.get(
                "datetime_end"
            )
        )

        if (
                latest_session_start
                and latest_session_end
        ):
            duration = round(
                (
                        latest_session_end
                        - latest_session_start
                ).total_seconds()
                / 60,
                1,
            )

        muscle_distribution = (
            self._build_muscle_distribution(
                exercises
            )
        )

        return {
            "session_id": session_id,
            "routine_id": routine_id,
            "iteration": latest_session.get(
                "iteration"
            ),
            "date": (
                session_start.date().isoformat()
                if session_start
                else ""
            ),
            "date_start": (
                session_start.isoformat()
                if session_start
                else None
            ),
            "date_end": (
                session_end.isoformat()
                if session_end
                else None
            ),
            "duration": duration,
            "workout_name": latest_session.get(
                "name"
            ),
            "routine_name": latest_session.get(
                "routine_name"
            ),
            "totals": {
                "total_exercises": total_exercises,
                "total_sets": total_sets,
                "total_repetitions": round(
                    total_repetitions,
                    1,
                ),
                "total_volume": round(
                    total_volume,
                    1,
                ),
            },
            "average_rir": average_rir,
            "exercises": exercises,
            "muscle_distribution": muscle_distribution,
            "muscle_distribution_note": (
                muscle_distribution_note
            ),
        }
