"""Sensor entities for Vallox RS485."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    EntityCategory,
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import ValloxConfigEntry
from .const import (
    get_device_info,
    DOMAIN,
    REQ_TEMP_OUTSIDE,
    REQ_TEMP_EXHAUST,
    REQ_TEMP_INSIDE,
    REQ_TEMP_INCOMING,
    REQ_HUMIDITY,
    REQ_HUMIDITY_SENSOR1,
    REQ_HUMIDITY_SENSOR2,
    REQ_CO2,
    REQ_FAN_SPEED,
    REQ_LAST_FAULT,
    REQ_FIREPLACE_COUNTDOWN,
    REQ_POST_HEATING_CNT,
)
from .coordinator import ValloxCoordinator
from .vallox_protocol import ValloxState


@dataclass(frozen=True)
class ValloxSensorEntityDescription(SensorEntityDescription):
    """Describes a Vallox sensor entity."""

    value_fn: Callable[[ValloxState], int | float | str | None] = lambda x: None
    required_registers: tuple[int, ...] | None = None


def _calculate_efficiency(state: ValloxState) -> int | None:
    """Calculate heat recovery efficiency percentage."""
    if (
        state.temp_outside is None
        or state.temp_inside is None
        or state.temp_incoming is None
    ):
        return None

    temp_diff = state.temp_inside - state.temp_outside
    if temp_diff == 0:
        return 0

    efficiency = ((state.temp_incoming - state.temp_outside) / temp_diff) * 100
    return max(0, min(100, int(round(efficiency))))


SENSOR_DESCRIPTIONS: tuple[ValloxSensorEntityDescription, ...] = (
    ValloxSensorEntityDescription(
        key="temp_outside",
        translation_key="temp_outside",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: state.temp_outside,
        required_registers=REQ_TEMP_OUTSIDE,
    ),
    ValloxSensorEntityDescription(
        key="temp_exhaust",
        translation_key="temp_exhaust",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: state.temp_exhaust,
        required_registers=REQ_TEMP_EXHAUST,
    ),
    ValloxSensorEntityDescription(
        key="temp_inside",
        translation_key="temp_inside",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: state.temp_inside,
        required_registers=REQ_TEMP_INSIDE,
    ),
    ValloxSensorEntityDescription(
        key="temp_incoming",
        translation_key="temp_incoming",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: state.temp_incoming,
        required_registers=REQ_TEMP_INCOMING,
    ),
    ValloxSensorEntityDescription(
        key="humidity",
        translation_key="humidity",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: state.humidity,
        required_registers=REQ_HUMIDITY,
    ),
    ValloxSensorEntityDescription(
        key="humidity_sensor1",
        translation_key="humidity_sensor1",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: state.humidity_sensor1,
        required_registers=REQ_HUMIDITY_SENSOR1,
    ),
    ValloxSensorEntityDescription(
        key="humidity_sensor2",
        translation_key="humidity_sensor2",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: state.humidity_sensor2,
        required_registers=REQ_HUMIDITY_SENSOR2,
    ),
    ValloxSensorEntityDescription(
        key="fan_speed",
        translation_key="fan_speed",
        icon="mdi:fan",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: state.fan_speed,
        required_registers=REQ_FAN_SPEED,
    ),
    ValloxSensorEntityDescription(
        key="co2_ppm",
        translation_key="co2_ppm",
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
        device_class=SensorDeviceClass.CO2,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda state: state.co2_ppm,
        required_registers=REQ_CO2,
    ),
    ValloxSensorEntityDescription(
        key="heat_recovery_efficiency",
        translation_key="heat_recovery_efficiency",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:heat-wave",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_calculate_efficiency,
        required_registers=REQ_TEMP_INSIDE,
    ),
    ValloxSensorEntityDescription(
        key="last_fault",
        translation_key="last_fault",
        icon="mdi:alert-circle",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.last_fault,
        required_registers=REQ_LAST_FAULT,
    ),
    ValloxSensorEntityDescription(
        key="fireplace_countdown",
        translation_key="fireplace_countdown",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        icon="mdi:fireplace",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.fireplace_countdown_minutes,
        required_registers=REQ_FIREPLACE_COUNTDOWN,
    ),
    ValloxSensorEntityDescription(
        key="post_heating_on_counter",
        translation_key="post_heating_on_counter",
        icon="mdi:counter",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda state: state.post_heating_on_counter,
        required_registers=REQ_POST_HEATING_CNT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ValloxConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Vallox sensors."""
    coordinator = entry.runtime_data

    entities = []
    for description in SENSOR_DESCRIPTIONS:
        if description.required_registers is None:
            entities.append(ValloxSensor(coordinator, description, entry))
        elif coordinator.has_seen_any_register(description.required_registers):
            entities.append(ValloxSensor(coordinator, description, entry))

    async_add_entities(entities)


class ValloxSensor(CoordinatorEntity[ValloxCoordinator], SensorEntity):
    """Representation of a Vallox sensor."""

    entity_description: ValloxSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ValloxCoordinator,
        description: ValloxSensorEntityDescription,
        entry: ValloxConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = get_device_info(entry.entry_id, entry.title)

    @property
    def native_value(self) -> int | float | str | None:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available:
            return False
        return self.entity_description.value_fn(self.coordinator.data) is not None
