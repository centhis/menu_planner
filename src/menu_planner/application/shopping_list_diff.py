from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from menu_planner.application.shopping_list_generation import (
    BuildShoppingListVersionCommand,
    build_shopping_list_version,
)
from menu_planner.domain.contracts.models import JsonObject, JsonValue
from menu_planner.domain.errors import DomainError


@dataclass(frozen=True)
class CreateShoppingListDiffCommand:
    replacement_id: str
    user_id: str
    source_menu_id: str
    source_menu_version: int
    replacement_menu_version: int
    target_meal_slot_id: str
    old_shopping_list_command: BuildShoppingListVersionCommand
    new_shopping_list_command: BuildShoppingListVersionCommand


@dataclass(frozen=True)
class ShoppingListDiffResult:
    diff: JsonObject | None
    errors: tuple[DomainError, ...] = ()
    side_effects_executed: bool = False
    confirmed_menu_changed: bool = False
    recipe_state_changed: bool = False
    shopping_list_state_changed: bool = False

    @property
    def ok(self) -> bool:
        return self.diff is not None and not self.errors


def create_shopping_list_diff(
    command: CreateShoppingListDiffCommand,
) -> ShoppingListDiffResult:
    old_result = build_shopping_list_version(command.old_shopping_list_command)
    if not old_result.ok or old_result.shopping_list_version is None:
        return ShoppingListDiffResult(diff=None, errors=old_result.errors)

    new_result = build_shopping_list_version(command.new_shopping_list_command)
    if not new_result.ok or new_result.shopping_list_version is None:
        return ShoppingListDiffResult(diff=None, errors=new_result.errors)

    old_items = _items_by_diff_key(old_result.shopping_list_version.generated_items)
    new_items = _items_by_diff_key(new_result.shopping_list_version.generated_items)
    changes = _item_changes(old_items, new_items)

    return ShoppingListDiffResult(
        diff={
            "kind": "shopping_list_replacement_diff",
            "replacement_id": command.replacement_id,
            "user_id": command.user_id,
            "source_menu_id": command.source_menu_id,
            "source_menu_version": command.source_menu_version,
            "replacement_menu_version": command.replacement_menu_version,
            "target_meal_slot_id": command.target_meal_slot_id,
            "old_shopping_list_id": (
                old_result.shopping_list_version.shopping_list_id
            ),
            "old_shopping_list_version": old_result.shopping_list_version.version,
            "old_source_hash": old_result.source_hash,
            "new_shopping_list_id": (
                new_result.shopping_list_version.shopping_list_id
            ),
            "new_shopping_list_version": new_result.shopping_list_version.version,
            "new_source_hash": new_result.source_hash,
            "old_recipe_version_refs": cast(
                JsonValue,
                old_result.shopping_list_version.recipe_version_refs,
            ),
            "new_recipe_version_refs": cast(
                JsonValue,
                new_result.shopping_list_version.recipe_version_refs,
            ),
            "catalog_snapshot_id": (
                new_result.shopping_list_version.catalog_snapshot_id
            ),
            "catalog_snapshot_version": (
                new_result.shopping_list_version.catalog_snapshot_version
            ),
            "changes": cast(JsonValue, changes),
            "unaffected_items": cast(
                JsonValue,
                _unaffected_items(old_items, new_items),
            ),
        },
    )


def _items_by_diff_key(items: list[JsonObject]) -> dict[str, JsonObject]:
    return {_diff_key(item): item for item in items}


def _diff_key(item: JsonObject) -> str:
    return "|".join(
        (
            str(item["ingredient_id"]),
            str(item["product_id"]),
            str(item["unit"]),
        )
    )


def _item_changes(
    old_items: dict[str, JsonObject],
    new_items: dict[str, JsonObject],
) -> list[JsonObject]:
    changes: list[JsonObject] = []
    for key in sorted(set(old_items) | set(new_items)):
        old_item = old_items.get(key)
        new_item = new_items.get(key)
        if old_item == new_item:
            continue
        if old_item is None and new_item is not None:
            changes.append(_added_change(key, new_item))
            continue
        if new_item is None and old_item is not None:
            changes.append(_removed_change(key, old_item))
            continue
        if old_item is not None and new_item is not None:
            if _relevant_item(old_item) == _relevant_item(new_item):
                continue
            changes.append(_quantity_changed_change(key, old_item, new_item))
    return changes


def _added_change(key: str, new_item: JsonObject) -> JsonObject:
    return {
        "kind": "added",
        "diff_key": key,
        "new_item": cast(JsonValue, new_item),
    }


def _removed_change(key: str, old_item: JsonObject) -> JsonObject:
    return {
        "kind": "removed",
        "diff_key": key,
        "old_item": cast(JsonValue, old_item),
    }


def _quantity_changed_change(
    key: str,
    old_item: JsonObject,
    new_item: JsonObject,
) -> JsonObject:
    return {
        "kind": "quantity_changed",
        "diff_key": key,
        "old_item": cast(JsonValue, old_item),
        "new_item": cast(JsonValue, new_item),
        "old_quantity": old_item["quantity"],
        "new_quantity": new_item["quantity"],
        "quantity_delta": round(
            _item_quantity(new_item) - _item_quantity(old_item),
            6,
        ),
        "old_package_count": old_item["package_count"],
        "new_package_count": new_item["package_count"],
    }


def _unaffected_items(
    old_items: dict[str, JsonObject],
    new_items: dict[str, JsonObject],
) -> list[JsonObject]:
    return [
        old_items[key]
        for key in sorted(set(old_items) & set(new_items))
        if _relevant_item(old_items[key]) == _relevant_item(new_items[key])
    ]


def _relevant_item(item: JsonObject) -> JsonObject:
    return {
        key: value
        for key, value in item.items()
        if key != "shopping_item_id"
    }


def _item_quantity(item: JsonObject) -> float:
    value = item["quantity"]
    if isinstance(value, bool):
        return 0
    if isinstance(value, int | float):
        return float(value)
    return 0
