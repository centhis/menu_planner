from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from menu_planner.application.menu_preview import MENU_ENTITY_TYPE
from menu_planner.application.safe_commit import (
    AuditEventRecord,
    OperationPreviewInput,
    SafeCommitUnitOfWork,
    VersionedRecord,
    build_operation_preview,
)
from menu_planner.domain.contracts.models import JsonObject, JsonValue, OperationPreview
from menu_planner.domain.errors import (
    DomainError,
    expected_version_mismatch,
    menu_meal_slot_missing,
    menu_replacement_not_local,
)

REPLACE_MEAL_SLOT_OPERATION = "replace_meal_slot"


@dataclass(frozen=True)
class ReplaceMealSlotCommand:
    record_id: str
    audit_event_id: str
    user_id: str
    menu_id: str
    source_version: int
    draft_version: int
    target_meal_slot_id: str
    candidate_menu_payload: JsonObject


@dataclass(frozen=True)
class ReplaceMealSlotResult:
    draft_record: VersionedRecord | None
    errors: tuple[DomainError, ...] = ()
    audit_event: AuditEventRecord | None = None
    side_effects_executed: bool = False
    shopping_list_changed: bool = False

    @property
    def ok(self) -> bool:
        return self.draft_record is not None and not self.errors


@dataclass(frozen=True)
class CreateReplacementDiffCommand:
    preview_id: str
    user_id: str
    menu_id: str
    source_version: int
    draft_version: int
    target_meal_slot_id: str
    source_menu_payload: JsonObject
    replacement_menu_payload: JsonObject
    recipe_version_id: str | None = None


@dataclass(frozen=True)
class ReplacementDiffResult:
    preview: OperationPreview | None
    errors: tuple[DomainError, ...] = ()

    @property
    def ok(self) -> bool:
        return self.preview is not None and not self.errors


