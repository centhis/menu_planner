from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import cast

from menu_planner.application.shopping_eval import run_m7_shopping_eval
from menu_planner.bootstrap.shopping_eval_cli import main
from menu_planner.domain.contracts.models import JsonObject


class ShoppingEvalTests(unittest.TestCase):
    def test_gate_eval_report_is_deterministic_and_green(self) -> None:
        first = run_m7_shopping_eval()
        second = run_m7_shopping_eval()
        metrics = cast(JsonObject, first["metrics"])
        experiment = cast(JsonObject, first["model_backed_experiment"])
        replacement_diff = cast(JsonObject, first["replacement_diff"])
        checklist = cast(JsonObject, first["checklist"])

        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], "m7.shopping_list_eval_report.v1")
        self.assertTrue(cast(bool, metrics["unit_conversion_ok"]))
        self.assertTrue(cast(bool, metrics["ingredient_scaling_merge_ok"]))
        self.assertTrue(cast(bool, metrics["mock_catalog_matching_ok"]))
        self.assertTrue(cast(bool, metrics["package_cost_calculation_ok"]))
        self.assertTrue(cast(bool, metrics["shopping_list_identity_ok"]))
        self.assertTrue(cast(bool, metrics["replacement_diff_ok"]))
        self.assertTrue(cast(bool, metrics["checklist_exact_update_ok"]))
        self.assertTrue(cast(bool, metrics["checklist_text_one_match_ok"]))
        self.assertTrue(
            cast(
                bool,
                metrics["checklist_text_ambiguous_requires_disambiguation"],
            )
        )
        self.assertTrue(cast(bool, metrics["checklist_text_no_match_controlled_error"]))
        self.assertFalse(cast(bool, metrics["confirmed_state_changed"]))
        self.assertFalse(cast(bool, metrics["side_effects_executed"]))
        self.assertFalse(cast(bool, metrics["external_provider_required"]))
        self.assertFalse(cast(bool, metrics["credentials_read"]))
        self.assertEqual(experiment["status"], "skipped")
        self.assertTrue(cast(bool, replacement_diff["created"]))
        self.assertGreater(cast(int, replacement_diff["change_count"]), 0)
        self.assertEqual(checklist["ambiguous_candidate_count"], 2)
        self.assertEqual(checklist["no_match_error_code"], "shopping.item_not_found")
        self.assertEqual(first["failures"], [])
        self.assertNotIn("OPENAI_API_KEY", json.dumps(first))
        self.assertNotIn("auth.json", json.dumps(first))

    def test_cli_writes_machine_readable_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "m7-shopping-eval-report.json"

            exit_code = main(["--output", str(output)])

            self.assertEqual(exit_code, 0)
            report = cast(
                JsonObject,
                json.loads(output.read_text(encoding="utf-8")),
            )
            self.assertEqual(
                report["schema_version"],
                "m7.shopping_list_eval_report.v1",
            )
            self.assertEqual(report["failures"], [])


if __name__ == "__main__":
    unittest.main()
