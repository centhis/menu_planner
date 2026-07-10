from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeGuard, cast

from menu_planner.domain.contracts.models import (
    SCHEMA_VERSION,
    AuditEvent,
    Confirmation,
    DraftStatus,
    Ingredient,
    JsonObject,
    MealSlot,
    MenuDraft,
    MenuVersion,
    OperationClass,
    OperationPreview,
    ParsedIntent,
    PlanningContext,
    PolicyDecision,
    PolicyDecisionOutcome,
    ProfileDraft,
    ProfileVersion,
    RecipeDraft,
    RecipeVersion,
    ShoppingList,
    ShoppingListItem,
    ToolErrorEnvelope,
    ToolSuccessEnvelope,
    ValidationResult,
    WorkflowRun,
    WorkflowState,
)
from menu_planner.domain.errors import (
    DomainError,
    invalid_contract_shape,
    invalid_enum_value,
    invalid_field_type,
    invalid_schema_version,
    missing_required_field,
)


@dataclass(frozen=True)
class FieldRule:
    name: str
    expected: str
    enum_type: type[StrEnum] | None = None


@dataclass(frozen=True)
class ContractValidationResult:
    contract_name: str
    value: object | None
    errors: tuple[DomainError, ...]

    @property
    def is_valid(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class ContractValidator:
    contract_name: str
    model: type[object]
    fields: tuple[FieldRule, ...]

    def validate(self, data: object) -> ContractValidationResult:
        if not _is_json_object(data):
            return _failure(self.contract_name, invalid_contract_shape())

        schema_version = data.get("schema_version")
        if schema_version is None:
            return _failure(
                self.contract_name, missing_required_field("schema_version")
            )
        if not isinstance(schema_version, str):
            return _failure(
                self.contract_name,
                invalid_field_type("schema_version", "string"),
            )
        if schema_version != SCHEMA_VERSION:
            return _failure(self.contract_name, invalid_schema_version(schema_version))

        values: dict[str, object] = {"schema_version": schema_version}
        for field in self.fields:
            if field.name not in data:
                return _failure(self.contract_name, missing_required_field(field.name))

            raw_value = data[field.name]
            if not _matches_expected_type(raw_value, field.expected):
                return _failure(
                    self.contract_name,
                    invalid_field_type(field.name, field.expected),
                )

            if field.enum_type is not None:
                if not isinstance(raw_value, str):
                    return _failure(
                        self.contract_name,
                        invalid_field_type(field.name, "string"),
                    )
                try:
                    values[field.name] = field.enum_type(raw_value)
                except ValueError:
                    expected = [item.value for item in field.enum_type]
                    return _failure(
                        self.contract_name,
                        invalid_enum_value(field.name, expected),
                    )
            elif field.expected == "number":
                values[field.name] = float(cast(float | int, raw_value))
            else:
                values[field.name] = raw_value

        model_factory = cast(Any, self.model)
        return ContractValidationResult(
            contract_name=self.contract_name,
            value=model_factory(**values),
            errors=(),
        )


def validate_contract(contract_name: str, data: object) -> ContractValidationResult:
    validator = CONTRACT_VALIDATORS[contract_name]
    return validator.validate(data)


def _failure(contract_name: str, error: DomainError) -> ContractValidationResult:
    return ContractValidationResult(
        contract_name=contract_name,
        value=None,
        errors=(error,),
    )


def _is_json_object(value: object) -> TypeGuard[JsonObject]:
    return isinstance(value, dict) and all(isinstance(key, str) for key in value)


def _is_number(value: object) -> TypeGuard[int | float]:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _is_string_array(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _is_object_array(value: object) -> bool:
    return isinstance(value, list) and all(_is_json_object(item) for item in value)


def _matches_expected_type(value: object, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return _is_number(value)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "object":
        return _is_json_object(value)
    if expected == "string_array":
        return _is_string_array(value)
    if expected == "object_array":
        return _is_object_array(value)
    raise ValueError(f"Unsupported field type rule: {expected}")


CONTRACT_VALIDATORS: dict[str, ContractValidator] = {
    "parsed_intent": ContractValidator(
        "parsed_intent",
        ParsedIntent,
        (
            FieldRule("intent", "string"),
            FieldRule("confidence", "number"),
            FieldRule("parameters", "object"),
            FieldRule("missing_fields", "string_array"),
            FieldRule("ambiguities", "string_array"),
            FieldRule("operation_class", "string", OperationClass),
            FieldRule("requires_confirmation", "boolean"),
            FieldRule("scope", "string"),
            FieldRule("suggested_next_action", "string"),
        ),
    ),
    "profile_draft": ContractValidator(
        "profile_draft",
        ProfileDraft,
        (
            FieldRule("user_id", "string"),
            FieldRule("draft_id", "string"),
            FieldRule("status", "string", DraftStatus),
            FieldRule("fields", "object"),
        ),
    ),
    "profile_version": ContractValidator(
        "profile_version",
        ProfileVersion,
        (
            FieldRule("user_id", "string"),
            FieldRule("profile_id", "string"),
            FieldRule("version", "integer"),
            FieldRule("fields", "object"),
        ),
    ),
    "planning_context": ContractValidator(
        "planning_context",
        PlanningContext,
        (
            FieldRule("user_id", "string"),
            FieldRule("context_id", "string"),
            FieldRule("profile_version", "integer"),
            FieldRule("constraints", "object"),
        ),
    ),
    "meal_slot": ContractValidator(
        "meal_slot",
        MealSlot,
        (
            FieldRule("date", "string"),
            FieldRule("meal_type", "string"),
            FieldRule("requirements", "object"),
        ),
    ),
    "menu_draft": ContractValidator(
        "menu_draft",
        MenuDraft,
        (
            FieldRule("user_id", "string"),
            FieldRule("draft_id", "string"),
            FieldRule("status", "string", DraftStatus),
            FieldRule("meal_slots", "object_array"),
        ),
    ),
    "menu_version": ContractValidator(
        "menu_version",
        MenuVersion,
        (
            FieldRule("user_id", "string"),
            FieldRule("menu_id", "string"),
            FieldRule("version", "integer"),
            FieldRule("meal_slots", "object_array"),
        ),
    ),
    "ingredient": ContractValidator(
        "ingredient",
        Ingredient,
        (
            FieldRule("name", "string"),
            FieldRule("quantity", "number"),
            FieldRule("unit", "string"),
        ),
    ),
    "recipe_draft": ContractValidator(
        "recipe_draft",
        RecipeDraft,
        (
            FieldRule("user_id", "string"),
            FieldRule("draft_id", "string"),
            FieldRule("status", "string", DraftStatus),
            FieldRule("ingredients", "object_array"),
        ),
    ),
    "recipe_version": ContractValidator(
        "recipe_version",
        RecipeVersion,
        (
            FieldRule("user_id", "string"),
            FieldRule("recipe_id", "string"),
            FieldRule("version", "integer"),
            FieldRule("ingredients", "object_array"),
        ),
    ),
    "shopping_list_item": ContractValidator(
        "shopping_list_item",
        ShoppingListItem,
        (
            FieldRule("name", "string"),
            FieldRule("quantity", "number"),
            FieldRule("unit", "string"),
            FieldRule("status", "string"),
        ),
    ),
    "shopping_list": ContractValidator(
        "shopping_list",
        ShoppingList,
        (
            FieldRule("user_id", "string"),
            FieldRule("shopping_list_id", "string"),
            FieldRule("items", "object_array"),
        ),
    ),
    "workflow_run": ContractValidator(
        "workflow_run",
        WorkflowRun,
        (
            FieldRule("workflow_id", "string"),
            FieldRule("user_id", "string"),
            FieldRule("state", "string", WorkflowState),
            FieldRule("allowed_actions", "string_array"),
            FieldRule("attempts", "integer"),
        ),
    ),
    "validation_result": ContractValidator(
        "validation_result",
        ValidationResult,
        (
            FieldRule("is_valid", "boolean"),
            FieldRule("errors", "object_array"),
        ),
    ),
    "operation_preview": ContractValidator(
        "operation_preview",
        OperationPreview,
        (
            FieldRule("preview_id", "string"),
            FieldRule("operation", "string"),
            FieldRule("entity_ref", "string"),
            FieldRule("summary_hash", "string"),
            FieldRule("changes", "object_array"),
            FieldRule("requires_confirmation", "boolean"),
        ),
    ),
    "confirmation": ContractValidator(
        "confirmation",
        Confirmation,
        (
            FieldRule("confirmation_id", "string"),
            FieldRule("user_id", "string"),
            FieldRule("operation", "string"),
            FieldRule("entity_id", "string"),
            FieldRule("expected_version", "integer"),
            FieldRule("draft_version", "integer"),
            FieldRule("expires_at", "string"),
            FieldRule("summary_hash", "string"),
            FieldRule("status", "string"),
        ),
    ),
    "policy_decision": ContractValidator(
        "policy_decision",
        PolicyDecision,
        (
            FieldRule("outcome", "string", PolicyDecisionOutcome),
            FieldRule("allowed", "boolean"),
            FieldRule("operation_class", "string", OperationClass),
            FieldRule("reason_code", "string"),
            FieldRule("current_state", "string"),
            FieldRule("allowed_actions", "string_array"),
            FieldRule("required_data", "string_array"),
            FieldRule("missing_fields", "string_array"),
            FieldRule("ambiguities", "string_array"),
            FieldRule("requires_confirmation", "boolean"),
            FieldRule("errors", "object_array"),
        ),
    ),
    "audit_event": ContractValidator(
        "audit_event",
        AuditEvent,
        (
            FieldRule("event_id", "string"),
            FieldRule("user_id", "string"),
            FieldRule("operation", "string"),
            FieldRule("occurred_at", "string"),
            FieldRule("outcome", "string"),
            FieldRule("details", "object"),
        ),
    ),
    "tool_success_envelope": ContractValidator(
        "tool_success_envelope",
        ToolSuccessEnvelope,
        (
            FieldRule("ok", "boolean"),
            FieldRule("result", "object"),
        ),
    ),
    "tool_error_envelope": ContractValidator(
        "tool_error_envelope",
        ToolErrorEnvelope,
        (
            FieldRule("ok", "boolean"),
            FieldRule("errors", "object_array"),
        ),
    ),
}
