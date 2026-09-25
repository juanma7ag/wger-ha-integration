"""Config flow for Wger."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WgerApi, WgerApiError, WgerAuthenticationError

from .const import (
    DOMAIN,
    CONF_TOKEN,
    CONF_URL,
    CONF_WEEKLY_GOAL,
    DEFAULT_WEEKLY_GOAL,
)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): str,
        vol.Required(CONF_TOKEN): str,
    }
)


class WgerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Wger."""

    VERSION = 1

    async def async_step_reauth(self, entry_data):
        """Ask for a replacement token after an authentication failure."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Validate the replacement token before updating the existing entry."""
        entry = self._get_reauth_entry()
        errors = {}

        if user_input is not None:
            api = WgerApi(
                session=async_get_clientsession(self.hass),
                base_url=entry.data[CONF_URL],
                token=user_input[CONF_TOKEN],
            )
            try:
                await api.profile.get_profile()
            except WgerAuthenticationError:
                errors["base"] = "invalid_auth"
            except (WgerApiError, TimeoutError):
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_TOKEN: user_input[CONF_TOKEN]},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            description_placeholders={"url": entry.data[CONF_URL]},
            errors=errors,
        )

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""

        errors = {}

        if user_input is not None:

            url = user_input[CONF_URL].rstrip("/")
            token = user_input[CONF_TOKEN]

            #
            # TODO
            # Aquí llamaremos a la API real.
            #
            try:
                # valid = await api.validate_connection()

                valid = True

                if valid:

                    await self.async_set_unique_id(url)

                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f"Wger ({url})",
                        data={
                            CONF_URL: url,
                            CONF_TOKEN: token,
                        },
                    )

                errors["base"] = "cannot_connect"

            except Exception:
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get options flow."""
        return WgerOptionsFlowHandler(config_entry)


class WgerOptionsFlowHandler(config_entries.OptionsFlowWithReload):
    """Wger options."""

    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage options."""

        if user_input is not None:
            return self.async_create_entry(
                title="", data={**self._config_entry.options, **user_input}
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_WEEKLY_GOAL,
                    default=self._config_entry.options.get(
                        CONF_WEEKLY_GOAL, DEFAULT_WEEKLY_GOAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=21)),
            }),
        )
