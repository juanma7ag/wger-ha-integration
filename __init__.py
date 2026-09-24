"""The Wger integration."""

from __future__ import annotations

import logging
from pathlib import Path

from aiohttp import ClientSession
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import (
    async_get_clientsession,
)

from .api import WgerApi
from .const import (
    CONF_TOKEN,
    CONF_URL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import (
    WgerDataUpdateCoordinator,
)

_LOGGER = logging.getLogger(__name__)

type WgerConfigEntry = ConfigEntry


async def async_setup(
    hass: HomeAssistant,
    config: dict,
) -> bool:
    """Set up integration."""

    frontend_path = Path(__file__).parent / "frontend"

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                "/wger/frontend",
                str(frontend_path),
                False,
            )
        ]
    )

    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up Wger from config entry."""

    _LOGGER.info("Setting up Wger integration")

    url = entry.data[CONF_URL]
    token = entry.data[CONF_TOKEN]

    session: ClientSession = (
        async_get_clientsession(hass)
    )

    api = WgerApi(
        session=session,
        base_url=url,
        token=token,
    )

    coordinator = (
        WgerDataUpdateCoordinator(
            hass=hass,
            api=api,
        )
    )

    #
    # Carga inicial
    #

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(
        DOMAIN,
        {}
    )

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    _LOGGER.info("Wger integration loaded successfully")

    return True