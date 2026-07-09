"""Hermes runtime readiness probe."""

from __future__ import annotations

import socket
from urllib.parse import urlparse


class HermesReachabilityProbe:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    def ping(self) -> None:
        if not self._base_url:
            raise RuntimeError("HERMES_BASE_URL is not configured")

        parsed = urlparse(self._base_url)
        host = parsed.hostname
        port = parsed.port or _default_port(parsed.scheme)
        if not host or port is None:
            raise RuntimeError(f"HERMES_BASE_URL is not reachable: {self._base_url}")

        try:
            with socket.create_connection((host, port), timeout=5):
                return
        except OSError as exc:
            raise RuntimeError(f"Hermes readiness check failed: {exc}") from exc


def _default_port(scheme: str) -> int | None:
    if scheme == "http":
        return 80
    if scheme == "https":
        return 443
    return None
