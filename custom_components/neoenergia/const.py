"""Constantes da integração Neoenergia."""

from __future__ import annotations

import logging

DOMAIN = "neoenergia"
LOGGER = logging.getLogger(__package__)

CONF_DOCUMENTO = "documento"
CONF_DISTRIBUIDORA = "distribuidora"
CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"

DISTRIBUIDORAS = ["cosern", "coelba", "celpe", "elektro", "neoenergia"]

DEFAULT_SCAN_INTERVAL_MINUTES = 360
