from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any, cast

from menu_planner.domain.contracts.models import (
    SCHEMA_VERSION,
    JsonObject,
    OperationClass,
    ParsedIntent,
    PolicyDecisionOutcome,
    WorkflowRun,
    WorkflowState,
)
from menu_planner.domain.policy import decide_policy
from menu_planner.domain.workflow import WorkflowAction, allowed_actions

TAXONOMY_PATH = Path("fixtures/evals/intent_router/taxonomy.v1.json")


def _load_taxonomy() -> JsonObject:
    return cast(JsonObject, json.loads(TAXONOMY_PATH.read_text(encoding="utf-8")))


def _workflow(state: WorkflowState) -> WorkflowRun:
    return WorkflowRun(
        schema_version=SCHEMA_VERSION,
        workflow_id=f"workflow_{state.value}",
        user_id="user_001",
        state=state,
        allowed_actions=[action.value for action in allowed_actions(state)],
        attempts=0,
    )


def _intent(intent_spec: JsonObject) -> ParsedIntent:
    return ParsedIntent(
        schema_version=SCHEMA_VERSION,
        intent=cast(str, intent_spec["workflow_action"]),
        confidence=1.0,
        parameters={},
        missing_fields=[],
        ambiguities=[],
        operation_class=OperationClass(cast(str, intent_spec["operation_class"])),
        requires_confirmation=cast(bool, intent_spec["requires_confirmation"]),
        scope=cast(str, intent_spec["scope"]),
        suggested_next_action=cast(str, intent_spec["workflow_action"]),
    )


class M5IntentTaxonomyTests(unittest.TestCase):
    def test_taxonomy_version_and_intents_are_reviewable(self) -> None:
        taxonomy = _load_taxonomy()

        self.assertEqual(taxonomy["schema_version"], "m5.intent_taxonomy.v1")
        self.assertEqual(taxonomy["taxonomy_version"], "m5.intent_taxonomy.v1")
        intents = cast(list[JsonObject], taxonomy["intents"])
        self.assertEqual(
            [intent["name"] for intent in intents],
            [
                "show_status",
                "submit_profile_draft",
                "confirm_profile_draft",
                "cancel_workflow",
                "install_skill",
                "unsupported",
            ],
        )

    def test_taxonomy_intents_map_to_current_workflow_actions(self) -> None:
        taxonomy = _load_taxonomy()
        intents = cast(list[JsonObject], taxonomy["intents"])

        for intent in intents:
            with self.subTest(intent=intent["name"]):
                action = WorkflowAction(cast(str, intent["workflow_action"]))
                operation_class = OperationClass(cast(str, intent["operation_class"]))
                self.assertEqual(action.value, intent["name"])
                self.assertEqual(operation_class.value, intent["operation_class"])
                self.assertIsInstance(intent["required_parameters"], list)
                self.assertIsInstance(intent["missing_field_policy"], str)
                self.assertIsInstance(intent["ambiguity_policy"], str)
                self.assertIsInstance(intent["scope"], str)
                self.assertIsInstance(intent["requires_confirmation"], bool)

    def test_representative_policy_outputs_match_existing_policy(self) -> None:
        taxonomy = _load_taxonomy()
        intents = cast(list[JsonObject], taxonomy["intents"])

        for intent in intents:
            cases = cast(list[JsonObject], intent["representative_policy_cases"])
            for case in cases:
                with self.subTest(intent=intent["name"], state=case["workflow_state"]):
                    decision = decide_policy(
                        _intent(intent),
                        _workflow(WorkflowState(cast(str, case["workflow_state"]))),
                    )

                    self.assertEqual(
                        decision.outcome,
                        PolicyDecisionOutcome(cast(str, case["expected_outcome"])),
                    )
                    self.assertEqual(decision.allowed, case["expected_allowed"])
                    self.assertEqual(
                        decision.reason_code,
                        case["expected_reason_code"],
                    )

    def test_unknown_and_future_intents_are_not_supported_by_m5_taxonomy(self) -> None:
        taxonomy = _load_taxonomy()
        intents = cast(list[JsonObject], taxonomy["intents"])
        supported_intent_names = {
            cast(str, intent["name"])
            for intent in intents
            if cast(bool, intent["supported"])
        }
        deferred_intent_names = cast(list[Any], taxonomy["deferred_intent_names"])

        self.assertNotIn("unsupported", supported_intent_names)
        self.assertNotIn("install_skill", supported_intent_names)
        for intent_name in deferred_intent_names:
            with self.subTest(intent=intent_name):
                self.assertNotIn(intent_name, supported_intent_names)

    def test_administrative_taxonomy_uses_existing_denial_path(self) -> None:
        taxonomy = _load_taxonomy()
        intents = cast(list[JsonObject], taxonomy["intents"])
        admin_intent = next(
            intent for intent in intents if intent["name"] == "install_skill"
        )

        decision = decide_policy(
            _intent(admin_intent),
            _workflow(WorkflowState.READY),
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.outcome, PolicyDecisionOutcome.DENY)
        self.assertEqual(
            decision.errors[0]["code"],
            "policy.administrative_action_denied",
        )


if __name__ == "__main__":
    unittest.main()
