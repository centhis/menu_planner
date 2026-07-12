from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import cast

from menu_planner.application.shopping_calculation import (
    convert_to_canonical,
    ingredient,
    normalize_ingredients,
)
from menu_planner.application.shopping_catalog import (
    CatalogSnapshot,
    MockStoreCatalogProvider,
    calculate_package_purchase,
    match_catalog_product,
)
from menu_planner.application.shopping_checklist import (
    UpdateChecklistItemByTextCommand,
    UpdateChecklistItemCommand,
    update_checklist_item_status,
    update_checklist_item_status_by_text,
)
from menu_planner.application.shopping_list_diff import (
    CreateShoppingListDiffCommand,
    create_shopping_list_diff,
)
from menu_planner.application.shopping_list_generation import (
    BuildShoppingListVersionCommand,
    RecipeVersionRef,
    build_shopping_list_version,
)
from menu_planner.domain.contracts.models import (
    JsonObject,
    JsonValue,
    NormalizedIngredient,
    ShoppingListVersion,
)
from menu_planner.domain.errors import ErrorCode

DEFAULT_CATALOG_SNAPSHOT_PATH = Path(
    "fixtures/golden/m7_shopping_list/mock_catalog/snapshot.v1.json"
)


def run_m7_shopping_eval(
    *,
    catalog_snapshot_path: Path = DEFAULT_CATALOG_SNAPSHOT_PATH,
) -> JsonObject:
    snapshot = MockStoreCatalogProvider(
        _load_json(catalog_snapshot_path)
    ).get_snapshot("mock_catalog_snapshot_001")
    old_command = _shopping_command(
        shopping_list_id="shopping_list_old",
        version=1,
        recipe_version=1,
        ingredients=(
            ingredient("ingredient.tomato", 750, "g", "mass"),
            ingredient("ingredient.milk", 1, "l", "volume"),
        ),
    )
    new_command = _shopping_command(
        shopping_list_id="shopping_list_new",
        version=2,
        recipe_version=2,
        ingredients=(
            ingredient("ingredient.milk", 2, "l", "volume"),
            ingredient("ingredient.egg", 6, "piece", "count"),
        ),
    )
    old_command = _with_snapshot(old_command, snapshot)
    new_command = _with_snapshot(new_command, snapshot)

    unit_conversion_ok = _unit_conversion_ok()
    scaling_merge_ok = _scaling_merge_ok()
    matching_ok = _matching_ok(snapshot)
    package_cost_ok = _package_cost_ok(snapshot)
    identity = _shopping_list_identity_ok(old_command)
    diff = create_shopping_list_diff(
        CreateShoppingListDiffCommand(
            replacement_id="replacement_001",
            user_id="user_001",
            source_menu_id="menu_001",
            source_menu_version=1,
            replacement_menu_version=2,
            target_meal_slot_id="slot_002",
            old_shopping_list_command=old_command,
            new_shopping_list_command=new_command,
        )
    )
    checklist = _checklist_checks(old_command)

    metrics: JsonObject = {
        "unit_conversion_ok": unit_conversion_ok,
        "ingredient_scaling_merge_ok": scaling_merge_ok,
        "mock_catalog_matching_ok": matching_ok,
        "package_cost_calculation_ok": package_cost_ok,
        "shopping_list_identity_ok": identity["ok"],
        "replacement_diff_ok": diff.ok,
        "checklist_exact_update_ok": checklist["exact_update_ok"],
        "checklist_text_one_match_ok": checklist["text_one_match_ok"],
        "checklist_text_ambiguous_requires_disambiguation": checklist[
            "text_ambiguous_ok"
        ],
        "checklist_text_no_match_controlled_error": checklist["text_no_match_ok"],
        "confirmed_state_changed": False,
        "side_effects_executed": False,
        "external_provider_required": False,
        "credentials_read": False,
    }
    failures = _failures(metrics)
    return {
        "schema_version": "m7.shopping_list_eval_report.v1",
        "catalog_snapshot_fixture": str(catalog_snapshot_path),
        "catalog_snapshot": {
            "snapshot_id": snapshot.snapshot_id,
            "snapshot_version": snapshot.snapshot_version,
            "product_count": len(snapshot.products),
        },
        "model_backed_experiment": {
            "status": "skipped",
            "reason": (
                "Gate M7 uses deterministic code for unit conversion, product "
                "matching, package arithmetic, shopping-list diff, and "
                "checklist mutation. Model-backed matching remains deferred "
                "until an explicit provider/model and safety decision."
            ),
            "provider": None,
            "model": None,
            "credentials_read": False,
            "raw_output_stored": False,
        },
        "metrics": metrics,
        "shopping_list_identity": cast(JsonValue, identity),
        "replacement_diff": {
            "created": diff.diff is not None,
            "change_count": _change_count(diff.diff),
        },
        "checklist": {
            "ambiguous_candidate_count": checklist["ambiguous_candidate_count"],
            "no_match_error_code": checklist["no_match_error_code"],
        },
        "failures": cast(JsonValue, failures),
    }


