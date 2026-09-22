"""Tests for Vallox RS485 protocol implementation."""

from __future__ import annotations

from vallox_rs485_protocol import (
    CELSIUS_TO_NTC,
    NTC_TO_CELSIUS,
    ValloxState,
    ValloxTelegram,
    celsius_to_ntc,
    create_read_request,
    create_write_request,
    decode_cell_defrost,
    decode_fan_speed,
    decode_fault,
    decode_humidity,
    encode_cell_defrost,
    encode_co2_setpoint,
    encode_fan_speed,
    encode_humidity,
    ntc_to_celsius,
    validate_co2_setpoint,
    validate_fan_speed,
    validate_humidity,
    validate_service_months,
    validate_temperature_setpoint,
)


class TestNtcConversion:
    """Tests for NTC temperature conversion."""

    def test_ntc_to_celsius_known_values(self) -> None:
        """Test NTC to Celsius conversion with known values from table."""
        assert ntc_to_celsius(0) == NTC_TO_CELSIUS[0]  # -74
        assert ntc_to_celsius(135) == NTC_TO_CELSIUS[135]  # 11
        assert ntc_to_celsius(255) == NTC_TO_CELSIUS[255]  # 100

    def test_celsius_to_ntc_known_values(self) -> None:
        """Test Celsius to NTC conversion with known values."""
        assert celsius_to_ntc(20) == CELSIUS_TO_NTC[20]
        assert celsius_to_ntc(-10) == CELSIUS_TO_NTC[-10]

    def test_ntc_roundtrip(self) -> None:
        """Test NTC conversion roundtrip."""
        for temp in [-10, 0, 10, 20, 30]:
            ntc = celsius_to_ntc(temp)
            result = ntc_to_celsius(ntc)
            assert result == temp

    def test_ntc_out_of_range(self) -> None:
        """Test NTC conversion with out of range values."""
        assert ntc_to_celsius(256) == 0
        assert ntc_to_celsius(-1) == 0


class TestFanSpeedConversion:
    """Tests for fan speed encoding/decoding."""

    def test_decode_fan_speed(self) -> None:
        """Test fan speed decoding."""
        assert decode_fan_speed(0x01) == 1
        assert decode_fan_speed(0x03) == 2
        assert decode_fan_speed(0x07) == 3
        assert decode_fan_speed(0x0F) == 4
        assert decode_fan_speed(0x1F) == 5
        assert decode_fan_speed(0x3F) == 6
        assert decode_fan_speed(0x7F) == 7
        assert decode_fan_speed(0xFF) == 8

    def test_decode_fan_speed_invalid(self) -> None:
        """Test fan speed decoding with invalid value."""
        assert decode_fan_speed(0x00) == 1

    def test_encode_fan_speed(self) -> None:
        """Test fan speed encoding."""
        assert encode_fan_speed(1) == 0x01
        assert encode_fan_speed(4) == 0x0F
        assert encode_fan_speed(8) == 0xFF

    def test_validate_fan_speed(self) -> None:
        """Test fan speed validation."""
        assert validate_fan_speed(0) == 1
        assert validate_fan_speed(5) == 5
        assert validate_fan_speed(10) == 8


class TestHumidityConversion:
    """Tests for humidity encoding/decoding."""

    def test_decode_humidity(self) -> None:
        """Test humidity decoding."""
        assert decode_humidity(0) == 0
        assert decode_humidity(51) == 0
        assert decode_humidity(255) == 100

    def test_decode_humidity_mid_range(self) -> None:
        """Test humidity decoding for mid-range values."""
        result = decode_humidity(153)
        assert 45 <= result <= 55

    def test_encode_humidity(self) -> None:
        """Test humidity encoding."""
        assert encode_humidity(0) == 51
        assert encode_humidity(100) == 255

    def test_encode_humidity_mid_range(self) -> None:
        """Test humidity encoding for mid-range values."""
        result = encode_humidity(50)
        assert 150 <= result <= 160

    def test_validate_humidity(self) -> None:
        """Test humidity validation."""
        assert validate_humidity(-10) == 0
        assert validate_humidity(50) == 50
        assert validate_humidity(150) == 100


class TestCellDefrostConversion:
    """Tests for cell defrost encoding/decoding."""

    def test_decode_cell_defrost(self) -> None:
        """Test cell defrost decoding (value / 3)."""
        assert decode_cell_defrost(0) == 0
        assert decode_cell_defrost(15) == 5
        assert decode_cell_defrost(30) == 10

    def test_encode_cell_defrost(self) -> None:
        """Test cell defrost encoding (temp * 3)."""
        assert encode_cell_defrost(0) == 0
        assert encode_cell_defrost(5) == 15
        assert encode_cell_defrost(10) == 30


class TestCo2Conversion:
    """Tests for CO2 setpoint encoding."""

    def test_encode_co2_setpoint(self) -> None:
        """Test CO2 setpoint encoding."""
        upper, lower = encode_co2_setpoint(1000)
        assert (upper << 8) | lower == 1000

    def test_validate_co2_setpoint(self) -> None:
        """Test CO2 setpoint validation."""
        assert validate_co2_setpoint(100) == 500
        assert validate_co2_setpoint(1000) == 1000
        assert validate_co2_setpoint(3000) == 2000


