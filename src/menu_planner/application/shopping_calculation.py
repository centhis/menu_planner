from __future__ import annotations

from dataclasses import dataclass

from menu_planner.domain.contracts.models import (
    SCHEMA_VERSION,
    NormalizedIngredient,
)
from menu_planner.domain.contracts.validation import (
    CANONICAL_UNIT_BY_DIMENSION,
    SUPPORTED_UNIT_DIMENSIONS,
    SUPPORTED_UNITS,
)
from menu_planner.domain.errors import (
    DomainError,
    invalid_range,
    shopping_unknown_unit,
    shopping_unsupported_dimension,
)

UNIT_TO_CANONICAL_FACTOR = {
    "g": 1.0,
    "kg": 1000.0,
    "ml": 1.0,
    "l": 1000.0,
    "piece": 1.0,
}
CALCULATION_DECIMAL_PLACES = 6


@dataclass(frozen=True)
class IngredientCalculationResult:
    ingredients: tuple[NormalizedIngredient, ...]
    errors: tuple[DomainError, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.errors


def scale_ingredient(
    ingredient: NormalizedIngredient,
    *,
    target_portions: int,
    recipe_portions: int,
) -> IngredientCalculationResult:
    portions_error = _validate_portions(target_portions, recipe_portions)
    if portions_error is not None:
        return IngredientCalculationResult(ingredients=(), errors=(portions_error,))

    unit_error = _validate_ingredient_unit_dimension(ingredient)
    if unit_error is not None:
        return IngredientCalculationResult(ingredients=(), errors=(unit_error,))

    ratio = target_portions / recipe_portions
    return IngredientCalculationResult(
        ingredients=(
            _replace_quantity(
                ingredient,
                _round_quantity(ingredient.quantity * ratio),
            ),
        ),
    )


def convert_to_canonical(
    ingredient: NormalizedIngredient,
) -> IngredientCalculationResult:
    unit_error = _validate_ingredient_unit_dimension(ingredient)
    if unit_error is not None:
        return IngredientCalculationResult(ingredients=(), errors=(unit_error,))

    canonical_unit = CANONICAL_UNIT_BY_DIMENSION[ingredient.dimension]
    factor = UNIT_TO_CANONICAL_FACTOR[ingredient.unit]
    return IngredientCalculationResult(
        ingredients=(
            NormalizedIngredient(
                schema_version=ingredient.schema_version,
                ingredient_id=ingredient.ingredient_id,
                display_name=ingredient.display_name,
                quantity=_round_quantity(ingredient.quantity * factor),
                unit=canonical_unit,
                dimension=ingredient.dimension,
            ),
        ),
    )


def merge_ingredients(
    ingredients: tuple[NormalizedIngredient, ...],
) -> IngredientCalculationResult:
    totals: dict[tuple[str, str], NormalizedIngredient] = {}
    dimensions_by_ingredient: dict[str, str] = {}

    for ingredient in ingredients:
        converted = convert_to_canonical(ingredient)
        if not converted.ok:
            return converted
        canonical = converted.ingredients[0]

        previous_dimension = dimensions_by_ingredient.get(canonical.ingredient_id)
        if previous_dimension is not None and previous_dimension != canonical.dimension:
            return IngredientCalculationResult(
                ingredients=(),
                errors=(
                    shopping_unsupported_dimension(
                        "dimension",
                        canonical.dimension,
                        [previous_dimension],
                    ),
                ),
            )
        dimensions_by_ingredient[canonical.ingredient_id] = canonical.dimension

        key = (canonical.ingredient_id, canonical.dimension)
        existing = totals.get(key)
        if existing is None:
            totals[key] = canonical
            continue
        totals[key] = _replace_quantity(
            existing,
            _round_quantity(existing.quantity + canonical.quantity),
        )

    return IngredientCalculationResult(
        ingredients=tuple(
            totals[key]
            for key in sorted(
                totals,
                key=lambda item: (item[0], item[1]),
            )
        )
    )


def normalize_ingredients(
    ingredients: tuple[NormalizedIngredient, ...],
    *,
    target_portions: int,
    recipe_portions: int,
) -> IngredientCalculationResult:
    scaled: list[NormalizedIngredient] = []
    for ingredient in ingredients:
        result = scale_ingredient(
            ingredient,
            target_portions=target_portions,
            recipe_portions=recipe_portions,
        )
        if not result.ok:
            return result
        scaled.append(result.ingredients[0])
    return merge_ingredients(tuple(scaled))


def _validate_portions(
    target_portions: int,
    recipe_portions: int,
) -> DomainError | None:
    if target_portions < 1:
        return invalid_range("target_portions", 1, 2147483647, target_portions)
    if recipe_portions < 1:
        return invalid_range("recipe_portions", 1, 2147483647, recipe_portions)
    return None


def _validate_ingredient_unit_dimension(
    ingredient: NormalizedIngredient,
) -> DomainError | None:
    if ingredient.unit not in SUPPORTED_UNITS:
        return shopping_unknown_unit("unit", ingredient.unit, sorted(SUPPORTED_UNITS))
    if ingredient.dimension not in SUPPORTED_UNIT_DIMENSIONS:
        return shopping_unsupported_dimension(
            "dimension",
            ingredient.dimension,
            sorted(SUPPORTED_UNIT_DIMENSIONS),
        )
    expected_dimension = SUPPORTED_UNITS[ingredient.unit]
    if ingredient.dimension != expected_dimension:
        return shopping_unsupported_dimension(
            "dimension",
            ingredient.dimension,
            [expected_dimension],
        )
    return None


def _replace_quantity(
    ingredient: NormalizedIngredient,
    quantity: float,
) -> NormalizedIngredient:
    return NormalizedIngredient(
        schema_version=ingredient.schema_version,
        ingredient_id=ingredient.ingredient_id,
        display_name=ingredient.display_name,
        quantity=quantity,
        unit=ingredient.unit,
        dimension=ingredient.dimension,
    )


def _round_quantity(value: float) -> float:
    return round(value, CALCULATION_DECIMAL_PLACES)


def ingredient(
    ingredient_id: str,
    quantity: float,
    unit: str,
    dimension: str,
    *,
    display_name: str | None = None,
) -> NormalizedIngredient:
    return NormalizedIngredient(
        schema_version=SCHEMA_VERSION,
        ingredient_id=ingredient_id,
        display_name=display_name or ingredient_id,
        quantity=quantity,
        unit=unit,
        dimension=dimension,
    )
