"""Sensores da Neoenergia (por UC + bandeira tarifária).

As respostas da Agência Virtual têm shape a confirmar via captura real; os
getters toleram nomes de campo variados (valor/valorTotal, vencimento/
dataVencimento etc.). Ajuste as listas de chaves após o primeiro login.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .entity import NeoenergiaUCEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import NeoenergiaDataUpdateCoordinator
    from .data import NeoenergiaConfigEntry


def _first(d: dict[str, Any], *keys: str) -> Any:
    """Primeiro valor não-nulo entre chaves candidatas."""
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, ""):
            return d[k]
    return None


def _faturas_list(node: dict[str, Any]) -> list[dict[str, Any]]:
    faturas = node.get("faturas")
    if isinstance(faturas, list):
        return [f for f in faturas if isinstance(f, dict)]
    if isinstance(faturas, dict):
        for k in ("content", "data", "faturas", "items"):
            if isinstance(faturas.get(k), list):
                return [f for f in faturas[k] if isinstance(f, dict)]
    return []


def _fatura_atual(node: dict[str, Any]) -> dict[str, Any] | None:
    faturas = _faturas_list(node)
    if not faturas:
        return None
    abertas = [
        f for f in faturas if str(_first(f, "status", "situacao") or "").lower()
        not in ("paga", "pago", "quitada")
    ]
    pool = abertas or faturas
    return pool[0]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NeoenergiaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Cria sensores por UC + bandeira tarifária."""
    coordinator = entry.runtime_data.coordinator
    entities: list[SensorEntity] = [NeoenergiaBandeiraSensor(coordinator)]
    for uc in (coordinator.data or {}).get("ucs", {}):
        entities.append(NeoenergiaFaturaSensor(coordinator, uc))
        entities.append(NeoenergiaConsumoSensor(coordinator, uc))
    async_add_entities(entities)


class NeoenergiaFaturaSensor(NeoenergiaUCEntity, SensorEntity):
    """Valor da fatura atual (em aberto, senão a última)."""

    _attr_translation_key = "fatura"
    _attr_native_unit_of_measurement = "BRL"

    def __init__(self, coordinator: NeoenergiaDataUpdateCoordinator, uc: str) -> None:
        """Inicializa o sensor de fatura."""
        super().__init__(coordinator, uc)
        self._attr_unique_id = f"{uc}_fatura"

    def _node(self) -> dict[str, Any]:
        return (self.coordinator.data or {}).get("ucs", {}).get(self._uc, {})

    @property
    def native_value(self) -> float | None:
        """Valor da fatura."""
        fatura = _fatura_atual(self._node())
        if not fatura:
            return None
        val = _first(fatura, "valor", "valorTotal", "valorFatura", "vlTotal")
        try:
            return float(val) if val is not None else None
        except (TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Vencimento, status, referência, código de barras, PIX."""
        fatura = _fatura_atual(self._node()) or {}
        return {
            "vencimento": _first(fatura, "dataVencimento", "vencimento", "dtVencimento"),
            "status": _first(fatura, "status", "situacao"),
            "referencia": _first(fatura, "referencia", "mesReferencia", "competencia"),
            "codigo_barras": _first(fatura, "codigoBarras", "linhaDigitavel"),
            "pix": _first(fatura, "pix", "qrCodePix", "pixCopiaECola"),
        }


class NeoenergiaConsumoSensor(NeoenergiaUCEntity, SensorEntity):
    """Consumo da fatura/histórico mais recente (kWh)."""

    _attr_translation_key = "consumo"
    _attr_native_unit_of_measurement = "kWh"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: NeoenergiaDataUpdateCoordinator, uc: str) -> None:
        """Inicializa o sensor de consumo."""
        super().__init__(coordinator, uc)
        self._attr_unique_id = f"{uc}_consumo"

    def _node(self) -> dict[str, Any]:
        return (self.coordinator.data or {}).get("ucs", {}).get(self._uc, {})

    def _historico_list(self) -> list[dict[str, Any]]:
        h = self._node().get("historico")
        if isinstance(h, list):
            return [x for x in h if isinstance(x, dict)]
        if isinstance(h, dict):
            for k in ("content", "data", "historico", "items", "consumos"):
                if isinstance(h.get(k), list):
                    return [x for x in h[k] if isinstance(x, dict)]
        return []

    @property
    def native_value(self) -> float | None:
        """Consumo mais recente (kWh)."""
        hist = self._historico_list()
        if hist:
            val = _first(hist[-1], "consumo", "consumoKwh", "quantidade", "valor")
        else:
            fatura = _fatura_atual(self._node()) or {}
            val = _first(fatura, "consumo", "consumoKwh", "quantidade")
        try:
            return float(val) if val is not None else None
        except (TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Série do histórico de consumo."""
        return {"historico": self._historico_list()}


class NeoenergiaBandeiraSensor(
    CoordinatorEntity["NeoenergiaDataUpdateCoordinator"], SensorEntity
):
    """Bandeira tarifária vigente."""

    _attr_has_entity_name = True
    _attr_translation_key = "bandeira"

    def __init__(self, coordinator: NeoenergiaDataUpdateCoordinator) -> None:
        """Inicializa o sensor de bandeira."""
        super().__init__(coordinator)
        self._attr_unique_id = f"neoenergia_bandeira_{coordinator.client.documento}"

    @property
    def native_value(self) -> str | None:
        """Cor/nome da bandeira tarifária."""
        b = (self.coordinator.data or {}).get("bandeira")
        if isinstance(b, dict):
            return _first(b, "bandeira", "cor", "nome", "descricao")
        if isinstance(b, str):
            return b
        return None
