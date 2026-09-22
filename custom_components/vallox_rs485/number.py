"""Number entities for Vallox RS485."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import ValloxConfigEntry
from .const import (
    REQ_HEATING_SETPOINT,
    REQ_PREHEATING_SETPOINT,
    REQ_BYPASS_SETPOINT,
    REQ_INPUT_FAN_STOP,
    REQ_CELL_DEFROST,
    REQ_FAN_SPEED_MIN,
    REQ_FAN_SPEED_MAX,
    REQ_SERVICE_REMINDER,
    REQ_CO2_SETPOINT,
    REQ_HUMIDITY_LEVEL,
)
from .coordinator import ValloxCoordinator
from .entity import ValloxDescribedEntity
from .vallox_protocol import ValloxState

# The coordinator owns the bus; entities never reach it in parallel.
PARALLEL_UPDATES = 1


@dataclass(frozen=True)
class ValloxNumberEntityDescription(NumberEntityDescription):
    """Describes a Vallox number entity."""

    value_fn: Callable[[ValloxState], int | None] = lambda x: None
    set_fn: str = ""
    required_registers: tuple[int, ...] | None = None


NUMBER_DESCRIPTIONS: tuple[ValloxNumberEntityDescription, ...] = (
    ValloxNumberEntityDescription(
        key="heating_setpoint",
        translation_key="heating_setpoint",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=10,
        native_max_value=30,
        native_step=1,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda state: state.heating_setpoint,
        set_fn="async_set_heating_setpoint",
        required_registers=REQ_HEATING_SETPOINT,
    ),
    ValloxNumberEntityDescription(
        key="preheating_setpoint",
        translation_key="preheating_setpoint",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=-6,
        native_max_value=15,
        native_step=1,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda state: state.preheating_setpoint,
        set_fn="async_set_preheating_setpoint",
        required_registers=REQ_PREHEATING_SETPOINT,
    ),
    ValloxNumberEntityDescription(
        key="bypass_setpoint",
        translation_key="bypass_setpoint",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=0,
        native_max_value=20,
        native_step=1,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda state: state.bypass_setpoint,
        set_fn="async_set_bypass_setpoint",
        required_registers=REQ_BYPASS_SETPOINT,
    ),
    ValloxNumberEntityDescription(
        key="input_fan_stop_threshold",
        translation_key="input_fan_stop_threshold",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=-6,
        native_max_value=15,
        native_step=1,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda state: state.input_fan_stop_threshold,
        set_fn="async_set_input_fan_stop_threshold",
        required_registers=REQ_INPUT_FAN_STOP,
    ),
    ValloxNumberEntityDescription(
        key="cell_defrost_setpoint",
        translation_key="cell_defrost_setpoint",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=0,
        native_max_value=10,
        native_step=1,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda state: state.cell_defrost_setpoint,
        set_fn="async_set_cell_defrost_setpoint",
        required_registers=REQ_CELL_DEFROST,
    ),
    ValloxNumberEntityDescription(
        key="fan_speed_min",
        translation_key="fan_speed_min",
        native_min_value=1,
        native_max_value=8,
        native_step=1,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda state: state.fan_speed_min,
        set_fn="async_set_fan_speed_min",
        required_registers=REQ_FAN_SPEED_MIN,
    ),
    ValloxNumberEntityDescription(
        key="fan_speed_max",
        translation_key="fan_speed_max",
        native_min_value=1,
        native_max_value=8,
        native_step=1,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda state: state.fan_speed_max,
        set_fn="async_set_fan_speed_max",
        required_registers=REQ_FAN_SPEED_MAX,
    ),
    ValloxNumberEntityDescription(
        key="service_reminder_months",
        translation_key="service_reminder_months",
        native_min_value=1,
        native_max_value=15,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda state: state.service_reminder_months,
        set_fn="async_set_service_reminder_months",
        required_registers=REQ_SERVICE_REMINDER,
    ),
    ValloxNumberEntityDescription(
        key="co2_setpoint",
        translation_key="co2_setpoint",
        native_unit_of_measurement="ppm",
        native_min_value=500,
        native_max_value=2000,
        native_step=50,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda state: state.co2_setpoint,
        set_fn="async_set_co2_setpoint",
        required_registers=REQ_CO2_SETPOINT,
    ),
    ValloxNumberEntityDescription(
        key="basic_humidity_level",
        translation_key="basic_humidity_level",
        native_unit_of_measurement="%",
        native_min_value=0,
        native_max_value=100,
        native_step=5,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda state: state.basic_humidity_level,
        set_fn="async_set_basic_humidity_level",
        required_registers=REQ_HUMIDITY_LEVEL,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ValloxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vallox number entities."""
    coordinator = entry.runtime_data

    entities = []
    for description in NUMBER_DESCRIPTIONS:
        if description.required_registers is None:
            entities.append(ValloxNumber(coordinator, description, entry))
        elif coordinator.has_seen_any_register(description.required_registers):
            entities.append(ValloxNumber(coordinator, description, entry))

    async_add_entities(entities)


class ValloxNumber(ValloxDescribedEntity, NumberEntity):
    """Representation of a Vallox number entity."""

    entity_description: ValloxNumberEntityDescription

    def __init__(
        self,
        coordinator: ValloxCoordinator,
        description: ValloxNumberEntityDescription,
        entry: ValloxConfigEntry,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, entry.entry_id, entry.title, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        value = self.entity_description.value_fn(self.coordinator.data)
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        method = getattr(self.coordinator, self.entity_description.set_fn, None)
        if method:
            await method(int(value))
        await self.coordinator.async_request_refresh()

