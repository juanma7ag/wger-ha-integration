"""Binary sensors for Wger training goals."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    """Expose whether the weekly training goal has been reached."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([WgerWeeklyGoalAchieved(coordinator, entry)])


class WgerWeeklyGoalAchieved(CoordinatorEntity, BinarySensorEntity):
    """Completion state for the current weekly goal."""

    _attr_name = "Weekly Goal Achieved"
    _attr_icon = "mdi:check-decagram"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"wger_{entry.entry_id}_weekly_goal_achieved"

    @property
    def is_on(self):
        return self.coordinator.data.get("weekly_goal", {}).get("achieved")

    @property
    def extra_state_attributes(self):
        return self.coordinator.data.get("weekly_goal", {})
