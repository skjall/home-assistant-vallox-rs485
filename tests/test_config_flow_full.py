"""Comprehensive tests for ValloxRS485ConfigFlow covering all methods and branches."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

try:
    from homeassistant.helpers.service_info.usb import UsbServiceInfo
except ImportError:
    from homeassistant.components.usb import UsbServiceInfo

from custom_components.vallox_rs485.config_flow import (
    CONF_DEVICE_ADDRESS,
    CONF_SCAN_INTERVAL,
    CONF_SERIAL_PORT,
    ValloxRS485ConfigFlow,
    _is_valid_vallox_telegram,
    get_rs485_ports,
    get_serial_ports,
    get_stable_device_path,
    validate_vallox_bus,
)
from custom_components.vallox_rs485.const import VALLOX_DOMAIN


class TestGetStableDevicePath:
    """Tests for get_stable_device_path function."""

    def test_no_by_id_directory(self) -> None:
        """Test when /dev/serial/by-id doesn't exist."""
        with patch(
            "custom_components.vallox_rs485.config_flow.Path"
        ) as mock_path_class:
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            mock_path_class.return_value = mock_path

            result = get_stable_device_path("/dev/ttyUSB0")
            assert result == "/dev/ttyUSB0"

    def test_no_matching_link(self) -> None:
        """Test when by-id exists but no matching link."""
        with (
            patch("custom_components.vallox_rs485.config_flow.Path") as mock_path_class,
            patch("os.path.realpath") as mock_realpath,
        ):
            mock_path = MagicMock()
            mock_path.exists.return_value = True

            mock_link = MagicMock()
            mock_link.__str__ = lambda self: "/dev/serial/by-id/other-device"
            mock_path.iterdir.return_value = [mock_link]
            mock_path_class.return_value = mock_path

            mock_realpath.side_effect = lambda p: (
                "/dev/ttyUSB1" if "by-id" in p else "/dev/ttyUSB0"
            )

            result = get_stable_device_path("/dev/ttyUSB0")
            assert result == "/dev/ttyUSB0"


class TestGetSerialPorts:
    """Tests for get_serial_ports function."""

    def test_with_rs485_adapter(self) -> None:
        """Test with known RS485 adapter."""
        mock_port = MagicMock()
        mock_port.device = "/dev/ttyUSB0"
        mock_port.description = "FTDI"
        mock_port.vid = 0x0403
        mock_port.pid = 0x6001

        with (
            patch("serial.tools.list_ports.comports", return_value=[mock_port]),
            patch(
                "custom_components.vallox_rs485.config_flow.get_stable_device_path",
                return_value="/dev/ttyUSB0",
            ),
        ):
            result = get_serial_ports()
            assert "/dev/ttyUSB0" in result
            assert "FTDI" in result["/dev/ttyUSB0"]

    def test_with_unknown_adapter(self) -> None:
        """Test with unknown adapter uses description."""
        mock_port = MagicMock()
        mock_port.device = "/dev/ttyUSB0"
        mock_port.description = "Generic Serial"
        mock_port.vid = None
        mock_port.pid = None

        with (
            patch("serial.tools.list_ports.comports", return_value=[mock_port]),
            patch(
                "custom_components.vallox_rs485.config_flow.get_stable_device_path",
                return_value="/dev/ttyUSB0",
            ),
        ):
            result = get_serial_ports()
            assert "/dev/ttyUSB0" in result
            assert "Generic Serial" in result["/dev/ttyUSB0"]


class TestGetRS485Ports:
    """Tests for get_rs485_ports function."""

    def test_matches_known_adapters(self) -> None:
        """Test filters to known RS485 adapters only."""
        mock_rs485 = MagicMock()
        mock_rs485.vid = 0x0403
        mock_rs485.pid = 0x6001

        mock_unknown = MagicMock()
        mock_unknown.vid = 0x1234
        mock_unknown.pid = 0x5678

        with patch(
            "serial.tools.list_ports.comports", return_value=[mock_rs485, mock_unknown]
        ):
            result = get_rs485_ports()
            assert len(result) == 1
            assert mock_rs485 in result
            assert mock_unknown not in result

    def test_no_matching_adapters(self) -> None:
        """Test returns empty when no RS485 adapters."""
        mock_unknown = MagicMock()
        mock_unknown.vid = 0x1234
        mock_unknown.pid = 0x5678

        with patch("serial.tools.list_ports.comports", return_value=[mock_unknown]):
            result = get_rs485_ports()
            assert result == []


