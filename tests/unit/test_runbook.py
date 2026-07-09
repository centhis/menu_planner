from __future__ import annotations

import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
RUNBOOK = ROOT / "docs" / "runbooks" / "local-development.md"


class LocalDevelopmentRunbookTests(unittest.TestCase):
    def test_runbook_covers_required_stage_1_topics(self) -> None:
        text = RUNBOOK.read_text(encoding="utf-8")

        required_fragments = [
            "cp .env.example .env",
            "Never commit",
            "scripts/dev.sh up",
            "scripts/dev.sh migrate",
            "scripts/dev.sh test",
            "scripts/dev.sh smoke",
            "scripts/dev.sh down",
            "docker compose down -v",
            "deletes named volumes",
        ]

        for fragment in required_fragments:
            self.assertIn(fragment, text)

    def test_runbook_does_not_include_obvious_secret_values(self) -> None:
        text = RUNBOOK.read_text(encoding="utf-8")

        forbidden_fragments = [
            "OPENAI_API_KEY=sk-",
            "ANTHROPIC_API_KEY=sk-",
            "BEGIN PRIVATE KEY",
            "TELEGRAM_BOT_TOKEN=",
        ]

        for fragment in forbidden_fragments:
            self.assertNotIn(fragment, text)


if __name__ == "__main__":
    unittest.main()