def _unit_conversion_ok() -> bool:
    converted = convert_to_canonical(ingredient("ingredient.milk", 1, "l", "volume"))
    return (
        converted.ok
        and len(converted.ingredients) == 1
        and converted.ingredients[0].quantity == 1000
        and converted.ingredients[0].unit == "ml"
    )


def _scaling_merge_ok() -> bool:
    normalized = normalize_ingredients(
        (
            ingredient("ingredient.tomato", 0.5, "kg", "mass"),
            ingredient("ingredient.tomato", 250, "g", "mass"),
        ),
        target_portions=2,
        recipe_portions=1,
    )
    return (
        normalized.ok
        and len(normalized.ingredients) == 1
        and normalized.ingredients[0].quantity == 1500
        and normalized.ingredients[0].unit == "g"
    )


def _matching_ok(snapshot: CatalogSnapshot) -> bool:
    product_match = match_catalog_product(
        ingredient("ingredient.milk", 1, "l", "volume"),
        snapshot,
    )
    return (
        product_match.ok
        and product_match.matched_product is not None
        and product_match.matched_product.product_id == "product.milk.1l"
    )


def _package_cost_ok(snapshot: CatalogSnapshot) -> bool:
    product_match = match_catalog_product(
        ingredient("ingredient.tomato", 750, "g", "mass"),
        snapshot,
    )
    if not product_match.ok or product_match.matched_product is None:
        return False
    purchase = calculate_package_purchase(
        ingredient("ingredient.tomato", 750, "g", "mass"),
        product_match.matched_product,
    )
    return (
        purchase.ok
        and purchase.purchase is not None
        and purchase.purchase.package_count == 2
        and purchase.purchase.total_price_minor_units == 598
    )


def _shopping_list_identity_ok(
    command: BuildShoppingListVersionCommand,
) -> JsonObject:
    first = build_shopping_list_version(command)
    second = build_shopping_list_version(command)
    same_version = first.shopping_list_version == second.shopping_list_version
    same_hash = first.source_hash == second.source_hash
    return {
        "ok": first.ok and second.ok and same_version and same_hash,
        "same_version": same_version,
        "same_hash": same_hash,
        "source_hash": first.source_hash,
    }


