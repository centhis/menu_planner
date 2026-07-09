"""HTTP application factory for the empty M1 skeleton."""

from __future__ import annotations

from typing import Any

from menu_planner.application.health import health_status, readiness_status
from menu_planner.config import get_settings
from menu_planner.infrastructure.database import (
    AlembicMigrationProbe,
    PsycopgDatabaseProbe,
)
from menu_planner.infrastructure.hermes import HermesReachabilityProbe


def create_app() -> Any:
    """Create the ASGI app.

    FastAPI is imported lazily so pure unit tests can run before dependencies
    are installed in the application container.
    """

    try:
        from fastapi import FastAPI, HTTPException
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "FastAPI is not installed. Install application dependencies before "
            "starting the ASGI service."
        ) from exc

    settings = get_settings()
    database = PsycopgDatabaseProbe(settings.database_url)
    migrations = AlembicMigrationProbe(
        settings.database_url,
        settings.expected_migration_revision,
    )
    hermes = HermesReachabilityProbe(settings.hermes_base_url)
    app = FastAPI(title=settings.service_name)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return health_status(settings.service_name).as_dict()

    @app.get("/readyz")
    def readyz() -> dict[str, object]:
        status = readiness_status(settings.service_name, database, migrations, hermes)
        if status.status != "ready":
            raise HTTPException(status_code=503, detail=status.as_dict())
        return status.as_dict()

    return app
