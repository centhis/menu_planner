from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SMOKE_SCRIPT = ROOT / "scripts" / "smoke.sh"
DEV_SCRIPT = ROOT / "scripts" / "dev.sh"


class SmokeScriptTests(unittest.TestCase):
    def test_smoke_script_checks_m1_runtime_contract(self) -> None:
        text = SMOKE_SCRIPT.read_text(encoding="utf-8")

        expected_fragments = [
            "$COMPOSE config --services",
            "$COMPOSE config --images",
            "$COMPOSE config --volumes",
            "nousresearch/hermes-agent:v2026.6.19",
            "postgres:16-alpine",
            "menu-planner-app:local",
            "Dockerfile.app",
            "hermes service must not contain build",
            "pg_isready",
            "tests.smoke.application_health",
            "scripts/http-smoke.py",
            "scripts/dev.sh migration-status",
            "Stage 0 probe plugin must not be mounted",
        ]

        for fragment in expected_fragments:
            self.assertIn(fragment, text)

    def test_dev_entrypoint_delegates_smoke_to_script(self) -> None:
        text = DEV_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("scripts/smoke.sh", text)


if __name__ == "__main__":
    unittest.main()
