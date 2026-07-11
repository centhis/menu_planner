from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import cast

from menu_planner.application.recipe_replacement_eval import (
    run_m6b_recipe_replacement_eval,
)
from menu_planner.bootstrap.recipe_replacement_eval_cli import main
from menu_planner.domain.contracts.models import JsonObject


class RecipeReplacementEvalTests(unittest.TestCase):
    def test_fake_gate_eval_skips_model_backed_experiment(self) -> None:
        report = run_m6b_recipe_replacement_eval()
        metrics = cast(JsonObject, report["metrics"])
        experiment = cast(JsonObject, report["model_backed_experiment"])
        generator = cast(JsonObject, report["generator_candidate"])
        preview = cast(JsonObject, report["preview"])

        self.assertEqual(
            report["schema_version"],
            "m6b.recipe_replacement_eval_report.v1",
        )
        self.assertEqual(generator["name"], "fake_recipe_draft_generator")
        self.assertEqual(experiment["status"], "skipped")
        self.assertIsNone(experiment["provider"])
        self.assertIsNone(experiment["model"])
        self.assertIsNone(experiment["prompt_schema_version"])
        self.assertFalse(cast(bool, experiment["credentials_read"]))
        self.assertFalse(cast(bool, experiment["raw_output_stored"]))
        self.assertTrue(cast(bool, metrics["generation_ok"]))
        self.assertTrue(cast(bool, metrics["validation_ok"]))
        self.assertTrue(cast(bool, metrics["replacement_diff_ok"]))
        self.assertTrue(cast(bool, metrics["stale_confirmation_rejected"]))
        self.assertFalse(cast(bool, metrics["external_provider_required"]))
        self.assertFalse(cast(bool, metrics["confirmed_state_changed"]))
        self.assertFalse(cast(bool, metrics["side_effects_executed"]))
        self.assertTrue(cast(bool, preview["created"]))
        self.assertTrue(cast(bool, preview["requires_confirmation"]))
        self.assertEqual(report["failures"], [])
        self.assertNotIn("OPENAI_API_KEY", json.dumps(report))
        self.assertNotIn("auth.json", json.dumps(report))

    def test_cli_writes_machine_readable_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "m6b-recipe-replacement-eval-report.json"

            exit_code = main(["--output", str(output)])

            self.assertEqual(exit_code, 0)
            report = cast(
                JsonObject,
                json.loads(output.read_text(encoding="utf-8")),
            )
            self.assertEqual(
                report["schema_version"],
                "m6b.recipe_replacement_eval_report.v1",
            )
            self.assertEqual(report["failures"], [])


if __name__ == "__main__":
    unittest.main()
