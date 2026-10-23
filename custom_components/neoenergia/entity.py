"""Entidade base da Neoenergia (device por unidade consumidora)."""

from __future__ import annotations

from homeassistant.helpers.device_info import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NeoenergiaDataUpdateCoordinator


class NeoenergiaUCEntity(CoordinatorEntity[NeoenergiaDataUpdateCoordinator]):
    """Base por UC (unidade consumidora)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NeoenergiaDataUpdateCoordinator, uc: str) -> None:
        """uc = número da unidade consumidora."""
        super().__init__(coordinator)
        self._uc = uc
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, uc)},
            manufacturer="Neoenergia",
            model=coordinator.client._distribuidora.upper(),  # noqa: SLF001
            name=f"Neoenergia UC {uc}",
        )
