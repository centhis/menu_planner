from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Protocol, cast

from menu_planner.application.intent_router import RuleBasedIntentRouter
from menu_planner.domain.contracts.models import (
    SCHEMA_VERSION,
    JsonObject,
    JsonValue,
    ParsedIntent,
    PolicyDecision,
    PolicyDecisionOutcome,
    WorkflowRun,
    WorkflowState,
)
from menu_planner.domain.contracts.validation import validate_contract
from menu_planner.domain.policy import decide_policy
from menu_planner.domain.workflow import allowed_actions


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    split: str
    user_text: str
    workflow_state: WorkflowState
    safety_labels: tuple[str, ...]
    expected_parsed_intent: JsonObject
    expected_policy_decision: JsonObject


@dataclass(frozen=True)
class RouterCandidateResult:
    parsed_intent_payload: JsonObject | None
    error: JsonObject | None = None


class RouterCandidate(Protocol):
    name: str
    version: str

    def route(self, case: EvalCase) -> RouterCandidateResult: ...


class FixtureExpectedRouterCandidate:
    name = "fixture_expected"
    version = "m5.eval_skeleton.v1"

    def route(self, case: EvalCase) -> RouterCandidateResult:
        return RouterCandidateResult(parsed_intent_payload=case.expected_parsed_intent)


class RuleBasedBaselineRouterCandidate:
    def __init__(self) -> None:
        self._router = RuleBasedIntentRouter()
        self.name = self._router.name
        self.version = self._router.version

    def route(self, case: EvalCase) -> RouterCandidateResult:
        return RouterCandidateResult(
            parsed_intent_payload=self._router.parse(case.user_text),
        )


def load_eval_dataset(path: Path) -> JsonObject:
    return cast(JsonObject, json.loads(path.read_text(encoding="utf-8")))


def load_eval_cases(path: Path, *, split: str | None = None) -> list[EvalCase]:
    dataset = load_eval_dataset(path)
    cases = []
    for raw_case in cast(list[JsonObject], dataset["cases"]):
        case_split = cast(str, raw_case["split"])
        if split is not None and case_split != split:
            continue
        expected = cast(JsonObject, raw_case["expected"])
        cases.append(
            EvalCase(
                case_id=cast(str, raw_case["id"]),
                split=case_split,
                user_text=cast(str, raw_case["user_text"]),
                workflow_state=WorkflowState(cast(str, raw_case["workflow_state"])),
                safety_labels=tuple(cast(list[str], raw_case["safety_labels"])),
                expected_parsed_intent=cast(JsonObject, expected["parsed_intent"]),
                expected_policy_decision=cast(
                    JsonObject,
                    expected["policy_decision"],
                ),
            )
        )
    return cases


def run_intent_router_eval(
    *,
    dataset_path: Path,
    candidate: RouterCandidate,
    split: str | None = None,
) -> JsonObject:
    dataset = load_eval_dataset(dataset_path)
    cases = load_eval_cases(dataset_path, split=split)
    started = perf_counter()
    evaluated = [_evaluate_case(case, candidate) for case in cases]
    elapsed_ms = (perf_counter() - started) * 1000

    metrics = _metrics(evaluated)
    failures = [
        result
        for result in evaluated
        if cast(list[JsonObject], result["failures"])
    ]
    return {
        "schema_version": "m5.intent_eval_report.v1",
        "dataset_version": dataset["dataset_version"],
        "taxonomy_version": dataset["taxonomy_version"],
        "split": split or "all",
        "router_candidate": {
            "name": candidate.name,
            "version": candidate.version,
        },
        "model_backed_experiment": {
            "status": "skipped",
            "reason": (
                "ADR-0007 defers model-backed routing until provider/model "
                "choice, credentials handling, prompt/schema versioning, "
                "raw-output policy, and eval logging are explicitly approved."
            ),
            "provider": None,
            "model": None,
            "prompt_schema_version": None,
        },
        "case_count": len(cases),
        "metrics": {
            **metrics,
            "latency_ms_total": round(elapsed_ms, 3),
            "latency_ms_per_case_avg": _safe_round(
                elapsed_ms / len(cases) if cases else 0.0
            ),
            "cost": None,
        },
        "failures": cast(JsonValue, failures),
    }


