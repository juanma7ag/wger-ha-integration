"""Focused lifecycle tests. Run with: python -m unittest discover -s tests."""

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "wger", ROOT / "__init__.py", submodule_search_locations=[str(ROOT)]
)
wger = importlib.util.module_from_spec(spec)
sys.modules["wger"] = wger
spec.loader.exec_module(wger)

from wger.api import WgerApiError, WgerAuthenticationError, WgerConnectionError
from wger.config_flow import WgerConfigFlow
from wger.coordinator import WgerDataUpdateCoordinator


class UnloadTests(unittest.IsolatedAsyncioTestCase):
    async def test_success_preserves_other_entries_and_shared_session(self):
        coordinator = SimpleNamespace(async_shutdown=AsyncMock())
        api = MagicMock()
        other = object()
        hass = SimpleNamespace(
            data={"wger": {"one": {"api": api, "coordinator": coordinator}, "two": other}},
            config_entries=SimpleNamespace(async_unload_platforms=AsyncMock(return_value=True)),
        )
        self.assertTrue(await wger.async_unload_entry(hass, SimpleNamespace(entry_id="one")))
        self.assertEqual(hass.data["wger"], {"two": other})
        coordinator.async_shutdown.assert_awaited_once()
        self.assertEqual(api.mock_calls, [])

    async def test_last_entry_removes_domain(self):
        hass = SimpleNamespace(
            data={"wger": {"one": {"coordinator": SimpleNamespace(async_shutdown=AsyncMock())}}},
            config_entries=SimpleNamespace(async_unload_platforms=AsyncMock(return_value=True)),
        )
        self.assertTrue(await wger.async_unload_entry(hass, SimpleNamespace(entry_id="one")))
        self.assertNotIn("wger", hass.data)

    async def test_failed_unload_keeps_runtime_data(self):
        coordinator = SimpleNamespace(async_shutdown=AsyncMock())
        runtime = {"coordinator": coordinator}
        hass = SimpleNamespace(
            data={"wger": {"one": runtime}},
            config_entries=SimpleNamespace(async_unload_platforms=AsyncMock(return_value=False)),
        )
        self.assertFalse(await wger.async_unload_entry(hass, SimpleNamespace(entry_id="one")))
        self.assertIs(hass.data["wger"]["one"], runtime)
        coordinator.async_shutdown.assert_not_awaited()


class CoordinatorTests(unittest.IsolatedAsyncioTestCase):
    async def test_error_mapping(self):
        coordinator = object.__new__(WgerDataUpdateCoordinator)
        for api_error, expected in (
            (WgerAuthenticationError, ConfigEntryAuthFailed),
            (WgerConnectionError, UpdateFailed),
            (WgerApiError, UpdateFailed),
        ):
            with self.subTest(error=api_error):
                coordinator._async_fetch_data = AsyncMock(side_effect=api_error("failure"))
                with self.assertRaises(expected):
                    await coordinator._async_update_data()

    async def test_success_returns_data(self):
        coordinator = object.__new__(WgerDataUpdateCoordinator)
        data = {"current_weight": 80}
        coordinator._async_fetch_data = AsyncMock(return_value=data)
        self.assertIs(await coordinator._async_update_data(), data)


class ReauthTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.flow = WgerConfigFlow()
        self.flow.hass = MagicMock()
        self.entry = SimpleNamespace(data={"url": "https://wger.example", "token": "old"})
        self.flow._get_reauth_entry = MagicMock(return_value=self.entry)
        self.flow.async_update_reload_and_abort = MagicMock(return_value={"type": "abort"})

    async def test_initial_form_does_not_expose_token(self):
        result = await self.flow.async_step_reauth(self.entry.data)
        self.assertEqual(result["step_id"], "reauth_confirm")
        self.assertEqual(result["description_placeholders"], {"url": "https://wger.example"})
        self.assertNotIn("'old'", str(result))

    async def test_success_updates_existing_entry_only(self):
        with patch("wger.config_flow.async_get_clientsession"), patch("wger.config_flow.WgerApi") as api:
            api.return_value.profile.get_profile = AsyncMock(return_value={})
            await self.flow.async_step_reauth_confirm({"token": "new"})
            api.return_value.profile.get_profile.assert_awaited_once()
            self.assertEqual(api.call_args.kwargs["base_url"], self.entry.data["url"])
        self.flow.async_update_reload_and_abort.assert_called_once_with(
            self.entry, data_updates={"token": "new"}
        )

    async def test_failures_preserve_credentials(self):
        for error, expected in (
            (WgerAuthenticationError, "invalid_auth"),
            (WgerConnectionError, "cannot_connect"),
            (WgerApiError, "cannot_connect"),
            (TimeoutError, "cannot_connect"),
        ):
            with self.subTest(error=error):
                with patch("wger.config_flow.async_get_clientsession"), patch("wger.config_flow.WgerApi") as api:
                    api.return_value.profile.get_profile = AsyncMock(side_effect=error())
                    result = await self.flow.async_step_reauth_confirm({"token": "new"})
                self.assertEqual(result["errors"], {"base": expected})
                self.assertEqual(self.entry.data["token"], "old")
                self.flow.async_update_reload_and_abort.assert_not_called()


if __name__ == "__main__":
    unittest.main()
