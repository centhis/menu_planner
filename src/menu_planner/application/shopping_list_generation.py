from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import cast

from menu_planner.application.shopping_calculation import normalize_ingredients
from menu_planner.application.shopping_catalog import (
    CatalogSnapshot,
    calculate_package_purchase,
    match_catalog_product,
)
from menu_planner.domain.contracts.models import (
    SCHEMA_VERSION,
    JsonObject,
    JsonValue,
    NormalizedIngredient,
    ShoppingListVersion,
)
from menu_planner.domain.contracts.validation import validate_contract
from menu_planner.domain.errors import DomainError

SHOPPING_LIST_CALCULATOR_VERSION = "m7.deterministic_shopping_list.v1"


@dataclass(frozen=True)
class RecipeVersionRef:
    recipe_id: str
    version: int


@dataclass(frozen=True)
class BuildShoppingListVersionCommand:
    user_id: str
    shopping_list_id: str
    version: int
    source_menu_id: str
    source_menu_version: int
    recipe_version_refs: tuple[RecipeVersionRef, ...]
    catalog_snapshot: CatalogSnapshot
    ingredients: tuple[NormalizedIngredient, ...]
    target_portions: int
    recipe_portions: int


@dataclass(frozen=True)
class ShoppingListVersionResult:
    shopping_list_version: ShoppingListVersion | None
    errors: tuple[DomainError, ...] = ()
    source_hash: str | None = None
    side_effects_executed: bool = False
    confirmed_menu_changed: bool = False
    recipe_state_changed: bool = False

    @property
    def ok(self) -> bool:
        return self.shopping_list_version is not None and not self.errors


def build_shopping_list_version(
    command: BuildShoppingListVersionCommand,
) -> ShoppingListVersionResult:
    normalized = normalize_ingredients(
        command.ingredients,
        target_portions=command.target_portions,
        recipe_portions=command.recipe_portions,
    )
    if not normalized.ok:
        return ShoppingListVersionResult(
            shopping_list_version=None,
            errors=normalized.errors,
        )

    generated_items: list[JsonObject] = []
    for index, item in enumerate(normalized.ingredients, start=1):
        match = match_catalog_product(item, command.catalog_snapshot)
        if not match.ok or match.matched_product is None:
            return ShoppingListVersionResult(
                shopping_list_version=None,
                errors=(cast(DomainError, match.error),),
            )
        package = calculate_package_purchase(item, match.matched_product)
        if not package.ok or package.purchase is None:
            return ShoppingListVersionResult(
                shopping_list_version=None,
                errors=(cast(DomainError, package.error),),
            )
        generated_items.append(
            {
                "shopping_item_id": f"{command.shopping_list_id}:item:{index:03d}",
                "ingredient_id": item.ingredient_id,
                "display_name": item.display_name,
                "product_id": package.purchase.product_id,
                "quantity": package.purchase.required_quantity,
                "unit": package.purchase.required_unit,
                "package_count": package.purchase.package_count,
                "total_quantity": package.purchase.total_quantity,
                "total_price_minor_units": package.purchase.total_price_minor_units,
                "currency": package.purchase.currency,
            }
        )

    refs: list[JsonObject] = [
        cast(JsonObject, {"recipe_id": ref.recipe_id, "version": ref.version})
        for ref in sorted(
            command.recipe_version_refs,
            key=lambda ref: (ref.recipe_id, ref.version),
        )
    ]
    source_hash = _source_hash(command, generated_items, refs)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "user_id": command.user_id,
        "shopping_list_id": command.shopping_list_id,
        "version": command.version,
        "source_menu_id": command.source_menu_id,
        "source_menu_version": command.source_menu_version,
        "recipe_version_refs": refs,
        "catalog_snapshot_id": command.catalog_snapshot.snapshot_id,
        "catalog_snapshot_version": command.catalog_snapshot.snapshot_version,
        "generated_items": generated_items,
        "calculation_metadata": {
            "calculator": SHOPPING_LIST_CALCULATOR_VERSION,
            "source_hash": source_hash,
        },
    }
    validation = validate_contract("shopping_list_version", payload)
    if not validation.is_valid or validation.value is None:
        return ShoppingListVersionResult(
            shopping_list_version=None,
            errors=validation.errors,
        )
    return ShoppingListVersionResult(
        shopping_list_version=cast(ShoppingListVersion, validation.value),
        source_hash=source_hash,
    )


def _source_hash(
    command: BuildShoppingListVersionCommand,
    generated_items: list[JsonObject],
    recipe_refs: list[JsonObject],
) -> str:
    payload: JsonObject = {
        "calculator": SHOPPING_LIST_CALCULATOR_VERSION,
        "user_id": command.user_id,
        "source_menu_id": command.source_menu_id,
        "source_menu_version": command.source_menu_version,
        "recipe_version_refs": cast(JsonValue, recipe_refs),
        "catalog_snapshot_id": command.catalog_snapshot.snapshot_id,
        "catalog_snapshot_version": command.catalog_snapshot.snapshot_version,
        "generated_items": cast(JsonValue, generated_items),
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
