from __future__ import annotations

import itertools
import unittest

from menu_planner.application.shopping_calculation import (
    convert_to_canonical,
    ingredient,
    merge_ingredients,
    normalize_ingredients,
    scale_ingredient,
)
from menu_planner.domain.errors import ErrorCode


class ShoppingCalculationTests(unittest.TestCase):
    def test_scale_ingredient_by_portions(self) -> None:
        result = scale_ingredient(
            ingredient("ingredient.tomato", 250, "g", "mass"),
            target_portions=4,
            recipe_portions=2,
        )

        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.ingredients[0].quantity, 500)
        self.assertEqual(result.ingredients[0].unit, "g")

    def test_convert_to_canonical_unit(self) -> None:
        result = convert_to_canonical(
            ingredient("ingredient.tomato", 1.5, "kg", "mass")
        )

        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.ingredients[0].quantity, 1500)
        self.assertEqual(result.ingredients[0].unit, "g")

    def test_merge_converts_and_sorts_same_ingredient(self) -> None:
        result = merge_ingredients(
            (
                ingredient(
                    "ingredient.tomato",
                    250,
                    "g",
                    "mass",
                    display_name="Tomato",
                ),
                ingredient("ingredient.milk", 1, "l", "volume", display_name="Milk"),
                ingredient(
                    "ingredient.tomato",
                    0.5,
                    "kg",
                    "mass",
                    display_name="Tomato",
                ),
            )
        )

        self.assertTrue(result.ok, result.errors)
        self.assertEqual(
            [
                (item.ingredient_id, item.quantity, item.unit)
                for item in result.ingredients
            ],
            [
                ("ingredient.milk", 1000, "ml"),
                ("ingredient.tomato", 750, "g"),
            ],
        )

    def test_normalize_scales_converts_and_merges(self) -> None:
        result = normalize_ingredients(
            (
                ingredient("ingredient.tomato", 250, "g", "mass"),
                ingredient("ingredient.tomato", 0.25, "kg", "mass"),
            ),
            target_portions=4,
            recipe_portions=2,
        )

        self.assertTrue(result.ok, result.errors)
        self.assertEqual(result.ingredients[0].quantity, 1000)
        self.assertEqual(result.ingredients[0].unit, "g")

    def test_unknown_unit_returns_controlled_error(self) -> None:
        result = convert_to_canonical(
            ingredient("ingredient.tomato", 8, "oz", "mass")
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, ErrorCode.SHOPPING_UNKNOWN_UNIT)
        self.assertEqual(result.errors[0].path, ("unit",))

    def test_incompatible_dimension_is_rejected(self) -> None:
        result = convert_to_canonical(
            ingredient("ingredient.tomato", 250, "g", "volume")
        )

        self.assertFalse(result.ok)
        self.assertEqual(
            result.errors[0].code,
            ErrorCode.SHOPPING_UNSUPPORTED_DIMENSION,
        )
        self.assertEqual(result.errors[0].path, ("dimension",))

    def test_invalid_portions_are_rejected(self) -> None:
        result = scale_ingredient(
            ingredient("ingredient.tomato", 250, "g", "mass"),
            target_portions=0,
            recipe_portions=2,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.errors[0].code, ErrorCode.INVALID_RANGE)
        self.assertEqual(result.errors[0].path, ("target_portions",))

    def test_merge_order_is_stable_for_permutations(self) -> None:
        ingredients = (
            ingredient("ingredient.tomato", 250, "g", "mass"),
            ingredient("ingredient.milk", 1, "l", "volume"),
            ingredient("ingredient.tomato", 0.5, "kg", "mass"),
        )
        expected = merge_ingredients(ingredients).ingredients

        for ordering in itertools.permutations(ingredients):
            with self.subTest(ordering=ordering):
                self.assertEqual(merge_ingredients(ordering).ingredients, expected)

    def test_merge_is_associative_for_disjoint_groups(self) -> None:
        first = (
            ingredient("ingredient.tomato", 250, "g", "mass"),
            ingredient("ingredient.tomato", 0.5, "kg", "mass"),
        )
        second = (
            ingredient("ingredient.milk", 250, "ml", "volume"),
            ingredient("ingredient.milk", 0.75, "l", "volume"),
        )
        direct = merge_ingredients(first + second)
        first_merged = merge_ingredients(first)
        second_merged = merge_ingredients(second)
        regrouped = merge_ingredients(
            first_merged.ingredients + second_merged.ingredients
        )

        self.assertTrue(direct.ok, direct.errors)
        self.assertTrue(regrouped.ok, regrouped.errors)
        self.assertEqual(regrouped.ingredients, direct.ingredients)

    def test_same_inputs_produce_same_normalized_totals(self) -> None:
        ingredients = (
            ingredient("ingredient.tomato", 250, "g", "mass"),
            ingredient("ingredient.tomato", 0.5, "kg", "mass"),
        )

        first = normalize_ingredients(
            ingredients,
            target_portions=3,
            recipe_portions=2,
        )
        second = normalize_ingredients(
            ingredients,
            target_portions=3,
            recipe_portions=2,
        )

        self.assertTrue(first.ok, first.errors)
        self.assertEqual(first.ingredients, second.ingredients)


if __name__ == "__main__":
    unittest.main()
