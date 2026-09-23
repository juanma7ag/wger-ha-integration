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
            f"wger_{description.key}"
        )

    @property
    def native_value(self):
        """Return sensor state."""

        key = self.entity_description.key

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
            return (
                self.coordinator.todays_sets
            )

        if key == "todays_repetitions":
            return (
                self.coordinator.todays_repetitions
            )

        return None

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""

        if (
            self.entity_description.key
            != "todays_workout"
        ):
            return None

        workout = (
            self.coordinator.todays_workout
        )

        if not workout:
            return None

        day = workout.get(
            "day",
            {},
        )

        exercise_names = workout.get(
            "exercise_names",
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

        exercises = []

        for slot in workout.get(
            "slots",
            [],
        ):
            for exercise_id in slot.get(
                "exercises",
                [],
            ):
                exercise_data = {
                    "exercise_id": exercise_id,
                    "name": exercise_names.get(
                        str(exercise_id)
                    ),
                    "sets": [],
                }

                for workout_set in slot.get(
                    "sets",
                    [],
                ):
                    if workout_set.get(
                        "exercise"
                    ) != exercise_id:
                        continue

                    exercise_data["sets"].append(
                        {
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
                    )

                exercises.append(
                    exercise_data
                )

        attributes["exercises"] = exercises

        return attributes