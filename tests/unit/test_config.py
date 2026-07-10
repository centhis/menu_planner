from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from menu_planner.config import (
    DEFAULT_ENVIRONMENT,
    DEFAULT_EXPECTED_MIGRATION_REVISION,
    DEFAULT_HERMES_BASE_URL,
    DEFAULT_SERVICE_NAME,
    get_settings,
    redact_database_url,
)


class ConfigTests(unittest.TestCase):
    def test_defaults_are_safe_for_empty_environment(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = get_settings()

        self.assertEqual(settings.service_name, DEFAULT_SERVICE_NAME)
        self.assertEqual(settings.environment, DEFAULT_ENVIRONMENT)
        self.assertEqual(settings.database_url, "")
        self.assertEqual(settings.hermes_base_url, DEFAULT_HERMES_BASE_URL)
        self.assertEqual(
            settings.expected_migration_revision,
            DEFAULT_EXPECTED_MIGRATION_REVISION,
        )

    def test_safe_summary_redacts_database_credentials(self) -> None:
        with patch.dict(
            os.environ,
            {
                "APP_SERVICE_NAME": "menu-planner-test",
                "APP_ENV": "test",
                "DATABASE_URL": "postgresql://user:secret@postgres:5432/menu",
                "HERMES_BASE_URL": "http://hermes:8642",
                "EXPECTED_MIGRATION_REVISION": "20260710_0002",
            },
            clear=True,
        ):
            settings = get_settings()

        self.assertEqual(
            settings.safe_summary(),
            {
                "service_name": "menu-planner-test",
                "environment": "test",
                "database_url": "postgresql://<redacted>@postgres:5432/menu",
                "hermes_base_url": "http://hermes:8642",
                "expected_migration_revision": "20260710_0002",
            },
        )

    def test_redact_database_url_preserves_non_credential_urls(self) -> None:
        self.assertEqual(
            redact_database_url("postgresql://postgres/menu"),
            "postgresql://postgres/menu",
        )


if __name__ == "__main__":
    unittest.main()
