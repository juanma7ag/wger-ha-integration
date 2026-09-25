"""Sensor platform for Wger."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .const import DOMAIN
from .coordinator import WgerDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class WgerSensorEntityDescription(
    SensorEntityDescription,
):
    """Wger sensor description."""


SENSORS: tuple[
    WgerSensorEntityDescription,
    ...
] = (
    WgerSensorEntityDescription(
        key="weekly_streak", name="Weekly Streak",
        native_unit_of_measurement="weeks", icon="mdi:fire",
    ),
    WgerSensorEntityDescription(
        key="weekly_best_streak", name="Weekly Best Streak",
        native_unit_of_measurement="weeks", icon="mdi:trophy-outline",
    ),
    WgerSensorEntityDescription(
        key="weekly_goal_target", name="Weekly Goal Target", icon="mdi:target",
    ),
    WgerSensorEntityDescription(
        key="weekly_goal_progress", name="Weekly Goal Progress",
        native_unit_of_measurement="%", icon="mdi:progress-check",
    ),
    WgerSensorEntityDescription(
        key="weekly_goal_remaining", name="Weekly Goal Remaining", icon="mdi:calendar-check",
    ),
    WgerSensorEntityDescription(
        key="current_weight",
        name="Current Weight",
        native_unit_of_measurement="kg",
        icon="mdi:scale-bathroom",
    ),
    WgerSensorEntityDescription(
        key="trainings_this_week",
        name="Trainings This Week",
        icon="mdi:dumbbell",
    ),
    WgerSensorEntityDescription(
        key="last_session",
        name="Last Session",
        icon="mdi:history",
    ),
    WgerSensorEntityDescription(
        key="last_workout",
        name="Last Workout",
        icon="mdi:history",
    ),
    WgerSensorEntityDescription(
        key="workout_progress",
        name="Workout Progress",
        icon="mdi:chart-line",
    ),
    WgerSensorEntityDescription(
        key="last_workout_duration",
        name="Last Workout Duration",
        native_unit_of_measurement="min",
        icon="mdi:timer-outline",
    ),
    WgerSensorEntityDescription(
        key="days_since_last_workout",
        name="Days Since Last Workout",
        native_unit_of_measurement="d",
        icon="mdi:calendar-clock",
    ),
    WgerSensorEntityDescription(
        key="weekly_volume",
        name="Weekly Volume",
        native_unit_of_measurement="kg",
        icon="mdi:weight-kilogram",
    ),
    WgerSensorEntityDescription(
        key="weekly_sets",
        name="Weekly Sets",
        native_unit_of_measurement="sets",
        icon="mdi:counter",
    ),
    WgerSensorEntityDescription(
        key="weekly_intensity",
        name="Weekly Intensity",
        native_unit_of_measurement="%",
        icon="mdi:chart-line",
    ),
    WgerSensorEntityDescription(
        key="weekly_repetitions",
        name="Weekly Repetitions",
        native_unit_of_measurement="reps",
        icon="mdi:repeat",
    ),
    WgerSensorEntityDescription(
        key="todays_workout",
        name="Today's Workout",
        icon="mdi:calendar-today",
    ),
    WgerSensorEntityDescription(
        key="todays_exercises",
        name="Today's Exercises",
        icon="mdi:dumbbell",
    ),
    WgerSensorEntityDescription(
        key="todays_sets",
        name="Today's Sets",
        native_unit_of_measurement="sets",
        icon="mdi:counter",
    ),
    WgerSensorEntityDescription(
        key="todays_repetitions",
        name="Today's Repetitions",
        native_unit_of_measurement="reps",
        icon="mdi:repeat",
    ),
    WgerSensorEntityDescription(
        key="next_workout",
        name="Next Workout",
        icon="mdi:calendar-arrow-right",
    ),
    WgerSensorEntityDescription(
        key="next_exercises",
        name="Next Exercises",
        icon="mdi:dumbbell-arrow-right",
    ),
    WgerSensorEntityDescription(
        key="next_sets",
        name="Next Sets",
        native_unit_of_measurement="sets",
        icon="mdi:counter",
    ),
    WgerSensorEntityDescription(
        key="next_repetitions",
        name="Next Repetitions",
        native_unit_of_measurement="reps",
        icon="mdi:repeat",
    ),
)


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities,
) -> None:
    """Set up sensors."""

    coordinator: WgerDataUpdateCoordinator = (
        hass.data[DOMAIN][entry.entry_id]["coordinator"]
    )

    async_add_entities(
        WgerSensor(
            coordinator,
            description,
        )
        for description in SENSORS
    )


class WgerSensor(
    CoordinatorEntity,
    SensorEntity,
):
    """Generic Wger sensor."""

    entity_description: WgerSensorEntityDescription

    def __init__(
            self,
            coordinator: WgerDataUpdateCoordinator,
            description: WgerSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""

        super().__init__(coordinator)

        self.entity_description = description

        self._attr_unique_id = (
            f"wger_{coordinator.entry.entry_id}_{description.key}"
            if description.key.startswith("weekly_goal_")
            or description.key in ("weekly_streak", "weekly_best_streak")
            else f"wger_{description.key}"
        )

    @property
    def native_value(self):
        """Return sensor state."""

        key = self.entity_description.key

        if key in ("weekly_streak", "weekly_best_streak"):
            metric = "current_streak" if key == "weekly_streak" else "best_streak"
            return self.coordinator.data.get("weekly_consistency", {}).get(metric)


        if key.startswith("weekly_goal_"):
            return self.coordinator.data.get("weekly_goal", {}).get(
                key.removeprefix("weekly_goal_")
            )

        if key == "current_weight":
            return self.coordinator.current_weight

        if key == "trainings_this_week":
            return self.coordinator.trainings_this_week

        if key == "last_session":
            session = (
                self.coordinator.latest_session
            )

            if not session:
                return None

            return session.get(
                "datetime_start"
            )

        if key == "last_workout":
            workout = (
                self.coordinator.last_workout
            )

            if not workout:
                return None

            return (
                workout.get(
                    "workout_name"
                )
                or workout.get(
                    "routine_name"
                )
                or "Last Workout"
            )

        if key == "workout_progress":
            progress = (
                self.coordinator.workout_progress
            )

            return len(progress)

        if key == "last_workout_duration":
            return (
                self.coordinator.last_workout_duration
            )

        if key == "days_since_last_workout":
            return (
                self.coordinator.days_since_last_workout
            )

        if key == "weekly_volume":
            return self.coordinator.weekly_volume

        if key == "weekly_sets":
            return self.coordinator.weekly_sets

        if key == "weekly_intensity":
            intensity = (
                self.coordinator.weekly_intensity
            )

            if intensity is None:
                return None

            return round(
                float(intensity) * 100,
                1,
            )

        if key == "weekly_repetitions":
            return (
                self.coordinator.weekly_repetitions
            )

        if key == "todays_workout":
            workout = (
                self.coordinator.todays_workout
            )

            if not workout:
                return None

            return workout.get(
                "day",
                {},
            ).get(
                "name"
            )

        if key == "todays_exercises":
            return (
                self.coordinator.todays_exercises
            )

        if key == "todays_sets":
            return self.coordinator.todays_sets

        if key == "todays_repetitions":
            return (
                self.coordinator.todays_repetitions
            )

        if key == "next_workout":
            workout = (
                self.coordinator.next_workout
            )

            if not workout:
                return None

            return workout.get(
                "day",
                {},
            ).get(
                "name"
            )

        if key == "next_exercises":
            return self.coordinator.next_exercises

        if key == "next_sets":
            return self.coordinator.next_sets

        if key == "next_repetitions":
            return self.coordinator.next_repetitions

        return None

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""

        key = self.entity_description.key

        if key in ("weekly_streak", "weekly_best_streak"):
            return self.coordinator.data.get("weekly_consistency", {})


        if key.startswith("weekly_goal_"):
            return self.coordinator.data.get("weekly_goal", {})

        if key == "last_workout":
            workout = (
                self.coordinator.last_workout
            )

            if not workout:
                return None

            return {
                "session_id": workout.get(
                    "session_id"
                ),
                "routine_id": workout.get(
                    "routine_id"
                ),
                "iteration": workout.get(
                    "iteration"
                ),
                "date": workout.get(
                    "date"
                ),
                "date_start": workout.get(
                    "date_start"
                ),
                "date_end": workout.get(
                    "date_end"
                ),
                "duration": workout.get(
                    "duration"
                ),
                "workout_name": workout.get(
                    "workout_name"
                ),
                "routine_name": workout.get(
                    "routine_name"
                ),
                "totals": workout.get(
                    "totals",
                    {},
                ),
                "average_rir": workout.get(
                    "average_rir"
                ),
                "exercises": workout.get(
                    "exercises",
                    [],
                ),
                "muscle_distribution": workout.get(
                    "muscle_distribution",
                    [],
                ),
                "muscle_distribution_note": workout.get(
                    "muscle_distribution_note"
                ),
            }

        if key == "workout_progress":
            progress = (
                self.coordinator.workout_progress
            )

            return {
                "workouts": progress,
                "total_workouts": len(
                    progress
                ),
            }

        if key not in (
                "todays_workout",
                "next_workout",
        ):
            return None

        workout = (
            self.coordinator.todays_workout
            if key == "todays_workout"
            else self.coordinator.next_workout
        )

        if not workout:
            return None

        day = workout.get(
            "day",
            {},
        )

        exercise_details = workout.get(
            "exercise_details",
            {},
        )

        attributes = {
            "date": workout.get(
                "date"
            ),
            "day_id": day.get(
                "id"
            ),
            "order": day.get(
                "order"
            ),
            "iteration": workout.get(
                "iteration"
            ),
            "is_rest": day.get(
                "is_rest"
            ),
            "need_logs_to_advance": day.get(
                "need_logs_to_advance"
            ),
            "type": day.get(
                "type"
            ),
            "description": day.get(
                "description"
            ),
        }

        attributes["workout_name"] = day.get(
            "name"
        )

        attributes["exercise_count"] = len(
            [
                exercise_id
                for slot in workout.get(
                    "slots",
                    [],
                )
                for exercise_id in slot.get(
                    "exercises",
                    [],
                )
            ]
        )

        attributes["total_sets"] = 0
        attributes["total_repetitions"] = 0
        attributes["exercise_names"] = []

        exercises = []

        for slot in workout.get(
                "slots",
                [],
        ):
            for exercise_id in slot.get(
                    "exercises",
                    [],
            ):
                details = exercise_details.get(
                    str(exercise_id),
                    {},
                )

                exercise_data = {
                    "exercise_id": exercise_id,
                    "name": details.get(
                        "name"
                    ),
                    "category": details.get(
                        "category"
                    ),
                    "muscles": details.get(
                        "muscles",
                        [],
                    ),
                    "muscles_secondary": details.get(
                        "muscles_secondary",
                        [],
                    ),
                    "muscle_names": [
                        muscle.get("name")
                        for muscle in details.get(
                            "muscles",
                            [],
                        )
                        if muscle.get("name")
                    ],
                    "muscle_names_secondary": [
                        muscle.get("name")
                        for muscle in details.get(
                            "muscles_secondary",
                            [],
                        )
                        if muscle.get("name")
                    ],
                    "equipment": details.get(
                        "equipment",
                        [],
                    ),
                    "equipment_names": [
                        item.get("name")
                        for item in details.get(
                            "equipment",
                            [],
                        )
                        if item.get("name")
                    ],
                    "image": details.get(
                        "image"
                    ),
                    "thumbnail_small": details.get(
                        "thumbnail_small"
                    ),
                    "thumbnail_medium": details.get(
                        "thumbnail_medium"
                    ),
                    "description": details.get(
                        "description"
                    ),
                    "notes": details.get(
                        "notes",
                        [],
                    ),
                    "images": details.get(
                        "images",
                        [],
                    ),
                    "videos": details.get(
                        "videos",
                        [],
                    ),
                    "variation_group": details.get(
                        "variation_group"
                    ),
                    "sets": [],
                    "total_sets": 0,
                    "total_repetitions": 0,
                }

                for workout_set in slot.get(
                        "sets",
                        [],
                ):
                    if workout_set.get(
                            "exercise"
                    ) != exercise_id:
                        continue

                    set_data = {
                        "sets": workout_set.get(
                            "sets"
                        ),
                        "repetitions": workout_set.get(
                            "repetitions"
                        ),
                        "weight": workout_set.get(
                            "weight"
                        ),
                        "weight_unit": workout_set.get(
                            "weight_unit"
                        ),
                        "rir": workout_set.get(
                            "rir"
                        ),
                        "rpe": workout_set.get(
                            "rpe"
                        ),
                        "rest": workout_set.get(
                            "rest"
                        ),
                        "type": workout_set.get(
                            "type"
                        ),
                        "text_repr": workout_set.get(
                            "text_repr"
                        ),
                        "comment": workout_set.get(
                            "comment"
                        ),
                    }

                    exercise_data["sets"].append(
                        set_data
                    )

                    try:
                        sets_value = int(
                            workout_set.get(
                                "sets"
                            ) or 0
                        )
                    except (
                            TypeError,
                            ValueError,
                    ):
                        sets_value = 0

                    try:
                        repetitions_value = int(
                            workout_set.get(
                                "repetitions"
                            ) or 0
                        )
                    except (
                            TypeError,
                            ValueError,
                    ):
                        repetitions_value = 0

                    exercise_data["total_sets"] += (
                        sets_value
                    )

                    exercise_data["total_repetitions"] += (
                        sets_value * repetitions_value
                    )

                    attributes["total_sets"] += (
                        sets_value
                    )

                    attributes["total_repetitions"] += (
                        sets_value * repetitions_value
                    )

                if exercise_data["name"]:
                    attributes["exercise_names"].append(
                        exercise_data["name"]
                    )

                exercises.append(
                    exercise_data
                )

        attributes["exercises"] = exercises

        return attributes