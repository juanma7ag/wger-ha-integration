"""Sensor platform for Wger."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
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

        super().__init__(coordinator)

        self.entity_description = description

        self._attr_unique_id = (
            f"wger_{description.key}"
        )

    @property
    def native_value(self):
        """Return state."""

        if self.entity_description.key == "current_weight":
            return self.coordinator.current_weight

        if self.entity_description.key == "trainings_this_week":
            return self.coordinator.trainings_this_week

        if self.entity_description.key == "last_session":
            session = (
                self.coordinator.latest_session
            )

            if not session:
                return None

            return session.get(
                "datetime_start"
            )

        if self.entity_description.key == "last_workout_duration":
            return self.coordinator.last_workout_duration

        if self.entity_description.key == "days_since_last_workout":
            return self.coordinator.days_since_last_workout

        return None