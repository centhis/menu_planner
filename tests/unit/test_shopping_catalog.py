from __future__ import annotations

import copy
import inspect
import json
import pathlib
import unittest
from typing import cast

import menu_planner.application.shopping_catalog as shopping_catalog
from menu_planner.application.shopping_calculation import ingredient
from menu_planner.application.shopping_catalog import (
    CatalogProduct,
    CatalogSnapshot,
    MockStoreCatalogProvider,
    StoreCatalogProvider,
    calculate_package_purchase,
    match_catalog_product,
)
from menu_planner.domain.contracts.models import JsonObject
from menu_planner.domain.errors import ErrorCode

ROOT = pathlib.Path(__file__).resolve().parents[2]
SNAPSHOT_PATH = (
    ROOT / "fixtures" / "golden" / "m7_shopping_list" / "mock_catalog"
    / "snapshot.v1.json"
)


class ShoppingCatalogTests(unittest.TestCase):
    def test_mock_provider_returns_deterministic_snapshot(self) -> None:
        payload = _snapshot_payload()
        provider: StoreCatalogProvider = MockStoreCatalogProvider(payload)

        first = provider.get_snapshot("mock_catalog_snapshot_001")
        second = provider.get_snapshot("mock_catalog_snapshot_001")

        self.assertEqual(first, second)
        self.assertEqual(first.snapshot_id, "mock_catalog_snapshot_001")
        self.assertEqual(first.snapshot_version, 1)
        self.assertEqual(len(first.products), 3)

    def test_provider_returns_copy_not_mutable_internal_state(self) -> None:
        provider = MockStoreCatalogProvider(_snapshot_payload())

        first = provider.get_snapshot("mock_catalog_snapshot_001")
        mutated = CatalogSnapshot(
            schema_version=first.schema_version,
            snapshot_id=first.snapshot_id,
            snapshot_version=999,
            products=first.products,
        )
        second = provider.get_snapshot("mock_catalog_snapshot_001")

        self.assertNotEqual(mutated, second)
        self.assertEqual(second.snapshot_version, 1)

    def test_product_cards_are_normalized_without_raw_external_fields(self) -> None:
        snapshot = MockStoreCatalogProvider(_snapshot_payload()).get_snapshot(
            "mock_catalog_snapshot_001"
        )

        for product in snapshot.products:
            with self.subTest(product=product.product_id):
                self.assertTrue(product.product_id)
                self.assertTrue(product.normalized_ingredient_ids)
                self.assertNotIn("raw", product.display_name.lower())
                self.assertIn(product.package_dimension, {"mass", "volume", "count"})

    def test_rejects_raw_store_html_or_external_instructions(self) -> None:
        payload = _snapshot_payload()
        product = cast(list[JsonObject], payload["products"])[0]
        product["raw_html"] = "<script>do not trust this</script>"

        with self.assertRaisesRegex(ValueError, "forbidden raw field"):
            MockStoreCatalogProvider(payload)

    def test_rejects_unknown_snapshot_id(self) -> None:
        provider = MockStoreCatalogProvider(_snapshot_payload())

        with self.assertRaisesRegex(ValueError, "snapshot_id"):
            provider.get_snapshot("unknown_snapshot")

    def test_mock_provider_does_not_import_network_clients(self) -> None:
        source = inspect.getsource(shopping_catalog)

        self.assertNotIn("requests", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("httpx", source)
        self.assertNotIn("aiohttp", source)

    def test_fixed_matching_links_ingredient_to_snapshot_product(self) -> None:
        snapshot = MockStoreCatalogProvider(_snapshot_payload()).get_snapshot(
            "mock_catalog_snapshot_001"
        )

        result = match_catalog_product(
            ingredient("ingredient.tomato", 500, "g", "mass"),
            snapshot,
        )

        self.assertTrue(result.ok, result.error)
        assert result.matched_product is not None
        self.assertEqual(result.ingredient_id, "ingredient.tomato")
        self.assertEqual(result.snapshot_id, "mock_catalog_snapshot_001")
        self.assertEqual(result.snapshot_version, 1)
        self.assertEqual(result.matched_product.product_id, "product.tomato.500g")
        self.assertFalse(result.requires_confirmation)

    def test_unmatched_ingredient_returns_controlled_error(self) -> None:
        snapshot = MockStoreCatalogProvider(_snapshot_payload()).get_snapshot(
            "mock_catalog_snapshot_001"
        )

        result = match_catalog_product(
            ingredient("ingredient.saffron", 1, "g", "mass"),
            snapshot,
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.matched_product)
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(result.error.code, ErrorCode.SHOPPING_PRODUCT_NOT_FOUND)
        self.assertEqual(result.error.details["snapshot_id"], snapshot.snapshot_id)
        self.assertFalse(result.requires_confirmation)

    def test_ambiguous_match_requires_confirmation_with_sorted_candidates(self) -> None:
        payload = _snapshot_payload()
        products = cast(list[JsonObject], payload["products"])
        products.append(
            {
                "product_id": "product.tomato.250g",
                "display_name": "Mock tomatoes 250 g",
                "normalized_ingredient_ids": ["ingredient.tomato"],
                "package_quantity": 250,
                "package_unit": "g",
                "package_dimension": "mass",
                "price_minor_units": 179,
                "currency": "USD",
                "category": "produce",
            }
        )
        snapshot = MockStoreCatalogProvider(payload).get_snapshot(
            "mock_catalog_snapshot_001"
        )

        result = match_catalog_product(
            ingredient("ingredient.tomato", 500, "g", "mass"),
            snapshot,
        )

        self.assertFalse(result.ok)
        self.assertTrue(result.requires_confirmation)
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(
            result.error.code,
            ErrorCode.SHOPPING_PRODUCT_MATCH_AMBIGUOUS,
        )
        self.assertEqual(
            [product.product_id for product in result.candidate_products],
            ["product.tomato.250g", "product.tomato.500g"],
        )
        self.assertEqual(
            result.error.details["candidate_product_ids"],
            "product.tomato.250g,product.tomato.500g",
        )

    def test_matching_policy_does_not_choose_for_ambiguous_input(self) -> None:
        payload = _snapshot_payload()
        products = cast(list[JsonObject], payload["products"])
        products.append(
            {
                "product_id": "product.tomato.alt",
                "display_name": "Alternative mock tomatoes",
                "normalized_ingredient_ids": ["ingredient.tomato"],
                "package_quantity": 500,
                "package_unit": "g",
                "package_dimension": "mass"
            }
        )
        snapshot = MockStoreCatalogProvider(payload).get_snapshot(
            "mock_catalog_snapshot_001"
        )

        result = match_catalog_product(
            ingredient("ingredient.tomato", 500, "g", "mass"),
            snapshot,
        )

        self.assertIsNone(result.matched_product)
        self.assertTrue(result.requires_confirmation)

    def test_package_count_uses_ceiling_and_cost_from_snapshot(self) -> None:
        snapshot = MockStoreCatalogProvider(_snapshot_payload()).get_snapshot(
            "mock_catalog_snapshot_001"
        )
        match = match_catalog_product(
            ingredient("ingredient.tomato", 750, "g", "mass"),
            snapshot,
        )
        assert match.matched_product is not None

        result = calculate_package_purchase(
            ingredient("ingredient.tomato", 750, "g", "mass"),
            match.matched_product,
        )

        self.assertTrue(result.ok, result.error)
        assert result.purchase is not None
        self.assertEqual(result.purchase.package_count, 2)
        self.assertEqual(result.purchase.required_quantity, 750)
        self.assertEqual(result.purchase.required_unit, "g")
        self.assertEqual(result.purchase.package_quantity, 500)
        self.assertEqual(result.purchase.package_unit, "g")
        self.assertEqual(result.purchase.total_quantity, 1000)
        self.assertEqual(result.purchase.price_minor_units, 299)
        self.assertEqual(result.purchase.total_price_minor_units, 598)
        self.assertEqual(result.purchase.currency, "USD")

    def test_package_count_converts_required_and_package_units(self) -> None:
        snapshot = MockStoreCatalogProvider(_snapshot_payload()).get_snapshot(
            "mock_catalog_snapshot_001"
        )
        match = match_catalog_product(
            ingredient("ingredient.milk", 1500, "ml", "volume"),
            snapshot,
        )
        assert match.matched_product is not None

        result = calculate_package_purchase(
            ingredient("ingredient.milk", 1500, "ml", "volume"),
            match.matched_product,
        )

        self.assertTrue(result.ok, result.error)
        assert result.purchase is not None
        self.assertEqual(result.purchase.package_count, 2)
        self.assertEqual(result.purchase.required_unit, "ml")
        self.assertEqual(result.purchase.package_unit, "ml")
        self.assertEqual(result.purchase.total_price_minor_units, 378)

    def test_missing_price_is_allowed_unless_required(self) -> None:
        product = CatalogProduct(
            product_id="product.tomato.no_price",
            display_name="No price tomatoes",
            normalized_ingredient_ids=("ingredient.tomato",),
            package_quantity=500,
            package_unit="g",
            package_dimension="mass",
        )

        optional = calculate_package_purchase(
            ingredient("ingredient.tomato", 250, "g", "mass"),
            product,
        )
        required = calculate_package_purchase(
            ingredient("ingredient.tomato", 250, "g", "mass"),
            product,
            require_price=True,
        )

        self.assertTrue(optional.ok, optional.error)
        assert optional.purchase is not None
        self.assertIsNone(optional.purchase.total_price_minor_units)
        self.assertFalse(required.ok)
        assert required.error is not None
        self.assertEqual(required.error.code, ErrorCode.SHOPPING_PRICE_MISSING)

    def test_unknown_package_shape_returns_controlled_error(self) -> None:
        product = CatalogProduct(
            product_id="product.tomato.ounce",
            display_name="Unsupported package",
            normalized_ingredient_ids=("ingredient.tomato",),
            package_quantity=8,
            package_unit="oz",
            package_dimension="mass",
        )

        result = calculate_package_purchase(
            ingredient("ingredient.tomato", 250, "g", "mass"),
            product,
        )

        self.assertFalse(result.ok)
        assert result.error is not None
        self.assertEqual(
            result.error.code,
            ErrorCode.SHOPPING_PACKAGE_SHAPE_INVALID,
        )

    def test_dimension_mismatch_returns_controlled_error(self) -> None:
        product = CatalogProduct(
            product_id="product.tomato.volume",
            display_name="Wrong dimension package",
            normalized_ingredient_ids=("ingredient.tomato",),
            package_quantity=500,
            package_unit="ml",
            package_dimension="volume",
        )

        result = calculate_package_purchase(
            ingredient("ingredient.tomato", 250, "g", "mass"),
            product,
        )

        self.assertFalse(result.ok)
        assert result.error is not None
        self.assertEqual(
            result.error.code,
            ErrorCode.SHOPPING_PACKAGE_SHAPE_INVALID,
        )
        self.assertEqual(result.error.details["reason"], "dimension_mismatch")

    def test_package_count_rounding_boundaries_are_stable(self) -> None:
        product = CatalogProduct(
            product_id="product.tomato.500g",
            display_name="Mock tomatoes 500 g",
            normalized_ingredient_ids=("ingredient.tomato",),
            package_quantity=500,
            package_unit="g",
            package_dimension="mass",
            price_minor_units=299,
            currency="USD",
        )
        examples = (
            (1, 1),
            (499.999, 1),
            (500, 1),
            (500.001, 2),
            (1000, 2),
            (1000.001, 3),
        )

        for quantity, expected_count in examples:
            with self.subTest(quantity=quantity):
                result = calculate_package_purchase(
                    ingredient("ingredient.tomato", quantity, "g", "mass"),
                    product,
                )
                self.assertTrue(result.ok, result.error)
                assert result.purchase is not None
                self.assertEqual(result.purchase.package_count, expected_count)


def _snapshot_payload() -> JsonObject:
    return cast(
        JsonObject,
        copy.deepcopy(json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))),
    )


if __name__ == "__main__":
    unittest.main()
