"""Cliente da API da Neoenergia (Cosern/Coelba/Celpe/Elektro) — Agência Virtual.

Engenharia reversa do web app Angular `agenciavirtual.neoenergia.com`:

- Gateway WSO2 em `https://apineprd.neoenergia.com` (região NE cobre **Cosern**,
  Coelba, Celpe). Login = **OAuth2 password grant** em `/token` com
  `grant_type=password`, `client_id`/`client_secret` (por canal), `username`
  (CPF/CNPJ), `password`, `scope=openid`. Resposta: access_token / refresh_token
  / id_token / expires_in. As chamadas de dados usam `Authorization: Bearer <access_token>`.
- Mapa de endpoints (de `environment.endpoints`): UCs, faturas, histórico de
  consumo, minha-conta, débitos, bandeira tarifária, autoleitura.

⚠️ IMPORTANTE (credencial do gateway): os `client_id`/`client_secret` abaixo
vieram do bundle estático, mas o gateway de produção respondeu `invalid_client`
para eles — provavelmente são decifrados em runtime. Rode
`scripts/capturar_credencial.py` (ou um login real) para capturar o
`client_id`/`client_secret` reais e informe-os na configuração (campos avançados)
ou substitua as constantes aqui. Enquanto isso, o login falhará com
`invalid_client`.
"""

from __future__ import annotations

import socket
import time
from typing import Any

import aiohttp
import async_timeout

HOST = "https://apineprd.neoenergia.com"
HOST_ANL = "https://avapineanl.neoenergia.com"
TOKEN_URL = f"{HOST}/token"
SCOPE = "openid"

# Endpoints (environment.endpoints, caso NE: celpe/coelba/cosern)
EP = {
    "ucs": f"{HOST}/imoveis/1.1.0/clientes/{{documento}}/ucs",
    "faturas": f"{HOST}/multilogin/2.0.0/servicos/faturas/ucs/faturas",
    "faturas_simplificada": f"{HOST}/multilogin/2.0.0/servicos/faturas/faturas-simplificada",
    "minha_conta": f"{HOST}/multilogin/2.0.0/servicos/minha-conta",
    "historico": f"{HOST}/multilogin/2.0.0/servicos/historicos/",
    "consultar_debitos": f"{HOST}/multilogin/2.0.0/servicos/consultar-debitos",
    "bandeira_tarifaria": f"{HOST}/bandeira-tarifaria/1.0.0/",
    "autoleitura_ucs": f"{HOST}/multilogin/2.0.0/servicos/autoleitura/ucs/",
}

# client_id/client_secret por canal (do bundle; ver aviso no topo).
# AGC=Coelba, AGP=Pernambuco/Celpe, AGE=Elektro, AGR=?, default(AGU)=Neoenergia.
CLIENTS = {
    "cosern": ("a_vrfGrkqevUPzXWSZbC_KwkEX8a", "ZmILVM_atdaM7C7O6sayq029XM4a"),
    "coelba": ("YicYeqO8E_XACfWfjeQgLSo6Md0a", "FFiuHe1wEiSKJZRU8ENqMC4sA0oa"),
    "celpe": ("uScXQQwAe2qxKATIvv1EfB77IoYa", "agbpXX7kWfSfuOCH8cdfzwf7Riga"),
    "elektro": ("7fUw6KahtPMfaNz_8DQ241Fqo2Ia", "KRQZu1qipiNr3N2v61qOuskJYmAa"),
    "neoenergia": ("a_vrfGrkqevUPzXWSZbC_KwkEX8a", "ZmILVM_atdaM7C7O6sayq029XM4a"),
}

_TIMEOUT = 40
_REFRESH_SKEW = 60


class NeoenergiaApiError(Exception):
    """Erro geral da API."""


class NeoenergiaApiCommunicationError(NeoenergiaApiError):
    """Falha de comunicação/timeout."""


class NeoenergiaAuthError(NeoenergiaApiError):
    """Credenciais/cliente inválidos ou sessão expirada."""


