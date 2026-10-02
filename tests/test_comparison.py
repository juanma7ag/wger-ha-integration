"""Session selection, units and failure behavior for workout comparisons."""

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

from wger.api.comparison import WgerComparisonApi, build_comparison
from wger.api.client import WgerApiError, WgerAuthenticationError
from wger.coordinator import WgerDataUpdateCoordinator
from wger.sensor import WgerSensor, SENSORS

NOW = datetime(2026, 9, 25, 12, tzinfo=ZoneInfo("Europe/Madrid"))
CURRENT = {"id": "new", "name": "Torso A", "routine": 10, "day": 20, "datetime_start": "2026-09-25T08:00:00Z", "datetime_end": "2026-09-25T09:00:00Z"}
PREVIOUS = {"id": "old", "name": "Torso anterior", "routine": 10, "day": 20, "datetime_start": "2026-09-18T08:00:00Z", "datetime_end": "2026-09-18T08:45:00Z"}
REPS = [{"id": 1, "unit_type": "REPETITIONS"}, {"id": 2, "unit_type": "TIME"}]
WEIGHTS = [{"id": 1, "name": "kg"}, {"id": 2, "name": "lb"}, {"id": 3, "name": "Body Weight"}]


def log(weight="50", reps="10", weight_unit=1, reps_unit=1, exercise=7):
    return {"exercise": exercise, "weight": weight, "repetitions": reps,
            "weight_unit": weight_unit, "repetitions_unit": reps_unit}


def comparison(current_logs, previous_logs):
    return build_comparison(CURRENT, PREVIOUS, current_logs, previous_logs, REPS, WEIGHTS, NOW)


class ComparisonTests(unittest.TestCase):
    def test_signed_deltas_and_local_dates(self):
        result = comparison([log("60"), log("60")], [log()])
        self.assertEqual(result["metrics"]["sets"]["delta"], 1)
        self.assertEqual(result["metrics"]["repetitions"]["delta"], 10)
        self.assertEqual(result["metrics"]["volume"]["delta"], 700)
        self.assertEqual(result["metrics"]["duration"]["delta"], 15)
        self.assertEqual(result["metrics"]["volume"]["percent"], 140)
        self.assertEqual(result["current"]["date_start"], "2026-09-25T10:00:00+02:00")
        self.assertEqual(result["current"]["workout_name"], "Torso A")
        self.assertEqual(result["previous"]["workout_name"], "Torso anterior")

    def test_pounds_converted_to_kg(self):
        result = comparison([log("100", weight_unit=2)], [log("45.359237")])
        self.assertEqual(result["metrics"]["volume"]["delta"], 0)
        self.assertEqual(result["metrics"]["volume"]["current"], 453.6)

    def test_unknown_and_bodyweight_do_not_produce_fake_volume(self):
        for unit in (3, None, 999):
            result = comparison([log(weight_unit=unit)], [log()])
            self.assertIsNone(result["metrics"]["volume"]["delta"])
            self.assertTrue(result["repetitions_comparable"])
            self.assertFalse(result["volume_comparable"])

    def test_time_and_invalid_values_do_not_become_repetitions(self):
        for current in (log(reps_unit=2), log(reps_unit=None), log(reps=None), log(reps="NaN"), log(reps="-1")):
            result = comparison([current], [log()])
            self.assertIsNone(result["metrics"]["repetitions"]["current"])
            self.assertIsNone(result["metrics"]["volume"]["delta"])

    def test_zero_reference_has_no_percentage_and_changes_are_flagged(self):
        result = comparison([log(exercise=8)], [log(weight="0", reps="0")])
        self.assertIsNone(result["metrics"]["volume"]["percent"])
        self.assertEqual(result["metrics"]["volume"]["delta"], 500)
        self.assertTrue(result["exercise_selection_changed"])

    def test_sensor_exposes_snapshot_and_failure_is_unknown(self):
        description = next(d for d in SENSORS if d.key == "workout_comparison")
        data = comparison([log()], [log()])
        coordinator = SimpleNamespace(entry=SimpleNamespace(entry_id="test"),
                                      data={"workout_comparison": data})
        sensor = WgerSensor(coordinator, description)
        self.assertEqual(sensor.native_value, "ready")
        self.assertEqual(sensor.extra_state_attributes, data)
        coordinator.data["workout_comparison"] = {"status": "unavailable"}
        self.assertIsNone(sensor.native_value)


class ComparisonApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_comparison_names_use_recorded_routine_day(self):
        coordinator = object.__new__(WgerDataUpdateCoordinator)
        sequence = [
            {"date": "2026-09-18", "day": {"id": 20, "name": "Espalda-Bíceps"}},
            {"date": "2026-09-25", "day": {"id": 20, "name": "Espalda-Bíceps"}},
            {"date": "2026-09-25", "day": {"id": 21, "name": "Piernas"}},
        ]
        get_sequence = AsyncMock(return_value={"results": sequence})
        coordinator.api = SimpleNamespace(routines=SimpleNamespace(
            get_routine_date_sequence_display=get_sequence))
        result = comparison([log()], [log()])
        result["current"]["workout_name"] = None
        result["previous"]["workout_name"] = None
        await coordinator._async_enrich_comparison_names(result)
        self.assertEqual(result["current"]["workout_name"], "Espalda-Bíceps")
        self.assertEqual(result["previous"]["workout_name"], "Espalda-Bíceps")
        get_sequence.assert_awaited_once_with(10)

    async def test_exact_session_filters_and_complete_logs(self):
        requests = []
        async def get(url):
            requests.append(url)
            parts = urlsplit(url)
            query = parse_qs(parts.query)
            if parts.path == "/workoutsession/":
                self.assertEqual(query["ordering"], ["-datetime_start"])
                self.assertEqual(query["datetime_end__lte"], [NOW.isoformat()])
                if "day" in query:
                    self.assertEqual(query["day"], ["20"])
                    self.assertEqual(query["routine"], ["10"])
                    self.assertEqual(query["datetime_start__lt"], [CURRENT["datetime_start"]])
                    return {"results": [PREVIOUS]}
                return {"results": [CURRENT]}
            if parts.path == "/workoutlog/":
                self.assertIn(query["session"][0], ["new", "old"])
                return {"count": 1, "next": None, "results": [log()]}
            return {"results": REPS if "repetitionunit" in url else WEIGHTS}
        api = WgerComparisonApi(SimpleNamespace(_get=get))
        self.assertEqual((await api.get_comparison(NOW))["status"], "ready")
        self.assertEqual(len(requests), 6)

    async def test_empty_missing_day_and_no_previous(self):
        for responses, status in [
            ([{"results": []}], "no_sessions"),
            ([{"results": [{**CURRENT, "day": None}]}], "no_day"),
            ([{"results": [CURRENT]}, {"results": []}], "no_previous"),
            ([{"results": [{**CURRENT, "datetime_end": None}]}], "invalid_session"),
            ([{"results": [CURRENT]}, {"results": [{**PREVIOUS, "day": 99}]}], "invalid_session"),
        ]:
            api = WgerComparisonApi(SimpleNamespace(_get=AsyncMock(side_effect=responses)))
            self.assertEqual((await api.get_comparison(NOW))["status"], status)

    async def test_partial_or_empty_logs_do_not_produce_totals(self):
        for data, status in [({"results": [], "count": 5, "next": "page2"}, "incomplete_history"),
                             ({"results": []}, "no_logs")]:
            responses = [{"results": [CURRENT]}, {"results": [PREVIOUS]}, data,
                         {"results": [log()]}, {"results": REPS}, {"results": WEIGHTS}]
            api = WgerComparisonApi(SimpleNamespace(_get=AsyncMock(side_effect=responses)))
            self.assertEqual((await api.get_comparison(NOW))["status"], status)

    async def test_optional_failure_preserves_other_sensors_but_auth_propagates(self):
        coordinator = object.__new__(WgerDataUpdateCoordinator)
        call = AsyncMock(side_effect=WgerApiError("offline"))
        coordinator.api = SimpleNamespace(comparison=SimpleNamespace(get_comparison=call))
        self.assertEqual(await coordinator._async_fetch_comparison(NOW), {"status": "unavailable"})
        call.side_effect = WgerAuthenticationError("expired")
        with self.assertRaises(WgerAuthenticationError):
            await coordinator._async_fetch_comparison(NOW)
