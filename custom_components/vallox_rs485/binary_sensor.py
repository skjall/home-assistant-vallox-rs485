"""Binary sensor entities for Vallox RS485."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ValloxConfigEntry
from .const import DOMAIN, REQ_SELECT, REQ_MULTI_PURPOSE_2, REQ_FLAGS_6, get_device_info
from .coordinator import ValloxCoordinator
from .vallox_protocol import ValloxState


@dataclass(frozen=True)
class ValloxBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a Vallox binary sensor entity."""

    value_fn: Callable[[ValloxState], bool | None] = lambda x: None
    required_registers: tuple[int, ...] | None = None


BINARY_SENSOR_DESCRIPTIONS: tuple[ValloxBinarySensorEntityDescription, ...] = (
    ValloxBinarySensorEntityDescription(
        key="supply_fan",
        translation_key="supply_fan",
        icon="mdi:fan",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda state: state.supply_fan_on,
        required_registers=REQ_MULTI_PURPOSE_2,
    ),
    ValloxBinarySensorEntityDescription(
        key="exhaust_fan",
        translation_key="exhaust_fan",
        icon="mdi:fan",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda state: state.exhaust_fan_on,
        required_registers=REQ_MULTI_PURPOSE_2,
    ),
    ValloxBinarySensorEntityDescription(
        key="pre_heating",
        translation_key="pre_heating",
        icon="mdi:radiator",
        device_class=BinarySensorDeviceClass.HEAT,
        value_fn=lambda state: state.pre_heating_on,
        required_registers=REQ_MULTI_PURPOSE_2,
    ),
    ValloxBinarySensorEntityDescription(
        key="fireplace_booster",
        translation_key="fireplace_booster",
        icon="mdi:fireplace",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda state: state.fireplace_booster_on,
        required_registers=REQ_MULTI_PURPOSE_2,
    ),
    ValloxBinarySensorEntityDescription(
        key="damper_motor_position",
        translation_key="damper_motor_position",
        icon="mdi:swap-horizontal",
        value_fn=lambda state: state.damper_motor_position,
        required_registers=REQ_MULTI_PURPOSE_2,
    ),
    ValloxBinarySensorEntityDescription(
        key="fault_signal",
        translation_key="fault_signal",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.fault_signal,
        required_registers=REQ_MULTI_PURPOSE_2,
    ),
    ValloxBinarySensorEntityDescription(
        key="filter_guard",
        translation_key="filter_guard",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.filter_guard,
        required_registers=REQ_SELECT,
    ),
    ValloxBinarySensorEntityDescription(
        key="service_reminder",
        translation_key="service_reminder",
        icon="mdi:wrench-clock",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.service_reminder_active,
        required_registers=REQ_SELECT,
    ),
    ValloxBinarySensorEntityDescription(
        key="heating_indicator",
        translation_key="heating_indicator",
        icon="mdi:radiator",
        device_class=BinarySensorDeviceClass.HEAT,
        value_fn=lambda state: state.heating_indicator,
        required_registers=REQ_SELECT,
    ),
    ValloxBinarySensorEntityDescription(
        key="remote_control_working",
        translation_key="remote_control_working",
        icon="mdi:remote",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.remote_control_working,
        required_registers=REQ_FLAGS_6,
    ),
    ValloxBinarySensorEntityDescription(
        key="fireplace_boost_active",
        translation_key="fireplace_boost_active",
        icon="mdi:fireplace",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda state: state.fireplace_boost_active,
        required_registers=REQ_FLAGS_6,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ValloxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vallox binary sensors."""
    coordinator = entry.runtime_data

    entities = []
    for description in BINARY_SENSOR_DESCRIPTIONS:
        if description.required_registers is None:
            entities.append(ValloxBinarySensor(coordinator, description, entry))
        elif coordinator.has_seen_any_register(description.required_registers):
            entities.append(ValloxBinarySensor(coordinator, description, entry))

    async_add_entities(entities)


class ValloxBinarySensor(CoordinatorEntity[ValloxCoordinator], BinarySensorEntity):
    """Representation of a Vallox binary sensor."""

    entity_description: ValloxBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ValloxCoordinator,
        description: ValloxBinarySensorEntityDescription,
        entry: ValloxConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = get_device_info(entry.entry_id, entry.title)

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available:
            return False
        return self.entity_description.value_fn(self.coordinator.data) is not None
