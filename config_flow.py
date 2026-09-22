"""Config flow for Wger."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_TOKEN,
    CONF_URL,
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


class WgerOptionsFlowHandler(config_entries.OptionsFlow):
    """Wger options."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage options."""

        return self.async_create_entry(
            title="",
            data={},
        )