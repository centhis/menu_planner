from __future__ import annotations

import copy
import math
from dataclasses import dataclass
from typing import Protocol, cast

from menu_planner.application.shopping_calculation import convert_to_canonical
from menu_planner.domain.contracts.models import JsonObject, NormalizedIngredient
from menu_planner.domain.contracts.validation import (
    SUPPORTED_UNIT_DIMENSIONS,
    SUPPORTED_UNITS,
)
from menu_planner.domain.errors import (
    DomainError,
    shopping_package_shape_invalid,
    shopping_price_missing,
    shopping_product_match_ambiguous,
    shopping_product_not_found,
)

FORBIDDEN_RAW_CATALOG_FIELDS = frozenset(
    {
        "raw_html",
        "raw_store_html",
        "raw_page",
        "external_instructions",
        "prompt",
        "system_prompt",
    }
)


@dataclass(frozen=True)
class CatalogProduct:
    product_id: str
    display_name: str
    normalized_ingredient_ids: tuple[str, ...]
    package_quantity: float
    package_unit: str
    package_dimension: str
    price_minor_units: int | None = None
    currency: str | None = None
    category: str | None = None


@dataclass(frozen=True)
class CatalogSnapshot:
    schema_version: str
    snapshot_id: str
    snapshot_version: int
    products: tuple[CatalogProduct, ...]


@dataclass(frozen=True)
class ProductMatchResult:
    ingredient_id: str
    snapshot_id: str
    snapshot_version: int
    matched_product: CatalogProduct | None = None
    candidate_products: tuple[CatalogProduct, ...] = ()
    error: DomainError | None = None
    requires_confirmation: bool = False

    @property
    def ok(self) -> bool:
        return self.matched_product is not None and self.error is None


@dataclass(frozen=True)
class PackagePurchase:
    ingredient_id: str
    product_id: str
    required_quantity: float
    required_unit: str
    package_quantity: float
    package_unit: str
    package_count: int
    total_quantity: float
    price_minor_units: int | None
    total_price_minor_units: int | None
    currency: str | None


@dataclass(frozen=True)
class PackageCalculationResult:
    purchase: PackagePurchase | None = None
    error: DomainError | None = None

    @property
    def ok(self) -> bool:
        return self.purchase is not None and self.error is None


class StoreCatalogProvider(Protocol):
    def get_snapshot(self, snapshot_id: str) -> CatalogSnapshot: ...


class MockStoreCatalogProvider:
    def __init__(self, snapshot_payload: JsonObject) -> None:
        self._snapshot = _snapshot_from_payload(snapshot_payload)

    def get_snapshot(self, snapshot_id: str) -> CatalogSnapshot:
        if snapshot_id != self._snapshot.snapshot_id:
            raise ValueError("mock catalog snapshot_id does not match request")
        return copy.deepcopy(self._snapshot)


def match_catalog_product(
    ingredient: NormalizedIngredient,
    snapshot: CatalogSnapshot,
) -> ProductMatchResult:
    candidates = tuple(
        sorted(
            (
                product
                for product in snapshot.products
                if ingredient.ingredient_id in product.normalized_ingredient_ids
            ),
            key=lambda product: product.product_id,
        )
    )
    if len(candidates) == 1:
        return ProductMatchResult(
            ingredient_id=ingredient.ingredient_id,
            snapshot_id=snapshot.snapshot_id,
            snapshot_version=snapshot.snapshot_version,
            matched_product=candidates[0],
        )
    if not candidates:
        return ProductMatchResult(
            ingredient_id=ingredient.ingredient_id,
            snapshot_id=snapshot.snapshot_id,
            snapshot_version=snapshot.snapshot_version,
            error=shopping_product_not_found(
                ingredient.ingredient_id,
                snapshot.snapshot_id,
                snapshot.snapshot_version,
            ),
        )
    return ProductMatchResult(
        ingredient_id=ingredient.ingredient_id,
        snapshot_id=snapshot.snapshot_id,
        snapshot_version=snapshot.snapshot_version,
        candidate_products=candidates,
        error=shopping_product_match_ambiguous(
            ingredient.ingredient_id,
            snapshot.snapshot_id,
            snapshot.snapshot_version,
            [product.product_id for product in candidates],
        ),
        requires_confirmation=True,
    )


