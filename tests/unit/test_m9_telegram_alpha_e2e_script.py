from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "m9_telegram_alpha_e2e.py"
DEV_SCRIPT = ROOT / "scripts" / "dev.sh"


def _load_script() -> Any:
    spec = importlib.util.spec_from_file_location("m9_telegram_alpha_e2e", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["m9_telegram_alpha_e2e"] = module
    spec.loader.exec_module(module)
    return module


class M9TelegramAlphaE2EScriptTests(unittest.TestCase):
    def test_dev_command_exists(self) -> None:
        text = DEV_SCRIPT.read_text(encoding="utf-8")

        self.assertIn("m9-telegram-alpha-e2e", text)
        self.assertIn("scripts/m9_telegram_alpha_e2e.py", text)

    def test_synthetic_e2e_command_writes_safe_transcript(self) -> None:
        script = _load_script()

        exit_code = script.main()

        self.assertEqual(exit_code, 0)
        transcript = script.TRANSCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn('"ok": true', transcript)
        self.assertIn('"telegram_network_used": false', transcript)
        self.assertIn('"credentials_used": false', transcript)
        self.assertIn('"direct_db_writes": false', transcript)
        self.assertIn('"meaningful_changes_require_confirmation": true', transcript)
        self.assertIn('"name": "create_update_profile"', transcript)
        self.assertIn('"name": "generate_menu_or_accepted_path"', transcript)
        self.assertIn('"name": "revision"', transcript)
        self.assertIn('"name": "confirm"', transcript)
        self.assertIn('"name": "recipe_view"', transcript)
        self.assertIn('"name": "shopping_checklist"', transcript)
        self.assertIn('"name": "cancel"', transcript)
        self.assertIn('"name": "expired_confirmation"', transcript)
        self.assertNotIn("TELEGRAM_BOT_TOKEN", transcript)
        self.assertNotIn("OPENAI_API_KEY", transcript)


if __name__ == "__main__":
    unittest.main()
