"""PostgreSQL readiness probe."""

from __future__ import annotations


class PsycopgDatabaseProbe:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def ping(self) -> None:
        if not self._database_url:
            raise RuntimeError("DATABASE_URL is not configured")

        try:
            import psycopg
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "psycopg is not installed. Install application dependencies "
                "before checking database readiness."
            ) from exc

        try:
            with psycopg.connect(self._database_url, connect_timeout=5) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("select 1")
                    cursor.fetchone()
        except Exception as exc:  # noqa: BLE001 - readiness converts driver errors.
            raise RuntimeError(f"database readiness check failed: {exc}") from exc


class AlembicMigrationProbe:
    def __init__(self, database_url: str, expected_revision: str) -> None:
        self._database_url = database_url
        self._expected_revision = expected_revision

    def ping(self) -> None:
        if not self._database_url:
            raise RuntimeError("DATABASE_URL is not configured")
        if not self._expected_revision:
            raise RuntimeError("EXPECTED_MIGRATION_REVISION is not configured")

        try:
            import psycopg
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "psycopg is not installed. Install application dependencies "
                "before checking migration readiness."
            ) from exc

        try:
            with psycopg.connect(self._database_url, connect_timeout=5) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("select version_num from alembic_version")
                    row = cursor.fetchone()
        except Exception as exc:  # noqa: BLE001 - readiness converts driver errors.
            raise RuntimeError(f"migration readiness check failed: {exc}") from exc

        actual_revision = row[0] if row else None
        if actual_revision != self._expected_revision:
            raise RuntimeError(
                "migration revision mismatch: "
                f"expected {self._expected_revision}, got {actual_revision or '<none>'}"
            )
