from __future__ import annotations

from collections.abc import Callable
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
    invalid_range,
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
    custom_validate: Callable[[dict[str, object]], DomainError | None] | None = None

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

        if self.custom_validate is not None:
            custom_error = self.custom_validate(values)
            if custom_error is not None:
                return _failure(self.contract_name, custom_error)

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


def _is_object_array(value: object) -> TypeGuard[list[JsonObject]]:
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


def _validate_positive_integer_field(
    value: object,
    field_path: str,
) -> DomainError | None:
    if not isinstance(value, int) or isinstance(value, bool):
        return invalid_field_type(field_path, "integer")
    if value < 1:
        return invalid_range(field_path, 1, 2147483647, value)
    return None


def _validate_non_empty_string_field(
    value: object,
    field_path: str,
) -> DomainError | None:
    if not isinstance(value, str):
        return invalid_field_type(field_path, "string")
    if value == "":
        return invalid_range(field_path, 1, 2147483647, 0)
    return None


def _validate_non_empty_string_array(
    value: object,
    field_path: str,
) -> DomainError | None:
    if not isinstance(value, list):
        return invalid_field_type(field_path, "string_array")
    for index, item in enumerate(value):
        item_path = f"{field_path}.{index}"
        error = _validate_non_empty_string_field(item, item_path)
        if error is not None:
            return error
    return None


def _validate_profile_named_item_array(
    value: object,
    field_path: str,
    required_fields: tuple[str, ...],
) -> DomainError | None:
    if not _is_object_array(value):
        return invalid_field_type(field_path, "object_array")

    for index, item in enumerate(value):
        for field_name in required_fields:
            item_path = f"{field_path}.{index}.{field_name}"
            if field_name not in item:
                return missing_required_field(item_path)
            error = _validate_non_empty_string_field(item[field_name], item_path)
            if error is not None:
                return error
    return None


def _validate_m4_profile_fields(values: dict[str, object]) -> DomainError | None:
    fields = values["fields"]
    if not _is_json_object(fields):
        return invalid_field_type("fields", "object")

    required_top_level = (
        "user_facts",
        "strict_restrictions",
        "soft_preferences",
    )
    for field_name in required_top_level:
        if field_name not in fields:
            return missing_required_field(f"fields.{field_name}")

    user_facts = fields["user_facts"]
    if not _is_json_object(user_facts):
        return invalid_field_type("fields.user_facts", "object")

    required_user_facts = (
        "people_count",
        "locale",
        "timezone",
        "available_equipment",
        "default_max_active_time_minutes",
    )
    for field_name in required_user_facts:
        if field_name not in user_facts:
            return missing_required_field(f"fields.user_facts.{field_name}")

    checks = (
        _validate_positive_integer_field(
            user_facts["people_count"],
            "fields.user_facts.people_count",
        ),
        _validate_non_empty_string_field(
            user_facts["locale"],
            "fields.user_facts.locale",
        ),
        _validate_non_empty_string_field(
            user_facts["timezone"],
            "fields.user_facts.timezone",
        ),
        _validate_non_empty_string_array(
            user_facts["available_equipment"],
            "fields.user_facts.available_equipment",
        ),
        _validate_positive_integer_field(
            user_facts["default_max_active_time_minutes"],
            "fields.user_facts.default_max_active_time_minutes",
        ),
        _validate_profile_named_item_array(
            fields["strict_restrictions"],
            "fields.strict_restrictions",
            ("kind", "value"),
        ),
        _validate_profile_named_item_array(
            fields["soft_preferences"],
            "fields.soft_preferences",
            ("direction", "value"),
        ),
    )
    return next((error for error in checks if error is not None), None)


def _validate_m4_profile_version(values: dict[str, object]) -> DomainError | None:
    version = values["version"]
    version_error = _validate_positive_integer_field(version, "version")
    if version_error is not None:
        return version_error
    return _validate_m4_profile_fields(values)