class TestFaultDecoding:
    """Tests for fault code decoding."""

    def test_decode_fault(self) -> None:
        """Test fault code decoding."""
        assert decode_fault(0) == "no_fault"
        assert decode_fault(5) == "supply_air_sensor_fault"
        assert "unknown_fault" in decode_fault(0xFE)


class TestValidation:
    """Tests for validation functions."""

    def test_validate_temperature_setpoint(self) -> None:
        """Test temperature setpoint validation (range -6 to 30)."""
        assert validate_temperature_setpoint(-10) == -6
        assert validate_temperature_setpoint(5) == 5
        assert validate_temperature_setpoint(20) == 20
        assert validate_temperature_setpoint(40) == 30

    def test_validate_service_months(self) -> None:
        """Test service months validation."""
        assert validate_service_months(0) == 1
        assert validate_service_months(6) == 6
        assert validate_service_months(20) == 15


class TestValloxTelegram:
    """Tests for ValloxTelegram class."""

    def test_create_telegram(self) -> None:
        """Test telegram creation."""
        telegram = ValloxTelegram(
            domain=0x01,
            sender=0x22,
            receiver=0x11,
            register=0x29,
            value=0x0F,
        )
        assert telegram.domain == 0x01
        assert telegram.sender == 0x22
        assert telegram.receiver == 0x11
        assert telegram.register == 0x29
        assert telegram.value == 0x0F

    def test_telegram_to_bytes(self) -> None:
        """Test telegram serialization."""
        telegram = ValloxTelegram(
            domain=0x01,
            sender=0x22,
            receiver=0x11,
            register=0x29,
            value=0x0F,
        )
        data = telegram.to_bytes()
        assert len(data) == 6
        assert data[0] == 0x01
        checksum = sum(data[:5]) & 0xFF
        assert data[5] == checksum

    def test_telegram_from_bytes_valid(self) -> None:
        """Test telegram deserialization with valid data."""
        telegram = ValloxTelegram(
            domain=0x01,
            sender=0x11,
            receiver=0x22,
            register=0x29,
            value=0x0F,
        )
        data = telegram.to_bytes()
        parsed = ValloxTelegram.from_bytes(data)
        assert parsed is not None
        assert parsed.sender == 0x11
        assert parsed.register == 0x29

    def test_telegram_from_bytes_invalid_checksum(self) -> None:
        """Test telegram deserialization with invalid checksum."""
        data = bytes([0x01, 0x11, 0x22, 0x29, 0x0F, 0xFF])
        assert ValloxTelegram.from_bytes(data) is None

    def test_telegram_from_bytes_short(self) -> None:
        """Test telegram deserialization with short data."""
        data = bytes([0x01, 0x11, 0x22])
        assert ValloxTelegram.from_bytes(data) is None

    def test_telegram_checksum(self) -> None:
        """Test telegram checksum calculation."""
        telegram = ValloxTelegram(
            domain=0x01,
            sender=0x22,
            receiver=0x11,
            register=0x29,
            value=0x0F,
        )
        expected = (0x01 + 0x22 + 0x11 + 0x29 + 0x0F) & 0xFF
        assert telegram.calculate_checksum() == expected


class TestCreateRequests:
    """Tests for request creation functions."""

    def test_create_read_request(self) -> None:
        """Test read request creation."""
        telegram = create_read_request(0x29)
        assert telegram.domain == 0x01
        assert telegram.receiver == 0x11
        # Per docs/PROTOCOL.md: VARIABLE is 0x00 and DATA carries the
        # register being asked for.
        assert telegram.register == 0x00
        assert telegram.value == 0x29

    def test_create_write_request(self) -> None:
        """Test write request creation."""
        telegram = create_write_request(0x29, 0x0F, 0x22)
        assert telegram.domain == 0x01
        assert telegram.sender == 0x22
        assert telegram.receiver == 0x11
        assert telegram.register == 0x29
        assert telegram.value == 0x0F


class TestValloxState:
    """Tests for ValloxState class."""

    def test_initial_state(self) -> None:
        """Test initial state values."""
        state = ValloxState()
        assert state.temp_outside is None
        assert state.fan_speed is None
        assert state.power_state is None

    def test_update_co2_ppm(self) -> None:
        """Test CO2 ppm calculation."""
        state = ValloxState()
        state.co2_high = 0x03
        state.co2_low = 0xE8
        state.update_co2_ppm()
        assert state.co2_ppm == 1000

    def test_update_co2_ppm_none(self) -> None:
        """Test CO2 ppm calculation with missing values."""
        state = ValloxState()
        state.co2_high = 0x03
        state.update_co2_ppm()
        assert state.co2_ppm is None

    def test_state_has_raw_values(self) -> None:
        """Test state has raw values dict."""
        state = ValloxState()
        assert hasattr(state, "_raw_values")
        assert isinstance(state._raw_values, dict)
