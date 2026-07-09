"""Configuration loading for the empty application skeleton."""

from __future__ import annotations

from dataclasses import dataclass
from os import environ

DEFAULT_SERVICE_NAME = "menu-planner-app"
DEFAULT_ENVIRONMENT = "development"
DEFAULT_HERMES_BASE_URL = "http://hermes:8642"
DEFAULT_EXPECTED_MIGRATION_REVISION = "20260709_0001"


@dataclass(frozen=True)
class Settings:
    service_name: str
    environment: str
    database_url: str
    hermes_base_url: str
    expected_migration_revision: str

    def safe_summary(self) -> dict[str, str]:
        return {
            "service_name": self.service_name,
            "environment": self.environment,
            "database_url": redact_database_url(self.database_url),
            "hermes_base_url": self.hermes_base_url,
            "expected_migration_revision": self.expected_migration_revision,
        }


def get_settings() -> Settings:
    return Settings(
        service_name=environ.get("APP_SERVICE_NAME", DEFAULT_SERVICE_NAME),
        environment=environ.get("APP_ENV", DEFAULT_ENVIRONMENT),
        database_url=environ.get("DATABASE_URL", ""),
        hermes_base_url=environ.get("HERMES_BASE_URL", DEFAULT_HERMES_BASE_URL),
        expected_migration_revision=environ.get(
            "EXPECTED_MIGRATION_REVISION",
            DEFAULT_EXPECTED_MIGRATION_REVISION,
        ),
    )


def redact_database_url(database_url: str) -> str:
    if not database_url:
        return ""

    if "@" not in database_url:
        return database_url

    scheme, separator, rest = database_url.partition("://")
    credentials, at, host_part = rest.partition("@")
    if not separator or not at or not credentials:
        return database_url
    return f"{scheme}{separator}<redacted>@{host_part}"
