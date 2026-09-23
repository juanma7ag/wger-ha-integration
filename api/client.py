"""Base API client for Wger."""

from __future__ import annotations

import logging

from aiohttp import ClientError
from aiohttp import ClientSession

from ..const import API_VERSION

_LOGGER = logging.getLogger(__name__)


#
# Exceptions
#


class WgerApiError(Exception):
    """Generic Wger API error."""


class WgerAuthenticationError(WgerApiError):
    """Authentication error."""


class WgerConnectionError(WgerApiError):
    """Connection error."""


#
# API Client
#


class WgerApiClient:
    """Low-level HTTP client for the Wger API."""

    def __init__(
        self,
        session: ClientSession,
        base_url: str,
        token: str,
    ) -> None:
        """Initialize the API client."""

        self._session = session
        self._base_url = base_url.rstrip("/")
        self._token = token

    @property
    def headers(self) -> dict[str, str]:
        """Return request headers."""

        return {
            "Authorization": f"Token {self._token}",
            "Accept": "application/json",
        }

    def build_url(
        self,
        endpoint: str,
    ) -> str:
        """Build a Wger API URL."""

        return (
            f"{self._base_url}"
            f"{API_VERSION}"
            f"{endpoint}"
        )

    async def _handle_response(
        self,
        response,
    ) -> dict:
        """Handle a Wger API response."""

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
        """Perform a GET request."""

        url = self.build_url(endpoint)

        _LOGGER.debug(
            "GET %s",
            url,
        )

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
        """Perform a POST request."""

        url = self.build_url(endpoint)

        _LOGGER.debug(
            "POST %s",
            url,
        )

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
        """Perform a PATCH request."""

        url = self.build_url(endpoint)

        _LOGGER.debug(
            "PATCH %s",
            url,
        )

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
        """Perform a DELETE request."""

        url = self.build_url(endpoint)

        _LOGGER.debug(
            "DELETE %s",
            url,
        )

        try:
            async with self._session.delete(
                url,
                headers=self.headers,
                timeout=30,
            ) as response:
                if response.status not in (200, 204):
                    raise WgerApiError(
                        f"Delete failed: {response.status}"
                    )

        except ClientError as err:
            raise WgerConnectionError(
                str(err)
            ) from err