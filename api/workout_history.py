"""WebSocket queries for the on-demand workout history card."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .client import WgerApiError, WgerAuthenticationError
from ..const import DOMAIN
from ..coordinator import _matching_workout_day

_LOGGER = logging.getLogger(__name__)


def _entry_data(hass: HomeAssistant, entry_id: str | None) -> dict | None:
    entries = hass.data.get(DOMAIN, {})
    if entry_id:
        return entries.get(entry_id)
    return next(iter(entries.values())) if len(entries) == 1 else None


async def _enrich_names(api, workouts: list[dict], routines: list[dict]) -> None:
    """Name sessions using their recorded day rather than a date alone."""
    names = {routine.get("id"): routine.get("name") for routine in routines}
    sequences = {}
    for workout in workouts:
        routine_id = workout.get("routine_id")
        workout["routine_name"] = names.get(routine_id)
        if routine_id is None or workout.get("day_id") is None:
            continue
        if routine_id not in sequences:
            try:
                sequence = await api.routines.get_routine_date_sequence_display(routine_id)
                sequences[routine_id] = (
                    sequence if isinstance(sequence, list) else sequence.get("results", [])
                )
            except WgerAuthenticationError:
                raise
            except (WgerApiError, TimeoutError) as err:
                _LOGGER.warning("Unable to load routine sequence %s: %s", routine_id, err)
                sequences[routine_id] = []
        entry = _matching_workout_day(
            sequences[routine_id], workout["day_id"],
            (workout.get("date_start") or "")[:10],
        )
        if entry and entry["day"].get("name"):
            workout["workout_name"] = entry["day"]["name"]


@websocket_api.websocket_command({
    vol.Required("type"): "wger/workout_history",
    vol.Optional("entry_id"): str,
})
@websocket_api.async_response
async def websocket_workout_history(hass, connection, msg):
    """List the latest 20 completed workouts."""
    runtime = _entry_data(hass, msg.get("entry_id"))
    if runtime is None:
        connection.send_error(msg["id"], "entry_not_found", "Select a Wger config entry")
        return
    try:
        workouts = await runtime["api"].workouts.get_completed_workouts()
        routines = runtime["coordinator"].data.get("routines", {}).get("results", [])
        await _enrich_names(runtime["api"], workouts, routines)
    except (WgerApiError, TimeoutError):
        connection.send_error(msg["id"], "wger_unavailable", "Unable to load workouts")
        return
    connection.send_result(msg["id"], {"workouts": workouts})


@websocket_api.websocket_command({
    vol.Required("type"): "wger/workout_detail",
    vol.Required("session_id"): vol.All(str, vol.Match(r"^[0-9a-fA-F-]{36}$")),
    vol.Optional("entry_id"): str,
})
@websocket_api.async_response
async def websocket_workout_detail(hass, connection, msg):
    """Load a selected workout and its recorded sets."""
    runtime = _entry_data(hass, msg.get("entry_id"))
    if runtime is None:
        connection.send_error(msg["id"], "entry_not_found", "Select a Wger config entry")
        return
    try:
        workout = await runtime["api"].workouts.get_workout_analysis(msg["session_id"])
        routines = runtime["coordinator"].data.get("routines", {}).get("results", [])
        await _enrich_names(runtime["api"], [workout], routines)
    except (WgerApiError, TimeoutError):
        connection.send_error(msg["id"], "wger_unavailable", "Unable to load workout detail")
        return
    connection.send_result(msg["id"], {"workout": workout})
