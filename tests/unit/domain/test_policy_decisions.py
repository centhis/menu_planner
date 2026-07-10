from __future__ import annotations

import unittest

from menu_planner.domain.contracts.models import (
    SCHEMA_VERSION,
    OperationClass,
    ParsedIntent,
    PolicyDecisionOutcome,
    WorkflowRun,
    WorkflowState,
)
from menu_planner.domain.errors import ErrorCode
from menu_planner.domain.policy import (
    ALLOW_REASON_CODE,
    CONFIRM_REASON_CODE,
    decide_policy,
)
from menu_planner.domain.workflow import WorkflowAction, allowed_actions


def _workflow(state: WorkflowState, attempts: int = 0) -> WorkflowRun:
    return WorkflowRun(
        schema_version=SCHEMA_VERSION,
        workflow_id="workflow_001",
        user_id="user_001",
        state=state,
        allowed_actions=[action.value for action in allowed_actions(state)],
        attempts=attempts,
    )


def _intent(
    intent: WorkflowAction | str,
    operation_class: OperationClass = OperationClass.READ_ONLY,
    missing_fields: list[str] | None = None,
    ambiguities: list[str] | None = None,
) -> ParsedIntent:
    intent_value = intent.value if isinstance(intent, WorkflowAction) else intent
    return ParsedIntent(
        schema_version=SCHEMA_VERSION,
        intent=intent_value,
        confidence=1.0,
        parameters={},
        missing_fields=missing_fields or [],
        ambiguities=ambiguities or [],
        operation_class=operation_class,
        requires_confirmation=False,
        scope="current_workflow",
        suggested_next_action=intent_value,
    )


class PolicyDecisionTests(unittest.TestCase):
    def test_read_only_intent_is_allowed(self) -> None:
        decision = decide_policy(
            _intent(WorkflowAction.SHOW_STATUS, OperationClass.READ_ONLY),
            _workflow(WorkflowState.PROFILE_REQUIRED),
        )

        self.assertEqual(decision.outcome, PolicyDecisionOutcome.ALLOW)
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.operation_class, OperationClass.READ_ONLY)
        self.assertEqual(decision.reason_code, ALLOW_REASON_CODE)
        self.assertEqual(decision.current_state, "profile_required")
        self.assertFalse(decision.requires_confirmation)
        self.assertEqual(decision.errors, [])

    def test_draft_producing_intent_is_allowed(self) -> None:
        decision = decide_policy(
            _intent(WorkflowAction.GENERATE_MENU_DRAFT, OperationClass.DRAFT_PRODUCING),
            _workflow(WorkflowState.MENU_GENERATING),
        )

        self.assertEqual(decision.outcome, PolicyDecisionOutcome.ALLOW)
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.operation_class, OperationClass.DRAFT_PRODUCING)
        self.assertEqual(decision.required_data, ["planning_context_id"])

    def test_state_changing_intent_requires_confirmation_without_state_mutation(
        self,
    ) -> None:
        workflow = _workflow(WorkflowState.MENU_WAITING_CONFIRMATION)

        decision = decide_policy(
            _intent(WorkflowAction.CONFIRM_MENU_DRAFT, OperationClass.STATE_CHANGING),
            workflow,
        )

        self.assertEqual(decision.outcome, PolicyDecisionOutcome.CONFIRM)
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.operation_class, OperationClass.STATE_CHANGING)
        self.assertEqual(decision.reason_code, CONFIRM_REASON_CODE)
        self.assertTrue(decision.requires_confirmation)
        self.assertEqual(decision.current_state, workflow.state.value)
        self.assertEqual(workflow.state, WorkflowState.MENU_WAITING_CONFIRMATION)

    def test_forbidden_action_returns_denied_decision_with_allowed_actions(
        self,
    ) -> None:
        decision = decide_policy(
            _intent(WorkflowAction.CONFIRM_MENU_DRAFT, OperationClass.STATE_CHANGING),
            _workflow(WorkflowState.PROFILE_REQUIRED),
        )

        self.assertEqual(decision.outcome, PolicyDecisionOutcome.DENY)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason_code, ErrorCode.ACTION_NOT_ALLOWED.value)
        self.assertIn("submit_profile_draft", decision.allowed_actions)
        self.assertEqual(decision.errors[0]["code"], ErrorCode.ACTION_NOT_ALLOWED.value)

    def test_ambiguous_or_incomplete_input_returns_clarification_decision(self) -> None:
        decision = decide_policy(
            _intent(
                WorkflowAction.GENERATE_MENU_DRAFT,
                OperationClass.DRAFT_PRODUCING,
                missing_fields=["planning_context_id"],
                ambiguities=["meal_count"],
            ),
            _workflow(WorkflowState.MENU_GENERATING),
        )

        self.assertEqual(decision.outcome, PolicyDecisionOutcome.CLARIFY)
        self.assertFalse(decision.allowed)
        self.assertEqual(
            decision.reason_code,
            ErrorCode.AMBIGUOUS_OR_INCOMPLETE_INTENT.value,
        )
        self.assertEqual(decision.missing_fields, ["planning_context_id"])
        self.assertEqual(decision.ambiguities, ["meal_count"])

    def test_unsupported_intent_does_not_pass_as_read_only(self) -> None:
        decision = decide_policy(
            _intent("order_delivery", OperationClass.READ_ONLY),
            _workflow(WorkflowState.READY),
        )

        self.assertEqual(decision.outcome, PolicyDecisionOutcome.UNSUPPORTED)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.operation_class, OperationClass.UNSUPPORTED)
        self.assertEqual(decision.reason_code, ErrorCode.UNSUPPORTED_INTENT.value)

    def test_administrative_intent_is_denied_from_user_workflow(self) -> None:
        decision = decide_policy(
            _intent(WorkflowAction.INSTALL_SKILL, OperationClass.ADMINISTRATIVE),
            _workflow(WorkflowState.READY),
        )

        self.assertEqual(decision.outcome, PolicyDecisionOutcome.DENY)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.operation_class, OperationClass.ADMINISTRATIVE)
        self.assertEqual(
            decision.reason_code,
            ErrorCode.ADMINISTRATIVE_ACTION_DENIED.value,
        )


if __name__ == "__main__":
    unittest.main()
