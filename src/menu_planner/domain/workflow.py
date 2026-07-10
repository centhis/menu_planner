from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from menu_planner.domain.contracts.models import (
    OperationClass,
    WorkflowRun,
    WorkflowState,
)
from menu_planner.domain.errors import (
    DomainError,
    action_not_allowed,
    administrative_action_denied,
    retry_limit_reached,
    unsupported_intent,
)

DEFAULT_RETRY_LIMIT = 3


class WorkflowAction(StrEnum):
    SHOW_STATUS = "show_status"
    SUBMIT_PROFILE_DRAFT = "submit_profile_draft"
    CONFIRM_PROFILE_DRAFT = "confirm_profile_draft"
    PREPARE_CONTEXT = "prepare_context"
    GENERATE_MENU_DRAFT = "generate_menu_draft"
    VALIDATE_MENU_DRAFT = "validate_menu_draft"
    REQUEST_MENU_REVISION = "request_menu_revision"
    CONFIRM_MENU_DRAFT = "confirm_menu_draft"
    GENERATE_RECIPE_DRAFTS = "generate_recipe_drafts"
    VALIDATE_RECIPE_DRAFTS = "validate_recipe_drafts"
    MATCH_PRODUCTS = "match_products"
    BUILD_SHOPPING_LIST = "build_shopping_list"
    MARK_READY = "mark_ready"
    CANCEL_WORKFLOW = "cancel_workflow"
    INSTALL_SKILL = "install_skill"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class StateRule:
    state: WorkflowState
    allowed_actions: tuple[WorkflowAction, ...]
    transitions: dict[WorkflowAction, WorkflowState]
    required_data: tuple[str, ...] = ()
    terminal: bool = False
    retry_limit: int = DEFAULT_RETRY_LIMIT


@dataclass(frozen=True)
class TransitionResult:
    allowed: bool
    current_state: WorkflowState
    action: WorkflowAction
    operation_class: OperationClass
    next_state: WorkflowState | None
    required_data: tuple[str, ...]
    terminal: bool
    retry_limit: int
    error: DomainError | None = None


ACTION_OPERATION_CLASSES: dict[WorkflowAction, OperationClass] = {
    WorkflowAction.SHOW_STATUS: OperationClass.READ_ONLY,
    WorkflowAction.SUBMIT_PROFILE_DRAFT: OperationClass.DRAFT_PRODUCING,
    WorkflowAction.CONFIRM_PROFILE_DRAFT: OperationClass.STATE_CHANGING,
    WorkflowAction.PREPARE_CONTEXT: OperationClass.DRAFT_PRODUCING,
    WorkflowAction.GENERATE_MENU_DRAFT: OperationClass.DRAFT_PRODUCING,
    WorkflowAction.VALIDATE_MENU_DRAFT: OperationClass.DRAFT_PRODUCING,
    WorkflowAction.REQUEST_MENU_REVISION: OperationClass.DRAFT_PRODUCING,
    WorkflowAction.CONFIRM_MENU_DRAFT: OperationClass.STATE_CHANGING,
    WorkflowAction.GENERATE_RECIPE_DRAFTS: OperationClass.DRAFT_PRODUCING,
    WorkflowAction.VALIDATE_RECIPE_DRAFTS: OperationClass.DRAFT_PRODUCING,
    WorkflowAction.MATCH_PRODUCTS: OperationClass.DRAFT_PRODUCING,
    WorkflowAction.BUILD_SHOPPING_LIST: OperationClass.DRAFT_PRODUCING,
    WorkflowAction.MARK_READY: OperationClass.STATE_CHANGING,
    WorkflowAction.CANCEL_WORKFLOW: OperationClass.STATE_CHANGING,
    WorkflowAction.INSTALL_SKILL: OperationClass.ADMINISTRATIVE,
    WorkflowAction.UNSUPPORTED: OperationClass.UNSUPPORTED,
}


