"""API client for Wger."""

from __future__ import annotations

import logging
from datetime import datetime
from datetime import timedelta

from aiohttp import ClientError
from aiohttp import ClientSession

from .const import (
    API_VERSION,
    DEFAULT_LOG_LIMIT,
    DEFAULT_PAGE_LIMIT,
    ENDPOINT_EXERCISE_INFO,
    ENDPOINT_MEASUREMENTS,
    ENDPOINT_PROFILE,
    ENDPOINT_ROUTINES,
    ENDPOINT_WEIGHT_ENTRIES,
    ENDPOINT_WORKOUT_LOGS,
    ENDPOINT_WORKOUT_SESSIONS,
)

_LOGGER = logging.getLogger(__name__)


#
# Exceptions
#


class WgerApiError(Exception):
    """Generic API error."""


class WgerAuthenticationError(WgerApiError):
    """Authentication error."""


class WgerConnectionError(WgerApiError):
    """Connection error."""


#
# API Client
#


class WgerApi:
    """Wger API client."""

    def __init__(
        self,
        session: ClientSession,
        base_url: str,
        token: str,
    ) -> None:

        self._session = session
        self._base_url = base_url.rstrip("/")
        self._token = token

        self._exercise_cache: dict[int, dict] = {}

    #
    # Helpers
    #

    @property
    def headers(self) -> dict[str, str]:
        """Return request headers."""

        return {
            "Authorization": f"Token {self._token}",
            "Accept": "application/json",
        }

    def build_url(self, endpoint: str) -> str:
        """Build a Wger URL."""

        return (
            f"{self._base_url}"
            f"{API_VERSION}"
            f"{endpoint}"
        )

    async def _handle_response(self, response):
        """Handle common response logic."""

        if response.status in (401, 403):
            raise WgerAuthenticationError(
                "Authentication failed"
            )

        if response.status >= 400:

            body = await response.text()

            raise WgerApiError(
                f"HTTP {response.status}: {body}"
            )

        return await response.json()

    async def _get(
        self,
        endpoint: str,
    ) -> dict:

        url = self.build_url(endpoint)

        _LOGGER.debug("GET %s", url)

        try:

            async with self._session.get(
                url,
                headers=self.headers,
                timeout=30,
            ) as response:

                return await self._handle_response(
                    response
                )

        except ClientError as err:

            raise WgerConnectionError(
                str(err)
            ) from err

    async def _post(
        self,
        endpoint: str,
        payload: dict,
    ) -> dict:

        url = self.build_url(endpoint)

        try:

            async with self._session.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=30,
            ) as response:

                return await self._handle_response(
                    response
                )

        except ClientError as err:

            raise WgerConnectionError(
                str(err)
            ) from err

    async def _patch(
        self,
        endpoint: str,
        payload: dict,
    ) -> dict:

        url = self.build_url(endpoint)

        try:

            async with self._session.patch(
                url,
                headers=self.headers,
                json=payload,
                timeout=30,
            ) as response:

                return await self._handle_response(
                    response
                )

        except ClientError as err:

            raise WgerConnectionError(
                str(err)
            ) from err

    async def _delete(
        self,
        endpoint: str,
    ) -> None:

        url = self.build_url(endpoint)

        try:

            async with self._session.delete(
                url,
                headers=self.headers,
                timeout=30,
            ) as response:

                if response.status not in (
                    200,
                    204,
                ):
                    raise WgerApiError(
                        f"Delete failed: {response.status}"
                    )

        except ClientError as err:

            raise WgerConnectionError(
                str(err)
            ) from err

    #
    # Validation
    #

    async def validate_connection(self) -> bool:
        """Validate credentials."""

        try:

            await self.get_profile()

            return True

        except WgerApiError:

            return False

    #
    # Profile
    #

    async def get_profile(self) -> dict:
        """Get user profile."""

        return await self._get(
            ENDPOINT_PROFILE
        )

    #
    # Routines
    #

    async def get_routines(self) -> dict:
        """Get routines."""

        return await self._get(
            ENDPOINT_ROUTINES
        )

    async def get_routine(
        self,
        routine_id: int,
    ) -> dict:
        """Get routine."""

        return await self._get(
            f"{ENDPOINT_ROUTINES}{routine_id}/"
        )

    async def get_routine_structure(
        self,
        routine_id: int,
    ) -> dict:
        """Get routine structure."""

        return await self._get(
            f"{ENDPOINT_ROUTINES}"
            f"{routine_id}/structure/"
        )

    #
    # Workout sessions
    #

    async def get_workout_sessions(
        self,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> dict:
        """Get workout sessions."""

        return await self._get(
            f"{ENDPOINT_WORKOUT_SESSIONS}"
            f"?limit={limit}"
        )

    async def get_latest_session(self):
        """Get latest session."""

        data = await self._get(
            f"{ENDPOINT_WORKOUT_SESSIONS}"
            f"?ordering=-datetime_start"
            f"&limit=1"
        )

        results = data.get(
            "results",
            [],
        )

        return results[0] if results else None

    #
    # Workout logs
    #

    async def get_workout_logs(
        self,
        limit: int = DEFAULT_LOG_LIMIT,
    ) -> dict:
        """Get workout logs."""

        return await self._get(
            f"{ENDPOINT_WORKOUT_LOGS}"
            f"?limit={limit}"
        )

    #
    # Weight
    #

    async def get_weight_entries(
        self,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> dict:
        """Get weight history."""

        return await self._get(
            f"{ENDPOINT_WEIGHT_ENTRIES}"
            f"?ordering=-date"
            f"&limit={limit}"
        )

    async def get_current_weight(
        self,
    ) -> float | None:
        """Get latest body weight."""

        data = await self.get_weight_entries(
            limit=1
        )

        results = data.get(
            "results",
            [],
        )

        if not results:
            return None

        return float(
            results[0]["weight"]
        )

    #
    # Measurements
    #

    async def get_measurements(
        self,
        limit: int = DEFAULT_PAGE_LIMIT,
    ) -> dict:
        """Get measurements."""

        return await self._get(
            f"{ENDPOINT_MEASUREMENTS}"
            f"?limit={limit}"
        )

    #
    # Exercise database
    #

    async def get_exercises(
        self,
        limit: int = DEFAULT_LOG_LIMIT,
    ) -> dict:
        """Get exercises."""

        return await self._get(
            f"{ENDPOINT_EXERCISE_INFO}"
            f"?limit={limit}"
        )

    async def build_exercise_cache(
        self,
    ) -> None:
        """Build exercise cache."""

        data = await self.get_exercises()

        self._exercise_cache = {
            exercise["id"]: exercise
            for exercise in data.get(
                "results",
                []
            )
        }

    def get_cached_exercise(
        self,
        exercise_id: int,
    ) -> dict | None:
        """Return cached exercise."""

        return self._exercise_cache.get(
            exercise_id
        )

    #
    # Dashboard helpers
    #

    async def get_trainings_this_week(
        self,
    ) -> int:
        """Count sessions this week."""

        data = await self.get_workout_sessions(
            limit=250
        )

        sessions = data.get(
            "results",
            []
        )

        today = datetime.now()

        week_start = (
            today
            - timedelta(
                days=today.weekday()
            )
        ).date()

        count = 0

        for session in sessions:

            start = session.get(
                "datetime_start"
            )

            if not start:
                continue

            session_date = (
                datetime.fromisoformat(
                    start.replace(
                        "Z",
                        "+00:00",
                    )
                )
                .date()
            )

            if session_date >= week_start:
                count += 1

        return count

    async def get_dashboard_data(self) -> dict:
      return {
            "profile": await self.get_profile(),
            "routines": await self.get_routines(),
            "latest_session": await self.get_latest_session(),
            "weights": await self.get_weight_entries(
                limit=50
            ),
            "measurements": await self.get_measurements(
                limit=100
            ),
        }