class NeoenergiaApiClient:
    """Cliente autenticado da Agência Virtual (OAuth2 password grant)."""

    def __init__(
        self,
        documento: str,
        password: str,
        session: aiohttp.ClientSession,
        distribuidora: str = "cosern",
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        """documento = CPF/CNPJ (só dígitos); distribuidora ∈ CLIENTS."""
        self._documento = "".join(c for c in documento if c.isdigit())
        self._password = password
        self._session = session
        self._distribuidora = distribuidora
        default_id, default_secret = CLIENTS.get(distribuidora, CLIENTS["neoenergia"])
        self._client_id = client_id or default_id
        self._client_secret = client_secret or default_secret
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at = 0.0

    @property
    def documento(self) -> str:
        """CPF/CNPJ (só dígitos)."""
        return self._documento

    async def async_login(self) -> None:
        """OAuth2 password grant."""
        await self._token_request(
            {
                "grant_type": "password",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "username": self._documento,
                "password": self._password,
                "scope": SCOPE,
            }
        )

    async def _refresh(self) -> None:
        await self._token_request(
            {
                "grant_type": "refresh_token",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
            }
        )

    async def _token_request(self, form: dict[str, Any]) -> None:
        try:
            async with async_timeout.timeout(_TIMEOUT):
                resp = await self._session.post(
                    TOKEN_URL,
                    data=form,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                body = await resp.json(content_type=None)
        except (TimeoutError, aiohttp.ClientError, socket.gaierror) as err:
            msg = f"erro de comunicação com a Neoenergia: {err}"
            raise NeoenergiaApiCommunicationError(msg) from err
        if resp.status >= 400 or "access_token" not in (body or {}):
            err = (body or {}).get("error") or f"HTTP {resp.status}"
            desc = (body or {}).get("error_description", "")
            msg = f"login recusado: {err} {desc}".strip()
            raise NeoenergiaAuthError(msg)
        self._access_token = body["access_token"]
        self._refresh_token = body.get("refresh_token", self._refresh_token)
        self._expires_at = time.monotonic() + int(body.get("expires_in", 3600))

    async def _token(self) -> str:
        if self._access_token is None:
            await self.async_login()
        elif time.monotonic() >= self._expires_at - _REFRESH_SKEW:
            await self._refresh()
        return self._access_token  # type: ignore[return-value]

    async def _get(self, url: str, params: dict[str, Any] | None = None) -> Any:
        token = await self._token()
        try:
            async with async_timeout.timeout(_TIMEOUT):
                resp = await self._session.get(
                    url,
                    params=params,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json",
                    },
                )
        except (TimeoutError, aiohttp.ClientError, socket.gaierror) as err:
            msg = f"erro de comunicação com a Neoenergia: {err}"
            raise NeoenergiaApiCommunicationError(msg) from err
        if resp.status in (401, 403):
            msg = "token recusado pela Neoenergia (401/403)"
            raise NeoenergiaAuthError(msg)
        if resp.status >= 400:
            text = await resp.text()
            msg = f"Neoenergia respondeu {resp.status}: {text[:200]}"
            raise NeoenergiaApiError(msg)
        return await resp.json(content_type=None)

    # --- leituras (shapes a confirmar com captura real) ---

    async def async_list_ucs(self) -> Any:
        """GET imoveis/.../clientes/{documento}/ucs -> unidades consumidoras."""
        url = EP["ucs"].format(documento=self._documento)
        return await self._get(
            url, params={"documento": self._documento, "distribuidora": self._distribuidora}
        )

    async def async_faturas(self, uc: str, instalacao: str | None = None) -> Any:
        """GET servicos/faturas/ucs/faturas -> faturas da UC."""
        params = {"documentoCliente": self._documento, "uc": uc}
        if instalacao:
            params["instalacao"] = instalacao
        return await self._get(EP["faturas"], params=params)

    async def async_debitos(self, uc: str) -> Any:
        """GET servicos/faturas/faturas-simplificada -> débitos/2ª via."""
        return await self._get(
            EP["faturas_simplificada"],
            params={"documentoCliente": self._documento, "uc": uc},
        )

    async def async_minha_conta(self) -> Any:
        """GET servicos/minha-conta -> dados da conta/usuário."""
        return await self._get(EP["minha_conta"], params={"documento": self._documento})

    async def async_historico(self, uc: str) -> Any:
        """GET servicos/historicos/{uc} -> histórico de consumo (kWh)."""
        return await self._get(f"{EP['historico']}{uc}")

    async def async_bandeira(self) -> Any:
        """GET bandeira-tarifaria -> bandeira tarifária vigente."""
        return await self._get(EP["bandeira_tarifaria"])
