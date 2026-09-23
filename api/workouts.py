"""Wger workouts API."""

from __future__ import annotations

import logging
from datetime import datetime

from ..const import (
    DEFAULT_LOG_LIMIT,
    DEFAULT_PAGE_LIMIT,
    ENDPOINT_WORKOUT_LOGS,
    ENDPOINT_WORKOUT_SESSIONS,
)
from .client import WgerApiClient

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

    async def get_trainings_this_week(self) -> int:
        """Count workout sessions this week."""

        data = await self.get_workout_sessions(
            limit=250
        )

        sessions = data.get(
            "results",
            [],
        )

        today = datetime.now().astimezone()

        current_year, current_week, _ = (
            today.isocalendar()
        )

        count = 0

        for session in sessions:
            start = session.get(
                "datetime_start"
            )

            if not start:
                continue

            try:
                session_date = datetime.fromisoformat(
                    start.replace(
                        "Z",
                        "+00:00",
                    )
                )

                (
                    session_year,
                    session_week,
                    _,
                ) = session_date.isocalendar()

                if (
                    session_year == current_year
                    and session_week == current_week
                ):
                    count += 1

            except ValueError:
                _LOGGER.warning(
                    "Invalid workout session date: %s",
                    start,
                )

        return count

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