"""Coordinator da Neoenergia: UCs + faturas + histórico + bandeira."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NeoenergiaApiError, NeoenergiaAuthError
from .const import DEFAULT_SCAN_INTERVAL_MINUTES, DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .api import NeoenergiaApiClient


def _as_list(data: Any) -> list[dict[str, Any]]:
    """Normaliza respostas que podem vir como lista ou {content|data|ucs: [...]}."""
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("content", "data", "ucs", "unidadesConsumidoras", "items"):
            inner = data.get(key)
            if isinstance(inner, list):
                return [x for x in inner if isinstance(x, dict)]
        return [data]
    return []


def _uc_id(uc: dict[str, Any]) -> str | None:
    """Extrai o número da UC tolerando nomes de campo variados."""
    for key in ("uc", "numeroUc", "numeroUC", "codigoUc", "instalacao", "numeroInstalacao"):
        val = uc.get(key)
        if val:
            return str(val)
    return None


class NeoenergiaDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Puxa UCs e, por UC, faturas + histórico; + bandeira tarifária."""

    def __init__(self, hass: HomeAssistant, client: NeoenergiaApiClient) -> None:
        """Inicializa o coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self._fetch_all()
        except NeoenergiaAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except NeoenergiaApiError as err:
            raise UpdateFailed(str(err)) from err

    async def _fetch_all(self) -> dict[str, Any]:
        ucs_raw = await self.client.async_list_ucs()
        bandeira: Any = None
        try:
            bandeira = await self.client.async_bandeira()
        except NeoenergiaApiError as err:
            LOGGER.debug("bandeira indisponível: %s", err)

        ucs: dict[str, dict[str, Any]] = {}
        for uc in _as_list(ucs_raw):
            uid = _uc_id(uc)
            if not uid:
                continue
            faturas, historico = await asyncio.gather(
                self.client.async_faturas(uid),
                self.client.async_historico(uid),
                return_exceptions=True,
            )
            ucs[uid] = {
                "uc": uc,
                "faturas": None if isinstance(faturas, Exception) else faturas,
                "historico": None if isinstance(historico, Exception) else historico,
            }
        return {"ucs": ucs, "bandeira": bandeira}
