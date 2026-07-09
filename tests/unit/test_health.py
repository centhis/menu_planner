from __future__ import annotations

import unittest

from menu_planner.application.health import health_status, readiness_status


class PassingDatabaseProbe:
    def ping(self) -> None:
        return None


class FailingDatabaseProbe:
    def ping(self) -> None:
        raise RuntimeError("database unavailable")


class PassingMigrationProbe:
    def ping(self) -> None:
        return None


class FailingMigrationProbe:
    def ping(self) -> None:
        raise RuntimeError("migration mismatch")


class PassingHermesProbe:
    def ping(self) -> None:
        return None


class FailingHermesProbe:
    def ping(self) -> None:
        raise RuntimeError("hermes unavailable")


class HealthTests(unittest.TestCase):
    def test_health_status_is_ok(self) -> None:
        status = health_status("menu-planner-test")

        self.assertEqual(
            status.as_dict(),
            {
                "status": "ok",
                "service": "menu-planner-test",
            },
        )

    def test_readiness_status_is_ready_when_database_ping_passes(self) -> None:
        status = readiness_status(
            "menu-planner-test",
            PassingDatabaseProbe(),
            PassingMigrationProbe(),
            PassingHermesProbe(),
        )

        self.assertEqual(
            status.as_dict(),
            {
                "status": "ready",
                "service": "menu-planner-test",
                "database": "available",
                "migrations": "current",
                "hermes": "available",
            },
        )

    def test_readiness_status_reports_database_failure(self) -> None:
        status = readiness_status(
            "menu-planner-test",
            FailingDatabaseProbe(),
            PassingMigrationProbe(),
            PassingHermesProbe(),
        )

        self.assertEqual(
            status.as_dict(),
            {
                "status": "not_ready",
                "service": "menu-planner-test",
                "database": "unavailable",
                "migrations": "current",
                "hermes": "available",
                "errors": {"database": "database unavailable"},
            },
        )

    def test_readiness_status_reports_migration_and_hermes_failures(self) -> None:
        status = readiness_status(
            "menu-planner-test",
            PassingDatabaseProbe(),
            FailingMigrationProbe(),
            FailingHermesProbe(),
        )

        self.assertEqual(
            status.as_dict(),
            {
                "status": "not_ready",
                "service": "menu-planner-test",
                "database": "available",
                "migrations": "not_current",
                "hermes": "unavailable",
                "errors": {
                    "migrations": "migration mismatch",
                    "hermes": "hermes unavailable",
                },
            },
        )


if __name__ == "__main__":
    unittest.main()
