from __future__ import annotations

import unittest

from menu_planner.domain.contracts.models import (
    SCHEMA_VERSION,
    OperationClass,
    WorkflowRun,
    WorkflowState,
)
from menu_planner.domain.errors import ErrorCode
from menu_planner.domain.workflow import (
    ACTION_OPERATION_CLASSES,
    STATE_RULES,
    WorkflowAction,
    allowed_actions,
    evaluate_transition,
    is_terminal_state,
)


def _workflow(state: WorkflowState, attempts: int = 0) -> WorkflowRun:
    return WorkflowRun(
        schema_version=SCHEMA_VERSION,
        workflow_id="workflow_001",
        user_id="user_001",
        state=state,
        allowed_actions=[action.value for action in allowed_actions(state)],
        attempts=attempts,
    )


class WorkflowStateMachineTests(unittest.TestCase):
    def test_state_table_covers_all_contract_states(self) -> None:
        self.assertEqual(set(STATE_RULES), set(WorkflowState))

    def test_every_allowed_action_has_operation_class_and_transition(self) -> None:
        for state, rule in STATE_RULES.items():
            with self.subTest(state=state.value):
                for action in rule.allowed_actions:
                    self.assertIn(action, ACTION_OPERATION_CLASSES)
                    self.assertIn(action, rule.transitions)

    def test_happy_path_reaches_ready_without_business_commit(self) -> None:
        path = [
            (WorkflowState.PROFILE_REQUIRED, WorkflowAction.SUBMIT_PROFILE_DRAFT),
            (
                WorkflowState.PROFILE_WAITING_CONFIRMATION,
                WorkflowAction.CONFIRM_PROFILE_DRAFT,
            ),
            (WorkflowState.CONTEXT_PREPARING, WorkflowAction.PREPARE_CONTEXT),
            (WorkflowState.MENU_GENERATING, WorkflowAction.GENERATE_MENU_DRAFT),
            (WorkflowState.MENU_VALIDATING, WorkflowAction.VALIDATE_MENU_DRAFT),
            (
                WorkflowState.MENU_WAITING_CONFIRMATION,
                WorkflowAction.CONFIRM_MENU_DRAFT,
            ),
            (WorkflowState.RECIPES_GENERATING, WorkflowAction.GENERATE_RECIPE_DRAFTS),
            (WorkflowState.RECIPES_VALIDATING, WorkflowAction.VALIDATE_RECIPE_DRAFTS),
            (WorkflowState.PRODUCTS_MATCHING, WorkflowAction.MATCH_PRODUCTS),
            (
                WorkflowState.SHOPPING_LIST_BUILDING,
                WorkflowAction.BUILD_SHOPPING_LIST,
            ),
            (WorkflowState.SHOPPING_LIST_BUILDING, WorkflowAction.MARK_READY),
        ]

        for state, action in path:
            with self.subTest(state=state.value, action=action.value):
                result = evaluate_transition(_workflow(state), action)

                self.assertTrue(result.allowed)
                self.assertIsNone(result.error)
                self.assertIn(result.operation_class, set(OperationClass))

        final_result = evaluate_transition(
            _workflow(WorkflowState.SHOPPING_LIST_BUILDING),
            WorkflowAction.MARK_READY,
        )
        self.assertEqual(final_result.next_state, WorkflowState.READY)

    def test_negative_matrix_blocks_actions_not_allowed_in_current_state(self) -> None:
        matrix = [
            (WorkflowState.PROFILE_REQUIRED, WorkflowAction.GENERATE_MENU_DRAFT),
            (WorkflowState.MENU_GENERATING, WorkflowAction.CONFIRM_MENU_DRAFT),
            (WorkflowState.RECIPES_GENERATING, WorkflowAction.MATCH_PRODUCTS),
            (WorkflowState.READY, WorkflowAction.MARK_READY),
        ]

        for state, action in matrix:
            with self.subTest(state=state.value, action=action.value):
                result = evaluate_transition(_workflow(state), action)

                self.assertFalse(result.allowed)
                self.assertIsNotNone(result.error)
                assert result.error is not None
                self.assertEqual(result.error.code, ErrorCode.ACTION_NOT_ALLOWED)
                self.assertEqual(result.next_state, None)

    def test_administrative_action_is_denied_from_user_workflow(self) -> None:
        result = evaluate_transition(
            _workflow(WorkflowState.READY),
            WorkflowAction.INSTALL_SKILL,
        )

        self.assertFalse(result.allowed)
        self.assertEqual(result.operation_class, OperationClass.ADMINISTRATIVE)
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(result.error.code, ErrorCode.ADMINISTRATIVE_ACTION_DENIED)

    def test_unsupported_action_is_denied_with_machine_error(self) -> None:
        result = evaluate_transition(
            _workflow(WorkflowState.PROFILE_REQUIRED),
            WorkflowAction.UNSUPPORTED,
        )

        self.assertFalse(result.allowed)
        self.assertEqual(result.operation_class, OperationClass.UNSUPPORTED)
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(result.error.code, ErrorCode.UNSUPPORTED_INTENT)

    def test_retry_limit_denies_non_terminal_looping_action(self) -> None:
        result = evaluate_transition(
            _workflow(WorkflowState.MENU_GENERATING, attempts=3),
            WorkflowAction.GENERATE_MENU_DRAFT,
        )

        self.assertFalse(result.allowed)
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(result.error.code, ErrorCode.RETRY_LIMIT_REACHED)

    def test_retry_limit_still_allows_status_and_cancel_escape(self) -> None:
        status_result = evaluate_transition(
            _workflow(WorkflowState.MENU_GENERATING, attempts=3),
            WorkflowAction.SHOW_STATUS,
        )
        cancel_result = evaluate_transition(
            _workflow(WorkflowState.MENU_GENERATING, attempts=3),
            WorkflowAction.CANCEL_WORKFLOW,
        )

        self.assertTrue(status_result.allowed)
        self.assertEqual(status_result.next_state, WorkflowState.MENU_GENERATING)
        self.assertTrue(cancel_result.allowed)
        self.assertEqual(cancel_result.next_state, WorkflowState.CANCELLED)

    def test_terminal_states_only_allow_read_only_status(self) -> None:
        for state in [
            WorkflowState.READY,
            WorkflowState.FAILED,
            WorkflowState.CANCELLED,
        ]:
            with self.subTest(state=state.value):
                self.assertTrue(is_terminal_state(state))
                self.assertEqual(allowed_actions(state), (WorkflowAction.SHOW_STATUS,))


if __name__ == "__main__":
    unittest.main()
