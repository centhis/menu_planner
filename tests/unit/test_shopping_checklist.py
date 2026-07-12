from __future__ import annotations

import copy
import json
import pathlib
import unittest
from typing import cast

from menu_planner.application.shopping_calculation import ingredient
from menu_planner.application.shopping_catalog import (
    CatalogSnapshot,
    MockStoreCatalogProvider,
)
from menu_planner.application.shopping_checklist import (
    UpdateChecklistItemByTextCommand,
    UpdateChecklistItemCommand,
    update_checklist_item_status,
    update_checklist_item_status_by_text,
)
from menu_planner.application.shopping_list_generation import (
    BuildShoppingListVersionCommand,
    RecipeVersionRef,
    build_shopping_list_version,
)
from menu_planner.domain.contracts.models import JsonObject, ShoppingListVersion
from menu_planner.domain.errors import ErrorCode

ROOT = pathlib.Path(__file__).resolve().parents[2]
SNAPSHOT_PATH = (
    ROOT / "fixtures" / "golden" / "m7_shopping_list" / "mock_catalog"
    / "snapshot.v1.json"
)


class ShoppingChecklistTests(unittest.TestCase):
    def test_status_update_by_exact_item_id_changes_only_target_item(self) -> None:
        shopping_list, source_hash = _shopping_list()
        before = copy.deepcopy(shopping_list)

        result = update_checklist_item_status(
            _command(shopping_list, source_hash, "shopping_list_001:item:001")
        )

        self.assertTrue(result.ok, result.errors)
        assert result.shopping_list is not None
        self.assertEqual(
            before.generated_items[1],
            result.shopping_list.generated_items[1],
        )
        self.assertEqual(
            result.shopping_list.generated_items[0]["checklist_status"],
            "completed",
        )
        self.assertEqual(
            result.shopping_list.generated_items[0]["checklist_updated_at"],
            "2026-07-11T10:00:00Z",
        )
        self.assertEqual(before.generated_items[0].get("checklist_status"), None)
        self.assertTrue(result.side_effects_executed)

    def test_repeating_same_status_update_is_idempotent(self) -> None:
        shopping_list, source_hash = _shopping_list()
        first = update_checklist_item_status(
            _command(shopping_list, source_hash, "shopping_list_001:item:001")
        )
        assert first.shopping_list is not None
        first_items = copy.deepcopy(first.shopping_list.generated_items)

        second = update_checklist_item_status(
            _command(
                first.shopping_list,
                source_hash,
                "shopping_list_001:item:001",
                occurred_at="2026-07-11T10:05:00Z",
            )
        )

        self.assertTrue(second.ok, second.errors)
        assert second.shopping_list is not None
        self.assertEqual(second.shopping_list.generated_items, first_items)
        self.assertFalse(second.side_effects_executed)
        assert second.audit_metadata is not None
        self.assertTrue(second.audit_metadata["idempotent"])

    def test_missing_item_is_rejected_deterministically(self) -> None:
        shopping_list, source_hash = _shopping_list()

        result = update_checklist_item_status(
            _command(shopping_list, source_hash, "shopping_list_001:item:999")
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.shopping_list)
        self.assertEqual(result.errors[0].code, ErrorCode.SHOPPING_ITEM_NOT_FOUND)
        self.assertFalse(result.side_effects_executed)

    def test_stale_version_is_rejected_deterministically(self) -> None:
        shopping_list, source_hash = _shopping_list()

        result = update_checklist_item_status(
            _command(
                shopping_list,
                source_hash,
                "shopping_list_001:item:001",
                expected_version=0,
            )
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.shopping_list)
        self.assertEqual(result.errors[0].code, ErrorCode.SHOPPING_LIST_STALE)
        self.assertFalse(result.side_effects_executed)

    def test_stale_source_hash_is_rejected_deterministically(self) -> None:
        shopping_list, source_hash = _shopping_list()

        result = update_checklist_item_status(
            _command(
                shopping_list,
                f"{source_hash}.stale",
                "shopping_list_001:item:001",
            )
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.shopping_list)
        self.assertEqual(result.errors[0].code, ErrorCode.SHOPPING_LIST_STALE)
        self.assertFalse(result.side_effects_executed)

    def test_audit_metadata_has_no_item_payload_or_private_data(self) -> None:
        shopping_list, source_hash = _shopping_list()

        result = update_checklist_item_status(
            _command(shopping_list, source_hash, "shopping_list_001:item:001")
        )

        self.assertTrue(result.ok, result.errors)
        assert result.audit_metadata is not None
        self.assertEqual(
            set(result.audit_metadata),
            {
                "operation",
                "audit_event_id",
                "actor_id",
                "shopping_list_id",
                "shopping_list_version",
                "shopping_item_id",
                "previous_status",
                "new_status",
                "idempotent",
                "source_hash",
                "occurred_at",
            },
        )

    def test_one_match_text_update_changes_resolved_item(self) -> None:
        shopping_list, source_hash = _shopping_list()
        shopping_list = _with_item_display_name(
            shopping_list,
            "shopping_list_001:item:001",
            "молоко",
        )

        result = update_checklist_item_status_by_text(
            _text_command(shopping_list, source_hash, "молоко куплено")
        )

        self.assertTrue(result.ok, result.errors)
        assert result.shopping_list is not None
        self.assertEqual(
            result.shopping_list.generated_items[0]["checklist_status"],
            "completed",
        )
        self.assertNotIn("checklist_status", result.shopping_list.generated_items[1])
        self.assertEqual(result.disambiguation_candidates, ())

    def test_multiple_text_matches_require_disambiguation(self) -> None:
        shopping_list, source_hash = _shopping_list_with_second_milk_item()
        before = copy.deepcopy(shopping_list.generated_items)

        result = update_checklist_item_status_by_text(
            _text_command(shopping_list, source_hash, "milk bought")
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.shopping_list)
        self.assertEqual(
            result.errors[0].code,
            ErrorCode.SHOPPING_ITEM_MATCH_AMBIGUOUS,
        )
        self.assertEqual(
            [
                candidate["shopping_item_id"]
                for candidate in result.disambiguation_candidates
            ],
            ["shopping_list_001:item:001", "shopping_list_001:item:003"],
        )
        self.assertEqual(shopping_list.generated_items, before)
        self.assertFalse(result.side_effects_executed)

    def test_no_text_match_returns_controlled_error(self) -> None:
        shopping_list, source_hash = _shopping_list()

        result = update_checklist_item_status_by_text(
            _text_command(shopping_list, source_hash, "saffron bought")
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.shopping_list)
        self.assertEqual(result.errors[0].code, ErrorCode.SHOPPING_ITEM_NOT_FOUND)
        self.assertEqual(result.disambiguation_candidates, ())
        self.assertFalse(result.side_effects_executed)


