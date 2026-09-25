"""Weekly goal boundary, API and entity tests."""

from datetime import datetime
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock
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

from wger.api.workouts import WgerWorkoutsApi
from wger.binary_sensor import WgerWeeklyGoalAchieved
from wger.config_flow import WgerOptionsFlowHandler
from wger.sensor import WgerSensor, SENSORS
from wger.api.weekly_goal import build_weekly_goal, count_completed_sessions, week_bounds

MADRID = ZoneInfo("Europe/Madrid")


def session(id, start, end):
    return {"id": id, "datetime_start": start, "datetime_end": end}


class WeeklyGoalTests(unittest.TestCase):
    def test_completed_only_local_monday_and_no_duplicates(self):
        now = datetime(2026, 9, 21, 12, tzinfo=MADRID)
        monday = session("one", "2026-09-20T22:30:00Z", "2026-09-20T23:30:00Z")
        sessions = [
            monday, monday,
            session("sunday", "2026-09-20T21:00:00Z", "2026-09-20T21:30:00Z"),
            session("open", "2026-09-21T08:00:00Z", None),
            session("future", "2026-09-21T08:00:00Z", "2026-09-22T10:00:00Z"),
            session("invalid", "bad", "bad"),
            session("naive", "2026-09-21T08:00:00", "2026-09-21T09:00:00"),
        ]
        self.assertEqual(count_completed_sessions(sessions, now), 1)

    def test_year_boundary_and_dst(self):
        now = datetime(2027, 1, 1, 12, tzinfo=MADRID)
        self.assertEqual(week_bounds(now)[0].date().isoformat(), "2026-12-28")
        now = datetime(2026, 3, 29, 12, tzinfo=MADRID)
        start, end = week_bounds(now)
        self.assertEqual(start.isoformat(), "2026-03-23T00:00:00+01:00")
        self.assertEqual(end.isoformat(), "2026-03-30T00:00:00+02:00")

    def test_goal_zero_partial_reached_exceeded(self):
        now = datetime(2026, 9, 25, 12, tzinfo=MADRID)
        for completed, progress, remaining, achieved in [
            (0, 0, 3, False), (2, 66.7, 1, False),
            (3, 100, 0, True), (4, 100, 0, True),
        ]:
            result = build_weekly_goal(completed, 3, now)
            self.assertEqual((result["progress"], result["remaining"], result["achieved"]),
                             (progress, remaining, achieved))
            self.assertEqual(result["completed"], completed)
            self.assertEqual(result["week_end"], "2026-09-27")

    def test_entities_share_goal_snapshot(self):
        goal = build_weekly_goal(4, 3, datetime(2026, 9, 25, tzinfo=MADRID))
        entry = SimpleNamespace(entry_id="test")
        coordinator = SimpleNamespace(data={"weekly_goal": goal}, entry=entry,
                                      last_update_success=True)
        for description in SENSORS:
            if description.key.startswith("weekly_goal_"):
                entity = WgerSensor(coordinator, description)
                self.assertEqual(entity.native_value, goal[description.key.removeprefix("weekly_goal_")])
                self.assertEqual(entity.extra_state_attributes, goal)
        binary = WgerWeeklyGoalAchieved(coordinator, entry)
        self.assertTrue(binary.is_on)
        coordinator.last_update_success = False
        self.assertFalse(binary.available)


class WeeklyGoalAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_api_filters_current_local_week(self):
        client = SimpleNamespace(_get=AsyncMock(return_value={"results": [
            session("one", "2026-09-20T22:30:00Z", "2026-09-20T23:00:00Z"),
        ]}))
        now = datetime(2026, 9, 21, 12, tzinfo=MADRID)
        self.assertEqual(await WgerWorkoutsApi(client).get_trainings_this_week(now), 1)
        url = client._get.call_args.args[0]
        query = parse_qs(urlsplit(url).query)
        self.assertEqual(query["datetime_start__gte"], ["2026-09-21T00:00:00+02:00"])
        self.assertEqual(query["datetime_start__lt"], ["2026-09-28T00:00:00+02:00"])

    async def test_options_default_validation_and_preservation(self):
        flow = WgerOptionsFlowHandler(SimpleNamespace(options={"other": True}))
        result = await flow.async_step_init()
        schema = result["data_schema"]
        self.assertEqual(schema({}), {"weekly_goal": 3})
        import voluptuous as vol
        for invalid in (0, -1, 22, "invalid"):
            with self.assertRaises(vol.Invalid):
                schema({"weekly_goal": invalid})
        result = await flow.async_step_init({"weekly_goal": 4})
        self.assertEqual(result["data"], {"other": True, "weekly_goal": 4})
