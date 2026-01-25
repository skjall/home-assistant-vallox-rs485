"""Tests for Vallox RS485 config flow helper functions."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.vallox_rs485.const import DOMAIN


class TestConfigFlowHelpers:
    """Tests for config flow helper functions."""

    def test_domain_defined(self) -> None:
        """Test that domain is defined."""
        assert DOMAIN == "vallox_rs485"

    def test_get_serial_ports_function(self) -> None:
        """Test get_serial_ports function exists and works."""
        from custom_components.vallox_rs485.config_flow import get_serial_ports

        mock_port = MagicMock()
        mock_port.device = "/dev/ttyUSB0"
        mock_port.description = "FTDI USB"
        mock_port.vid = 0x0403
        mock_port.pid = 0x6001

        with patch(
            "serial.tools.list_ports.comports",
            return_value=[mock_port],
        ):
            result = get_serial_ports()
            assert "/dev/ttyUSB0" in result
            assert "ttyUSB0" in result["/dev/ttyUSB0"]

    def test_get_serial_ports_empty(self) -> None:
        """Test get_serial_ports with no ports."""
        from custom_components.vallox_rs485.config_flow import get_serial_ports

        with patch("serial.tools.list_ports.comports", return_value=[]):
            result = get_serial_ports()
            assert result == {}

    def test_validate_vallox_bus_success(self) -> None:
        """Test validate_vallox_bus with valid Vallox traffic."""
        from custom_components.vallox_rs485.config_flow import validate_vallox_bus
        from custom_components.vallox_rs485.vallox_protocol import ValloxTelegram
        from custom_components.vallox_rs485.const import ADDR_MAINBOARD

        telegram = ValloxTelegram(
            domain=0x01,
            sender=ADDR_MAINBOARD,
            receiver=0x22,
            register=0x29,
            value=0x0F,
        )
        valid_data = telegram.to_bytes()

        mock_serial = MagicMock()
        # The function reads byte by byte with read(1), so we return each byte individually
        mock_serial.read.side_effect = [bytes([b]) for b in valid_data]

        with patch(
            "custom_components.vallox_rs485.config_flow.serial.Serial",
            return_value=mock_serial,
        ):
            result = validate_vallox_bus("/dev/ttyUSB0")
            assert result is True

    def test_validate_vallox_bus_no_traffic(self) -> None:
        """Test validate_vallox_bus with no traffic."""
        from custom_components.vallox_rs485.config_flow import validate_vallox_bus

        mock_serial = MagicMock()
        mock_serial.read.return_value = b""  # Empty read simulates no traffic

        with patch(
            "custom_components.vallox_rs485.config_flow.serial.Serial",
            return_value=mock_serial,
        ):
            result = validate_vallox_bus("/dev/ttyUSB0", timeout=0.1)
            assert result is False

    def test_validate_vallox_bus_invalid_data(self) -> None:
        """Test validate_vallox_bus with invalid data."""
        from custom_components.vallox_rs485.config_flow import validate_vallox_bus

        invalid_data = b"\x00\x00\x00\x00\x00\x00"
        mock_serial = MagicMock()
        # Return bytes one by one, then empty to stop reading
        mock_serial.read.side_effect = [bytes([b]) for b in invalid_data] + [b""] * 100

        with patch(
            "custom_components.vallox_rs485.config_flow.serial.Serial",
            return_value=mock_serial,
        ):
            result = validate_vallox_bus("/dev/ttyUSB0", timeout=0.1)
            assert result is False

    def test_get_stable_device_path_same(self) -> None:
        """Test get_stable_device_path returns same path when /dev/serial/by-id doesn't exist."""
        from custom_components.vallox_rs485.config_flow import get_stable_device_path

        with patch(
            "custom_components.vallox_rs485.config_flow.Path"
        ) as mock_path_class:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = False
            mock_path_class.return_value = mock_path_instance

            result = get_stable_device_path("/dev/ttyUSB0")
            assert result == "/dev/ttyUSB0"

    def test_get_stable_device_path_by_id(self) -> None:
        """Test get_stable_device_path finds by-id path."""
        import os
        from custom_components.vallox_rs485.config_flow import get_stable_device_path

        with (
            patch(
                "custom_components.vallox_rs485.config_flow.Path"
            ) as mock_path_class,
            patch("os.path.realpath") as mock_realpath,
        ):
            # Mock the by-id directory
            mock_by_id_path = MagicMock()
            mock_by_id_path.exists.return_value = True

            # Mock a link entry that matches
            mock_link = MagicMock()
            mock_link.__str__ = lambda self: "/dev/serial/by-id/usb-FTDI_FT232R-if00-port0"
            mock_by_id_path.iterdir.return_value = [mock_link]

            mock_path_class.return_value = mock_by_id_path

            # Both paths resolve to the same device
            mock_realpath.side_effect = lambda p: "/dev/ttyUSB0"

            result = get_stable_device_path("/dev/ttyUSB0")
            assert result == "/dev/serial/by-id/usb-FTDI_FT232R-if00-port0"


class TestConfigFlowDataSchema:
    """Tests for config flow data schema."""

    def test_default_scan_interval(self) -> None:
        """Test default scan interval."""
        from custom_components.vallox_rs485.const import DEFAULT_SCAN_INTERVAL

        assert DEFAULT_SCAN_INTERVAL == 30

    def test_default_baudrate(self) -> None:
        """Test default baudrate."""
        from custom_components.vallox_rs485.const import DEFAULT_BAUDRATE

        assert DEFAULT_BAUDRATE == 9600

    def test_device_addresses(self) -> None:
        """Test device addresses are defined."""
        from custom_components.vallox_rs485.const import (
            ADDR_MAINBOARD,
            ADDR_THIS_DEVICE,
        )

        assert ADDR_MAINBOARD == 0x11
        assert ADDR_THIS_DEVICE == 0x22