def _validate_m6a_meal_slot_object(
    value: JsonObject,
    field_path: str,
) -> DomainError | None:
    required_fields = ("schema_version", "slot_id", "date", "meal_type", "requirements")
    for field_name in required_fields:
        item_path = f"{field_path}.{field_name}"
        if field_name not in value:
            return missing_required_field(item_path)

    if value["schema_version"] != SCHEMA_VERSION:
        return invalid_schema_version(cast(str, value["schema_version"]))

    for field_name in ("slot_id", "date", "meal_type"):
        error = _validate_non_empty_string_field(
            value[field_name],
            f"{field_path}.{field_name}",
        )
        if error is not None:
            return error

    if not _is_json_object(value["requirements"]):
        return invalid_field_type(f"{field_path}.requirements", "object")
    return None


def _validate_m6a_meal_slots(
    value: object,
    field_path: str,
) -> DomainError | None:
    if not _is_object_array(value):
        return invalid_field_type(field_path, "object_array")
    if not value:
        return invalid_range(field_path, 1, 2147483647, 0)

    for index, item in enumerate(value):
        error = _validate_m6a_meal_slot_object(item, f"{field_path}.{index}")
        if error is not None:
            return error
    return None


def _validate_m6a_one_day_period(values: dict[str, object]) -> DomainError | None:
    period_start = values["period_start"]
    period_end = values["period_end"]
    for field_name, value in (
        ("period_start", period_start),
        ("period_end", period_end),
    ):
        error = _validate_non_empty_string_field(value, field_name)
        if error is not None:
            return error
    if period_start != period_end:
        return invalid_range("period_end", 1, 1, 2)
    return None


def _validate_m6a_planning_context(values: dict[str, object]) -> DomainError | None:
    profile_version_error = _validate_positive_integer_field(
        values["profile_version"],
        "profile_version",
    )
    if profile_version_error is not None:
        return profile_version_error

    for field_name in ("planning_request_id", "context_id", "user_id"):
        error = _validate_non_empty_string_field(values[field_name], field_name)
        if error is not None:
            return error

    period_error = _validate_m6a_one_day_period(values)
    if period_error is not None:
        return period_error

    return _validate_m6a_meal_slots(values["meal_slots"], "meal_slots")


def _validate_m6a_meal_slot(values: dict[str, object]) -> DomainError | None:
    error = _validate_non_empty_string_field(values["slot_id"], "slot_id")
    if error is not None:
        return error
    error = _validate_non_empty_string_field(values["date"], "date")
    if error is not None:
        return error
    return _validate_non_empty_string_field(values["meal_type"], "meal_type")


def _validate_m6a_generated_items(
    value: object,
    field_path: str,
) -> DomainError | None:
    if not _is_object_array(value):
        return invalid_field_type(field_path, "object_array")
    if not value:
        return invalid_range(field_path, 1, 2147483647, 0)

    for index, item in enumerate(value):
        for field_name in ("meal_slot_id", "title"):
            item_path = f"{field_path}.{index}.{field_name}"
            if field_name not in item:
                return missing_required_field(item_path)
            error = _validate_non_empty_string_field(item[field_name], item_path)
            if error is not None:
                return error
    return None


def _validate_m6a_menu_draft(values: dict[str, object]) -> DomainError | None:
    for field_name in ("planning_context_id", "draft_id", "user_id"):
        error = _validate_non_empty_string_field(values[field_name], field_name)
        if error is not None:
            return error

    period_error = _validate_m6a_one_day_period(values)
    if period_error is not None:
        return period_error

    meal_slots_error = _validate_m6a_meal_slots(values["meal_slots"], "meal_slots")
    if meal_slots_error is not None:
        return meal_slots_error

    return _validate_m6a_generated_items(
        values["generated_items"],
        "generated_items",
    )


def _validate_m6b_recipe_ingredient(
    value: JsonObject,
    field_path: str,
) -> DomainError | None:
    required_fields = (
        "schema_version",
        "ingredient_id",
        "name",
        "quantity",
        "unit",
    )
    for field_name in required_fields:
        item_path = f"{field_path}.{field_name}"
        if field_name not in value:
            return missing_required_field(item_path)

    if value["schema_version"] != SCHEMA_VERSION:
        return invalid_schema_version(cast(str, value["schema_version"]))

    for field_name in ("ingredient_id", "name", "unit"):
        error = _validate_non_empty_string_field(
            value[field_name],
            f"{field_path}.{field_name}",
        )
        if error is not None:
            return error

    quantity = value["quantity"]
    if not _is_number(quantity):
        return invalid_field_type(f"{field_path}.quantity", "number")
    if quantity <= 0:
        return invalid_range(f"{field_path}.quantity", 1, 2147483647, quantity)
    return None