def _evaluate_case(case: EvalCase, candidate: RouterCandidate) -> JsonObject:
    started = perf_counter()
    candidate_result = candidate.route(case)
    validation = validate_contract(
        "parsed_intent",
        candidate_result.parsed_intent_payload,
    )
    latency_ms = (perf_counter() - started) * 1000
    failures: list[JsonObject] = []
    actual_policy: PolicyDecision | None = None
    actual_intent: ParsedIntent | None = None

    if not validation.is_valid or validation.value is None:
        failures.append(
            {
                "field": "parsed_intent",
                "expected": "schema_valid",
                "actual": "invalid",
                "errors": cast(
                    JsonValue,
                    [error.to_json() for error in validation.errors],
                ),
            }
        )
    else:
        actual_intent = cast(ParsedIntent, validation.value)
        actual_policy = decide_policy(actual_intent, _workflow(case.workflow_state))
        failures.extend(_parsed_intent_failures(case, actual_intent))
        failures.extend(_policy_failures(case, actual_policy))

    return {
        "case_id": case.case_id,
        "split": case.split,
        "safety_labels": cast(JsonValue, list(case.safety_labels)),
        "schema_valid": validation.is_valid,
        "actual_intent": actual_intent.intent if actual_intent is not None else None,
        "actual_operation_class": (
            actual_intent.operation_class.value if actual_intent is not None else None
        ),
        "actual_policy_outcome": (
            actual_policy.outcome.value if actual_policy is not None else None
        ),
        "actual_policy_allowed": (
            actual_policy.allowed if actual_policy is not None else None
        ),
        "actual_requires_confirmation": (
            actual_policy.requires_confirmation if actual_policy is not None else None
        ),
        "expected_ambiguities_present": bool(
            case.expected_parsed_intent["ambiguities"]
        ),
        "expected_missing_fields_present": bool(
            case.expected_parsed_intent["missing_fields"]
        ),
        "latency_ms": round(latency_ms, 3),
        "failures": cast(JsonValue, failures),
    }


def _workflow(state: WorkflowState) -> WorkflowRun:
    return WorkflowRun(
        schema_version=SCHEMA_VERSION,
        workflow_id=f"eval_{state.value}",
        user_id="user_001",
        state=state,
        allowed_actions=[action.value for action in allowed_actions(state)],
        attempts=0,
    )


def _parsed_intent_failures(case: EvalCase, actual: ParsedIntent) -> list[JsonObject]:
    failures: list[JsonObject] = []
    expected = case.expected_parsed_intent
    comparisons: tuple[tuple[str, JsonValue, JsonValue], ...] = (
        ("intent", expected["intent"], actual.intent),
        ("operation_class", expected["operation_class"], actual.operation_class.value),
        ("parameters", expected["parameters"], cast(JsonValue, actual.parameters)),
        (
            "missing_fields",
            expected["missing_fields"],
            cast(JsonValue, actual.missing_fields),
        ),
        ("ambiguities", expected["ambiguities"], cast(JsonValue, actual.ambiguities)),
        ("scope", expected["scope"], actual.scope),
        (
            "requires_confirmation",
            expected["requires_confirmation"],
            actual.requires_confirmation,
        ),
    )
    for field, expected_value, actual_value in comparisons:
        if expected_value != actual_value:
            failures.append(
                {
                    "field": f"parsed_intent.{field}",
                    "expected": expected_value,
                    "actual": actual_value,
                }
            )
    return failures


def _policy_failures(case: EvalCase, actual: PolicyDecision) -> list[JsonObject]:
    failures: list[JsonObject] = []
    expected = case.expected_policy_decision
    comparisons: tuple[tuple[str, JsonValue, JsonValue], ...] = (
        ("outcome", expected["outcome"], actual.outcome.value),
        ("allowed", expected["allowed"], actual.allowed),
        ("reason_code", expected["reason_code"], actual.reason_code),
        (
            "requires_confirmation",
            expected["requires_confirmation"],
            actual.requires_confirmation,
        ),
    )
    for field, expected_value, actual_value in comparisons:
        if expected_value != actual_value:
            failures.append(
                {
                    "field": f"policy_decision.{field}",
                    "expected": expected_value,
                    "actual": actual_value,
                }
            )
    return failures


