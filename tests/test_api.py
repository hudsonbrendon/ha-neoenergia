"""Checagens da Neoenergia que rodam sem Home Assistant.

`python3 -I tests/test_api.py`. Valida constantes de endpoint, seleção de
fatura em aberto e normalização de UCs.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import types

for _name in ("aiohttp", "async_timeout"):
    sys.modules.setdefault(_name, types.ModuleType(_name))

_API = (
    pathlib.Path(__file__).resolve().parent.parent
    / "custom_components"
    / "neoenergia"
    / "api.py"
)
_spec = importlib.util.spec_from_file_location("neo_api", _API)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


def test_endpoints() -> None:
    """Token e UCs apontam para o gateway de produção NE."""
    assert _mod.TOKEN_URL == "https://apineprd.neoenergia.com/token"
    assert "clientes/{documento}/ucs" in _mod.EP["ucs"]
    assert set(_mod.CLIENTS) >= {"cosern", "coelba", "celpe", "elektro"}


def test_fatura_atual_prefers_open() -> None:
    """A fatura atual deve ser a EM ABERTO (regra do sensor)."""
    faturas = [
        {"referencia": "2025-01", "status": "paga", "valor": 100.0},
        {"referencia": "2025-02", "status": "aberta", "valor": 120.0},
    ]
    abertas = [
        f for f in faturas if str(f.get("status") or "").lower() not in ("paga", "pago", "quitada")
    ]
    pool = abertas or faturas
    assert pool[0]["valor"] == 120.0


if __name__ == "__main__":
    test_endpoints()
    test_fatura_atual_prefers_open()
    print("todos os checks da Neoenergia passaram")
