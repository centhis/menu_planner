from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from typing import cast

from menu_planner.domain.contracts.models import (
    JsonObject,
    ParsedIntent,
    PolicyDecisionOutcome,
    WorkflowRun,
    WorkflowState,
)
from menu_planner.domain.contracts.validation import validate_contract
from menu_planner.domain.policy import decide_policy
from menu_planner.domain.workflow import allowed_actions

DATASET_PATH = Path("fixtures/evals/intent_router/dataset.v1.json")
TAXONOMY_PATH = Path("fixtures/evals/intent_router/taxonomy.v1.json")

FORBIDDEN_TEXT_PATTERNS = (
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"auth\.json",
        r"\.env",
        r"api[_-]?key",
        r"token",
        r"credential",
        r"telegram_\d{4,}",
    )
)

REQUIRED_LABELS = {
    "read_only",
    "draft_producing",
    "state_changing",
    "administrative",
    "unsupported",
    "incomplete",
    "ambiguous",
    "conflicting_workflow_state",
    "prompt_injection",
    "mixed_intent",
    "typo",
    "conversational_variant",
}


def _load_json(path: Path) -> JsonObject:
    return cast(JsonObject, json.loads(path.read_text(encoding="utf-8")))


def _cases() -> list[JsonObject]:
    return cast(list[JsonObject], _load_json(DATASET_PATH)["cases"])


def _workflow(state: WorkflowState) -> WorkflowRun:
    return WorkflowRun(
        schema_version="m2.v1",
        workflow_id=f"eval_{state.value}",
        user_id="user_001",
        state=state,
        allowed_actions=[action.value for action in allowed_actions(state)],
        attempts=0,
    )


class M5IntentEvalDatasetTests(unittest.TestCase):
    def test_dataset_metadata_and_splits_are_versioned(self) -> None:
        dataset = _load_json(DATASET_PATH)
        cases = cast(list[JsonObject], dataset["cases"])

        self.assertEqual(dataset["schema_version"], "m5.intent_eval_dataset.v1")
        self.assertEqual(dataset["dataset_version"], "m5.intent_eval_dataset.v1")
        self.assertEqual(dataset["taxonomy_version"], "m5.intent_taxonomy.v1")
        self.assertEqual(dataset["split_strategy"], "explicit_case_split")
        self.assertGreaterEqual(len(cases), 10)
        self.assertEqual(
            {case["split"] for case in cases},
            {"development", "holdout"},
        )
        self.assertEqual(
            len({case["id"] for case in cases}),
            len(cases),
        )

    def test_dataset_intents_are_known_to_taxonomy(self) -> None:
        taxonomy = _load_json(TAXONOMY_PATH)
        taxonomy_intents = {
            intent["name"] for intent in cast(list[JsonObject], taxonomy["intents"])
        }

        for case in _cases():
            expected = cast(JsonObject, case["expected"])
            parsed_intent = cast(JsonObject, expected["parsed_intent"])
            with self.subTest(case=case["id"]):
                self.assertIn(parsed_intent["intent"], taxonomy_intents)

    def test_dataset_covers_required_safety_labels(self) -> None:
        observed_labels = {
            label
            for case in _cases()
            for label in cast(list[str], case["safety_labels"])
        }

        self.assertLessEqual(REQUIRED_LABELS, observed_labels)

    def test_expected_parsed_intents_are_schema_valid(self) -> None:
        for case in _cases():
            expected = cast(JsonObject, case["expected"])
            parsed_intent = cast(JsonObject, expected["parsed_intent"])
            with self.subTest(case=case["id"]):
                validation = validate_contract("parsed_intent", parsed_intent)

                self.assertTrue(validation.is_valid, validation.errors)
                self.assertIsInstance(validation.value, ParsedIntent)

    def test_expected_policy_outputs_match_existing_policy(self) -> None:
        for case in _cases():
            expected = cast(JsonObject, case["expected"])
            parsed_intent_payload = cast(JsonObject, expected["parsed_intent"])
            validation = validate_contract("parsed_intent", parsed_intent_payload)
            self.assertIsInstance(validation.value, ParsedIntent)
            parsed_intent = cast(ParsedIntent, validation.value)
            expected_policy = cast(JsonObject, expected["policy_decision"])

            with self.subTest(case=case["id"]):
                decision = decide_policy(
                    parsed_intent,
                    _workflow(WorkflowState(cast(str, case["workflow_state"]))),
                )

                self.assertEqual(
                    decision.outcome,
                    PolicyDecisionOutcome(cast(str, expected_policy["outcome"])),
                )
                self.assertEqual(decision.allowed, expected_policy["allowed"])
                self.assertEqual(
                    decision.reason_code,
                    expected_policy["reason_code"],
                )
                self.assertEqual(
                    decision.requires_confirmation,
                    expected_policy["requires_confirmation"],
                )

    def test_dangerous_cases_never_expect_automatic_execution(self) -> None:
        dangerous_labels = {"dangerous_state_changing", "dangerous_admin"}
        for case in _cases():
            labels = set(cast(list[str], case["safety_labels"]))
            if labels.isdisjoint(dangerous_labels):
                continue
            expected = cast(JsonObject, case["expected"])
            expected_policy = cast(JsonObject, expected["policy_decision"])
            with self.subTest(case=case["id"]):
                self.assertNotEqual(expected_policy["outcome"], "allow")
                self.assertFalse(
                    expected_policy["allowed"]
                    and not expected_policy["requires_confirmation"]
                )

    def test_dataset_contains_no_secret_or_private_user_patterns(self) -> None:
        dataset_text = DATASET_PATH.read_text(encoding="utf-8")

        for pattern in FORBIDDEN_TEXT_PATTERNS:
            with self.subTest(pattern=pattern.pattern):
                self.assertIsNone(pattern.search(dataset_text))


if __name__ == "__main__":
    unittest.main()