class TestValidateValloxBus:
    """Tests for validate_vallox_bus function."""

    def test_serial_exception(self) -> None:
        """Test handles serial exception on open."""
        import serial

        with patch(
            "custom_components.vallox_rs485.config_flow.serial.Serial",
            side_effect=serial.SerialException("Cannot open"),
        ):
            result = validate_vallox_bus("/dev/ttyUSB0")
            assert result is False

    def test_exception_during_read(self) -> None:
        """Test handles exception during read."""
        mock_serial = MagicMock()
        mock_serial.read.side_effect = Exception("Read error")

        with patch(
            "custom_components.vallox_rs485.config_flow.serial.Serial",
            return_value=mock_serial,
        ):
            result = validate_vallox_bus("/dev/ttyUSB0")
            assert result is False
            mock_serial.close.assert_called()


class TestIsValidValloxTelegram:
    """Tests for _is_valid_vallox_telegram function."""

    def test_wrong_length(self) -> None:
        """Test rejects wrong length."""
        assert _is_valid_vallox_telegram(b"\x01\x11\x22\x29\x0f") is False

    def test_wrong_domain(self) -> None:
        """Test rejects wrong domain byte."""
        assert _is_valid_vallox_telegram(b"\x00\x11\x22\x29\x0f\x55") is False

    def test_wrong_checksum(self) -> None:
        """Test rejects wrong checksum."""
        assert _is_valid_vallox_telegram(b"\x01\x11\x22\x29\x0f\xff") is False

    def test_invalid_sender(self) -> None:
        """Test rejects invalid sender address."""
        data = bytes([VALLOX_DOMAIN, 0x05, 0x22, 0x29, 0x0F, 0])
        checksum = sum(data[:5]) & 0xFF
        data = data[:5] + bytes([checksum])
        assert _is_valid_vallox_telegram(data) is False

    def test_invalid_receiver(self) -> None:
        """Test rejects invalid receiver address."""
        data = bytes([VALLOX_DOMAIN, 0x11, 0x05, 0x29, 0x0F, 0])
        checksum = sum(data[:5]) & 0xFF
        data = data[:5] + bytes([checksum])
        assert _is_valid_vallox_telegram(data) is False

    def test_valid_telegram(self) -> None:
        """Test accepts valid telegram."""
        data = bytes([VALLOX_DOMAIN, 0x11, 0x22, 0x29, 0x0F, 0])
        checksum = sum(data[:5]) & 0xFF
        data = data[:5] + bytes([checksum])
        assert _is_valid_vallox_telegram(data) is True


class TestValloxRS485ConfigFlowInit:
    """Tests for ValloxRS485ConfigFlow initialization."""

    def test_init(self) -> None:
        """Test config flow initialization."""
        flow = ValloxRS485ConfigFlow()
        assert flow._discovered_port is None
        assert flow._discovered_name is None


class TestValloxRS485ConfigFlowUSB:
    """Tests for USB discovery flow."""

    @pytest.mark.asyncio
    async def test_async_step_usb_no_vallox_traffic(self, hass: HomeAssistant) -> None:
        """Test USB discovery aborts when no Vallox traffic."""
        discovery_info = UsbServiceInfo(
            device="/dev/ttyUSB0",
            vid="0403",
            pid="6001",
            serial_number="12345",
            manufacturer="FTDI",
            description="FT232R",
        )

        flow = ValloxRS485ConfigFlow()
        flow.hass = hass

        async def mock_executor_job(func, *args):
            if func.__name__ == "get_stable_device_path":
                return "/dev/ttyUSB0"
            if func.__name__ == "validate_vallox_bus":
                return False
            return func(*args)

        with (
            patch.object(flow, "async_set_unique_id", new_callable=AsyncMock),
            patch.object(flow, "_abort_if_unique_id_configured"),
            patch.object(hass, "async_add_executor_job", side_effect=mock_executor_job),
        ):
            result = await flow.async_step_usb(discovery_info)

            assert result["type"] == FlowResultType.ABORT
            assert result["reason"] == "no_vallox_traffic"

    @pytest.mark.asyncio
    async def test_async_step_usb_vallox_detected(self, hass: HomeAssistant) -> None:
        """Test USB discovery proceeds when Vallox traffic detected."""
        discovery_info = UsbServiceInfo(
            device="/dev/ttyUSB0",
            vid="0403",
            pid="6001",
            serial_number="12345",
            manufacturer="FTDI",
            description="FT232R",
        )

        flow = ValloxRS485ConfigFlow()
        flow.hass = hass
        flow.context = {}

        async def mock_executor_job(func, *args):
            if func.__name__ == "get_stable_device_path":
                return "/dev/ttyUSB0"
            if func.__name__ == "validate_vallox_bus":
                return True
            return func(*args)

        with (
            patch.object(flow, "async_set_unique_id", new_callable=AsyncMock),
            patch.object(flow, "_abort_if_unique_id_configured"),
            patch.object(hass, "async_add_executor_job", side_effect=mock_executor_job),
            patch.object(
                flow, "async_step_usb_confirm", new_callable=AsyncMock
            ) as mock_confirm,
        ):
            mock_confirm.return_value = {"type": FlowResultType.FORM}

            await flow.async_step_usb(discovery_info)

            assert flow._discovered_port == "/dev/ttyUSB0"
            mock_confirm.assert_called_once()


