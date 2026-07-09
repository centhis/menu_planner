from __future__ import annotations

import unittest
from collections.abc import Mapping, Sequence
from typing import Any
from unittest import mock

from menu_planner.infrastructure.database import (
    AlembicMigrationProbe,
    PsycopgDatabaseProbe,
)


class DatabaseProbeTests(unittest.TestCase):
    def test_ping_fails_clearly_when_database_url_is_missing(self) -> None:
        probe = PsycopgDatabaseProbe("")

        with self.assertRaisesRegex(RuntimeError, "DATABASE_URL is not configured"):
            probe.ping()

    def test_ping_fails_clearly_when_psycopg_is_missing(self) -> None:
        probe = PsycopgDatabaseProbe("postgresql://user:secret@postgres:5432/menu")
        real_import = __import__

        def fake_import(
            name: str,
            globals_: Mapping[str, object] | None = None,
            locals_: Mapping[str, object] | None = None,
            fromlist: Sequence[str] = (),
            level: int = 0,
        ) -> Any:
            if name == "psycopg":
                raise ModuleNotFoundError("No module named 'psycopg'")
            return real_import(name, globals_, locals_, fromlist, level)

        with self.assertRaisesRegex(RuntimeError, "psycopg is not installed"):
            with mock.patch("builtins.__import__", side_effect=fake_import):
                probe.ping()


class MigrationProbeTests(unittest.TestCase):
    def test_ping_fails_clearly_when_expected_revision_is_missing(self) -> None:
        probe = AlembicMigrationProbe(
            "postgresql://user:secret@postgres:5432/menu",
            "",
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "EXPECTED_MIGRATION_REVISION is not configured",
        ):
            probe.ping()


if __name__ == "__main__":
    unittest.main()