def _metrics(results: list[JsonObject]) -> JsonObject:
    count = len(results)
    schema_valid = _count(results, lambda result: cast(bool, result["schema_valid"]))
    exact_intent = _count(
        results,
        lambda result: _is_schema_valid(result)
        and _has_no_failure_with_prefix(result, "parsed_intent.intent"),
    )
    operation_class = _count(
        results,
        lambda result: _is_schema_valid(result)
        and _has_no_failure_with_prefix(
            result,
            "parsed_intent.operation_class",
        ),
    )
    parameters = _count(
        results,
        lambda result: _is_schema_valid(result)
        and _has_no_failure_with_prefix(result, "parsed_intent.parameters"),
    )
    policy_outcome = _count(
        results,
        lambda result: not any(
            cast(str, failure["field"]).startswith("policy_decision.")
            for failure in cast(list[JsonObject], result["failures"])
        ),
    )
    dangerous_results = [
        result for result in results if _has_any_label(result, "dangerous_")
    ]
    dangerous_false_automatic = _count(
        dangerous_results,
        lambda result: (
            result["actual_policy_allowed"] is True
            and result["actual_requires_confirmation"] is False
            and result["actual_policy_outcome"]
            == PolicyDecisionOutcome.ALLOW.value
        ),
    )
    administrative_results = [
        result for result in results if _has_label(result, "administrative")
    ]
    administrative_denied = _count(
        administrative_results,
        lambda result: result["actual_policy_outcome"]
        == PolicyDecisionOutcome.DENY.value,
    )
    unsupported_results = [
        result for result in results if _has_label(result, "unsupported")
    ]
    unsupported_handled = _count(
        unsupported_results,
        lambda result: (
            result["actual_policy_outcome"] == PolicyDecisionOutcome.UNSUPPORTED.value
        ),
    )

    return {
        "schema_valid_rate": _rate(schema_valid, count),
        "exact_intent_accuracy": _rate(exact_intent, count),
        "operation_class_accuracy": _rate(operation_class, count),
        "parameter_extraction_accuracy": _rate(parameters, count),
        "ambiguity_recall": _recall(results, "parsed_intent.ambiguities"),
        "missing_field_recall": _recall(results, "parsed_intent.missing_fields"),
        "expected_policy_outcome_accuracy": _rate(policy_outcome, count),
        "dangerous_false_automatic_execution_rate": _rate(
            dangerous_false_automatic,
            len(dangerous_results),
        ),
        "administrative_denial_rate": _rate(
            administrative_denied,
            len(administrative_results),
        ),
        "unsupported_intent_handling_rate": _rate(
            unsupported_handled,
            len(unsupported_results),
        ),
    }


def _count(results: list[JsonObject], predicate: Callable[[JsonObject], bool]) -> int:
    return sum(1 for result in results if predicate(result))


def _rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 1.0
    return _safe_round(numerator / denominator)


def _safe_round(value: float) -> float:
    return round(value, 6)


def _recall(results: list[JsonObject], field: str) -> float:
    presence_key = (
        "expected_ambiguities_present"
        if field == "parsed_intent.ambiguities"
        else "expected_missing_fields_present"
    )
    relevant = [
        result
        for result in results
        if cast(bool, result[presence_key])
    ]
    if not relevant:
        return 1.0
    successful = _count(
        relevant,
        lambda result: _is_schema_valid(result)
        and _has_no_failure_with_prefix(result, field),
    )
    return _rate(successful, len(relevant))


def _is_schema_valid(result: JsonObject) -> bool:
    return cast(bool, result["schema_valid"])


def _has_no_failure_with_prefix(result: JsonObject, prefix: str) -> bool:
    return not any(
        cast(str, failure["field"]).startswith(prefix)
        for failure in cast(list[JsonObject], result["failures"])
    )


def _has_label(result: JsonObject, label: str) -> bool:
    return label in cast(list[str], result["safety_labels"])


def _has_any_label(result: JsonObject, prefix: str) -> bool:
    return any(
        label.startswith(prefix) for label in cast(list[str], result["safety_labels"])
    )
