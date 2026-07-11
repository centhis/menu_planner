from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast

from menu_planner.application.intent_router import RuleBasedIntentRouter
from menu_planner.domain.contracts.models import (
    SCHEMA_VERSION,
    JsonObject,
    ParsedIntent,
    PolicyDecision,
    PolicyDecisionOutcome,
    WorkflowRun,
    WorkflowState,
)
from menu_planner.domain.contracts.validation import validate_contract
from menu_planner.domain.policy import decide_policy
from menu_planner.domain.workflow import allowed_actions


class IntentParser(Protocol):
    name: str
    version: str

    def parse(self, user_text: str) -> JsonObject: ...


@dataclass(frozen=True)
class IntentRoutingResult:
    router_name: str
    router_version: str
    parsed_intent: ParsedIntent | None
    policy_decision: PolicyDecision | None
    errors: tuple[JsonObject, ...]
    next_action: str | None
    side_effects_executed: bool = False


def route_user_text_to_policy(
    *,
    user_text: str,
    workflow_state: WorkflowState,
    router: IntentParser | None = None,
) -> IntentRoutingResult:
    selected_router = router or RuleBasedIntentRouter()
    validation = validate_contract("parsed_intent", selected_router.parse(user_text))
    if not validation.is_valid or validation.value is None:
        return IntentRoutingResult(
            router_name=selected_router.name,
            router_version=selected_router.version,
            parsed_intent=None,
            policy_decision=None,
            errors=tuple(error.to_json() for error in validation.errors),
            next_action=None,
        )

    parsed_intent = cast(ParsedIntent, validation.value)
    policy_decision = decide_policy(parsed_intent, _workflow(workflow_state))
    return IntentRoutingResult(
        router_name=selected_router.name,
        router_version=selected_router.version,
        parsed_intent=parsed_intent,
        policy_decision=policy_decision,
        errors=(),
        next_action=_next_action(parsed_intent, policy_decision),
    )


def _workflow(state: WorkflowState) -> WorkflowRun:
    return WorkflowRun(
        schema_version=SCHEMA_VERSION,
        workflow_id=f"intent_routing_{state.value}",
        user_id="user_001",
        state=state,
        allowed_actions=[action.value for action in allowed_actions(state)],
        attempts=0,
    )


def _next_action(intent: ParsedIntent, policy: PolicyDecision) -> str:
    if policy.outcome is PolicyDecisionOutcome.ALLOW:
        return intent.suggested_next_action
    if policy.outcome is PolicyDecisionOutcome.CONFIRM:
        return "request_confirmation"
    if policy.outcome is PolicyDecisionOutcome.CLARIFY:
        return "request_clarification"
    if policy.outcome is PolicyDecisionOutcome.DENY:
        return "deny"
    return "unsupported"
