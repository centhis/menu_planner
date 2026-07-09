from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASELINE = ROOT / "migrations" / "versions" / "20260709_0001_baseline.py"


class MigrationTests(unittest.TestCase):
    def test_baseline_migration_does_not_create_domain_tables(self) -> None:
        text = BASELINE.read_text(encoding="utf-8")

        forbidden_terms = [
            "create_table",
            "profile",
            "menu",
            "recipe",
            "shopping",
            "workflow",
            "confirmation",
        ]

        for term in forbidden_terms:
            self.assertNotIn(term, text)

    def test_migration_entrypoints_exist(self) -> None:
        self.assertTrue((ROOT / "scripts" / "migrate.sh").is_file())
        self.assertTrue((ROOT / "scripts" / "migration-status.sh").is_file())


if __name__ == "__main__":
    unittest.main()
