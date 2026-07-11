from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from menu_planner.application.menu_validation import MenuDraftValidationResult
from menu_planner.application.safe_commit import (
    OperationPreviewInput,
    build_operation_preview,
)
from menu_planner.domain.contracts.models import (
    JsonObject,
    JsonValue,
    MenuDraft,
    OperationPreview,
)
from menu_planner.domain.errors import DomainError

MENU_PREVIEW_OPERATION = "commit_menu_draft"
MENU_ENTITY_TYPE = "menu"


@dataclass(frozen=True)
class CreateMenuPreviewCommand:
    preview_id: str
    menu_id: str
    expected_version: int
    draft_version: int
    validation: MenuDraftValidationResult


@dataclass(frozen=True)
class MenuPreviewResult:
    preview: OperationPreview | None
    errors: tuple[DomainError, ...]
    side_effects_executed: bool = False
    confirmed_state_changed: bool = False

    @property
    def ok(self) -> bool:
        return self.preview is not None and not self.errors


def create_menu_preview(command: CreateMenuPreviewCommand) -> MenuPreviewResult:
    validation = command.validation
    if not validation.can_create_safe_preview or validation.draft is None:
        return MenuPreviewResult(
            preview=None,
            errors=validation.errors,
        )

    draft = validation.draft
    preview_input = OperationPreviewInput(
        preview_id=command.preview_id,
        operation=MENU_PREVIEW_OPERATION,
        user_id=draft.user_id,
        entity_type=MENU_ENTITY_TYPE,
        entity_id=command.menu_id,
        expected_version=command.expected_version,
        draft_version=command.draft_version,
        committed_relevant_payload=_committed_relevant_menu_payload(
            draft,
            command.menu_id,
        ),
        changes=[_user_facing_summary(draft, command.menu_id)],
    )
    return MenuPreviewResult(
        preview=build_operation_preview(preview_input),
        errors=(),
    )


def _committed_relevant_menu_payload(draft: MenuDraft, menu_id: str) -> JsonObject:
    return {
        "schema_version": draft.schema_version,
        "user_id": draft.user_id,
        "menu_id": menu_id,
        "source_draft_id": draft.draft_id,
        "planning_context_id": draft.planning_context_id,
        "period_start": draft.period_start,
        "period_end": draft.period_end,
        "meal_slots": cast(JsonValue, draft.meal_slots),
        "generated_items": cast(JsonValue, draft.generated_items),
    }


def _user_facing_summary(draft: MenuDraft, menu_id: str) -> JsonObject:
    return {
        "kind": "menu_preview",
        "summary": (
            f"Create preview for {draft.period_start} menu "
            f"with {len(draft.generated_items)} meal item(s)"
        ),
        "menu_id": menu_id,
        "draft_id": draft.draft_id,
        "period_start": draft.period_start,
        "period_end": draft.period_end,
        "meal_count": len(draft.generated_items),
    }