class MenuReplacementService:
    def __init__(
        self,
        unit_of_work_factory: Callable[[], SafeCommitUnitOfWork],
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def create_local_replacement_draft(
        self,
        command: ReplaceMealSlotCommand,
    ) -> ReplaceMealSlotResult:
        with self._unit_of_work_factory() as unit_of_work:
            current_record = unit_of_work.versioned_records.get_current_committed(
                command.user_id,
                MENU_ENTITY_TYPE,
                command.menu_id,
            )
            actual_version = (
                current_record.version if current_record is not None else -1
            )
            if actual_version != command.source_version:
                unit_of_work.rollback()
                return ReplaceMealSlotResult(
                    draft_record=None,
                    errors=(
                        expected_version_mismatch(
                            command.menu_id,
                            command.source_version,
                            actual_version,
                        ),
                    ),
                )

            source_record = unit_of_work.versioned_records.get(
                command.user_id,
                MENU_ENTITY_TYPE,
                command.menu_id,
                command.source_version,
                "committed",
            )
            if source_record is None:
                unit_of_work.rollback()
                return ReplaceMealSlotResult(
                    draft_record=None,
                    errors=(
                        expected_version_mismatch(
                            command.menu_id,
                            command.source_version,
                            actual_version,
                        ),
                    ),
                )

            errors = _validate_local_replacement(
                source_payload=source_record.payload,
                candidate_payload=command.candidate_menu_payload,
                target_meal_slot_id=command.target_meal_slot_id,
            )
            if errors:
                unit_of_work.rollback()
                return ReplaceMealSlotResult(draft_record=None, errors=errors)

            draft_payload = cast(
                JsonObject,
                copy.deepcopy(command.candidate_menu_payload),
            )
            draft_record = VersionedRecord(
                record_id=command.record_id,
                user_id=command.user_id,
                entity_type=MENU_ENTITY_TYPE,
                entity_id=command.menu_id,
                version=command.draft_version,
                lifecycle_status="draft",
                payload=draft_payload,
                audit_event_id=command.audit_event_id,
            )
            audit_event = AuditEventRecord(
                audit_event_id=command.audit_event_id,
                user_id=command.user_id,
                operation=REPLACE_MEAL_SLOT_OPERATION,
                entity_type=MENU_ENTITY_TYPE,
                entity_id=command.menu_id,
                result_status="success",
                previous_version=command.source_version,
                new_version=command.draft_version,
                event_metadata={
                    "target_meal_slot_id": command.target_meal_slot_id,
                    "source_record_id": source_record.record_id,
                },
            )

            try:
                unit_of_work.audit_events.add(audit_event)
                unit_of_work.versioned_records.add(draft_record)
                unit_of_work.commit()
            except Exception:
                unit_of_work.rollback()
                raise

            return ReplaceMealSlotResult(
                draft_record=draft_record,
                audit_event=audit_event,
                side_effects_executed=True,
            )


def create_replacement_diff(
    command: CreateReplacementDiffCommand,
) -> ReplacementDiffResult:
    errors = _validate_local_replacement(
        source_payload=command.source_menu_payload,
        candidate_payload=command.replacement_menu_payload,
        target_meal_slot_id=command.target_meal_slot_id,
    )
    if errors:
        return ReplacementDiffResult(preview=None, errors=errors)

    old_item = _generated_items_by_slot_id(command.source_menu_payload)[
        command.target_meal_slot_id
    ]
    new_item = _generated_items_by_slot_id(command.replacement_menu_payload)[
        command.target_meal_slot_id
    ]
    change = _replacement_change_summary(command, old_item, new_item)
    preview_input = OperationPreviewInput(
        preview_id=command.preview_id,
        operation=REPLACE_MEAL_SLOT_OPERATION,
        user_id=command.user_id,
        entity_type=MENU_ENTITY_TYPE,
        entity_id=command.menu_id,
        expected_version=command.source_version,
        draft_version=command.draft_version,
        committed_relevant_payload=_replacement_committed_relevant_payload(
            command,
            old_item,
            new_item,
        ),
        changes=[change],
    )
    return ReplacementDiffResult(
        preview=build_operation_preview(preview_input),
        errors=(),
    )


def _replacement_committed_relevant_payload(
    command: CreateReplacementDiffCommand,
    old_item: JsonObject,
    new_item: JsonObject,
) -> JsonObject:
    return {
        "user_id": command.user_id,
        "menu_id": command.menu_id,
        "source_menu_version": command.source_version,
        "draft_version": command.draft_version,
        "target_meal_slot_id": command.target_meal_slot_id,
        "old_item": cast(JsonValue, old_item),
        "new_item": cast(JsonValue, new_item),
        "recipe_version_impact": command.recipe_version_id or "none",
        "shopping_list_impact": "none",
    }


def _replacement_change_summary(
    command: CreateReplacementDiffCommand,
    old_item: JsonObject,
    new_item: JsonObject,
) -> JsonObject:
    return {
        "kind": "meal_slot_replacement",
        "source_menu_id": command.menu_id,
        "source_menu_version": command.source_version,
        "draft_version": command.draft_version,
        "target_meal_slot_id": command.target_meal_slot_id,
        "old_item": cast(JsonValue, old_item),
        "new_item": cast(JsonValue, new_item),
        "recipe_version_impact": command.recipe_version_id or "none",
        "shopping_list_impact": "none",
        "unaffected_slots": "unchanged",
    }


def _validate_local_replacement(
    *,
    source_payload: JsonObject,
    candidate_payload: JsonObject,
    target_meal_slot_id: str,
) -> tuple[DomainError, ...]:
    source_slots = _meal_slots_by_id(source_payload)
    candidate_slots = _meal_slots_by_id(candidate_payload)
    if target_meal_slot_id not in source_slots:
        return (
            menu_meal_slot_missing(
                [target_meal_slot_id],
                sorted(source_slots),
            ),
        )
    if source_slots != candidate_slots:
        return (
            menu_replacement_not_local(
                target_meal_slot_id,
                _changed_ids(source_slots, candidate_slots),
                "meal_slots_changed",
            ),
        )

    source_items = _generated_items_by_slot_id(source_payload)
    candidate_items = _generated_items_by_slot_id(candidate_payload)
    if target_meal_slot_id not in source_items:
        return (
            menu_meal_slot_missing(
                [target_meal_slot_id],
                sorted(source_items),
            ),
        )
    if set(source_items) != set(candidate_items):
        return (
            menu_replacement_not_local(
                target_meal_slot_id,
                sorted(set(source_items) ^ set(candidate_items)),
                "generated_item_slots_changed",
            ),
        )

    changed_item_ids = _changed_ids(source_items, candidate_items)
    if changed_item_ids != [target_meal_slot_id]:
        return (
            menu_replacement_not_local(
                target_meal_slot_id,
                changed_item_ids,
                "changed_slot_count_or_target_mismatch",
            ),
        )
    return ()


def _meal_slots_by_id(payload: JsonObject) -> dict[str, JsonObject]:
    return _objects_by_key(payload.get("meal_slots"), "slot_id")


def _generated_items_by_slot_id(payload: JsonObject) -> dict[str, JsonObject]:
    return _objects_by_key(payload.get("generated_items"), "meal_slot_id")


def _objects_by_key(value: object, key: str) -> dict[str, JsonObject]:
    if not isinstance(value, list):
        return {}
    objects: dict[str, JsonObject] = {}
    for item in value:
        if not isinstance(item, dict):
            continue
        raw_id = item.get(key)
        if isinstance(raw_id, str):
            objects[raw_id] = cast(JsonObject, copy.deepcopy(item))
    return objects


def _changed_ids(
    source: dict[str, JsonObject],
    candidate: dict[str, JsonObject],
) -> list[str]:
    ids = set(source) | set(candidate)
    return sorted(
        item_id for item_id in ids if source.get(item_id) != candidate.get(item_id)
    )
