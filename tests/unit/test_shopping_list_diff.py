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
from menu_planner.application.shopping_list_diff import (
    CreateShoppingListDiffCommand,
    create_shopping_list_diff,
)
from menu_planner.application.shopping_list_generation import (
    BuildShoppingListVersionCommand,
    RecipeVersionRef,
)
from menu_planner.domain.contracts.models import JsonObject, NormalizedIngredient
from menu_planner.domain.errors import ErrorCode

ROOT = pathlib.Path(__file__).resolve().parents[2]
SNAPSHOT_PATH = (
    ROOT / "fixtures" / "golden" / "m7_shopping_list" / "mock_catalog"
    / "snapshot.v1.json"
)


class ShoppingListDiffTests(unittest.TestCase):
    def test_one_slot_replacement_produces_deterministic_diff(self) -> None:
        first = create_shopping_list_diff(_diff_command())
        second = create_shopping_list_diff(_diff_command())

        self.assertTrue(first.ok, first.errors)
        self.assertTrue(second.ok, second.errors)
        self.assertEqual(first.diff, second.diff)
        assert first.diff is not None
        self.assertEqual(first.diff["replacement_id"], "replacement_001")
        self.assertEqual(first.diff["source_menu_version"], 1)
        self.assertEqual(first.diff["replacement_menu_version"], 2)
        self.assertEqual(first.diff["target_meal_slot_id"], "slot_002")

    def test_diff_contains_added_removed_and_changed_quantities(self) -> None:
        result = create_shopping_list_diff(_diff_command())

        self.assertTrue(result.ok, result.errors)
        assert result.diff is not None
        changes = cast(list[JsonObject], result.diff["changes"])
        self.assertEqual(
            [(change["kind"], change["diff_key"]) for change in changes],
            [
                ("added", "ingredient.egg|product.egg.12|piece"),
                ("quantity_changed", "ingredient.milk|product.milk.1l|ml"),
                ("removed", "ingredient.tomato|product.tomato.500g|g"),
            ],
        )
        milk_change = changes[1]
        self.assertEqual(milk_change["old_quantity"], 1000.0)
        self.assertEqual(milk_change["new_quantity"], 2000.0)
        self.assertEqual(milk_change["quantity_delta"], 1000.0)

    def test_unaffected_items_remain_unchanged(self) -> None:
        result = create_shopping_list_diff(
            _diff_command(
                old_ingredients=(
                    ingredient("ingredient.tomato", 750, "g", "mass"),
                    ingredient("ingredient.milk", 1, "l", "volume"),
                ),
                new_ingredients=(
                    ingredient("ingredient.tomato", 250, "g", "mass"),
                    ingredient("ingredient.milk", 1, "l", "volume"),
                ),
            )
        )

        self.assertTrue(result.ok, result.errors)
        assert result.diff is not None
        unaffected = cast(list[JsonObject], result.diff["unaffected_items"])
        self.assertEqual(len(unaffected), 1)
        self.assertEqual(unaffected[0]["ingredient_id"], "ingredient.milk")
        self.assertEqual(unaffected[0]["quantity"], 1000.0)

    def test_diff_links_to_menu_recipe_and_catalog_sources(self) -> None:
        result = create_shopping_list_diff(_diff_command())

        self.assertTrue(result.ok, result.errors)
        assert result.diff is not None
        self.assertEqual(result.diff["source_menu_id"], "menu_001")
        self.assertEqual(result.diff["old_recipe_version_refs"], _recipe_refs(1))
        self.assertEqual(result.diff["new_recipe_version_refs"], _recipe_refs(2))
        self.assertEqual(
            result.diff["catalog_snapshot_id"],
            "mock_catalog_snapshot_001",
        )
        self.assertEqual(result.diff["catalog_snapshot_version"], 1)
        self.assertIsNotNone(result.diff["old_source_hash"])
        self.assertIsNotNone(result.diff["new_source_hash"])
        self.assertNotEqual(
            result.diff["old_source_hash"],
            result.diff["new_source_hash"],
        )

    def test_generation_failure_leaves_state_unchanged(self) -> None:
        result = create_shopping_list_diff(
            _diff_command(
                new_ingredients=(
                    ingredient("ingredient.saffron", 1, "g", "mass"),
                )
            )
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.diff)
        self.assertEqual(result.errors[0].code, ErrorCode.SHOPPING_PRODUCT_NOT_FOUND)
        self.assertFalse(result.side_effects_executed)
        self.assertFalse(result.confirmed_menu_changed)
        self.assertFalse(result.recipe_state_changed)
        self.assertFalse(result.shopping_list_state_changed)


def _diff_command(
    *,
    old_ingredients: tuple[NormalizedIngredient, ...] | None = None,
    new_ingredients: tuple[NormalizedIngredient, ...] | None = None,
) -> CreateShoppingListDiffCommand:
    snapshot = _snapshot()
    return CreateShoppingListDiffCommand(
        replacement_id="replacement_001",
        user_id="user_001",
        source_menu_id="menu_001",
        source_menu_version=1,
        replacement_menu_version=2,
        target_meal_slot_id="slot_002",
        old_shopping_list_command=_shopping_command(
            shopping_list_id="shopping_list_old",
            menu_version=1,
            recipe_version=1,
            catalog_snapshot=snapshot,
            ingredients=old_ingredients
            if old_ingredients is not None
            else (
                ingredient("ingredient.tomato", 750, "g", "mass"),
                ingredient("ingredient.milk", 1, "l", "volume"),
            ),
        ),
        new_shopping_list_command=_shopping_command(
            shopping_list_id="shopping_list_new",
            menu_version=2,
            recipe_version=2,
            catalog_snapshot=snapshot,
            ingredients=new_ingredients
            if new_ingredients is not None
            else (
                ingredient("ingredient.milk", 2, "l", "volume"),
                ingredient("ingredient.egg", 6, "piece", "count"),
            ),
        ),
    )


def _shopping_command(
    *,
    shopping_list_id: str,
    menu_version: int,
    recipe_version: int,
    catalog_snapshot: CatalogSnapshot,
    ingredients: tuple[NormalizedIngredient, ...],
) -> BuildShoppingListVersionCommand:
    return BuildShoppingListVersionCommand(
        user_id="user_001",
        shopping_list_id=shopping_list_id,
        version=menu_version,
        source_menu_id="menu_001",
        source_menu_version=menu_version,
        recipe_version_refs=(RecipeVersionRef("recipe_slot_002", recipe_version),),
        catalog_snapshot=catalog_snapshot,
        ingredients=ingredients,
        target_portions=2,
        recipe_portions=2,
    )


def _recipe_refs(version: int) -> list[JsonObject]:
    return [cast(JsonObject, {"recipe_id": "recipe_slot_002", "version": version})]


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
