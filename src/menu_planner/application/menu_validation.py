from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from menu_planner.domain.contracts.models import (
    JsonObject,
    JsonValue,
    MenuDraft,
    PlanningContext,
)
from menu_planner.domain.contracts.validation import (
    ContractValidationResult,
    validate_contract,
)
from menu_planner.domain.errors import (
    DomainError,
    menu_active_time_exceeded,
    menu_equipment_unavailable,
    menu_meal_slot_missing,
    menu_period_incomplete,
    menu_portions_invalid,
    menu_referential_integrity_violated,
    menu_repetition_violated,
    menu_strict_restriction_violated,
)


@dataclass(frozen=True)
class MenuDraftValidationResult:
    draft_payload: JsonObject
    contract_validation: ContractValidationResult
    draft: MenuDraft | None
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
    def can_create_safe_preview(self) -> bool:
        return self.ok


def validate_menu_draft_for_context(
    *,
    draft: JsonObject | MenuDraft,
    planning_context: PlanningContext,
) -> MenuDraftValidationResult:
    payload = _draft_payload(draft)
    contract_validation = validate_contract("menu_draft", payload)
    if not contract_validation.is_valid or contract_validation.value is None:
        return MenuDraftValidationResult(
            draft_payload=payload,
            contract_validation=contract_validation,
            draft=None,
            errors=contract_validation.errors,
        )

    typed_draft = cast(MenuDraft, contract_validation.value)
    errors = tuple(_validate_semantics(typed_draft, payload, planning_context))
    return MenuDraftValidationResult(
        draft_payload=payload,
        contract_validation=contract_validation,
        draft=typed_draft if not errors else None,
        errors=errors,
    )


def _validate_semantics(
    draft: MenuDraft,
    payload: JsonObject,
    context: PlanningContext,
) -> list[DomainError]:
    errors: list[DomainError] = []
    expected_slot_ids = _slot_ids(context.meal_slots)
    draft_slot_ids = _slot_ids(draft.meal_slots)
    generated_items = cast(list[JsonObject], payload["generated_items"])

    if (
        draft.period_start != context.period_start
        or draft.period_end != context.period_end
    ):
        errors.append(
            menu_period_incomplete(
                context.period_start,
                context.period_end,
                draft.period_start,
                draft.period_end,
            )
        )

    generated_slot_ids = [
        cast(str, item["meal_slot_id"])
        for item in generated_items
        if isinstance(item.get("meal_slot_id"), str)
    ]
    if set(draft_slot_ids) != set(expected_slot_ids) or set(generated_slot_ids) != set(
        expected_slot_ids
    ):
        errors.append(menu_meal_slot_missing(expected_slot_ids, draft_slot_ids))

    known_slot_ids = sorted(set(expected_slot_ids) | set(draft_slot_ids))
    for meal_slot_id in generated_slot_ids:
        if meal_slot_id not in known_slot_ids or meal_slot_id not in expected_slot_ids:
            errors.append(
                menu_referential_integrity_violated(meal_slot_id, known_slot_ids)
            )

    errors.extend(_validate_strict_restrictions(generated_items, context.constraints))
    errors.extend(_validate_equipment(generated_items, context.constraints))
    errors.extend(_validate_active_time(generated_items, context.constraints))
    errors.extend(_validate_portions(generated_items, context.constraints))
    errors.extend(_validate_repetition(generated_items))
    return errors


def _draft_payload(draft: JsonObject | MenuDraft) -> JsonObject:
    if isinstance(draft, MenuDraft):
        return {
            "schema_version": draft.schema_version,
            "user_id": draft.user_id,
            "draft_id": draft.draft_id,
            "status": draft.status.value,
            "planning_context_id": draft.planning_context_id,
            "period_start": draft.period_start,
            "period_end": draft.period_end,
            "meal_slots": cast(JsonValue, draft.meal_slots),
            "generated_items": cast(JsonValue, draft.generated_items),
        }
    return draft


def _slot_ids(meal_slots: list[JsonObject]) -> list[str]:
    return [
        cast(str, meal_slot["slot_id"])
        for meal_slot in meal_slots
        if isinstance(meal_slot.get("slot_id"), str)
    ]


def _validate_strict_restrictions(
    generated_items: list[JsonObject],
    constraints: JsonObject,
) -> list[DomainError]:
    restrictions = _restriction_values(constraints.get("strict_restrictions"))
    errors: list[DomainError] = []
    for item in generated_items:
        title = cast(str, item["title"])
        normalized_title = title.casefold()
        for restriction in restrictions:
            if restriction.casefold() in normalized_title:
                errors.append(
                    menu_strict_restriction_violated(
                        restriction,
                        cast(str, item["meal_slot_id"]),
                        title,
                    )
                )
    return errors


def _validate_equipment(
    generated_items: list[JsonObject],
    constraints: JsonObject,
) -> list[DomainError]:
    available = _string_list(constraints.get("available_equipment"))
    if not available:
        return []

    available_set = set(available)
    errors: list[DomainError] = []
    for item in generated_items:
        required = _string_list(item.get("required_equipment"))
        unavailable = [
            equipment for equipment in required if equipment not in available_set
        ]
        if unavailable:
            errors.append(
                menu_equipment_unavailable(
                    unavailable,
                    available,
                    cast(str, item["meal_slot_id"]),
                )
            )
    return errors


def _validate_active_time(
    generated_items: list[JsonObject],
    constraints: JsonObject,
) -> list[DomainError]:
    limit = _positive_int(constraints.get("max_active_time_minutes"))
    if limit is None:
        return []

    errors: list[DomainError] = []
    for item in generated_items:
        actual = _positive_int(item.get("active_time_minutes"))
        if actual is not None and actual > limit:
            errors.append(
                menu_active_time_exceeded(
                    limit,
                    actual,
                    cast(str, item["meal_slot_id"]),
                )
            )
    return errors


def _validate_portions(
    generated_items: list[JsonObject],
    constraints: JsonObject,
) -> list[DomainError]:
    expected = _positive_int(constraints.get("people_count"))
    errors: list[DomainError] = []
    for item in generated_items:
        actual = _positive_int(item.get("portions"))
        if expected is not None and actual != expected:
            errors.append(
                menu_portions_invalid(
                    expected,
                    actual or 0,
                    cast(str, item["meal_slot_id"]),
                )
            )
        elif "portions" in item and actual is None:
            errors.append(
                menu_portions_invalid(
                    expected or 1,
                    0,
                    cast(str, item["meal_slot_id"]),
                )
            )
    return errors


def _validate_repetition(generated_items: list[JsonObject]) -> list[DomainError]:
    seen: dict[str, list[str]] = {}
    for item in generated_items:
        normalized_title = cast(str, item["title"]).casefold()
        seen.setdefault(normalized_title, []).append(cast(str, item["meal_slot_id"]))

    return [
        menu_repetition_violated(title, meal_slot_ids)
        for title, meal_slot_ids in seen.items()
        if len(meal_slot_ids) > 1
    ]


def _restriction_values(value: JsonValue) -> list[str]:
    if not isinstance(value, list):
        return []

    restrictions: list[str] = []
    for item in value:
        if isinstance(item, str):
            restrictions.append(item)
        elif isinstance(item, dict) and isinstance(item.get("value"), str):
            restrictions.append(cast(str, item["value"]))
    return restrictions


def _string_list(value: JsonValue) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _positive_int(value: JsonValue) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, float) and value.is_integer() and value > 0:
        return int(value)
    return None
