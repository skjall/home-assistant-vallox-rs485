"""Integration tests for Vallox RS485 using pytest-homeassistant-custom-component."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import Platform

from custom_components.vallox_rs485 import (
    async_setup_entry,
    async_unload_entry,
    PLATFORMS,
)
from custom_components.vallox_rs485.const import REG_FAN_SPEED
from custom_components.vallox_rs485.coordinator import ValloxCoordinator
from custom_components.vallox_rs485.vallox_protocol import create_read_request
from custom_components.vallox_rs485.vallox_protocol import ValloxState


@pytest.fixture
def vallox_config_entry() -> MockConfigEntry:
    """Create a mock config entry for Vallox RS485."""
    return MockConfigEntry(
        domain="vallox_rs485",
        data={
            "serial_port": "/dev/ttyUSB0",
            "scan_interval": 30,
            "device_address": 0x22,
        },
        title="Vallox RS485",
        entry_id="test_vallox_entry",
    )


class TestAsyncSetupEntry:
    """Tests for async_setup_entry."""

    @pytest.mark.asyncio
    async def test_async_setup_entry_success(
        self, hass: HomeAssistant, vallox_config_entry: MockConfigEntry
    ) -> None:
        """Test successful setup of config entry."""
        mock_coordinator = MagicMock(spec=ValloxCoordinator)
        mock_coordinator.data = ValloxState()
        mock_coordinator._seen_registers = {0x29, 0xA3}
        mock_coordinator.async_config_entry_first_refresh = AsyncMock()
        mock_coordinator.async_wait_for_initial_data = AsyncMock()
        mock_coordinator.has_seen_any_register = MagicMock(return_value=True)

        with (
            patch(
                "custom_components.vallox_rs485.ValloxCoordinator",
                return_value=mock_coordinator,
            ),
            patch.object(
                hass.config_entries,
                "async_forward_entry_setups",
                new_callable=AsyncMock,
            ) as mock_forward,
        ):
            vallox_config_entry.add_to_hass(hass)
            result = await async_setup_entry(hass, vallox_config_entry)

            assert result is True
            mock_coordinator.async_config_entry_first_refresh.assert_called_once()
            mock_coordinator.async_wait_for_initial_data.assert_called_once_with(timeout=15.0)
            mock_forward.assert_called_once_with(vallox_config_entry, PLATFORMS)
            assert vallox_config_entry.runtime_data is mock_coordinator


class TestAsyncUnloadEntry:
    """Tests for async_unload_entry."""

    @pytest.mark.asyncio
    async def test_async_unload_entry_success(
        self, hass: HomeAssistant, vallox_config_entry: MockConfigEntry
    ) -> None:
        """Test successful unload of config entry."""
        mock_coordinator = MagicMock(spec=ValloxCoordinator)
        mock_coordinator.async_shutdown = AsyncMock()

        vallox_config_entry.add_to_hass(hass)
        vallox_config_entry.runtime_data = mock_coordinator

        with patch.object(
            hass.config_entries,
            "async_unload_platforms",
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_unload:
            result = await async_unload_entry(hass, vallox_config_entry)

            assert result is True
            mock_unload.assert_called_once_with(vallox_config_entry, PLATFORMS)
            mock_coordinator.async_shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_unload_entry_failure(
        self, hass: HomeAssistant, vallox_config_entry: MockConfigEntry
    ) -> None:
        """Test unload entry when platforms fail to unload."""
        mock_coordinator = MagicMock(spec=ValloxCoordinator)
        mock_coordinator.async_shutdown = AsyncMock()

        vallox_config_entry.add_to_hass(hass)
        vallox_config_entry.runtime_data = mock_coordinator

        with patch.object(
            hass.config_entries,
            "async_unload_platforms",
            new_callable=AsyncMock,
            return_value=False,
        ):
            result = await async_unload_entry(hass, vallox_config_entry)

            assert result is False
            # Shutdown should not be called if unload failed
            mock_coordinator.async_shutdown.assert_not_called()


class TestPlatformsConstant:
    """Tests for PLATFORMS constant."""

    def test_platforms_contains_expected(self) -> None:
        """Test that PLATFORMS contains all expected platforms."""
        assert Platform.SENSOR in PLATFORMS
        assert Platform.FAN in PLATFORMS
        assert Platform.SWITCH in PLATFORMS
        assert Platform.BINARY_SENSOR in PLATFORMS
        assert Platform.NUMBER in PLATFORMS

    def test_platforms_count(self) -> None:
        """Test the number of platforms."""
        assert len(PLATFORMS) == 5


class TestCoordinatorIntegration:
    """Integration tests for ValloxCoordinator."""

    @pytest.mark.asyncio
    async def test_coordinator_initialization(self, hass: HomeAssistant) -> None:
        """Test coordinator initialization with mock serial."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(
                hass,
                serial_port="/dev/ttyUSB0",
                scan_interval=30,
                device_address=0x22,
            )

            assert coordinator._serial_port == "/dev/ttyUSB0"
            assert coordinator._device_address == 0x22
            assert coordinator._seen_registers == set()
            assert coordinator._reader is None
            assert coordinator._writer is None

    @pytest.mark.asyncio
    async def test_coordinator_has_seen_register(self, hass: HomeAssistant) -> None:
        """Test has_seen_register method."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(
                hass, serial_port="/dev/ttyUSB0"
            )
            coordinator._seen_registers = {0x29, 0x2A}

            assert coordinator.has_seen_register(0x29) is True
            assert coordinator.has_seen_register(0x30) is False

    @pytest.mark.asyncio
    async def test_coordinator_has_seen_any_register(self, hass: HomeAssistant) -> None:
        """Test has_seen_any_register method."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(
                hass, serial_port="/dev/ttyUSB0"
            )
            coordinator._seen_registers = {0x29, 0x2A}

            assert coordinator.has_seen_any_register((0x29, 0x30)) is True
            assert coordinator.has_seen_any_register((0x31, 0x32)) is False

    @pytest.mark.asyncio
    async def test_coordinator_close_serial(self, hass: HomeAssistant) -> None:
        """Closing drops the writer and clears both ends."""
        coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
        writer = MagicMock()
        writer.wait_closed = AsyncMock()
        coordinator._reader = MagicMock()
        coordinator._writer = writer

        await coordinator._close_serial()

        writer.close.assert_called_once()
        assert coordinator._reader is None
        assert coordinator._writer is None

    @pytest.mark.asyncio
    async def test_coordinator_close_serial_exception(self, hass: HomeAssistant) -> None:
        """A port that refuses to close still leaves the coordinator closed."""
        coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
        writer = MagicMock()
        writer.wait_closed = AsyncMock(side_effect=OSError("Close error"))
        coordinator._writer = writer

        await coordinator._close_serial()

        assert coordinator._reader is None
        assert coordinator._writer is None

    @pytest.mark.asyncio
    async def test_coordinator_log_unavailable(self, hass: HomeAssistant) -> None:
        """Test _log_unavailable method rate limiting."""
        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(
                hass, serial_port="/dev/ttyUSB0"
            )
            coordinator._last_unavailable_log = 0

            with patch("custom_components.vallox_rs485.coordinator._LOGGER") as mock_logger:
                # First call should log
                coordinator._log_unavailable("Test error")
                mock_logger.warning.assert_called_once()

                # Reset and call again immediately - should not log
                mock_logger.reset_mock()
                coordinator._log_unavailable("Another error")
                mock_logger.warning.assert_not_called()

    @pytest.mark.asyncio
    async def test_coordinator_async_shutdown(self, hass: HomeAssistant) -> None:
        """Shutting down closes the port and forgets both ends."""
        coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
        writer = MagicMock()
        writer.wait_closed = AsyncMock()
        coordinator._reader = MagicMock()
        coordinator._writer = writer

        await coordinator.async_shutdown()

        writer.close.assert_called_once()
        assert coordinator._writer is None

    @pytest.mark.asyncio
    async def test_coordinator_parse_buffer(self, hass: HomeAssistant) -> None:
        """Test _parse_buffer method."""
        from custom_components.vallox_rs485.vallox_protocol import ValloxTelegram
        from custom_components.vallox_rs485.const import REG_FAN_SPEED, ADDR_MAINBOARD

        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(
                hass, serial_port="/dev/ttyUSB0"
            )

            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_FAN_SPEED,
                value=0x0F,
            )
            buffer = telegram.to_bytes()

            coordinator._parse_buffer(buffer)

            assert REG_FAN_SPEED in coordinator._seen_registers
            assert coordinator._state.fan_speed == 4

    @pytest.mark.asyncio
    async def test_coordinator_process_telegram(self, hass: HomeAssistant) -> None:
        """Test _process_telegram method."""
        from custom_components.vallox_rs485.vallox_protocol import ValloxTelegram
        from custom_components.vallox_rs485.const import REG_HUMIDITY, ADDR_MAINBOARD

        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(
                hass, serial_port="/dev/ttyUSB0"
            )

            telegram = ValloxTelegram(
                domain=0x01,
                sender=ADDR_MAINBOARD,
                receiver=0x22,
                register=REG_HUMIDITY,
                value=153,
            )

            coordinator._process_telegram(telegram)

            assert coordinator.has_seen_register(REG_HUMIDITY)
            assert coordinator._state.humidity is not None

    @pytest.mark.asyncio
    async def test_coordinator_process_telegram_ignores_unknown(self, hass: HomeAssistant) -> None:
        """Test _process_telegram ignores unknown senders."""
        from custom_components.vallox_rs485.vallox_protocol import ValloxTelegram
        from custom_components.vallox_rs485.const import REG_FAN_SPEED

        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(
                hass, serial_port="/dev/ttyUSB0"
            )

            telegram = ValloxTelegram(
                domain=0x01,
                sender=0x99,  # Unknown sender
                receiver=0x22,
                register=REG_FAN_SPEED,
                value=0x0F,
            )

            coordinator._process_telegram(telegram)

            assert not coordinator.has_seen_register(REG_FAN_SPEED)
            assert coordinator._state.fan_speed is None

    @pytest.mark.asyncio
    async def test_coordinator_write_serial(self, hass: HomeAssistant) -> None:
        """Writing hands the bytes to the writer and drains them."""
        coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
        writer = MagicMock()
        writer.drain = AsyncMock()
        coordinator._writer = writer
        coordinator._ensure_connected = AsyncMock()
        telegram = create_read_request(REG_FAN_SPEED, coordinator._device_address)

        await coordinator._send_telegram(telegram)

        writer.write.assert_called_once_with(telegram.to_bytes())
        writer.drain.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_coordinator_write_serial_raises_when_closed(
        self, hass: HomeAssistant
    ) -> None:
        """A closed port reaches the user as an error, not as a library traceback."""
        coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
        coordinator._writer = None
        coordinator._ensure_connected = AsyncMock()
        telegram = create_read_request(REG_FAN_SPEED, coordinator._device_address)

        with pytest.raises(HomeAssistantError):
            await coordinator._send_telegram(telegram)

    @pytest.mark.asyncio
    async def test_coordinator_async_set_fan_speed(self, hass: HomeAssistant) -> None:
        """Test async_set_fan_speed method."""
        from custom_components.vallox_rs485.const import REG_FAN_SPEED
        from custom_components.vallox_rs485.vallox_protocol import encode_fan_speed

        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(
                hass, serial_port="/dev/ttyUSB0"
            )
            coordinator._send_command = AsyncMock()
            coordinator._ensure_connected = AsyncMock()

            await coordinator.async_set_fan_speed(5)

            coordinator._send_command.assert_called_once_with(
                REG_FAN_SPEED, encode_fan_speed(5)
            )

    @pytest.mark.asyncio
    async def test_coordinator_async_set_power_state(self, hass: HomeAssistant) -> None:
        """Test async_set_power_state method."""
        from custom_components.vallox_rs485.const import REG_SELECT, BIT_POWER_STATE

        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(
                hass, serial_port="/dev/ttyUSB0"
            )
            coordinator._send_command = AsyncMock()
            coordinator._ensure_connected = AsyncMock()
            coordinator._state._raw_values[REG_SELECT] = 0x00

            await coordinator.async_set_power_state(True)

            coordinator._send_command.assert_called_once()
            args = coordinator._send_command.call_args[0]
            assert args[0] == REG_SELECT
            assert args[1] & (1 << BIT_POWER_STATE)

    @pytest.mark.asyncio
    async def test_coordinator_async_set_heating_setpoint(self, hass: HomeAssistant) -> None:
        """Test async_set_heating_setpoint method."""
        from custom_components.vallox_rs485.const import REG_HEATING_SETPOINT
        from custom_components.vallox_rs485.vallox_protocol import celsius_to_ntc

        with patch("custom_components.vallox_rs485.coordinator.serial.Serial"):
            coordinator = ValloxCoordinator(
                hass, serial_port="/dev/ttyUSB0"
            )
            coordinator._send_command = AsyncMock()
            coordinator._ensure_connected = AsyncMock()

            await coordinator.async_set_heating_setpoint(20)

            coordinator._send_command.assert_called_once_with(
                REG_HEATING_SETPOINT, celsius_to_ntc(20)
            )
