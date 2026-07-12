from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import cast

from menu_planner.domain.contracts.models import (
    JsonObject,
    ShoppingListVersion,
)
from menu_planner.domain.errors import (
    DomainError,
    shopping_item_match_ambiguous,
    shopping_item_not_found,
    shopping_list_stale,
)

CHECKLIST_STATUS_PENDING = "pending"
CHECKLIST_STATUS_COMPLETED = "completed"
SUPPORTED_CHECKLIST_STATUSES = frozenset(
    {CHECKLIST_STATUS_PENDING, CHECKLIST_STATUS_COMPLETED}
)


@dataclass(frozen=True)
class UpdateChecklistItemCommand:
    shopping_list: ShoppingListVersion
    expected_version: int
    expected_source_hash: str
    shopping_item_id: str
    status: str
    audit_event_id: str
    actor_id: str
    occurred_at: str


@dataclass(frozen=True)
class UpdateChecklistItemByTextCommand:
    shopping_list: ShoppingListVersion
    expected_version: int
    expected_source_hash: str
    text: str
    status: str
    audit_event_id: str
    actor_id: str
    occurred_at: str


@dataclass(frozen=True)
class ChecklistItemUpdateResult:
    shopping_list: ShoppingListVersion | None
    audit_metadata: JsonObject | None = None
    errors: tuple[DomainError, ...] = ()
    disambiguation_candidates: tuple[JsonObject, ...] = ()
    side_effects_executed: bool = False

    @property
    def ok(self) -> bool:
        return self.shopping_list is not None and not self.errors


def update_checklist_item_status(
    command: UpdateChecklistItemCommand,
) -> ChecklistItemUpdateResult:
    source_hash = _source_hash(command.shopping_list)
    if (
        command.shopping_list.version != command.expected_version
        or source_hash != command.expected_source_hash
    ):
        return ChecklistItemUpdateResult(
            shopping_list=None,
            errors=(
                shopping_list_stale(
                    command.shopping_list.shopping_list_id,
                    command.expected_version,
                    command.shopping_list.version,
                    command.expected_source_hash,
                    source_hash,
                ),
            ),
        )

    updated_items = [
        copy.deepcopy(item) for item in command.shopping_list.generated_items
    ]
    target_index = _find_item_index(updated_items, command.shopping_item_id)
    if target_index is None:
        return ChecklistItemUpdateResult(
            shopping_list=None,
            errors=(
                shopping_item_not_found(
                    command.shopping_list.shopping_list_id,
                    command.shopping_item_id,
                    command.shopping_list.version,
                ),
            ),
        )

    previous_status = _item_status(updated_items[target_index])
    if previous_status != command.status:
        updated_items[target_index]["checklist_status"] = command.status
        updated_items[target_index]["checklist_updated_at"] = command.occurred_at

    updated = ShoppingListVersion(
        schema_version=command.shopping_list.schema_version,
        user_id=command.shopping_list.user_id,
        shopping_list_id=command.shopping_list.shopping_list_id,
        version=command.shopping_list.version,
        source_menu_id=command.shopping_list.source_menu_id,
        source_menu_version=command.shopping_list.source_menu_version,
        recipe_version_refs=copy.deepcopy(command.shopping_list.recipe_version_refs),
        catalog_snapshot_id=command.shopping_list.catalog_snapshot_id,
        catalog_snapshot_version=command.shopping_list.catalog_snapshot_version,
        generated_items=cast(list[JsonObject], updated_items),
        calculation_metadata=copy.deepcopy(command.shopping_list.calculation_metadata),
    )
    audit_metadata: JsonObject = {
        "operation": "shopping_checklist_item_update",
        "audit_event_id": command.audit_event_id,
        "actor_id": command.actor_id,
        "shopping_list_id": command.shopping_list.shopping_list_id,
        "shopping_list_version": command.shopping_list.version,
        "shopping_item_id": command.shopping_item_id,
        "previous_status": previous_status,
        "new_status": command.status,
        "idempotent": previous_status == command.status,
        "source_hash": source_hash,
        "occurred_at": command.occurred_at,
    }
    return ChecklistItemUpdateResult(
        shopping_list=updated,
        audit_metadata=audit_metadata,
        side_effects_executed=previous_status != command.status,
    )