def calculate_package_purchase(
    ingredient: NormalizedIngredient,
    product: CatalogProduct,
    *,
    require_price: bool = False,
) -> PackageCalculationResult:
    converted = convert_to_canonical(ingredient)
    if not converted.ok:
        return PackageCalculationResult(error=converted.errors[0])
    canonical = converted.ingredients[0]

    package_ingredient = NormalizedIngredient(
        schema_version=ingredient.schema_version,
        ingredient_id=ingredient.ingredient_id,
        display_name=ingredient.display_name,
        quantity=product.package_quantity,
        unit=product.package_unit,
        dimension=product.package_dimension,
    )
    converted_package = convert_to_canonical(package_ingredient)
    if not converted_package.ok:
        return PackageCalculationResult(
            error=shopping_package_shape_invalid(
                ingredient.ingredient_id,
                product.product_id,
                converted_package.errors[0].code.value,
            )
        )
    canonical_package = converted_package.ingredients[0]
    if canonical.dimension != canonical_package.dimension:
        return PackageCalculationResult(
            error=shopping_package_shape_invalid(
                ingredient.ingredient_id,
                product.product_id,
                "dimension_mismatch",
            )
        )
    if canonical_package.quantity <= 0:
        return PackageCalculationResult(
            error=shopping_package_shape_invalid(
                ingredient.ingredient_id,
                product.product_id,
                "non_positive_package_quantity",
            )
        )
    if require_price and product.price_minor_units is None:
        return PackageCalculationResult(
            error=shopping_price_missing(product.product_id)
        )

    package_count = math.ceil(canonical.quantity / canonical_package.quantity)
    total_price = (
        product.price_minor_units * package_count
        if product.price_minor_units is not None
        else None
    )
    return PackageCalculationResult(
        purchase=PackagePurchase(
            ingredient_id=ingredient.ingredient_id,
            product_id=product.product_id,
            required_quantity=canonical.quantity,
            required_unit=canonical.unit,
            package_quantity=canonical_package.quantity,
            package_unit=canonical_package.unit,
            package_count=package_count,
            total_quantity=round(canonical_package.quantity * package_count, 6),
            price_minor_units=product.price_minor_units,
            total_price_minor_units=total_price,
            currency=product.currency,
        )
    )


def _snapshot_from_payload(payload: JsonObject) -> CatalogSnapshot:
    _reject_forbidden_raw_fields(payload)
    _require_string(payload, "schema_version")
    snapshot_id = _require_string(payload, "snapshot_id")
    snapshot_version = _require_positive_integer(payload, "snapshot_version")
    raw_products = payload.get("products")
    if not isinstance(raw_products, list) or not raw_products:
        raise ValueError("mock catalog snapshot requires non-empty products")

    products = tuple(
        _product_from_payload(cast(JsonObject, product), f"products.{index}")
        for index, product in enumerate(raw_products)
    )
    return CatalogSnapshot(
        schema_version=cast(str, payload["schema_version"]),
        snapshot_id=snapshot_id,
        snapshot_version=snapshot_version,
        products=products,
    )


def _product_from_payload(payload: JsonObject, path: str) -> CatalogProduct:
    _reject_forbidden_raw_fields(payload)
    product_id = _require_string(payload, "product_id", path)
    display_name = _require_string(payload, "display_name", path)
    ingredient_ids = _require_string_array(
        payload,
        "normalized_ingredient_ids",
        path,
    )
    package_quantity = _require_positive_number(payload, "package_quantity", path)
    package_unit = _require_string(payload, "package_unit", path)
    if package_unit not in SUPPORTED_UNITS:
        raise ValueError(f"{path}.package_unit is not supported")
    package_dimension = _require_string(payload, "package_dimension", path)
    if package_dimension not in SUPPORTED_UNIT_DIMENSIONS:
        raise ValueError(f"{path}.package_dimension is not supported")
    if SUPPORTED_UNITS[package_unit] != package_dimension:
        raise ValueError(f"{path}.package_dimension does not match package_unit")

    price_minor_units = _optional_positive_integer(
        payload,
        "price_minor_units",
        path,
    )
    currency = _optional_string(payload, "currency", path)
    category = _optional_string(payload, "category", path)
    return CatalogProduct(
        product_id=product_id,
        display_name=display_name,
        normalized_ingredient_ids=tuple(ingredient_ids),
        package_quantity=package_quantity,
        package_unit=package_unit,
        package_dimension=package_dimension,
        price_minor_units=price_minor_units,
        currency=currency,
        category=category,
    )


def _reject_forbidden_raw_fields(payload: JsonObject) -> None:
    forbidden = sorted(set(payload) & FORBIDDEN_RAW_CATALOG_FIELDS)
    if forbidden:
        raise ValueError(f"mock catalog contains forbidden raw field: {forbidden[0]}")


def _require_string(
    payload: JsonObject,
    field: str,
    path: str = "",
) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or value == "":
        prefix = f"{path}." if path else ""
        raise ValueError(f"{prefix}{field} must be a non-empty string")
    return value


def _optional_string(
    payload: JsonObject,
    field: str,
    path: str,
) -> str | None:
    if field not in payload:
        return None
    return _require_string(payload, field, path)


def _require_string_array(
    payload: JsonObject,
    field: str,
    path: str,
) -> tuple[str, ...]:
    value = payload.get(field)
    if not isinstance(value, list) or not value:
        raise ValueError(f"{path}.{field} must be a non-empty string array")
    if not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{path}.{field} must contain only non-empty strings")
    return tuple(cast(list[str], value))


def _require_positive_integer(
    payload: JsonObject,
    field: str,
    path: str = "",
) -> int:
    value = payload.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        prefix = f"{path}." if path else ""
        raise ValueError(f"{prefix}{field} must be a positive integer")
    return value


def _optional_positive_integer(
    payload: JsonObject,
    field: str,
    path: str,
) -> int | None:
    if field not in payload:
        return None
    return _require_positive_integer(payload, field, path)


def _require_positive_number(
    payload: JsonObject,
    field: str,
    path: str,
) -> float:
    value = payload.get(field)
    if not isinstance(value, int | float) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{path}.{field} must be a positive number")
    return float(value)
