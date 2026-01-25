"""Switch entities for Vallox RS485."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ValloxConfigEntry
from .const import DOMAIN, REQ_SELECT, get_device_info
from .coordinator import ValloxCoordinator
from .vallox_protocol import ValloxState


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
        icon="mdi:power",
        value_fn=lambda state: state.power_state,
        turn_on_fn="async_set_power_state",
        turn_off_fn="async_set_power_state",
        required_registers=REQ_SELECT,
    ),
    ValloxSwitchEntityDescription(
        key="heating_state",
        translation_key="heating_state",
        icon="mdi:radiator",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda state: state.heating_state,
        turn_on_fn="async_set_heating_state",
        turn_off_fn="async_set_heating_state",
        required_registers=REQ_SELECT,
    ),
    ValloxSwitchEntityDescription(
        key="co2_adjust",
        translation_key="co2_adjust",
        icon="mdi:molecule-co2",
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda state: state.co2_adjust,
        turn_on_fn="async_set_co2_adjust",
        turn_off_fn="async_set_co2_adjust",
        required_registers=REQ_SELECT,
    ),
    ValloxSwitchEntityDescription(
        key="rh_adjust",
        translation_key="rh_adjust",
        icon="mdi:water-percent",
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
        if description.required_registers is None:
            entities.append(ValloxSwitch(coordinator, description, entry))
        elif coordinator.has_seen_any_register(description.required_registers):
            entities.append(ValloxSwitch(coordinator, description, entry))

    async_add_entities(entities)


class ValloxSwitch(CoordinatorEntity[ValloxCoordinator], SwitchEntity):
    """Representation of a Vallox switch."""

    entity_description: ValloxSwitchEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ValloxCoordinator,
        description: ValloxSwitchEntityDescription,
        entry: ValloxConfigEntry,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = get_device_info(entry.entry_id, entry.title)

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

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available:
            return False
        return self.entity_description.value_fn(self.coordinator.data) is not None
