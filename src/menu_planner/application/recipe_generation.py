from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast

from menu_planner.domain.contracts.models import (
    SCHEMA_VERSION,
    DraftStatus,
    JsonObject,
    JsonValue,
    RecipeDraft,
)
from menu_planner.domain.contracts.validation import (
    ContractValidationResult,
    validate_contract,
)
from menu_planner.domain.errors import DomainError


@dataclass(frozen=True)
class RecipeDraftGenerationRequest:
    draft_id: str
    accepted_menu_item: JsonObject
    portions: int = 2


@dataclass(frozen=True)
class RecipeDraftGenerationResult:
    draft_payload: JsonObject
    validation: ContractValidationResult
    draft: RecipeDraft | None
    errors: tuple[DomainError, ...]
    side_effects_executed: bool = False

    @property
    def ok(self) -> bool:
        return self.draft is not None and self.validation.is_valid and not self.errors


class RecipeDraftGenerator(Protocol):
    name: str
    version: str

    def generate(self, request: RecipeDraftGenerationRequest) -> JsonObject: ...


class FakeRecipeDraftGenerator:
    name = "fake_recipe_draft_generator"
    version = "m6b.fake_recipe_generator.v1"

    def generate(self, request: RecipeDraftGenerationRequest) -> JsonObject:
        item = request.accepted_menu_item
        return {
            "schema_version": SCHEMA_VERSION,
            "user_id": item["user_id"],
            "draft_id": request.draft_id,
            "status": DraftStatus.GENERATED.value,
            "source_menu_id": item["menu_id"],
            "source_menu_version": item["menu_version"],
            "source_meal_slot_id": item["meal_slot_id"],
            "title": "M6B fake dinner recipe",
            "portions": request.portions,
            "ingredients": cast(
                JsonValue,
                [
                    {
                        "schema_version": SCHEMA_VERSION,
                        "ingredient_id": "ingredient_001",
                        "name": "rice",
                        "quantity": 200,
                        "unit": "gram",
                    }
                ],
            ),
            "equipment": ["stovetop"],
            "active_time_minutes": 20,
            "total_time_minutes": 30,
            "steps": cast(
                JsonValue,
                [
                    {
                        "schema_version": SCHEMA_VERSION,
                        "step_id": "step_001",
                        "order": 1,
                        "instruction": "Cook rice on the stovetop.",
                        "ingredient_ids": ["ingredient_001"],
                        "method": "simmer",
                    }
                ],
            ),
            "storage": {
                "instructions": "Refrigerate in a covered container.",
            },
            "reheating": {
                "instructions": "Reheat gently on the stovetop.",
            },
        }


def generate_recipe_draft(
    *,
    request: RecipeDraftGenerationRequest,
    generator: RecipeDraftGenerator | None = None,
) -> RecipeDraftGenerationResult:
    selected_generator = generator or FakeRecipeDraftGenerator()
    payload = selected_generator.generate(request)
    validation = validate_contract("recipe_draft", payload)
    if not validation.is_valid or validation.value is None:
        return RecipeDraftGenerationResult(
            draft_payload=payload,
            validation=validation,
            draft=None,
            errors=validation.errors,
        )

    return RecipeDraftGenerationResult(
        draft_payload=payload,
        validation=validation,
        draft=cast(RecipeDraft, validation.value),
        errors=(),
    )
