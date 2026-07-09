from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
MAKEFILE = ROOT / "Makefile"
DEV_SCRIPT = ROOT / "scripts" / "dev.sh"


class MakefileTests(unittest.TestCase):
    def test_required_m1_targets_exist(self) -> None:
        text = MAKEFILE.read_text(encoding="utf-8")
        target_names: set[str] = set()
        for line in text.splitlines():
            if ":" not in line or line.startswith("\t") or line.startswith("."):
                continue
            names, _separator, _body = line.partition(":")
            target_names.update(names.split())

        required_targets = [
            "setup",
            "up",
            "down",
            "test",
            "lint",
            "typecheck",
            "migrate",
            "smoke",
            "clean",
        ]

        for target in required_targets:
            self.assertIn(target, target_names)

    def test_targets_use_containerized_app_commands(self) -> None:
        text = DEV_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("app_run python -m pytest", text)
        self.assertIn("app_run python -m ruff check", text)
        self.assertIn("app_run python -m mypy", text)
        self.assertIn("scripts/migrate.sh", text)
        self.assertIn("scripts/migration-status.sh", text)

    def test_makefile_delegates_to_dev_script(self) -> None:
        text = MAKEFILE.read_text(encoding="utf-8")

        self.assertIn("scripts/dev.sh $@", text)


if __name__ == "__main__":
    unittest.main()
