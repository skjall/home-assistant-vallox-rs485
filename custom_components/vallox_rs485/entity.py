"""The entity every Vallox platform builds on.

All five platforms had the same three lines in their constructor: the name
flag, a unique id built from the entry, and a device info dict assembled
somewhere else. Three copies of a rule are three chances to break it - the
unique id in particular, which has to stay stable for the lifetime of an
installation, because changing it orphans every automation that named the
entity.

Availability is narrowed here as well. The coordinator only knows whether the
bus answered at all; whether a particular register arrived is per entity, and
an entity showing a stale value because nobody asked is worse than one that
admits it has nothing.
"""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ValloxCoordinator
from .vallox_protocol import ValloxState


class ValloxEntity(CoordinatorEntity[ValloxCoordinator]):
    """Base for every entity this integration creates."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ValloxCoordinator,
        entry_id: str,
        title: str,
        key: str,
    ) -> None:
        """Tie the entity to its coordinator and to the one device."""
        super().__init__(coordinator)
        # Derived from the entry, never from the name: a user renaming the
        # device must not create a second entity.
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=title,
            manufacturer="Vallox",
            model="RS485",
        )


class ValloxDescribedEntity(ValloxEntity):
    """An entity whose value comes from its description."""

    entity_description: EntityDescription

    @property
    def _value_fn(self) -> Callable[[ValloxState], object] | None:
        """Return the reader this entity was described with, if it has one."""
        return getattr(self.entity_description, "value_fn", None)

    @property
    def available(self) -> bool:
        """Report unavailable while the register behind this entity is unread."""
        if not super().available:
            return False
        value_fn = self._value_fn
        if value_fn is None:
            return True
        return value_fn(self.coordinator.data) is not None