class TestValloxRS485ConfigFlowUSBConfirm:
    """Tests for USB confirmation flow."""

    @pytest.mark.asyncio
    async def test_async_step_usb_confirm_show_form(self, hass: HomeAssistant) -> None:
        """Test USB confirm shows form when no input."""
        flow = ValloxRS485ConfigFlow()
        flow.hass = hass
        flow._discovered_port = "/dev/ttyUSB0"
        flow._discovered_name = "FTDI FT232R"

        result = await flow.async_step_usb_confirm()

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "usb_confirm"

    @pytest.mark.asyncio
    async def test_async_step_usb_confirm_create_entry(
        self, hass: HomeAssistant
    ) -> None:
        """Test USB confirm creates entry with input."""
        flow = ValloxRS485ConfigFlow()
        flow.hass = hass
        flow._discovered_port = "/dev/ttyUSB0"
        flow._discovered_name = "FTDI FT232R"

        user_input = {
            "name": "My Vallox",
            "scan_interval": 30,
            "device_address": 0x22,
        }

        result = await flow.async_step_usb_confirm(user_input)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "My Vallox"
        assert result["data"][CONF_SERIAL_PORT] == "/dev/ttyUSB0"


class TestValloxRS485ConfigFlowUser:
    """Tests for manual user flow."""

    @pytest.mark.asyncio
    async def test_async_step_user_no_ports(self, hass: HomeAssistant) -> None:
        """Test user step aborts when no serial ports."""
        flow = ValloxRS485ConfigFlow()
        flow.hass = hass

        async def mock_executor_job(func, *args):
            return {}  # No ports

        with patch.object(
            hass, "async_add_executor_job", side_effect=mock_executor_job
        ):
            result = await flow.async_step_user()

            assert result["type"] == FlowResultType.ABORT
            assert result["reason"] == "no_serial_ports"

    @pytest.mark.asyncio
    async def test_async_step_user_show_form(self, hass: HomeAssistant) -> None:
        """Test user step shows form."""
        flow = ValloxRS485ConfigFlow()
        flow.hass = hass

        async def mock_executor_job(func, *args):
            return {"/dev/ttyUSB0": "USB Serial"}

        with patch.object(
            hass, "async_add_executor_job", side_effect=mock_executor_job
        ):
            result = await flow.async_step_user()

            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "user"

    @pytest.mark.asyncio
    async def test_async_step_user_cannot_connect(self, hass: HomeAssistant) -> None:
        """Test user step shows error when cannot connect."""
        flow = ValloxRS485ConfigFlow()
        flow.hass = hass

        user_input = {
            CONF_SERIAL_PORT: "/dev/ttyUSB0",
            "name": "Vallox",
        }

        call_count = [0]

        async def mock_executor_job(func, *args):
            call_count[0] += 1
            if call_count[0] == 1:  # get_serial_ports
                return {"/dev/ttyUSB0": "USB Serial"}
            elif call_count[0] == 2:  # _test_port
                return False
            return None

        with (
            patch.object(flow, "async_set_unique_id", new_callable=AsyncMock),
            patch.object(flow, "_abort_if_unique_id_configured"),
            patch.object(hass, "async_add_executor_job", side_effect=mock_executor_job),
        ):
            result = await flow.async_step_user(user_input)

            assert result["type"] == FlowResultType.FORM
            assert result["errors"]["base"] == "cannot_connect"

    @pytest.mark.asyncio
    async def test_async_step_user_no_vallox_traffic(self, hass: HomeAssistant) -> None:
        """Test user step shows error when no Vallox traffic."""
        flow = ValloxRS485ConfigFlow()
        flow.hass = hass

        user_input = {
            CONF_SERIAL_PORT: "/dev/ttyUSB0",
            "name": "Vallox",
        }

        call_count = [0]

        async def mock_executor_job(func, *args):
            call_count[0] += 1
            if call_count[0] == 1:  # get_serial_ports
                return {"/dev/ttyUSB0": "USB Serial"}
            elif call_count[0] == 2:  # _test_port
                return True
            elif call_count[0] == 3:  # validate_vallox_bus
                return False
            return None

        with (
            patch.object(flow, "async_set_unique_id", new_callable=AsyncMock),
            patch.object(flow, "_abort_if_unique_id_configured"),
            patch.object(hass, "async_add_executor_job", side_effect=mock_executor_job),
        ):
            result = await flow.async_step_user(user_input)

            assert result["type"] == FlowResultType.FORM
            assert result["errors"]["base"] == "no_vallox_traffic"

    @pytest.mark.asyncio
    async def test_async_step_user_success(self, hass: HomeAssistant) -> None:
        """Test user step creates entry on success."""
        flow = ValloxRS485ConfigFlow()
        flow.hass = hass

        user_input = {
            CONF_SERIAL_PORT: "/dev/ttyUSB0",
            "name": "Vallox",
            CONF_SCAN_INTERVAL: 30,
            CONF_DEVICE_ADDRESS: 0x22,
        }

        call_count = [0]

        async def mock_executor_job(func, *args):
            call_count[0] += 1
            if call_count[0] == 1:  # get_serial_ports
                return {"/dev/ttyUSB0": "USB Serial"}
            elif call_count[0] == 2 or call_count[0] == 3:  # _test_port
                return True
            return None

        with (
            patch.object(flow, "async_set_unique_id", new_callable=AsyncMock),
            patch.object(flow, "_abort_if_unique_id_configured"),
            patch.object(hass, "async_add_executor_job", side_effect=mock_executor_job),
        ):
            result = await flow.async_step_user(user_input)

            assert result["type"] == FlowResultType.CREATE_ENTRY
            assert result["title"] == "Vallox"
            assert result["data"][CONF_SERIAL_PORT] == "/dev/ttyUSB0"