def _validate_m6b_recipe_ingredients(
    value: object,
) -> tuple[set[str], DomainError | None]:
    if not _is_object_array(value):
        return set(), invalid_field_type("ingredients", "object_array")
    if not value:
        return set(), invalid_range("ingredients", 1, 2147483647, 0)

    ingredient_ids: set[str] = set()
    for index, item in enumerate(value):
        error = _validate_m6b_recipe_ingredient(item, f"ingredients.{index}")
        if error is not None:
            return set(), error
        ingredient_id = cast(str, item["ingredient_id"])
        if ingredient_id in ingredient_ids:
            return set(), invalid_enum_value(
                f"ingredients.{index}.ingredient_id",
                sorted(ingredient_ids),
            )
        ingredient_ids.add(ingredient_id)
    return ingredient_ids, None


def _validate_m6b_recipe_step(
    value: JsonObject,
    field_path: str,
    ingredient_ids: set[str],
) -> DomainError | None:
    required_fields = (
        "schema_version",
        "step_id",
        "order",
        "instruction",
        "ingredient_ids",
        "method",
    )
    for field_name in required_fields:
        item_path = f"{field_path}.{field_name}"
        if field_name not in value:
            return missing_required_field(item_path)

    if value["schema_version"] != SCHEMA_VERSION:
        return invalid_schema_version(cast(str, value["schema_version"]))

    for field_name in ("step_id", "instruction", "method"):
        error = _validate_non_empty_string_field(
            value[field_name],
            f"{field_path}.{field_name}",
        )
        if error is not None:
            return error

    order_error = _validate_positive_integer_field(
        value["order"],
        f"{field_path}.order",
    )
    if order_error is not None:
        return order_error

    ingredient_refs_error = _validate_non_empty_string_array(
        value["ingredient_ids"],
        f"{field_path}.ingredient_ids",
    )
    if ingredient_refs_error is not None:
        return ingredient_refs_error
    for index, ingredient_id in enumerate(cast(list[str], value["ingredient_ids"])):
        if ingredient_id not in ingredient_ids:
            return invalid_enum_value(
                f"{field_path}.ingredient_ids.{index}",
                sorted(ingredient_ids),
            )

    method = cast(str, value["method"])
    if "temperature_celsius" in value:
        temperature = value["temperature_celsius"]
        if not isinstance(temperature, int) or isinstance(temperature, bool):
            return invalid_field_type(f"{field_path}.temperature_celsius", "integer")
        if temperature < 1:
            return invalid_range(
                f"{field_path}.temperature_celsius",
                1,
                1000,
                temperature,
            )
    elif method in {"bake", "roast"}:
        return missing_required_field(f"{field_path}.temperature_celsius")
    return None


def _validate_m6b_recipe_steps(
    value: object,
    ingredient_ids: set[str],
) -> DomainError | None:
    if not _is_object_array(value):
        return invalid_field_type("steps", "object_array")
    if not value:
        return invalid_range("steps", 1, 2147483647, 0)

    for index, item in enumerate(value):
        error = _validate_m6b_recipe_step(item, f"steps.{index}", ingredient_ids)
        if error is not None:
            return error
    return None


def _validate_m6b_recipe_notes(
    value: object,
    field_path: str,
) -> DomainError | None:
    if not _is_json_object(value):
        return invalid_field_type(field_path, "object")
    for field_name in ("instructions",):
        if field_name not in value:
            return missing_required_field(f"{field_path}.{field_name}")
        error = _validate_non_empty_string_field(
            value[field_name],
            f"{field_path}.{field_name}",
        )
        if error is not None:
            return error
    return None