STATE_RULES: dict[WorkflowState, StateRule] = {
    WorkflowState.PROFILE_REQUIRED: StateRule(
        state=WorkflowState.PROFILE_REQUIRED,
        allowed_actions=(
            WorkflowAction.SHOW_STATUS,
            WorkflowAction.SUBMIT_PROFILE_DRAFT,
            WorkflowAction.CANCEL_WORKFLOW,
        ),
        transitions={
            WorkflowAction.SHOW_STATUS: WorkflowState.PROFILE_REQUIRED,
            WorkflowAction.SUBMIT_PROFILE_DRAFT: (
                WorkflowState.PROFILE_WAITING_CONFIRMATION
            ),
            WorkflowAction.CANCEL_WORKFLOW: WorkflowState.CANCELLED,
        },
        required_data=("user_id",),
    ),
    WorkflowState.PROFILE_WAITING_CONFIRMATION: StateRule(
        state=WorkflowState.PROFILE_WAITING_CONFIRMATION,
        allowed_actions=(
            WorkflowAction.SHOW_STATUS,
            WorkflowAction.CONFIRM_PROFILE_DRAFT,
            WorkflowAction.CANCEL_WORKFLOW,
        ),
        transitions={
            WorkflowAction.SHOW_STATUS: WorkflowState.PROFILE_WAITING_CONFIRMATION,
            WorkflowAction.CONFIRM_PROFILE_DRAFT: WorkflowState.CONTEXT_PREPARING,
            WorkflowAction.CANCEL_WORKFLOW: WorkflowState.CANCELLED,
        },
        required_data=("profile_draft_id",),
    ),
    WorkflowState.CONTEXT_PREPARING: StateRule(
        state=WorkflowState.CONTEXT_PREPARING,
        allowed_actions=(
            WorkflowAction.SHOW_STATUS,
            WorkflowAction.PREPARE_CONTEXT,
            WorkflowAction.CANCEL_WORKFLOW,
        ),
        transitions={
            WorkflowAction.SHOW_STATUS: WorkflowState.CONTEXT_PREPARING,
            WorkflowAction.PREPARE_CONTEXT: WorkflowState.MENU_GENERATING,
            WorkflowAction.CANCEL_WORKFLOW: WorkflowState.CANCELLED,
        },
        required_data=("profile_version",),
    ),
    WorkflowState.MENU_GENERATING: StateRule(
        state=WorkflowState.MENU_GENERATING,
        allowed_actions=(
            WorkflowAction.SHOW_STATUS,
            WorkflowAction.GENERATE_MENU_DRAFT,
            WorkflowAction.CANCEL_WORKFLOW,
        ),
        transitions={
            WorkflowAction.SHOW_STATUS: WorkflowState.MENU_GENERATING,
            WorkflowAction.GENERATE_MENU_DRAFT: WorkflowState.MENU_VALIDATING,
            WorkflowAction.CANCEL_WORKFLOW: WorkflowState.CANCELLED,
        },
        required_data=("planning_context_id",),
    ),
    WorkflowState.MENU_VALIDATING: StateRule(
        state=WorkflowState.MENU_VALIDATING,
        allowed_actions=(
            WorkflowAction.SHOW_STATUS,
            WorkflowAction.VALIDATE_MENU_DRAFT,
            WorkflowAction.REQUEST_MENU_REVISION,
            WorkflowAction.CANCEL_WORKFLOW,
        ),
        transitions={
            WorkflowAction.SHOW_STATUS: WorkflowState.MENU_VALIDATING,
            WorkflowAction.VALIDATE_MENU_DRAFT: WorkflowState.MENU_WAITING_CONFIRMATION,
            WorkflowAction.REQUEST_MENU_REVISION: WorkflowState.MENU_REVISION_REQUIRED,
            WorkflowAction.CANCEL_WORKFLOW: WorkflowState.CANCELLED,
        },
        required_data=("menu_draft_id",),
    ),
    WorkflowState.MENU_REVISION_REQUIRED: StateRule(
        state=WorkflowState.MENU_REVISION_REQUIRED,
        allowed_actions=(
            WorkflowAction.SHOW_STATUS,
            WorkflowAction.REQUEST_MENU_REVISION,
            WorkflowAction.CANCEL_WORKFLOW,
        ),
        transitions={
            WorkflowAction.SHOW_STATUS: WorkflowState.MENU_REVISION_REQUIRED,
            WorkflowAction.REQUEST_MENU_REVISION: WorkflowState.MENU_GENERATING,
            WorkflowAction.CANCEL_WORKFLOW: WorkflowState.CANCELLED,
        },
        required_data=("menu_draft_id",),
    ),
    WorkflowState.MENU_WAITING_CONFIRMATION: StateRule(
        state=WorkflowState.MENU_WAITING_CONFIRMATION,
        allowed_actions=(
            WorkflowAction.SHOW_STATUS,
            WorkflowAction.CONFIRM_MENU_DRAFT,
            WorkflowAction.CANCEL_WORKFLOW,
        ),
        transitions={
            WorkflowAction.SHOW_STATUS: WorkflowState.MENU_WAITING_CONFIRMATION,
            WorkflowAction.CONFIRM_MENU_DRAFT: WorkflowState.RECIPES_GENERATING,
            WorkflowAction.CANCEL_WORKFLOW: WorkflowState.CANCELLED,
        },
        required_data=("menu_draft_id",),
    ),
    WorkflowState.RECIPES_GENERATING: StateRule(
        state=WorkflowState.RECIPES_GENERATING,
        allowed_actions=(
            WorkflowAction.SHOW_STATUS,
            WorkflowAction.GENERATE_RECIPE_DRAFTS,
            WorkflowAction.CANCEL_WORKFLOW,
        ),
        transitions={
            WorkflowAction.SHOW_STATUS: WorkflowState.RECIPES_GENERATING,
            WorkflowAction.GENERATE_RECIPE_DRAFTS: WorkflowState.RECIPES_VALIDATING,
            WorkflowAction.CANCEL_WORKFLOW: WorkflowState.CANCELLED,
        },
        required_data=("menu_version",),
    ),
    WorkflowState.RECIPES_VALIDATING: StateRule(
        state=WorkflowState.RECIPES_VALIDATING,
        allowed_actions=(
            WorkflowAction.SHOW_STATUS,
            WorkflowAction.VALIDATE_RECIPE_DRAFTS,
            WorkflowAction.CANCEL_WORKFLOW,
        ),
        transitions={
            WorkflowAction.SHOW_STATUS: WorkflowState.RECIPES_VALIDATING,
            WorkflowAction.VALIDATE_RECIPE_DRAFTS: WorkflowState.PRODUCTS_MATCHING,
            WorkflowAction.CANCEL_WORKFLOW: WorkflowState.CANCELLED,
        },
        required_data=("recipe_draft_ids",),
    ),
    WorkflowState.PRODUCTS_MATCHING: StateRule(
        state=WorkflowState.PRODUCTS_MATCHING,
        allowed_actions=(
            WorkflowAction.SHOW_STATUS,
            WorkflowAction.MATCH_PRODUCTS,
            WorkflowAction.CANCEL_WORKFLOW,
        ),
        transitions={
            WorkflowAction.SHOW_STATUS: WorkflowState.PRODUCTS_MATCHING,
            WorkflowAction.MATCH_PRODUCTS: WorkflowState.SHOPPING_LIST_BUILDING,
            WorkflowAction.CANCEL_WORKFLOW: WorkflowState.CANCELLED,
        },
        required_data=("recipe_version_ids",),
    ),
    WorkflowState.SHOPPING_LIST_BUILDING: StateRule(
        state=WorkflowState.SHOPPING_LIST_BUILDING,
        allowed_actions=(
            WorkflowAction.SHOW_STATUS,
            WorkflowAction.BUILD_SHOPPING_LIST,
            WorkflowAction.MARK_READY,
            WorkflowAction.CANCEL_WORKFLOW,
        ),
        transitions={
            WorkflowAction.SHOW_STATUS: WorkflowState.SHOPPING_LIST_BUILDING,
            WorkflowAction.BUILD_SHOPPING_LIST: WorkflowState.SHOPPING_LIST_BUILDING,
            WorkflowAction.MARK_READY: WorkflowState.READY,
            WorkflowAction.CANCEL_WORKFLOW: WorkflowState.CANCELLED,
        },
        required_data=("menu_version", "recipe_version_ids"),
    ),
    WorkflowState.READY: StateRule(
        state=WorkflowState.READY,
        allowed_actions=(WorkflowAction.SHOW_STATUS,),
        transitions={WorkflowAction.SHOW_STATUS: WorkflowState.READY},
        terminal=True,
    ),
    WorkflowState.FAILED: StateRule(
        state=WorkflowState.FAILED,
        allowed_actions=(WorkflowAction.SHOW_STATUS,),
        transitions={WorkflowAction.SHOW_STATUS: WorkflowState.FAILED},
        terminal=True,
    ),
    WorkflowState.CANCELLED: StateRule(
        state=WorkflowState.CANCELLED,
        allowed_actions=(WorkflowAction.SHOW_STATUS,),
        transitions={WorkflowAction.SHOW_STATUS: WorkflowState.CANCELLED},
        terminal=True,
    ),
}


