"""Config flow da Neoenergia (CPF/CNPJ + senha da Agência Virtual)."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import (
    NeoenergiaApiClient,
    NeoenergiaApiCommunicationError,
    NeoenergiaApiError,
    NeoenergiaAuthError,
)
from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_DISTRIBUIDORA,
    CONF_DOCUMENTO,
    DISTRIBUIDORAS,
    DOMAIN,
)


class NeoenergiaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Fluxo de configuração via UI."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """CPF/CNPJ + senha + distribuidora (+ credencial de gateway opcional)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            documento = "".join(c for c in user_input[CONF_DOCUMENTO] if c.isdigit())
            try:
                client = NeoenergiaApiClient(
                    documento=documento,
                    password=user_input[CONF_PASSWORD],
                    session=async_get_clientsession(self.hass),
                    distribuidora=user_input[CONF_DISTRIBUIDORA],
                    client_id=user_input.get(CONF_CLIENT_ID) or None,
                    client_secret=user_input.get(CONF_CLIENT_SECRET) or None,
                )
                await client.async_login()
            except NeoenergiaAuthError:
                errors["base"] = "invalid_auth"
            except NeoenergiaApiCommunicationError:
                errors["base"] = "cannot_connect"
            except NeoenergiaApiError:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(
                    f"{user_input[CONF_DISTRIBUIDORA]}:{documento}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Neoenergia {user_input[CONF_DISTRIBUIDORA].title()} ({documento})",
                    data={
                        CONF_DOCUMENTO: documento,
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_DISTRIBUIDORA: user_input[CONF_DISTRIBUIDORA],
                        CONF_CLIENT_ID: user_input.get(CONF_CLIENT_ID, ""),
                        CONF_CLIENT_SECRET: user_input.get(CONF_CLIENT_SECRET, ""),
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_DOCUMENTO): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_DISTRIBUIDORA, default="cosern"): SelectSelector(
                    SelectSelectorConfig(
                        options=DISTRIBUIDORAS, mode=SelectSelectorMode.DROPDOWN
                    )
                ),
                vol.Optional(CONF_CLIENT_ID): str,
                vol.Optional(CONF_CLIENT_SECRET): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
