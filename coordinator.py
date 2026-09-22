"""Data update coordinator for Wger."""

from __future__ import annotations

import asyncio
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import (
    WgerApi,
    WgerApiError,
)

from .const import (
    DEFAULT_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class WgerDataUpdateCoordinator(
    DataUpdateCoordinator,
):
    """Wger coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: WgerApi,
    ) -> None:

        self.api = api

        super().__init__(
            hass,
            _LOGGER,
            name="Wger",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )

    async def _async_update_data(self):
        """Fetch all data."""

        try:

            (
                profile,
                routines,
                latest_session,
                weights,
                measurements,
                trainings_this_week,
                current_weight,
            ) = await asyncio.gather(
                self.api.get_profile(),
                self.api.get_routines(),
                self.api.get_latest_session(),
                self.api.get_weight_entries(limit=50),
                self.api.get_measurements(limit=100),
                self.api.get_trainings_this_week(),
                self.api.get_current_weight(),
            )

            return {
                "profile": profile,
                "routines": routines,
                "latest_session": latest_session,
                "weights": weights,
                "measurements": measurements,
                "trainings_this_week":
                    trainings_this_week,
                "current_weight":
                    current_weight,
            }

        except WgerApiError as err:

            raise UpdateFailed(
                f"Wger API error: {err}"
            ) from err

    @property
    def current_weight(self):
        """Return current weight."""

        return self.data.get(
            "current_weight"
        )

    @property
    def trainings_this_week(self):
        """Return weekly trainings."""

        return self.data.get(
            "trainings_this_week"
        )

    @property
    def latest_session(self):
        """Return latest session."""

        return self.data.get(
            "latest_session"
        )