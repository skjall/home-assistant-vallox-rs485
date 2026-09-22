"""What happens when the bus does not play along.

These are the paths a working installation never takes, which is exactly why
they were the ones that were wrong: a command that silently did nothing, a
setup that built entities with no data behind them, and a switch that hung
the task outright.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import serial
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError

from custom_components.vallox_rs485.const import BIT_POWER_STATE, REG_SELECT
from custom_components.vallox_rs485.coordinator import ValloxCoordinator
from custom_components.vallox_rs485.entity import ValloxDescribedEntity, ValloxEntity
from custom_components.vallox_rs485.vallox_protocol import create_read_request


def _connected(coordinator: ValloxCoordinator) -> MagicMock:
    """Give the coordinator an open port that records what is written."""
    writer = MagicMock()
    writer.drain = AsyncMock()
    coordinator._reader = MagicMock()
    coordinator._writer = writer
    coordinator._ensure_connected = AsyncMock()
    return writer


class TestSelectRegister:
    """The register that holds several switches at once."""

    @pytest.mark.asyncio
    async def test_a_switch_does_not_deadlock(self, hass: HomeAssistant) -> None:
        """Setting a bit must not take the writer lock twice.

        Regression: _set_select_bit held self._lock and then called
        _send_telegram, which takes the same lock. asyncio.Lock is not
        reentrant, so every switch on this register hung for ever.
        """
        coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
        _connected(coordinator)
        coordinator._state._raw_values[REG_SELECT] = 0x00

        # A real lock, not a mock: the point is that it is only taken once.
        await asyncio.wait_for(
            coordinator._set_select_bit(BIT_POWER_STATE, True), timeout=2
        )

    @pytest.mark.asyncio
    async def test_an_unknown_register_is_reported(self, hass: HomeAssistant) -> None:
        """Without a value to modify, the user is told rather than ignored."""
        coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
        _connected(coordinator)
        coordinator._state._raw_values.pop(REG_SELECT, None)

        with pytest.raises(HomeAssistantError):
            await coordinator._set_select_bit(BIT_POWER_STATE, True)

    @pytest.mark.asyncio
    async def test_only_the_named_bit_moves(self, hass: HomeAssistant) -> None:
        """The other switches in the register keep their value."""
        coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
        _connected(coordinator)
        coordinator._state._raw_values[REG_SELECT] = 0xFF
        coordinator._send_command = AsyncMock()

        await coordinator._set_select_bit(BIT_POWER_STATE, False)

        _, value = coordinator._send_command.await_args.args
        assert value == 0xFF & ~(1 << BIT_POWER_STATE)


class TestWriting:
    """A write that fails has to reach the user."""

    @pytest.mark.asyncio
    async def test_a_broken_port_becomes_a_home_assistant_error(
        self, hass: HomeAssistant
    ) -> None:
        """A pyserial exception is not something to show a user."""
        coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
        writer = _connected(coordinator)
        writer.drain = AsyncMock(side_effect=serial.SerialException("gone"))

        with pytest.raises(HomeAssistantError):
            await coordinator._send_telegram(create_read_request(REG_SELECT))


class TestSetup:
    """Setting up against a bus that says nothing."""

    @pytest.mark.asyncio
    async def test_waiting_reports_that_nothing_arrived(
        self, hass: HomeAssistant
    ) -> None:
        """The wait reports its outcome instead of logging and going on."""
        coordinator = ValloxCoordinator(hass, serial_port="/dev/ttyUSB0")
        coordinator._seen_registers = set()
        coordinator.async_request_refresh = AsyncMock()

        with patch("asyncio.sleep", new=AsyncMock()):
            assert await coordinator.async_wait_for_initial_data(timeout=0.01) is False

    @pytest.mark.asyncio
    async def test_a_silent_bus_fails_setup(self, hass: HomeAssistant) -> None:
        """No data means ConfigEntryNotReady, not entities without values."""
        from pytest_homeassistant_custom_component.common import MockConfigEntry

        from custom_components.vallox_rs485 import async_setup_entry

        entry = MockConfigEntry(
            domain="vallox_rs485",
            data={"serial_port": "/dev/ttyUSB0", "scan_interval": 30},
        )
        entry.add_to_hass(hass)

        with (
            patch.object(
                ValloxCoordinator, "async_config_entry_first_refresh", AsyncMock()
            ),
            patch.object(
                ValloxCoordinator,
                "async_wait_for_initial_data",
                AsyncMock(return_value=False),
            ),
            patch.object(ValloxCoordinator, "async_shutdown", AsyncMock()) as closed,
            pytest.raises(ConfigEntryNotReady),
        ):
            await async_setup_entry(hass, entry)

        # The port opened during the attempt must not be left behind.
        closed.assert_awaited_once()


class TestEntityAvailability:
    """The base entity narrows what the coordinator reports."""

    def test_an_entity_without_a_reader_follows_the_coordinator(self) -> None:
        """Nothing to read means nothing to narrow."""
        coordinator = MagicMock()
        coordinator.last_update_success = True
        entity = ValloxDescribedEntity(coordinator, "entry", "Vallox", "probe")
        entity.entity_description = MagicMock(spec=[])

        assert entity.available is True

    def test_a_failed_update_beats_a_readable_value(self) -> None:
        """A coordinator that is down makes every entity unavailable."""
        coordinator = MagicMock()
        coordinator.last_update_success = False
        entity = ValloxDescribedEntity(coordinator, "entry", "Vallox", "probe")
        entity.entity_description = MagicMock(spec=[])

        assert entity.available is False

    def test_the_unique_id_comes_from_the_entry(self) -> None:
        """Never from the name: renaming must not create a second entity."""
        entity = ValloxEntity(MagicMock(), "entry-id", "Kitchen unit", "fan")

        assert entity.unique_id == "entry-id_fan"
