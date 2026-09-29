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
from wger.sensor import SENSORS, async_setup_entry as async_setup_sensors


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


class AccountSetupTests(unittest.IsolatedAsyncioTestCase):
    async def test_existing_entry_gets_account_identity(self):
        entry = SimpleNamespace(
            entry_id="alice-entry", unique_id="https://wger.example",
            data={"url": "https://wger.example", "token": "valid"},
        )
        coordinator = MagicMock()
        coordinator.data = {"profile": {"username": "alice"}}
        coordinator.async_config_entry_first_refresh = AsyncMock()
        hass = SimpleNamespace(
            data={},
            config_entries=SimpleNamespace(
                async_update_entry=MagicMock(),
                async_forward_entry_setups=AsyncMock(),
            ),
        )
        with patch("wger.async_get_clientsession"), patch("wger.WgerApi"), patch(
            "wger.WgerDataUpdateCoordinator", return_value=coordinator
        ):
            self.assertTrue(await wger.async_setup_entry(hass, entry))
        hass.config_entries.async_update_entry.assert_called_once_with(
            entry,
            unique_id="https://wger.example|alice",
            title="Wger (alice @ https://wger.example)",
            data={"url": "https://wger.example", "token": "valid", "username": "alice"},
        )
        coordinator.async_config_entry_first_refresh.assert_awaited_once()
        hass.config_entries.async_forward_entry_setups.assert_awaited_once()


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
        self.entry = SimpleNamespace(data={"url": "https://wger.example", "token": "old", "username": "alice"})
        self.flow._get_reauth_entry = MagicMock(return_value=self.entry)
        self.flow.async_update_reload_and_abort = MagicMock(return_value={"type": "abort"})

    async def test_initial_form_does_not_expose_token(self):
        result = await self.flow.async_step_reauth(self.entry.data)
        self.assertEqual(result["step_id"], "reauth_confirm")
        self.assertEqual(result["description_placeholders"], {"url": "https://wger.example"})
        self.assertNotIn("'old'", str(result))

    async def test_success_updates_existing_entry_only(self):
        with patch("wger.config_flow.async_get_clientsession"), patch("wger.config_flow.WgerApi") as api:
            api.return_value.profile.get_profile = AsyncMock(return_value={"username": "alice"})
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

    async def test_reauth_rejects_another_account(self):
        with patch("wger.config_flow.async_get_clientsession"), patch("wger.config_flow.WgerApi") as api:
            api.return_value.profile.get_profile = AsyncMock(return_value={"username": "bob"})
            result = await self.flow.async_step_reauth_confirm({"token": "bob-token"})
        self.assertEqual(result["errors"], {"base": "account_mismatch"})
        self.flow.async_update_reload_and_abort.assert_not_called()


class InitialConfigTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.flow = WgerConfigFlow()
        self.flow.hass = MagicMock()
        self.flow.async_set_unique_id = AsyncMock()
        self.flow._abort_if_unique_id_configured = MagicMock()
        self.flow.async_create_entry = MagicMock(return_value={"type": "create_entry"})

    async def test_success_validates_before_creating_entry(self):
        with patch("wger.config_flow.async_get_clientsession"), patch("wger.config_flow.WgerApi") as api:
            api.return_value.profile.get_profile = AsyncMock(return_value={"username": "alice"})
            result = await self.flow.async_step_user(
                {"url": "https://wger.example/", "token": "valid"}
            )

        self.assertEqual(result, {"type": "create_entry"})
        api.return_value.profile.get_profile.assert_awaited_once()
        self.flow.async_set_unique_id.assert_awaited_once_with("https://wger.example|alice")
        self.flow.async_create_entry.assert_called_once_with(
            title="Wger (alice @ https://wger.example)",
            data={"url": "https://wger.example", "token": "valid", "username": "alice"},
        )

    async def test_same_server_uses_distinct_account_ids(self):
        with patch("wger.config_flow.async_get_clientsession"), patch("wger.config_flow.WgerApi") as api:
            api.return_value.profile.get_profile = AsyncMock(
                side_effect=({"username": "alice"}, {"username": "bob"})
            )
            for token in ("alice-token", "bob-token"):
                await self.flow.async_step_user(
                    {"url": "https://wger.example", "token": token}
                )
        self.assertEqual(
            [call.args[0] for call in self.flow.async_set_unique_id.await_args_list],
            ["https://wger.example|alice", "https://wger.example|bob"],
        )

    async def test_connection_failures_do_not_create_entry(self):
        for error, expected in (
            (WgerAuthenticationError, "invalid_auth"),
            (WgerConnectionError, "cannot_connect"),
            (WgerApiError, "cannot_connect"),
            (TimeoutError, "cannot_connect"),
        ):
            with self.subTest(error=error):
                with patch("wger.config_flow.async_get_clientsession"), patch("wger.config_flow.WgerApi") as api:
                    api.return_value.profile.get_profile = AsyncMock(side_effect=error())
                    result = await self.flow.async_step_user(
                        {"url": "https://wger.example", "token": "invalid"}
                    )

                self.assertEqual(result["errors"], {"base": expected})
                self.flow.async_set_unique_id.assert_not_awaited()
                self.flow.async_create_entry.assert_not_called()


class SensorMigrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_existing_entity_keeps_its_entity_id(self):
        entry = SimpleNamespace(entry_id="alice-entry")
        coordinator = MagicMock(entry=entry)
        hass = SimpleNamespace(data={"wger": {entry.entry_id: {"coordinator": coordinator}}})
        registry = MagicMock()
        registry.async_get_entity_id.side_effect = (
            lambda platform, domain, unique_id:
            "sensor.last_workout" if unique_id == "wger_last_workout" else None
        )
        registry.async_get.return_value = SimpleNamespace(config_entry_id="alice-entry")
        with patch("wger.sensor.er.async_get", return_value=registry):
            await async_setup_sensors(hass, entry, MagicMock())
        registry.async_update_entity.assert_called_once_with(
            "sensor.last_workout", new_unique_id="wger_alice-entry_last_workout"
        )

    async def test_other_account_does_not_claim_legacy_entity(self):
        entry = SimpleNamespace(entry_id="bob-entry")
        coordinator = MagicMock(entry=entry)
        hass = SimpleNamespace(data={"wger": {entry.entry_id: {"coordinator": coordinator}}})
        registry = MagicMock()
        registry.async_get_entity_id.return_value = "sensor.last_workout"
        registry.async_get.return_value = SimpleNamespace(config_entry_id="alice-entry")
        add_entities = MagicMock()
        with patch("wger.sensor.er.async_get", return_value=registry):
            await async_setup_sensors(hass, entry, add_entities)
        registry.async_update_entity.assert_not_called()
        entities = list(add_entities.call_args.args[0])
        self.assertEqual(len(entities), len(SENSORS))
        self.assertEqual(
            {entity.unique_id for entity in entities},
            {f"wger_bob-entry_{description.key}" for description in SENSORS},
        )


if __name__ == "__main__":
    unittest.main()
