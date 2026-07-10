from __future__ import annotations

from menu_planner.domain.contracts.models import (
    SCHEMA_VERSION,
    JsonObject,
    OperationClass,
    ParsedIntent,
    PolicyDecision,
    PolicyDecisionOutcome,
    WorkflowRun,
)
from menu_planner.domain.errors import (
    DomainError,
    ErrorCode,
    ambiguous_or_incomplete_intent,
    unsupported_intent,
)
from menu_planner.domain.workflow import (
    ACTION_OPERATION_CLASSES,
    WorkflowAction,
    allowed_actions,
    evaluate_transition,
)

ALLOW_REASON_CODE = "policy.allowed"
CONFIRM_REASON_CODE = "policy.requires_confirmation"


def decide_policy(intent: ParsedIntent, workflow: WorkflowRun) -> PolicyDecision:
    action = _action_from_intent(intent.intent)
    current_allowed_actions = [
        action.value for action in allowed_actions(workflow.state)
    ]

    if action is None:
        error = unsupported_intent(intent.intent)
        return _decision(
            outcome=PolicyDecisionOutcome.UNSUPPORTED,
            allowed=False,
            operation_class=OperationClass.UNSUPPORTED,
            reason_code=error.code.value,
            workflow=workflow,
            allowed_action_values=current_allowed_actions,
            required_data=[],
            missing_fields=intent.missing_fields,
            ambiguities=intent.ambiguities,
            requires_confirmation=False,
            errors=[error],
        )

    operation_class = ACTION_OPERATION_CLASSES[action]

    if intent.missing_fields or intent.ambiguities:
        error = ambiguous_or_incomplete_intent(
            intent.intent,
            intent.missing_fields,
            intent.ambiguities,
        )
        return _decision(
            outcome=PolicyDecisionOutcome.CLARIFY,
            allowed=False,
            operation_class=operation_class,
            reason_code=error.code.value,
            workflow=workflow,
            allowed_action_values=current_allowed_actions,
            required_data=[],
            missing_fields=intent.missing_fields,
            ambiguities=intent.ambiguities,
            requires_confirmation=False,
            errors=[error],
        )

    transition = evaluate_transition(workflow, action)
    if not transition.allowed:
        transition_error = transition.error
        error = (
            transition_error
            if transition_error is not None
            else unsupported_intent(intent.intent)
        )
        outcome = (
            PolicyDecisionOutcome.UNSUPPORTED
            if error.code is ErrorCode.UNSUPPORTED_INTENT
            else PolicyDecisionOutcome.DENY
        )
        return _decision(
            outcome=outcome,
            allowed=False,
            operation_class=transition.operation_class,
            reason_code=error.code.value,
            workflow=workflow,
            allowed_action_values=current_allowed_actions,
            required_data=list(transition.required_data),
            missing_fields=[],
            ambiguities=[],
            requires_confirmation=False,
            errors=[error],
        )

    if transition.operation_class is OperationClass.STATE_CHANGING:
        return _decision(
            outcome=PolicyDecisionOutcome.CONFIRM,
            allowed=True,
            operation_class=transition.operation_class,
            reason_code=CONFIRM_REASON_CODE,
            workflow=workflow,
            allowed_action_values=current_allowed_actions,
            required_data=list(transition.required_data),
            missing_fields=[],
            ambiguities=[],
            requires_confirmation=True,
            errors=[],
        )

    return _decision(
        outcome=PolicyDecisionOutcome.ALLOW,
        allowed=True,
        operation_class=transition.operation_class,
        reason_code=ALLOW_REASON_CODE,
        workflow=workflow,
        allowed_action_values=current_allowed_actions,
        required_data=list(transition.required_data),
        missing_fields=[],
        ambiguities=[],
        requires_confirmation=False,
        errors=[],
    )


def _action_from_intent(intent: str) -> WorkflowAction | None:
    try:
        return WorkflowAction(intent)
    except ValueError:
        return None


def _decision(
    outcome: PolicyDecisionOutcome,
    allowed: bool,
    operation_class: OperationClass,
    reason_code: str,
    workflow: WorkflowRun,
    allowed_action_values: list[str],
    required_data: list[str],
    missing_fields: list[str],
    ambiguities: list[str],
    requires_confirmation: bool,
    errors: list[DomainError],
) -> PolicyDecision:
    return PolicyDecision(
        schema_version=SCHEMA_VERSION,
        outcome=outcome,
        allowed=allowed,
        operation_class=operation_class,
        reason_code=reason_code,
        current_state=workflow.state.value,
        allowed_actions=allowed_action_values,
        required_data=required_data,
        missing_fields=missing_fields,
        ambiguities=ambiguities,
        requires_confirmation=requires_confirmation,
        errors=[_error_json(error) for error in errors],
    )


def _error_json(error: DomainError) -> JsonObject:
    return error.to_json()
