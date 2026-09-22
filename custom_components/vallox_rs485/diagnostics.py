"""Diagnostics support for Vallox RS485."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import ValloxCoordinator

TO_REDACT = {"serial_port"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: ValloxCoordinator = entry.runtime_data

    state = coordinator.data
    raw_values = state._raw_values if state else {}

    diagnostics_data = {
        "config_entry": {
            "entry_id": entry.entry_id,
            "version": entry.version,
            "domain": entry.domain,
            "title": entry.title,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "serial_connected": coordinator._writer is not None,
            "seen_registers": sorted(list(coordinator._seen_registers)),
            "seen_registers_hex": [
                f"0x{r:02X}" for r in sorted(coordinator._seen_registers)
            ],
            "seen_register_count": len(coordinator._seen_registers),
        },
        "state": {
            "temperatures": {
                "outside": state.temp_outside if state else None,
                "exhaust": state.temp_exhaust if state else None,
                "inside": state.temp_inside if state else None,
                "incoming": state.temp_incoming if state else None,
            },
            "humidity": {
                "main": state.humidity if state else None,
                "sensor1": state.humidity_sensor1 if state else None,
                "sensor2": state.humidity_sensor2 if state else None,
                "basic_level": state.basic_humidity_level if state else None,
            },
            "co2": {
                "ppm": state.co2_ppm if state else None,
                "high_byte": state.co2_high if state else None,
                "low_byte": state.co2_low if state else None,
                "setpoint": state.co2_setpoint if state else None,
            },
            "fan": {
                "speed": state.fan_speed if state else None,
                "speed_min": state.fan_speed_min if state else None,
                "speed_max": state.fan_speed_max if state else None,
            },
            "control_states": {
                "power_state": state.power_state if state else None,
                "heating_state": state.heating_state if state else None,
                "co2_adjust": state.co2_adjust if state else None,
                "rh_adjust": state.rh_adjust if state else None,
                "filter_guard": state.filter_guard if state else None,
            },
            "indicators": {
                "heating_indicator": state.heating_indicator if state else None,
                "fault_indicator": state.fault_indicator if state else None,
                "service_reminder_active": (
                    state.service_reminder_active if state else None
                ),
            },
            "fan_status": {
                "supply_fan_on": state.supply_fan_on if state else None,
                "exhaust_fan_on": state.exhaust_fan_on if state else None,
                "pre_heating_on": state.pre_heating_on if state else None,
                "fireplace_booster_on": state.fireplace_booster_on if state else None,
            },
            "setpoints": {
                "heating_setpoint": state.heating_setpoint if state else None,
                "preheating_setpoint": state.preheating_setpoint if state else None,
                "bypass_setpoint": state.bypass_setpoint if state else None,
                "input_fan_stop_threshold": (
                    state.input_fan_stop_threshold if state else None
                ),
                "cell_defrost_setpoint": (
                    state.cell_defrost_setpoint if state else None
                ),
            },
            "service": {
                "service_reminder_months": (
                    state.service_reminder_months if state else None
                ),
                "last_fault": state.last_fault if state else None,
            },
            "other": {
                "damper_motor_position": (
                    state.damper_motor_position if state else None
                ),
                "fault_signal": state.fault_signal if state else None,
                "fireplace_countdown_minutes": (
                    state.fireplace_countdown_minutes if state else None
                ),
            },
        },
        "raw_register_values": {
            f"0x{reg:02X}": value for reg, value in sorted(raw_values.items())
        },
    }

    return diagnostics_data
