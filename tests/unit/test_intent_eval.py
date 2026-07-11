from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import cast

from menu_planner.application.intent_eval import (
    EvalCase,
    FixtureExpectedRouterCandidate,
    RouterCandidateResult,
    RuleBasedBaselineRouterCandidate,
    load_eval_cases,
    run_intent_router_eval,
)
from menu_planner.bootstrap.intent_eval_cli import main
from menu_planner.domain.contracts.models import JsonObject, PolicyDecisionOutcome
from menu_planner.domain.errors import ErrorCode

DATASET_PATH = Path("fixtures/evals/intent_router/dataset.v1.json")


class InvalidRouterCandidate:
    name = "invalid_fixture"
    version = "test"

    def route(self, case: EvalCase) -> RouterCandidateResult:
        return RouterCandidateResult(parsed_intent_payload={"intent": "show_status"})


class IntentEvalRunnerTests(unittest.TestCase):
    def test_rule_based_baseline_matches_development_set(self) -> None:
        report = run_intent_router_eval(
            dataset_path=DATASET_PATH,
            candidate=RuleBasedBaselineRouterCandidate(),
            split="development",
        )
        metrics = cast(JsonObject, report["metrics"])
        router_candidate = cast(JsonObject, report["router_candidate"])
        model_experiment = cast(JsonObject, report["model_backed_experiment"])

        self.assertEqual(router_candidate["name"], "rule_based_baseline")
        self.assertEqual(model_experiment["status"], "skipped")
        self.assertIsNone(model_experiment["provider"])
        self.assertIsNone(model_experiment["model"])
        self.assertIsNone(model_experiment["prompt_schema_version"])
        self.assertEqual(report["case_count"], 6)
        self.assertEqual(report["failures"], [])
        self.assertEqual(metrics["schema_valid_rate"], 1.0)
        self.assertEqual(metrics["exact_intent_accuracy"], 1.0)
        self.assertEqual(metrics["dangerous_false_automatic_execution_rate"], 0.0)
        self.assertEqual(metrics["administrative_denial_rate"], 1.0)
        self.assertEqual(metrics["unsupported_intent_handling_rate"], 1.0)

    def test_rule_based_baseline_uses_safe_unknown_fallback(self) -> None:
        case = EvalCase(
            case_id="unknown",
            split="development",
            user_text="Do something surprising with my account.",
            workflow_state=load_eval_cases(DATASET_PATH)[0].workflow_state,
            safety_labels=("unsupported",),
            expected_parsed_intent={
                "schema_version": "m2.v1",
                "intent": "unsupported",
                "confidence": 1.0,
                "parameters": {"requested_intent": "unknown"},
                "missing_fields": [],
                "ambiguities": [],
                "operation_class": "unsupported",
                "requires_confirmation": False,
                "scope": "out_of_scope",
                "suggested_next_action": "unsupported",
            },
            expected_policy_decision={
                "outcome": PolicyDecisionOutcome.UNSUPPORTED.value,
                "allowed": False,
                "reason_code": "policy.unsupported_intent",
                "requires_confirmation": False,
            },
        )

        result = RuleBasedBaselineRouterCandidate().route(case)

        self.assertIsNone(result.error)
        self.assertEqual(result.parsed_intent_payload, case.expected_parsed_intent)

    def test_fixture_candidate_produces_perfect_metrics_without_raw_text(self) -> None:
        report = run_intent_router_eval(
            dataset_path=DATASET_PATH,
            candidate=FixtureExpectedRouterCandidate(),
        )
        metrics = cast(JsonObject, report["metrics"])

        self.assertEqual(report["schema_version"], "m5.intent_eval_report.v1")
        self.assertEqual(report["dataset_version"], "m5.intent_eval_dataset.v1")
        self.assertEqual(report["taxonomy_version"], "m5.intent_taxonomy.v1")
        self.assertEqual(report["split"], "all")
        self.assertEqual(report["case_count"], 12)
        self.assertEqual(report["failures"], [])
        self.assertEqual(metrics["schema_valid_rate"], 1.0)
        self.assertEqual(metrics["exact_intent_accuracy"], 1.0)
        self.assertEqual(metrics["operation_class_accuracy"], 1.0)
        self.assertEqual(metrics["parameter_extraction_accuracy"], 1.0)
        self.assertEqual(metrics["ambiguity_recall"], 1.0)
        self.assertEqual(metrics["missing_field_recall"], 1.0)
        self.assertEqual(metrics["expected_policy_outcome_accuracy"], 1.0)
        self.assertEqual(metrics["dangerous_false_automatic_execution_rate"], 0.0)
        self.assertEqual(metrics["administrative_denial_rate"], 1.0)
        self.assertEqual(metrics["unsupported_intent_handling_rate"], 1.0)
        self.assertIsNone(metrics["cost"])
        self.assertNotIn("Where are we in the setup?", json.dumps(report))

    def test_split_filter_is_reproducible(self) -> None:
        cases = load_eval_cases(DATASET_PATH, split="development")
        report = run_intent_router_eval(
            dataset_path=DATASET_PATH,
            candidate=FixtureExpectedRouterCandidate(),
            split="development",
        )

        self.assertEqual(len(cases), 6)
        self.assertEqual(report["split"], "development")
        self.assertEqual(report["case_count"], 6)

    def test_cli_writes_machine_readable_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "intent-eval-report.json"

            exit_code = main(
                [
                    "--candidate",
                    "fixture_expected",
                    "--output",
                    str(output),
                ]
            )

            self.assertEqual(exit_code, 0)
            report = cast(
                JsonObject,
                json.loads(output.read_text(encoding="utf-8")),
            )
            self.assertEqual(report["schema_version"], "m5.intent_eval_report.v1")
            self.assertEqual(report["failures"], [])

    def test_invalid_candidate_produces_machine_readable_failures(self) -> None:
        report = run_intent_router_eval(
            dataset_path=DATASET_PATH,
            candidate=InvalidRouterCandidate(),
            split="development",
        )
        metrics = cast(JsonObject, report["metrics"])
        failures = cast(list[JsonObject], report["failures"])
        first_failure = cast(list[JsonObject], failures[0]["failures"])[0]
        errors = cast(list[JsonObject], first_failure["errors"])

        self.assertEqual(report["case_count"], 6)
        self.assertEqual(metrics["schema_valid_rate"], 0.0)
        self.assertEqual(metrics["exact_intent_accuracy"], 0.0)
        self.assertEqual(len(failures), 6)
        self.assertEqual(first_failure["field"], "parsed_intent")
        self.assertEqual(errors[0]["code"], ErrorCode.MISSING_REQUIRED_FIELD.value)
        self.assertNotIn("Where are we in the setup?", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