def _validate_m6b_recipe_draft(values: dict[str, object]) -> DomainError | None:
    for field_name in (
        "draft_id",
        "user_id",
        "source_menu_id",
        "source_meal_slot_id",
        "title",
    ):
        error = _validate_non_empty_string_field(values[field_name], field_name)
        if error is not None:
            return error

    for field_name in (
        "source_menu_version",
        "portions",
        "active_time_minutes",
        "total_time_minutes",
    ):
        error = _validate_positive_integer_field(values[field_name], field_name)
        if error is not None:
            return error

    if cast(int, values["active_time_minutes"]) > cast(
        int,
        values["total_time_minutes"],
    ):
        return invalid_range(
            "active_time_minutes",
            1,
            cast(int, values["total_time_minutes"]),
            cast(int, values["active_time_minutes"]),
        )

    equipment_error = _validate_non_empty_string_array(
        values["equipment"],
        "equipment",
    )
    if equipment_error is not None:
        return equipment_error

    ingredient_ids, ingredients_error = _validate_m6b_recipe_ingredients(
        values["ingredients"]
    )
    if ingredients_error is not None:
        return ingredients_error

    steps_error = _validate_m6b_recipe_steps(values["steps"], ingredient_ids)
    if steps_error is not None:
        return steps_error

    storage_error = _validate_m6b_recipe_notes(values["storage"], "storage")
    if storage_error is not None:
        return storage_error
    return _validate_m6b_recipe_notes(values["reheating"], "reheating")


def _validate_m6b_recipe_version(values: dict[str, object]) -> DomainError | None:
    version_error = _validate_positive_integer_field(values["version"], "version")
    if version_error is not None:
        return version_error

    recipe_id_error = _validate_non_empty_string_field(
        values["recipe_id"],
        "recipe_id",
    )
    if recipe_id_error is not None:
        return recipe_id_error

    draft_like_values = dict(values)
    draft_like_values["draft_id"] = values["recipe_id"]
    return _validate_m6b_recipe_draft(draft_like_values)


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
        _validate_m4_profile_fields,
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
        _validate_m4_profile_version,
    ),
    "planning_context": ContractValidator(
        "planning_context",
        PlanningContext,
        (
            FieldRule("user_id", "string"),
            FieldRule("context_id", "string"),
            FieldRule("profile_version", "integer"),
            FieldRule("planning_request_id", "string"),
            FieldRule("period_start", "string"),
            FieldRule("period_end", "string"),
            FieldRule("meal_slots", "object_array"),
            FieldRule("constraints", "object"),
        ),
        _validate_m6a_planning_context,
    ),
    "meal_slot": ContractValidator(
        "meal_slot",
        MealSlot,
        (
            FieldRule("slot_id", "string"),
            FieldRule("date", "string"),
            FieldRule("meal_type", "string"),
            FieldRule("requirements", "object"),
        ),
        _validate_m6a_meal_slot,
    ),
    "menu_draft": ContractValidator(
        "menu_draft",
        MenuDraft,
        (
            FieldRule("user_id", "string"),
            FieldRule("draft_id", "string"),
            FieldRule("status", "string", DraftStatus),
            FieldRule("planning_context_id", "string"),
            FieldRule("period_start", "string"),
            FieldRule("period_end", "string"),
            FieldRule("meal_slots", "object_array"),
            FieldRule("generated_items", "object_array"),
        ),
        _validate_m6a_menu_draft,
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
            FieldRule("source_menu_id", "string"),
            FieldRule("source_menu_version", "integer"),
            FieldRule("source_meal_slot_id", "string"),
            FieldRule("title", "string"),
            FieldRule("portions", "integer"),
            FieldRule("ingredients", "object_array"),
            FieldRule("equipment", "string_array"),
            FieldRule("active_time_minutes", "integer"),
            FieldRule("total_time_minutes", "integer"),
            FieldRule("steps", "object_array"),
            FieldRule("storage", "object"),
            FieldRule("reheating", "object"),
        ),
        _validate_m6b_recipe_draft,
    ),
    "recipe_version": ContractValidator(
        "recipe_version",
        RecipeVersion,
        (
            FieldRule("user_id", "string"),
            FieldRule("recipe_id", "string"),
            FieldRule("version", "integer"),
            FieldRule("source_menu_id", "string"),
            FieldRule("source_menu_version", "integer"),
            FieldRule("source_meal_slot_id", "string"),
            FieldRule("title", "string"),
            FieldRule("portions", "integer"),
            FieldRule("ingredients", "object_array"),
            FieldRule("equipment", "string_array"),
            FieldRule("active_time_minutes", "integer"),
            FieldRule("total_time_minutes", "integer"),
            FieldRule("steps", "object_array"),
            FieldRule("storage", "object"),
            FieldRule("reheating", "object"),
        ),
        _validate_m6b_recipe_version,
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
