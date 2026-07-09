"""Health and readiness behavior for the empty application skeleton."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol


class ComponentProbe(Protocol):
    """Minimal probe contract used by readiness checks."""

    def ping(self) -> None:
        """Raise a meaningful exception when the component is unavailable."""


@dataclass(frozen=True)
class HealthStatus:
    status: str
    service: str

    def as_dict(self) -> dict[str, str]:
        return {
            "status": self.status,
            "service": self.service,
        }


@dataclass(frozen=True)
class ReadinessStatus:
    status: str
    service: str
    database: str
    migrations: str
    hermes: str
    errors: dict[str, str] | None = None
    error: str | None = None

    def as_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "status": self.status,
            "service": self.service,
            "database": self.database,
            "migrations": self.migrations,
            "hermes": self.hermes,
        }
        if self.errors:
            payload["errors"] = self.errors
        if self.error is not None:
            payload["error"] = self.error
        return payload


def health_status(service_name: str) -> HealthStatus:
    return HealthStatus(status="ok", service=service_name)


def readiness_status(
    service_name: str,
    database: ComponentProbe,
    migrations: ComponentProbe,
    hermes: ComponentProbe,
) -> ReadinessStatus:
    component_statuses: dict[str, str] = {
        "database": "available",
        "migrations": "current",
        "hermes": "available",
    }
    errors: dict[str, str] = {}

    for name, probe in _components(
        ("database", database),
        ("migrations", migrations),
        ("hermes", hermes),
    ):
        try:
            probe.ping()
        except Exception as exc:  # noqa: BLE001 - readiness exposes controlled failure.
            component_statuses[name] = _unavailable_status(name)
            errors[name] = str(exc)

    if errors:
        return ReadinessStatus(
            status="not_ready",
            service=service_name,
            database=component_statuses["database"],
            migrations=component_statuses["migrations"],
            hermes=component_statuses["hermes"],
            errors=errors,
        )

    return ReadinessStatus(
        status="ready",
        service=service_name,
        database=component_statuses["database"],
        migrations=component_statuses["migrations"],
        hermes=component_statuses["hermes"],
    )


def _components(
    *items: tuple[str, ComponentProbe],
) -> Iterable[tuple[str, ComponentProbe]]:
    return items


def _unavailable_status(name: str) -> str:
    if name == "migrations":
        return "not_current"
    return "unavailable"
