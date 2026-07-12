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
from menu_planner.application.shopping_list_generation import (
    BuildShoppingListVersionCommand,
    RecipeVersionRef,
    build_shopping_list_version,
)
from menu_planner.domain.contracts.models import JsonObject, NormalizedIngredient
from menu_planner.domain.errors import ErrorCode

ROOT = pathlib.Path(__file__).resolve().parents[2]
SNAPSHOT_PATH = (
    ROOT / "fixtures" / "golden" / "m7_shopping_list" / "mock_catalog"
    / "snapshot.v1.json"
)


class ShoppingListGenerationTests(unittest.TestCase):
    def test_same_sources_create_same_shopping_list_version(self) -> None:
        first = build_shopping_list_version(_command())
        second = build_shopping_list_version(_command())

        self.assertTrue(first.ok, first.errors)
        self.assertTrue(second.ok, second.errors)
        self.assertEqual(first.shopping_list_version, second.shopping_list_version)
        self.assertEqual(first.source_hash, second.source_hash)
        assert first.shopping_list_version is not None
        self.assertEqual(first.shopping_list_version.source_menu_version, 1)
        self.assertEqual(
            first.shopping_list_version.catalog_snapshot_id,
            "mock_catalog_snapshot_001",
        )
        self.assertEqual(len(first.shopping_list_version.generated_items), 2)
        self.assertFalse(first.side_effects_executed)
        self.assertFalse(first.confirmed_menu_changed)
        self.assertFalse(first.recipe_state_changed)

    def test_changed_recipe_version_changes_source_hash(self) -> None:
        base = build_shopping_list_version(_command())
        changed = build_shopping_list_version(
            _command(recipe_refs=(RecipeVersionRef("recipe_001", 2),))
        )

        self.assertTrue(base.ok, base.errors)
        self.assertTrue(changed.ok, changed.errors)
        self.assertNotEqual(base.source_hash, changed.source_hash)

    def test_changed_menu_version_changes_source_hash(self) -> None:
        base = build_shopping_list_version(_command())
        changed = build_shopping_list_version(_command(source_menu_version=2))

        self.assertTrue(base.ok, base.errors)
        self.assertTrue(changed.ok, changed.errors)
        self.assertNotEqual(base.source_hash, changed.source_hash)

    def test_changed_catalog_snapshot_version_changes_source_hash(self) -> None:
        base = build_shopping_list_version(_command())
        snapshot = _snapshot_payload()
        snapshot["snapshot_version"] = 2
        changed = build_shopping_list_version(
            _command(catalog_snapshot=_snapshot(snapshot))
        )

        self.assertTrue(base.ok, base.errors)
        self.assertTrue(changed.ok, changed.errors)
        self.assertNotEqual(base.source_hash, changed.source_hash)

    def test_unmatched_ingredient_fails_without_state_changes(self) -> None:
        result = build_shopping_list_version(
            _command(
                ingredients=(ingredient("ingredient.saffron", 1, "g", "mass"),)
            )
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.shopping_list_version)
        self.assertEqual(result.errors[0].code, ErrorCode.SHOPPING_PRODUCT_NOT_FOUND)
        self.assertFalse(result.side_effects_executed)
        self.assertFalse(result.confirmed_menu_changed)
        self.assertFalse(result.recipe_state_changed)

    def test_input_snapshot_payload_is_not_mutated(self) -> None:
        payload = _snapshot_payload()
        before = copy.deepcopy(payload)

        result = build_shopping_list_version(
            _command(catalog_snapshot=_snapshot(payload))
        )

        self.assertTrue(result.ok, result.errors)
        self.assertEqual(payload, before)


def _command(
    *,
    recipe_refs: tuple[RecipeVersionRef, ...] = (
        RecipeVersionRef("recipe_001", 1),
    ),
    source_menu_version: int = 1,
    catalog_snapshot: CatalogSnapshot | None = None,
    ingredients: tuple[NormalizedIngredient, ...] | None = None,
) -> BuildShoppingListVersionCommand:
    selected_snapshot = (
        catalog_snapshot if catalog_snapshot is not None else _snapshot()
    )
    return BuildShoppingListVersionCommand(
        user_id="user_001",
        shopping_list_id="shopping_list_001",
        version=1,
        source_menu_id="menu_001",
        source_menu_version=source_menu_version,
        recipe_version_refs=recipe_refs,
        catalog_snapshot=selected_snapshot,
        ingredients=ingredients
        if ingredients is not None
        else (
            ingredient("ingredient.tomato", 750, "g", "mass"),
            ingredient("ingredient.milk", 1, "l", "volume"),
        ),
        target_portions=2,
        recipe_portions=2,
    )


def _snapshot(payload: JsonObject | None = None) -> CatalogSnapshot:
    return MockStoreCatalogProvider(
        payload if payload is not None else _snapshot_payload()
    ).get_snapshot("mock_catalog_snapshot_001")


def _snapshot_payload() -> JsonObject:
    return cast(
        JsonObject,
        copy.deepcopy(json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))),
    )


if __name__ == "__main__":
    unittest.main()