def update_checklist_item_status_by_text(
    command: UpdateChecklistItemByTextCommand,
) -> ChecklistItemUpdateResult:
    source_hash = _source_hash(command.shopping_list)
    if (
        command.shopping_list.version != command.expected_version
        or source_hash != command.expected_source_hash
    ):
        return ChecklistItemUpdateResult(
            shopping_list=None,
            errors=(
                shopping_list_stale(
                    command.shopping_list.shopping_list_id,
                    command.expected_version,
                    command.shopping_list.version,
                    command.expected_source_hash,
                    source_hash,
                ),
            ),
        )

    matches = _matching_items(command.shopping_list.generated_items, command.text)
    if not matches:
        return ChecklistItemUpdateResult(
            shopping_list=None,
            errors=(
                shopping_item_not_found(
                    command.shopping_list.shopping_list_id,
                    _normalize_text(command.text),
                    command.shopping_list.version,
                ),
            ),
        )
    if len(matches) > 1:
        candidates = tuple(_candidate(item) for item in matches)
        return ChecklistItemUpdateResult(
            shopping_list=None,
            errors=(
                shopping_item_match_ambiguous(
                    command.text,
                    [
                        str(candidate["shopping_item_id"])
                        for candidate in candidates
                    ],
                ),
            ),
            disambiguation_candidates=candidates,
        )

    return update_checklist_item_status(
        UpdateChecklistItemCommand(
            shopping_list=command.shopping_list,
            expected_version=command.expected_version,
            expected_source_hash=command.expected_source_hash,
            shopping_item_id=str(matches[0]["shopping_item_id"]),
            status=command.status,
            audit_event_id=command.audit_event_id,
            actor_id=command.actor_id,
            occurred_at=command.occurred_at,
        )
    )


def _source_hash(shopping_list: ShoppingListVersion) -> str:
    value = shopping_list.calculation_metadata.get("source_hash")
    return value if isinstance(value, str) else ""


def _find_item_index(items: list[JsonObject], shopping_item_id: str) -> int | None:
    for index, item in enumerate(items):
        if item.get("shopping_item_id") == shopping_item_id:
            return index
    return None


def _item_status(item: JsonObject) -> str:
    value = item.get("checklist_status", CHECKLIST_STATUS_PENDING)
    if isinstance(value, str):
        return value
    return CHECKLIST_STATUS_PENDING


def _matching_items(items: list[JsonObject], text: str) -> list[JsonObject]:
    query_terms = _query_terms(text)
    if not query_terms:
        return []
    return [
        item
        for item in items
        if all(term in _search_text(item) for term in query_terms)
    ]


def _query_terms(text: str) -> tuple[str, ...]:
    normalized = _normalize_text(text)
    stopwords = {"bought", "done", "куплено", "купил", "купила"}
    return tuple(term for term in normalized.split() if term not in stopwords)


def _normalize_text(text: str) -> str:
    return " ".join(text.casefold().replace("_", " ").replace(".", " ").split())


def _search_text(item: JsonObject) -> str:
    values: list[str] = []
    for field_name in (
        "shopping_item_id",
        "ingredient_id",
        "product_id",
        "display_name",
    ):
        value = item.get(field_name)
        if isinstance(value, str):
            values.append(value)
    return _normalize_text(" ".join(values))


def _candidate(item: JsonObject) -> JsonObject:
    return {
        "shopping_item_id": item["shopping_item_id"],
        "ingredient_id": item["ingredient_id"],
        "product_id": item["product_id"],
        "display_name": item.get("display_name", ""),
    }
