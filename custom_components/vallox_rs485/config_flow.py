"""Config flow for Vallox RS485 integration."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, TYPE_CHECKING

import serial
import serial.tools.list_ports
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_NAME

if TYPE_CHECKING:
    from homeassistant.helpers.service_info.usb import UsbServiceInfo
else:
    try:
        from homeassistant.helpers.service_info.usb import UsbServiceInfo
    except ImportError:
        from homeassistant.components.usb import UsbServiceInfo

from .const import (
    DEFAULT_BAUDRATE,
    DEFAULT_DEVICE_ADDRESS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    VALLOX_DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

CONF_SERIAL_PORT = "serial_port"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_DEVICE_ADDRESS = "device_address"

RS485_ADAPTERS = {
    ("0403", "6001"): "FTDI FT232R",
    ("1A86", "7523"): "CH340/CH341",
    ("10C4", "EA60"): "CP210x",
    ("067B", "2303"): "Prolific PL2303",
}

DEVICE_ADDRESS_OPTIONS = {
    0x2E: "0x2E (46) - Default",
    0x22: "0x22 (34)",
    0x23: "0x23 (35)",
    0x24: "0x24 (36)",
    0x25: "0x25 (37)",
    0x26: "0x26 (38)",
    0x27: "0x27 (39)",
    0x28: "0x28 (40)",
    0x29: "0x29 (41)",
    0x2A: "0x2A (42)",
    0x2B: "0x2B (43)",
    0x2C: "0x2C (44)",
    0x2D: "0x2D (45)",
    0x2F: "0x2F (47)",
}


def get_stable_device_path(device: str) -> str:
    """Get stable /dev/serial/by-id/ path for a device if available."""
    by_id_path = Path("/dev/serial/by-id")
    if not by_id_path.exists():
        return device

    device_realpath = os.path.realpath(device)
    for link in by_id_path.iterdir():
        if os.path.realpath(str(link)) == device_realpath:
            return str(link)
    return device


def get_serial_ports() -> dict[str, str]:
    """Get available serial ports with stable paths, prioritizing RS485 adapters."""
    ports = serial.tools.list_ports.comports()
    result = {}
    for port in ports:
        vid = f"{port.vid:04X}" if port.vid else None
        pid = f"{port.pid:04X}" if port.pid else None
        adapter_name = RS485_ADAPTERS.get((vid, pid)) if vid and pid else None

        stable_path = get_stable_device_path(port.device)
        display_name = os.path.basename(stable_path)

        if adapter_name:
            result[stable_path] = f"{display_name} - {adapter_name}"
        else:
            result[stable_path] = f"{display_name} - {port.description}"
    return result


def get_rs485_ports() -> list[Any]:
    """Get only ports that match known RS485 adapter VID/PIDs."""
    ports = serial.tools.list_ports.comports()
    rs485_ports: list[Any] = []
    for port in ports:
        vid = f"{port.vid:04X}" if port.vid else None
        pid = f"{port.pid:04X}" if port.pid else None
        if (vid, pid) in RS485_ADAPTERS:
            rs485_ports.append(port)
    return rs485_ports


def validate_vallox_bus(port: str, timeout: float = 3.0) -> bool:
    """Check if valid Vallox traffic exists on the serial port."""
    try:
        ser = serial.Serial(
            port=port,
            baudrate=DEFAULT_BAUDRATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
        )
    except serial.SerialException:
        return False

    try:
        buffer = bytearray()
        bytes_read = 0
        max_bytes = 100

        while bytes_read < max_bytes:
            data = ser.read(1)
            if not data:
                break
            buffer.append(data[0])
            bytes_read += 1

            if len(buffer) >= 6:
                for i in range(len(buffer) - 5):
                    telegram = buffer[i : i + 6]
                    if _is_valid_vallox_telegram(telegram):
                        ser.close()
                        return True
                buffer = buffer[-5:]

        ser.close()
        return False
    except Exception:
        ser.close()
        return False


def _is_valid_vallox_telegram(data: bytes | bytearray) -> bool:
    """Check if 6 bytes form a valid Vallox telegram."""
    if len(data) != 6:
        return False
    if data[0] != VALLOX_DOMAIN:
        return False
    expected_checksum = sum(data[:5]) & 0xFF
    if data[5] != expected_checksum:
        return False
    if not (0x10 <= data[1] <= 0x2F and 0x10 <= data[2] <= 0x2F):
        return False
    return True


class ValloxRS485ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vallox RS485."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_port: str | None = None
        self._discovered_name: str | None = None

    async def async_step_usb(
        self, discovery_info: UsbServiceInfo
    ) -> ConfigFlowResult:
        """Handle USB discovery."""
        device = discovery_info.device
        vid = discovery_info.vid
        pid = discovery_info.pid

        _LOGGER.warning(
            "USB discovery triggered: %s (VID=%s, PID=%s)", device, vid, pid
        )

        stable_path = await self.hass.async_add_executor_job(
            get_stable_device_path, device
        )

        await self.async_set_unique_id(stable_path)
        self._abort_if_unique_id_configured(
            updates={CONF_SERIAL_PORT: stable_path}
        )

        vid_str = vid.upper() if vid else ""
        pid_str = pid.upper() if pid else ""
        adapter_name = RS485_ADAPTERS.get((vid_str, pid_str), "RS485 Adapter")

        _LOGGER.warning("Checking for Vallox traffic on %s", stable_path)
        is_vallox = await self.hass.async_add_executor_job(
            validate_vallox_bus, stable_path
        )
        _LOGGER.warning("Vallox traffic check result: %s", is_vallox)

        if not is_vallox:
            _LOGGER.warning("No Vallox traffic detected on %s", stable_path)
            return self.async_abort(reason="no_vallox_traffic")

        self._discovered_port = stable_path
        self._discovered_name = adapter_name

        self.context["title_placeholders"] = {"name": f"Vallox ({adapter_name})"}

        return await self.async_step_usb_confirm()

    async def async_step_usb_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm USB discovery."""
        if user_input is not None:
            return self.async_create_entry(
                title=user_input.get(CONF_NAME, "Vallox RS485"),
                data={
                    CONF_SERIAL_PORT: self._discovered_port,
                    CONF_SCAN_INTERVAL: user_input.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                    CONF_DEVICE_ADDRESS: user_input.get(
                        CONF_DEVICE_ADDRESS, DEFAULT_DEVICE_ADDRESS
                    ),
                },
            )

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default="Vallox"): str,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
                vol.Optional(
                    CONF_DEVICE_ADDRESS, default=DEFAULT_DEVICE_ADDRESS
                ): vol.In(DEVICE_ADDRESS_OPTIONS),
            }
        )

        return self.async_show_form(
            step_id="usb_confirm",
            data_schema=data_schema,
            description_placeholders={
                "port": self._discovered_port or "unknown",
                "adapter": self._discovered_name or "unknown",
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step (manual configuration)."""
        errors: dict[str, str] = {}

        ports = await self.hass.async_add_executor_job(get_serial_ports)

        if not ports:
            return self.async_abort(reason="no_serial_ports")

        if user_input is not None:
            serial_port = user_input[CONF_SERIAL_PORT]

            await self.async_set_unique_id(serial_port)
            self._abort_if_unique_id_configured()

            can_open = await self.hass.async_add_executor_job(
                self._test_port, serial_port
            )
            if not can_open:
                errors["base"] = "cannot_connect"
            else:
                is_vallox = await self.hass.async_add_executor_job(
                    validate_vallox_bus, serial_port
                )
                if not is_vallox:
                    errors["base"] = "no_vallox_traffic"
                else:
                    return self.async_create_entry(
                        title=user_input.get(CONF_NAME, "Vallox RS485"),
                        data={
                            CONF_SERIAL_PORT: serial_port,
                            CONF_SCAN_INTERVAL: user_input.get(
                                CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                            ),
                            CONF_DEVICE_ADDRESS: user_input.get(
                                CONF_DEVICE_ADDRESS, DEFAULT_DEVICE_ADDRESS
                            ),
                        },
                    )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_SERIAL_PORT): vol.In(ports),
                vol.Optional(CONF_NAME, default="Vallox"): str,
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
                vol.Optional(
                    CONF_DEVICE_ADDRESS, default=DEFAULT_DEVICE_ADDRESS
                ): vol.In(DEVICE_ADDRESS_OPTIONS),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    def _test_port(self, port: str) -> bool:
        """Test if the serial port can be opened."""
        try:
            test_serial = serial.Serial(
                port=port,
                baudrate=DEFAULT_BAUDRATE,
                timeout=1,
            )
            test_serial.close()
            return True
        except serial.SerialException as err:
            _LOGGER.error("Failed to open serial port %s: %s", port, err)
            return False

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of the integration."""
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        if entry is None:
            return self.async_abort(reason="reconfigure_failed")

        errors: dict[str, str] = {}

        if user_input is not None:
            return self.async_update_reload_and_abort(
                entry,
                reason="reconfigure_successful",
                data={
                    **entry.data,
                    CONF_SCAN_INTERVAL: user_input.get(
                        CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL)
                    ),
                    CONF_DEVICE_ADDRESS: user_input.get(
                        CONF_DEVICE_ADDRESS, entry.data.get(CONF_DEVICE_ADDRESS)
                    ),
                },
            )

        current_scan_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        current_device_address = entry.data.get(
            CONF_DEVICE_ADDRESS, DEFAULT_DEVICE_ADDRESS
        )

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=current_scan_interval
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
                vol.Optional(
                    CONF_DEVICE_ADDRESS, default=current_device_address
                ): vol.In(DEVICE_ADDRESS_OPTIONS),
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "serial_port": entry.data.get(CONF_SERIAL_PORT, "unknown"),
            },
        )
