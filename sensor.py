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

        return None