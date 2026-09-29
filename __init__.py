"""The Wger integration."""

from __future__ import annotations

import logging
from pathlib import Path

from aiohttp import ClientSession
from homeassistant.components import websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import (
    async_get_clientsession,
)

from .api import WgerApi
from .api.account import CONF_USERNAME, account_title, account_unique_id, account_username
from .const import (
    CONF_TOKEN,
    CONF_URL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import (
    WgerDataUpdateCoordinator,
)
from .api.workout_history import websocket_workout_history, websocket_workout_detail

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

    websocket_api.async_register_command(hass, websocket_workout_history)
    websocket_api.async_register_command(hass, websocket_workout_detail)

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
            entry=entry,
        )
    )

    #
    # Carga inicial
    #

    await coordinator.async_config_entry_first_refresh()

    username = account_username(coordinator.data["profile"])
    unique_id = account_unique_id(url, username)
    if entry.unique_id != unique_id or entry.data.get(CONF_USERNAME) != username:
        hass.config_entries.async_update_entry(
            entry,
            unique_id=unique_id,
            title=account_title(url, username),
            data={**entry.data, CONF_USERNAME: username},
        )

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


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload platforms and release this entry's runtime data."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False

    entry_data = hass.data[DOMAIN][entry.entry_id]
    await entry_data["coordinator"].async_shutdown()
    hass.data[DOMAIN].pop(entry.entry_id)
    if not hass.data[DOMAIN]:
        hass.data.pop(DOMAIN)

    # The HTTP session belongs to Home Assistant and must remain open.
    return True
