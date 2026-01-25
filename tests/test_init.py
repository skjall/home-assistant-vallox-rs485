"""Tests for Vallox RS485 integration module."""
from __future__ import annotations

import pytest


class TestIntegrationConstants:
    """Tests for integration constants."""

    def test_platforms_defined(self) -> None:
        """Test that platforms are defined."""
        from custom_components.vallox_rs485 import PLATFORMS

        assert len(PLATFORMS) == 5
        assert "sensor" in PLATFORMS
        assert "binary_sensor" in PLATFORMS
        assert "switch" in PLATFORMS
        assert "number" in PLATFORMS
        assert "fan" in PLATFORMS

    def test_parallel_updates(self) -> None:
        """Test that parallel updates is set."""
        from custom_components.vallox_rs485 import PARALLEL_UPDATES

        assert PARALLEL_UPDATES == 1

    def test_domain_available(self) -> None:
        """Test that domain is available from init."""
        from custom_components.vallox_rs485.const import DOMAIN

        assert DOMAIN == "vallox_rs485"


class TestModuleImports:
    """Tests for module imports."""

    def test_coordinator_import(self) -> None:
        """Test coordinator can be imported."""
        from custom_components.vallox_rs485.coordinator import ValloxCoordinator

        assert ValloxCoordinator is not None

    def test_protocol_import(self) -> None:
        """Test protocol can be imported."""
        from custom_components.vallox_rs485.vallox_protocol import (
            ValloxState,
            ValloxTelegram,
        )

        assert ValloxState is not None
        assert ValloxTelegram is not None

    def test_const_import(self) -> None:
        """Test constants can be imported."""
        from custom_components.vallox_rs485.const import (
            DOMAIN,
            DEFAULT_SCAN_INTERVAL,
            DEFAULT_BAUDRATE,
        )

        assert DOMAIN is not None
        assert DEFAULT_SCAN_INTERVAL is not None
        assert DEFAULT_BAUDRATE is not None


class TestRequiredRegisters:
    """Tests for required register tuples."""

    def test_sensor_required_registers(self) -> None:
        """Test sensor required registers are defined."""
        from custom_components.vallox_rs485.const import (
            REQ_TEMP_OUTSIDE,
            REQ_TEMP_EXHAUST,
            REQ_TEMP_INSIDE,
            REQ_TEMP_INCOMING,
            REQ_HUMIDITY,
            REQ_FAN_SPEED,
            REQ_CO2,
        )

        assert isinstance(REQ_TEMP_OUTSIDE, tuple)
        assert isinstance(REQ_TEMP_EXHAUST, tuple)
        assert isinstance(REQ_TEMP_INSIDE, tuple)
        assert isinstance(REQ_TEMP_INCOMING, tuple)
        assert isinstance(REQ_HUMIDITY, tuple)
        assert isinstance(REQ_FAN_SPEED, tuple)
        assert isinstance(REQ_CO2, tuple)

    def test_switch_required_registers(self) -> None:
        """Test switch required registers are defined."""
        from custom_components.vallox_rs485.const import REQ_SELECT

        assert isinstance(REQ_SELECT, tuple)

    def test_binary_sensor_required_registers(self) -> None:
        """Test binary sensor required registers are defined."""
        from custom_components.vallox_rs485.const import REQ_MULTI_PURPOSE_2

        assert isinstance(REQ_MULTI_PURPOSE_2, tuple)


class TestNtcTable:
    """Tests for NTC temperature conversion table."""

    def test_ntc_table_size(self) -> None:
        """Test NTC table has correct size."""
        from custom_components.vallox_rs485.const import NTC_TO_CELSIUS

        assert len(NTC_TO_CELSIUS) == 256

    def test_ntc_table_range(self) -> None:
        """Test NTC table values are reasonable temperatures."""
        from custom_components.vallox_rs485.const import NTC_TO_CELSIUS

        for value in NTC_TO_CELSIUS:
            assert -100 < value < 150

    def test_celsius_to_ntc_map_exists(self) -> None:
        """Test Celsius to NTC map exists."""
        from custom_components.vallox_rs485.const import CELSIUS_TO_NTC

        assert len(CELSIUS_TO_NTC) > 0


class TestFanSpeedMaps:
    """Tests for fan speed conversion maps."""

    def test_fan_speed_to_hex_complete(self) -> None:
        """Test fan speed to hex map has all speeds."""
        from custom_components.vallox_rs485.const import FAN_SPEED_TO_HEX

        for speed in range(1, 9):
            assert speed in FAN_SPEED_TO_HEX

    def test_hex_to_fan_speed_complete(self) -> None:
        """Test hex to fan speed map has all values."""
        from custom_components.vallox_rs485.const import HEX_TO_FAN_SPEED

        expected_hex = [0x01, 0x03, 0x07, 0x0F, 0x1F, 0x3F, 0x7F, 0xFF]
        for hex_val in expected_hex:
            assert hex_val in HEX_TO_FAN_SPEED


class TestFaultCodes:
    """Tests for fault code definitions."""

    def test_fault_codes_defined(self) -> None:
        """Test fault codes are defined."""
        from custom_components.vallox_rs485.const import FAULT_CODES

        assert len(FAULT_CODES) > 0
        assert 0 in FAULT_CODES
        assert FAULT_CODES[0] == "no_fault"

    def test_fault_codes_have_messages(self) -> None:
        """Test all fault codes have string messages."""
        from custom_components.vallox_rs485.const import FAULT_CODES

        for code, message in FAULT_CODES.items():
            assert isinstance(code, int)
            assert isinstance(message, str)
            assert len(message) > 0