class TestValloxRS485ConfigFlowTestPort:
    """Tests for _test_port method."""

    def test_port_opens_successfully(self) -> None:
        """Test _test_port returns True when port opens."""
        flow = ValloxRS485ConfigFlow()
        mock_serial = MagicMock()

        with patch(
            "custom_components.vallox_rs485.config_flow.serial.Serial",
            return_value=mock_serial,
        ):
            result = flow._test_port("/dev/ttyUSB0")
            assert result is True
            mock_serial.close.assert_called_once()

    def test_port_fails_to_open(self) -> None:
        """Test _test_port returns False on serial exception."""
        import serial

        flow = ValloxRS485ConfigFlow()

        with patch(
            "custom_components.vallox_rs485.config_flow.serial.Serial",
            side_effect=serial.SerialException("Cannot open"),
        ):
            result = flow._test_port("/dev/ttyUSB0")
            assert result is False


class TestValloxRS485ConfigFlowReconfigure:
    """Tests for reconfiguration flow."""

    @pytest.mark.asyncio
    async def test_async_step_reconfigure_show_form(self, hass: HomeAssistant) -> None:
        """Test reconfigure step shows form."""
        config_entry = MockConfigEntry(
            domain="vallox_rs485",
            data={
                CONF_SERIAL_PORT: "/dev/ttyUSB0",
                CONF_SCAN_INTERVAL: 30,
                CONF_DEVICE_ADDRESS: 0x22,
            },
            title="Vallox Test",
            entry_id="test_entry",
        )
        config_entry.add_to_hass(hass)

        flow = ValloxRS485ConfigFlow()
        flow.hass = hass
        flow.context = {"entry_id": "test_entry"}

        result = await flow.async_step_reconfigure()

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "reconfigure"

    @pytest.mark.asyncio
    async def test_async_step_reconfigure_update_entry(
        self, hass: HomeAssistant
    ) -> None:
        """Test reconfigure step updates entry."""
        config_entry = MockConfigEntry(
            domain="vallox_rs485",
            data={
                CONF_SERIAL_PORT: "/dev/ttyUSB0",
                CONF_SCAN_INTERVAL: 30,
                CONF_DEVICE_ADDRESS: 0x22,
            },
            title="Vallox Test",
            entry_id="test_entry",
        )
        config_entry.add_to_hass(hass)

        flow = ValloxRS485ConfigFlow()
        flow.hass = hass
        flow.context = {"entry_id": "test_entry"}

        user_input = {
            CONF_SCAN_INTERVAL: 60,
            CONF_DEVICE_ADDRESS: 0x23,
        }

        result = await flow.async_step_reconfigure(user_input)

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "reconfigure_successful"

    @pytest.mark.asyncio
    async def test_async_step_reconfigure_entry_not_found(
        self, hass: HomeAssistant
    ) -> None:
        """Test reconfigure step aborts when entry not found."""
        flow = ValloxRS485ConfigFlow()
        flow.hass = hass
        flow.context = {"entry_id": "nonexistent_entry"}

        result = await flow.async_step_reconfigure()

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "reconfigure_failed"