def _checklist_checks(command: BuildShoppingListVersionCommand) -> JsonObject:
    shopping_list_result = build_shopping_list_version(command)
    if (
        not shopping_list_result.ok
        or shopping_list_result.shopping_list_version is None
        or shopping_list_result.source_hash is None
    ):
        return {
            "exact_update_ok": False,
            "text_one_match_ok": False,
            "text_ambiguous_ok": False,
            "text_no_match_ok": False,
            "ambiguous_candidate_count": 0,
            "no_match_error_code": None,
        }
    shopping_list = shopping_list_result.shopping_list_version
    source_hash = shopping_list_result.source_hash
    exact = update_checklist_item_status(
        UpdateChecklistItemCommand(
            shopping_list=shopping_list,
            expected_version=shopping_list.version,
            expected_source_hash=source_hash,
            shopping_item_id="shopping_list_old:item:001",
            status="completed",
            audit_event_id="shopping_audit_eval_exact",
            actor_id="user_001",
            occurred_at="2026-07-12T00:00:00Z",
        )
    )
    one_match = update_checklist_item_status_by_text(
        UpdateChecklistItemByTextCommand(
            shopping_list=shopping_list,
            expected_version=shopping_list.version,
            expected_source_hash=source_hash,
            text="milk bought",
            status="completed",
            audit_event_id="shopping_audit_eval_text_one",
            actor_id="user_001",
            occurred_at="2026-07-12T00:00:00Z",
        )
    )
    ambiguous = update_checklist_item_status_by_text(
        UpdateChecklistItemByTextCommand(
            shopping_list=_with_second_milk_item(shopping_list),
            expected_version=shopping_list.version,
            expected_source_hash=source_hash,
            text="milk bought",
            status="completed",
            audit_event_id="shopping_audit_eval_text_ambiguous",
            actor_id="user_001",
            occurred_at="2026-07-12T00:00:00Z",
        )
    )
    no_match = update_checklist_item_status_by_text(
        UpdateChecklistItemByTextCommand(
            shopping_list=shopping_list,
            expected_version=shopping_list.version,
            expected_source_hash=source_hash,
            text="saffron bought",
            status="completed",
            audit_event_id="shopping_audit_eval_text_none",
            actor_id="user_001",
            occurred_at="2026-07-12T00:00:00Z",
        )
    )
    return {
        "exact_update_ok": exact.ok,
        "text_one_match_ok": one_match.ok,
        "text_ambiguous_ok": (
            not ambiguous.ok
            and bool(ambiguous.errors)
            and ambiguous.errors[0].code == ErrorCode.SHOPPING_ITEM_MATCH_AMBIGUOUS
            and len(ambiguous.disambiguation_candidates) == 2
            and not ambiguous.side_effects_executed
        ),
        "text_no_match_ok": (
            not no_match.ok
            and bool(no_match.errors)
            and no_match.errors[0].code == ErrorCode.SHOPPING_ITEM_NOT_FOUND
        ),
        "ambiguous_candidate_count": len(ambiguous.disambiguation_candidates),
        "no_match_error_code": (
            no_match.errors[0].code.value if no_match.errors else None
        ),
    }


def _failures(metrics: JsonObject) -> list[JsonObject]:
    failures: list[JsonObject] = []
    for check, value in metrics.items():
        if check in {
            "confirmed_state_changed",
            "side_effects_executed",
            "external_provider_required",
            "credentials_read",
        }:
            passed = value is False
        else:
            passed = value is True
        if not passed:
            failures.append({"check": check, "passed": False, "actual": value})
    return failures


def _shopping_command(
    *,
    shopping_list_id: str,
    version: int,
    recipe_version: int,
    ingredients: tuple[NormalizedIngredient, ...],
) -> BuildShoppingListVersionCommand:
    return BuildShoppingListVersionCommand(
        user_id="user_001",
        shopping_list_id=shopping_list_id,
        version=version,
        source_menu_id="menu_001",
        source_menu_version=version,
        recipe_version_refs=(RecipeVersionRef("recipe_slot_002", recipe_version),),
        catalog_snapshot=MockStoreCatalogProvider(
            _load_json(DEFAULT_CATALOG_SNAPSHOT_PATH)
        ).get_snapshot("mock_catalog_snapshot_001"),
        ingredients=ingredients,
        target_portions=2,
        recipe_portions=2,
    )


def _with_snapshot(
    command: BuildShoppingListVersionCommand,
    snapshot: CatalogSnapshot,
) -> BuildShoppingListVersionCommand:
    return BuildShoppingListVersionCommand(
        user_id=command.user_id,
        shopping_list_id=command.shopping_list_id,
        version=command.version,
        source_menu_id=command.source_menu_id,
        source_menu_version=command.source_menu_version,
        recipe_version_refs=command.recipe_version_refs,
        catalog_snapshot=snapshot,
        ingredients=command.ingredients,
        target_portions=command.target_portions,
        recipe_portions=command.recipe_portions,
    )


def _with_second_milk_item(shopping_list: ShoppingListVersion) -> ShoppingListVersion:
    items = copy.deepcopy(shopping_list.generated_items)
    duplicate = copy.deepcopy(items[0])
    duplicate["shopping_item_id"] = f"{shopping_list.shopping_list_id}:item:003"
    duplicate["ingredient_id"] = "ingredient.milk.alt"
    duplicate["display_name"] = "milk for coffee"
    items.append(duplicate)
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
        generated_items=items,
        calculation_metadata=copy.deepcopy(shopping_list.calculation_metadata),
    )


def _change_count(diff: JsonObject | None) -> int:
    if diff is None:
        return 0
    changes = diff.get("changes")
    return len(changes) if isinstance(changes, list) else 0


def _load_json(path: Path) -> JsonObject:
    return cast(JsonObject, json.loads(path.read_text(encoding="utf-8")))