def _command(
    shopping_list: ShoppingListVersion,
    source_hash: str,
    shopping_item_id: str,
    *,
    expected_version: int | None = None,
    occurred_at: str = "2026-07-11T10:00:00Z",
) -> UpdateChecklistItemCommand:
    return UpdateChecklistItemCommand(
        shopping_list=shopping_list,
        expected_version=expected_version
        if expected_version is not None
        else shopping_list.version,
        expected_source_hash=source_hash,
        shopping_item_id=shopping_item_id,
        status="completed",
        audit_event_id="shopping_audit_001",
        actor_id="user_001",
        occurred_at=occurred_at,
    )


def _text_command(
    shopping_list: ShoppingListVersion,
    source_hash: str,
    text: str,
) -> UpdateChecklistItemByTextCommand:
    return UpdateChecklistItemByTextCommand(
        shopping_list=shopping_list,
        expected_version=shopping_list.version,
        expected_source_hash=source_hash,
        text=text,
        status="completed",
        audit_event_id="shopping_audit_text_001",
        actor_id="user_001",
        occurred_at="2026-07-11T10:00:00Z",
    )


def _shopping_list() -> tuple[ShoppingListVersion, str]:
    result = build_shopping_list_version(
        BuildShoppingListVersionCommand(
            user_id="user_001",
            shopping_list_id="shopping_list_001",
            version=1,
            source_menu_id="menu_001",
            source_menu_version=1,
            recipe_version_refs=(RecipeVersionRef("recipe_001", 1),),
            catalog_snapshot=_snapshot(),
            ingredients=(
                ingredient("ingredient.tomato", 750, "g", "mass"),
                ingredient("ingredient.milk", 1, "l", "volume"),
            ),
            target_portions=2,
            recipe_portions=2,
        )
    )
    assert result.shopping_list_version is not None
    assert result.source_hash is not None
    return result.shopping_list_version, result.source_hash


def _shopping_list_with_second_milk_item() -> tuple[ShoppingListVersion, str]:
    shopping_list, source_hash = _shopping_list()
    items = copy.deepcopy(shopping_list.generated_items)
    second_milk = copy.deepcopy(items[1])
    second_milk["shopping_item_id"] = "shopping_list_001:item:003"
    second_milk["ingredient_id"] = "ingredient.milk.alt"
    second_milk["display_name"] = "milk for coffee"
    items.append(second_milk)
    return _with_generated_items(shopping_list, items), source_hash


def _with_item_display_name(
    shopping_list: ShoppingListVersion,
    shopping_item_id: str,
    display_name: str,
) -> ShoppingListVersion:
    items = copy.deepcopy(shopping_list.generated_items)
    for item in items:
        if item["shopping_item_id"] == shopping_item_id:
            item["display_name"] = display_name
    return _with_generated_items(shopping_list, items)


def _with_generated_items(
    shopping_list: ShoppingListVersion,
    generated_items: list[JsonObject],
) -> ShoppingListVersion:
    return ShoppingListVersion(
        schema_version=shopping_list.schema_version,
        user_id=shopping_list.user_id,
        shopping_list_id=shopping_list.shopping_list_id,
        version=shopping_list.version,
        source_menu_id=shopping_list.source_menu_id,
        source_menu_version=shopping_list.source_menu_version,
        recipe_version_refs=copy.deepcopy(shopping_list.recipe_version_refs),
        catalog_snapshot_id=shopping_list.catalog_snapshot_id,
        catalog_snapshot_version=shopping_list.catalog_snapshot_version,
        generated_items=generated_items,
        calculation_metadata=copy.deepcopy(shopping_list.calculation_metadata),
    )


def _snapshot() -> CatalogSnapshot:
    return MockStoreCatalogProvider(_snapshot_payload()).get_snapshot(
        "mock_catalog_snapshot_001"
    )


def _snapshot_payload() -> JsonObject:
    return cast(
        JsonObject,
        copy.deepcopy(json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))),
    )


if __name__ == "__main__":
    unittest.main()
