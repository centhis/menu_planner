from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast

from menu_planner.domain.contracts.models import (
    SCHEMA_VERSION,
    DraftStatus,
    JsonObject,
    JsonValue,
    MenuDraft,
    PlanningContext,
)
from menu_planner.domain.contracts.validation import (
    ContractValidationResult,
    validate_contract,
)
from menu_planner.domain.errors import DomainError


@dataclass(frozen=True)
class MenuDraftGenerationRequest:
    draft_id: str
    planning_context: PlanningContext


@dataclass(frozen=True)
class MenuDraftGenerationResult:
    draft_payload: JsonObject
    validation: ContractValidationResult
    draft: MenuDraft | None
    errors: tuple[DomainError, ...]
    side_effects_executed: bool = False

    @property
    def ok(self) -> bool:
        return self.draft is not None and self.validation.is_valid and not self.errors


class MenuDraftGenerator(Protocol):
    name: str
    version: str

    def generate(self, request: MenuDraftGenerationRequest) -> JsonObject: ...


class FakeMenuDraftGenerator:
    name = "fake_menu_draft_generator"
    version = "m6a.fake_generator.v1"

    def generate(self, request: MenuDraftGenerationRequest) -> JsonObject:
        context = request.planning_context
        return {
            "schema_version": SCHEMA_VERSION,
            "user_id": context.user_id,
            "draft_id": request.draft_id,
            "status": DraftStatus.GENERATED.value,
            "planning_context_id": context.context_id,
            "period_start": context.period_start,
            "period_end": context.period_end,
            "meal_slots": cast(JsonValue, context.meal_slots),
            "generated_items": cast(
                JsonValue,
                [_generated_item(slot) for slot in context.meal_slots],
            ),
        }


def generate_menu_draft(
    *,
    request: MenuDraftGenerationRequest,
    generator: MenuDraftGenerator | None = None,
) -> MenuDraftGenerationResult:
    selected_generator = generator or FakeMenuDraftGenerator()
    payload = selected_generator.generate(request)
    validation = validate_contract("menu_draft", payload)
    if not validation.is_valid or validation.value is None:
        return MenuDraftGenerationResult(
            draft_payload=payload,
            validation=validation,
            draft=None,
            errors=validation.errors,
        )

    return MenuDraftGenerationResult(
        draft_payload=payload,
        validation=validation,
        draft=cast(MenuDraft, validation.value),
        errors=(),
    )


def _generated_item(slot: JsonObject) -> JsonObject:
    slot_id = cast(str, slot["slot_id"])
    meal_type = cast(str, slot["meal_type"])
    return {
        "meal_slot_id": slot_id,
        "title": f"M6A fake {meal_type}",
    }
