"""Switch entities for Vallox RS485."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from vallox_rs485_protocol import ValloxState

from . import ValloxConfigEntry
from .const import REQ_SELECT
from .coordinator import ValloxCoordinator
from .entity import ValloxDescribedEntity

# The coordinator owns the bus; entities never reach it in parallel.
PARALLEL_UPDATES = 1


@dataclass(frozen=True)
class ValloxSwitchEntityDescription(SwitchEntityDescription):
    """Describes a Vallox switch entity."""

    value_fn: Callable[[ValloxState], bool | None] = lambda x: None
    turn_on_fn: str = ""
    turn_off_fn: str = ""
    required_registers: tuple[int, ...] | None = None


SWITCH_DESCRIPTIONS: tuple[ValloxSwitchEntityDescription, ...] = (
    ValloxSwitchEntityDescription(
        key="power_state",
        translation_key="power_state",
        value_fn=lambda state: state.power_state,
        turn_on_fn="async_set_power_state",
        turn_off_fn="async_set_power_state",
        required_registers=REQ_SELECT,
    ),
    ValloxSwitchEntityDescription(
        key="heating_state",
        translation_key="heating_state",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda state: state.heating_state,
        turn_on_fn="async_set_heating_state",
        turn_off_fn="async_set_heating_state",
        required_registers=REQ_SELECT,
    ),
    ValloxSwitchEntityDescription(
        key="co2_adjust",
        translation_key="co2_adjust",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda state: state.co2_adjust,
        turn_on_fn="async_set_co2_adjust",
        turn_off_fn="async_set_co2_adjust",
        required_registers=REQ_SELECT,
    ),
    ValloxSwitchEntityDescription(
        key="rh_adjust",
        translation_key="rh_adjust",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda state: state.rh_adjust,
        turn_on_fn="async_set_rh_adjust",
        turn_off_fn="async_set_rh_adjust",
        required_registers=REQ_SELECT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ValloxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vallox switches."""
    coordinator = entry.runtime_data

    entities = []
    for description in SWITCH_DESCRIPTIONS:
        if description.required_registers is None or coordinator.has_seen_any_register(
            description.required_registers
        ):
            entities.append(ValloxSwitch(coordinator, description, entry))

    async_add_entities(entities)


class ValloxSwitch(ValloxDescribedEntity, SwitchEntity):
    """Representation of a Vallox switch."""

    entity_description: ValloxSwitchEntityDescription
    _attr_assumed_state = True  # Prevent HA from restoring state on startup

    def __init__(
        self,
        coordinator: ValloxCoordinator,
        description: ValloxSwitchEntityDescription,
        entry: ValloxConfigEntry,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, entry.entry_id, entry.title, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        method = getattr(self.coordinator, self.entity_description.turn_on_fn, None)
        if method:
            await method(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        method = getattr(self.coordinator, self.entity_description.turn_off_fn, None)
        if method:
            await method(False)
        await self.coordinator.async_request_refresh()
