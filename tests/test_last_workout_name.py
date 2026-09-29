"""The last workout title follows the session's recorded day."""

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

ROOT = Path(__file__).resolve().parents[1]
if "wger" not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        "wger", ROOT / "__init__.py", submodule_search_locations=[str(ROOT)]
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["wger"] = module
    spec.loader.exec_module(module)

from wger.api.workouts import WgerWorkoutsApi
from wger.coordinator import _matching_workout_day


class LastWorkoutNameTests(unittest.TestCase):
    def test_session_day_wins_over_another_day_on_the_same_date(self):
        sequence = [
            {"date": "2026-09-29", "day": {"id": 2, "name": "Piernas"}, "iteration": 3},
            {"date": "2026-09-29", "day": {"id": 1, "name": "Torso"}, "iteration": 3},
        ]
        self.assertEqual(
            _matching_workout_day(sequence, 1, "2026-09-29")["day"]["name"],
            "Torso",
        )

    def test_recorded_day_can_differ_from_scheduled_date(self):
        sequence = [
            {"date": "2026-09-29", "day": {"id": 2, "name": "Piernas"}},
            {"date": "2026-09-30", "day": {"id": 1, "name": "Torso"}},
        ]
        self.assertEqual(
            _matching_workout_day(sequence, 1, "2026-09-29")["day"]["name"],
            "Torso",
        )
        self.assertIsNone(_matching_workout_day(sequence, 3, "2026-09-29"))


class LastWorkoutAnalysisTests(unittest.IsolatedAsyncioTestCase):
    async def test_analysis_keeps_the_session_day_when_there_are_no_logs(self):
        api = WgerWorkoutsApi(SimpleNamespace())
        api.get_latest_session = AsyncMock(return_value={
            "id": 10, "routine": 20, "day": 30,
            "name": "Torso", "datetime_start": "2026-09-29T08:00:00Z",
        })
        api.get_workout_logs = AsyncMock(return_value={"results": []})
        analysis = await api.get_last_workout_analysis()
        self.assertEqual(analysis["day_id"], 30)
