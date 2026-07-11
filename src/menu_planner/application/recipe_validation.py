from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from menu_planner.domain.contracts.models import (
    DraftStatus,
    JsonObject,
    JsonValue,
    RecipeDraft,
)
from menu_planner.domain.contracts.validation import (
    ContractValidationResult,
    validate_contract,
)
from menu_planner.domain.errors import (
    DomainError,
    recipe_equipment_unavailable,
    recipe_source_mismatch,
)


@dataclass(frozen=True)
class RecipeDraftValidationResult:
    draft_payload: JsonObject
    contract_validation: ContractValidationResult
    draft: RecipeDraft | None
    errors: tuple[DomainError, ...]
    side_effects_executed: bool = False

    @property
    def ok(self) -> bool:
        return (
            self.draft is not None
            and self.contract_validation.is_valid
            and not self.errors
        )

    @property
    def can_persist_valid_version(self) -> bool:
        return self.ok


def validate_recipe_draft_for_menu_item(
    *,
    draft: JsonObject | RecipeDraft,
    accepted_menu_item: JsonObject,
) -> RecipeDraftValidationResult:
    payload = _draft_payload(draft)
    contract_validation = validate_contract("recipe_draft", payload)
    if not contract_validation.is_valid or contract_validation.value is None:
        return RecipeDraftValidationResult(
            draft_payload=payload,
            contract_validation=contract_validation,
            draft=None,
            errors=contract_validation.errors,
        )

    typed_draft = cast(RecipeDraft, contract_validation.value)
    errors = tuple(_validate_semantics(typed_draft, accepted_menu_item))
    return RecipeDraftValidationResult(
        draft_payload=payload,
        contract_validation=contract_validation,
        draft=typed_draft if not errors else None,
        errors=errors,
    )


def _validate_semantics(
    draft: RecipeDraft,
    accepted_menu_item: JsonObject,
) -> list[DomainError]:
    errors: list[DomainError] = []
    source_checks = (
        ("user_id", draft.user_id, _string_value(accepted_menu_item, "user_id")),
        (
            "source_menu_id",
            draft.source_menu_id,
            _string_value(accepted_menu_item, "menu_id"),
        ),
        (
            "source_menu_version",
            str(draft.source_menu_version),
            _string_value(accepted_menu_item, "menu_version"),
        ),
        (
            "source_meal_slot_id",
            draft.source_meal_slot_id,
            _string_value(accepted_menu_item, "meal_slot_id"),
        ),
    )
    for field, actual, expected in source_checks:
        if actual != expected:
            errors.append(recipe_source_mismatch(field, expected, actual))

    available_equipment = _string_list(accepted_menu_item.get("available_equipment"))
    if available_equipment:
        unavailable = [
            equipment
            for equipment in draft.equipment
            if equipment not in available_equipment
        ]
        if unavailable:
            errors.append(
                recipe_equipment_unavailable(unavailable, available_equipment)
            )

    return errors


def _draft_payload(draft: JsonObject | RecipeDraft) -> JsonObject:
    if isinstance(draft, RecipeDraft):
        return {
            "schema_version": draft.schema_version,
            "user_id": draft.user_id,
            "draft_id": draft.draft_id,
            "status": draft.status.value
            if isinstance(draft.status, DraftStatus)
            else draft.status,
            "source_menu_id": draft.source_menu_id,
            "source_menu_version": draft.source_menu_version,
            "source_meal_slot_id": draft.source_meal_slot_id,
            "title": draft.title,
            "portions": draft.portions,
            "ingredients": cast(JsonValue, draft.ingredients),
            "equipment": cast(JsonValue, draft.equipment),
            "active_time_minutes": draft.active_time_minutes,
            "total_time_minutes": draft.total_time_minutes,
            "steps": cast(JsonValue, draft.steps),
            "storage": draft.storage,
            "reheating": draft.reheating,
        }
    return draft


def _string_value(payload: JsonObject, field_name: str) -> str:
    value = payload.get(field_name)
    if isinstance(value, str):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return ""


def _string_list(value: JsonValue) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
