"""On-demand workout history queries."""

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
if "wger" not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        "wger", ROOT / "__init__.py", submodule_search_locations=[str(ROOT)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["wger"] = module
    spec.loader.exec_module(module)

from wger.api.client import WgerApiError
from wger.api.workouts import WgerWorkoutsApi
from wger.api.workout_history import _enrich_names

SESSION_ID = "01a0e931-733b-7e65-8a4e-f718ec08a900"


class WorkoutHistoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_only_completed_sessions(self):
        client = SimpleNamespace(_get=AsyncMock(return_value={"results": [
            {"id": 3, "name": "Torso", "day": 8, "routine": 9,
             "datetime_start": "2026-09-29T08:00:00Z", "datetime_end": "2026-09-29T09:00:00Z"},
            {"id": 4, "datetime_start": "2026-09-29T10:00:00Z", "datetime_end": None},
        ]}))
        result = await WgerWorkoutsApi(client).get_completed_workouts()
        self.assertEqual([item["session_id"] for item in result], [3])
        query = parse_qs(urlsplit(client._get.call_args.args[0]).query)
        self.assertEqual(query["limit"], ["20"])
        self.assertEqual(query["ordering"], ["-datetime_start"])
        self.assertIn("datetime_end__lte", query)

    async def test_detail_requests_only_selected_session_logs(self):
        session = {"id": SESSION_ID, "routine": 9, "day": 8, "name": "Torso",
                   "datetime_start": "2026-09-28T08:00:00Z", "datetime_end": "2026-09-28T09:00:00Z"}
        client = SimpleNamespace(_get=AsyncMock(side_effect=[session, {"count": 0, "results": []}]))
        result = await WgerWorkoutsApi(client).get_workout_analysis(SESSION_ID)
        self.assertEqual(result["day_id"], 8)
        self.assertEqual(result["duration"], 60)
        self.assertEqual(result["totals"]["total_sets"], 0)
        self.assertEqual(parse_qs(urlsplit(client._get.call_args.args[0]).query)["session"], [SESSION_ID])

    async def test_incomplete_logs_do_not_look_like_complete_detail(self):
        session = {"id": SESSION_ID, "datetime_end": "2026-09-28T09:00:00Z"}
        client = SimpleNamespace(_get=AsyncMock(side_effect=[session, {
            "count": 2, "next": "next", "results": [{}],
        }]))
        with self.assertRaises(WgerApiError):
            await WgerWorkoutsApi(client).get_workout_analysis(SESSION_ID)

    async def test_detail_converts_pounds_and_includes_set_units(self):
        session = {"id": SESSION_ID, "routine": 9, "day": 8, "name": "Torso",
                   "datetime_start": "2026-09-28T08:00:00Z", "datetime_end": "2026-09-28T09:00:00Z"}
        logs = {"count": 1, "results": [{
            "id": 11, "session": SESSION_ID, "exercise": 7, "repetitions": "10",
            "repetitions_unit": 1, "weight": "100", "weight_unit": 2,
        }]}
        weights = {"results": [{"id": 2, "name": "lb"}]}
        repetitions = {"results": [{"id": 1, "name": "repetitions", "unit_type": "REPETITIONS"}]}
        client = SimpleNamespace(_get=AsyncMock(side_effect=[session, logs, weights, repetitions]))
        with patch("wger.api.exercises.WgerExercisesApi.get_exercise_details",
                   new_callable=AsyncMock, return_value={"name": "Press banca"}):
            result = await WgerWorkoutsApi(client).get_workout_analysis(SESSION_ID)
        self.assertEqual(result["totals"]["total_volume"], 453.59237)
        self.assertEqual(result["exercises"][0]["sets"][0]["weight_unit_name"], "lb")

    async def test_name_uses_recorded_day_even_when_date_points_to_another(self):
        api = SimpleNamespace(routines=SimpleNamespace(
            get_routine_date_sequence_display=AsyncMock(return_value=[
                {"date": "2026-09-29", "day": {"id": 1, "name": "Piernas"}},
                {"date": "2026-09-30", "day": {"id": 2, "name": "Torso"}},
            ])))
        workouts = [{"session_id": 3, "routine_id": 9, "day_id": 2,
                     "date_start": "2026-09-29T08:00:00Z", "workout_name": "Otro"}]
        await _enrich_names(api, workouts, [{"id": 9, "name": "Fuerza"}])
        self.assertEqual(workouts[0]["workout_name"], "Torso")
        self.assertEqual(workouts[0]["routine_name"], "Fuerza")
