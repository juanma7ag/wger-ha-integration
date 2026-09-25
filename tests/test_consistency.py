"""Weekly streak semantics and integration wiring."""

from datetime import datetime, timedelta
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
if "wger" not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        "wger", ROOT / "__init__.py", submodule_search_locations=[str(ROOT)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["wger"] = module
    spec.loader.exec_module(module)

from wger.api.consistency import build_consistency
from wger.api.weekly_goal import week_bounds
from wger.api.workouts import WgerWorkoutsApi
from wger.coordinator import WgerDataUpdateCoordinator
from wger.sensor import WgerSensor, SENSORS

NOW = datetime(2026, 9, 25, 12, tzinfo=ZoneInfo("Europe/Madrid"))


def sessions_for_weeks(counts, now=NOW):
    monday, _ = week_bounds(now)
    sessions = []
    for age, count in counts.items():
        for index in range(count):
            start = monday - timedelta(weeks=age) + timedelta(hours=9, minutes=index)
            sessions.append({"id": f"{age}-{index}", "datetime_start": start.isoformat(),
                             "datetime_end": (start + timedelta(hours=1)).isoformat()})
    return sessions


class ConsistencyTests(unittest.TestCase):
    def test_open_week_preserves_previous_streak(self):
        result = build_consistency(sessions_for_weeks({0: 1, 1: 3, 2: 4}), 3, NOW)
        self.assertEqual(result["current_streak"], 2)
        self.assertEqual(result["best_streak"], 2)
        self.assertEqual(result["weeks"][-1]["status"], "in_progress")
        self.assertEqual(result["remaining"], 2)

    def test_current_week_extends_streak_and_gap_breaks_it(self):
        result = build_consistency(sessions_for_weeks({0: 3, 1: 3, 3: 3, 4: 3, 5: 3}), 3, NOW)
        self.assertEqual(result["current_streak"], 2)
        self.assertEqual(result["best_streak"], 3)
        self.assertEqual(result["weeks"][-1]["status"], "achieved")
        self.assertEqual(result["weeks"][-3]["status"], "missed")

    def test_new_monday_breaks_unfinished_previous_week(self):
        sessions = sessions_for_weeks({0: 2, 1: 3, 2: 3})
        monday = datetime(2026, 9, 28, tzinfo=NOW.tzinfo)
        result = build_consistency(sessions, 3, monday)
        self.assertEqual(result["current_streak"], 0)
        self.assertEqual(result["best_streak"], 2)

    def test_empty_history_and_changed_target(self):
        result = build_consistency([], 3, NOW)
        self.assertEqual(result["current_streak"], 0)
        self.assertEqual(len(result["weeks"]), 12)
        sessions = sessions_for_weeks({0: 2, 1: 2})
        self.assertEqual(build_consistency(sessions, 2, NOW)["current_streak"], 2)
        self.assertEqual(build_consistency(sessions, 3, NOW)["current_streak"], 0)

    def test_window_boundary_is_explicit_and_older_sessions_excluded(self):
        result = build_consistency(sessions_for_weeks({i: 1 for i in range(54)}), 1, NOW)
        self.assertEqual(result["current_streak"], 52)
        self.assertEqual(result["best_streak"], 52)
        self.assertTrue(result["streak_at_least"])

    def test_timezone_duplicates_invalid_and_unfinished_sessions(self):
        monday = {"id": "monday", "datetime_start": "2026-09-20T22:30:00Z",
                  "datetime_end": "2026-09-20T23:30:00Z"}
        sessions = [monday, monday, {"id": "bad"},
                    {"id": "open", "datetime_start": "2026-09-21T10:00:00Z", "datetime_end": None},
                    {"id": "future", "datetime_start": "2026-09-26T10:00:00Z", "datetime_end": "2026-09-26T11:00:00Z"}]
        result = build_consistency(sessions, 1, NOW)
        self.assertEqual(result["current_week_completed"], 1)
        self.assertEqual(result["current_streak"], 1)

    def test_streak_across_year_and_dst_changes(self):
        for now in (datetime(2027, 1, 1, 12, tzinfo=NOW.tzinfo),
                    datetime(2026, 3, 30, 12, tzinfo=NOW.tzinfo)):
            result = build_consistency(sessions_for_weeks({0: 1, 1: 1, 2: 1}, now), 1, now)
            self.assertEqual(result["current_streak"], 3)

    def test_sensor_state_and_incomplete_history(self):
        entry = SimpleNamespace(entry_id="test")
        result = build_consistency(sessions_for_weeks({1: 3}), 3, NOW)
        coordinator = SimpleNamespace(data={"weekly_consistency": result}, entry=entry,
                                      last_update_success=True)
        for description in SENSORS:
            if description.key in ("weekly_streak", "weekly_best_streak"):
                sensor = WgerSensor(coordinator, description)
                self.assertEqual(sensor.native_value, 1)
                self.assertEqual(sensor.extra_state_attributes, result)
        coordinator.data["weekly_consistency"] = {"history_complete": False}
        self.assertIsNone(sensor.native_value)


class ConsistencyAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_api_date_filters_and_single_request(self):
        client = SimpleNamespace(_get=AsyncMock(return_value={"results": []}))
        result = await WgerWorkoutsApi(client).get_weekly_consistency(3, NOW)
        self.assertEqual(result["current_streak"], 0)
        client._get.assert_awaited_once()
        query = parse_qs(urlsplit(client._get.call_args.args[0]).query)
        self.assertEqual(query["limit"], ["999"])
        self.assertEqual(query["datetime_start__gte"], ["2025-09-29T00:00:00+02:00"])
        self.assertEqual(query["datetime_start__lt"], ["2026-09-28T00:00:00+02:00"])

    async def test_incomplete_history_is_not_reported_as_zero(self):
        client = SimpleNamespace(_get=AsyncMock(return_value={"results": [], "count": 1000, "next": "page2"}))
        result = await WgerWorkoutsApi(client).get_weekly_consistency(3, NOW)
        self.assertFalse(result["history_complete"])
        self.assertNotIn("current_streak", result)
        client._get.assert_awaited_once()

    async def test_coordinator_uses_configured_target_and_shared_time(self):
        coordinator = object.__new__(WgerDataUpdateCoordinator)
        coordinator.entry = SimpleNamespace(options={"weekly_goal": 4})
        consistency = build_consistency([], 4, NOW)
        workouts = SimpleNamespace(
            get_latest_session=AsyncMock(return_value=None),
            get_trainings_this_week=AsyncMock(return_value=0),
            get_last_workout_analysis=AsyncMock(return_value=None),
            get_workout_progress=AsyncMock(return_value=[]),
            get_weekly_consistency=AsyncMock(return_value=consistency),
        )
        coordinator.api = SimpleNamespace(
            profile=SimpleNamespace(get_profile=AsyncMock(return_value={})),
            routines=SimpleNamespace(get_routines=AsyncMock(return_value={"results": []})),
            measurements=SimpleNamespace(get_weight_entries=AsyncMock(return_value={}),
                                         get_measurements=AsyncMock(return_value={}),
                                         get_current_weight=AsyncMock(return_value=None)),
            workouts=workouts,
        )
        with patch("wger.coordinator.dt_util.now", return_value=NOW):
            result = await coordinator._async_fetch_data()
        workouts.get_weekly_consistency.assert_awaited_once_with(4, NOW)
        self.assertEqual(result["weekly_consistency"], consistency)
        self.assertEqual(result["weekly_goal"]["target"], 4)