def allowed_actions(state: WorkflowState) -> tuple[WorkflowAction, ...]:
    return STATE_RULES[state].allowed_actions


def is_terminal_state(state: WorkflowState) -> bool:
    return STATE_RULES[state].terminal


def evaluate_transition(
    workflow: WorkflowRun,
    action: WorkflowAction,
) -> TransitionResult:
    rule = STATE_RULES[workflow.state]
    operation_class = ACTION_OPERATION_CLASSES[action]

    if operation_class is OperationClass.ADMINISTRATIVE:
        return _denied_result(
            workflow=workflow,
            action=action,
            rule=rule,
            error=administrative_action_denied(action.value, "user_workflow"),
        )

    if operation_class is OperationClass.UNSUPPORTED:
        return _denied_result(
            workflow=workflow,
            action=action,
            rule=rule,
            error=unsupported_intent(action.value),
        )

    if action not in rule.allowed_actions:
        return _denied_result(
            workflow=workflow,
            action=action,
            rule=rule,
            error=action_not_allowed(
                workflow.state.value,
                action.value,
                [allowed.value for allowed in rule.allowed_actions],
            ),
        )

    if _retry_limit_reached(workflow, rule, action):
        return _denied_result(
            workflow=workflow,
            action=action,
            rule=rule,
            error=retry_limit_reached(
                workflow.workflow_id,
                workflow.state.value,
                workflow.attempts,
                rule.retry_limit,
            ),
        )

    return TransitionResult(
        allowed=True,
        current_state=workflow.state,
        action=action,
        operation_class=operation_class,
        next_state=rule.transitions[action],
        required_data=rule.required_data,
        terminal=rule.terminal,
        retry_limit=rule.retry_limit,
        error=None,
    )


def _retry_limit_reached(
    workflow: WorkflowRun,
    rule: StateRule,
    action: WorkflowAction,
) -> bool:
    return (
        action is not WorkflowAction.SHOW_STATUS
        and action is not WorkflowAction.CANCEL_WORKFLOW
        and not rule.terminal
        and workflow.attempts >= rule.retry_limit
    )


def _denied_result(
    workflow: WorkflowRun,
    action: WorkflowAction,
    rule: StateRule,
    error: DomainError,
) -> TransitionResult:
    return TransitionResult(
        allowed=False,
        current_state=workflow.state,
        action=action,
        operation_class=ACTION_OPERATION_CLASSES[action],
        next_state=None,
        required_data=rule.required_data,
        terminal=rule.terminal,
        retry_limit=rule.retry_limit,
        error=error,
    )
