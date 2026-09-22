"""Fan entity for Vallox RS485."""
from __future__ import annotations

import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ValloxConfigEntry
from .const import REQ_FAN_SPEED
from .coordinator import ValloxCoordinator
from .entity import ValloxEntity

# The coordinator owns the bus; entities never reach it in parallel.
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ValloxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vallox fan."""
    coordinator = entry.runtime_data

    if coordinator.has_seen_any_register(REQ_FAN_SPEED):
        async_add_entities([ValloxFan(coordinator, entry)])


class ValloxFan(ValloxEntity, FanEntity):
    """Representation of the Vallox ventilation fan."""

    _attr_translation_key = "ventilation"
    _attr_supported_features = FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE
    _attr_speed_count = 8
    _attr_preset_modes = ["1", "2", "3", "4", "5", "6", "7", "8"]

    def __init__(
        self,
        coordinator: ValloxCoordinator,
        entry: ValloxConfigEntry,
    ) -> None:
        """Initialize the fan."""
        super().__init__(coordinator, entry.entry_id, entry.title, "fan")

    @property
    def is_on(self) -> bool | None:
        """Return true if the fan is on."""
        if self.coordinator.data.power_state is None:
            return None
        return self.coordinator.data.power_state

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        if self.coordinator.data.fan_speed is None:
            return None
        # Convert 1-8 to 0-100%
        return int(self.coordinator.data.fan_speed * 100 / 8)

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        if self.coordinator.data.fan_speed is None:
            return None
        return str(self.coordinator.data.fan_speed)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        await self.coordinator.async_set_power_state(True)

        if preset_mode is not None:
            await self.coordinator.async_set_fan_speed(int(preset_mode))
        elif percentage is not None:
            speed = max(1, min(8, math.ceil(percentage * 8 / 100)))
            await self.coordinator.async_set_fan_speed(speed)

        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        await self.coordinator.async_set_power_state(False)
        await self.coordinator.async_request_refresh()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage."""
        if percentage == 0:
            await self.async_turn_off()
            return

        speed = max(1, min(8, math.ceil(percentage * 8 / 100)))
        await self.coordinator.async_set_fan_speed(speed)
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode."""
        await self.coordinator.async_set_fan_speed(int(preset_mode))
        await self.coordinator.async_request_refresh()
