from __future__ import annotations

import json
import pathlib
import unittest
from typing import cast

from menu_planner.application.recipe_generation import (
    FakeRecipeDraftGenerator,
    RecipeDraftGenerationRequest,
    generate_recipe_draft,
)
from menu_planner.domain.contracts.models import JsonObject
from menu_planner.domain.contracts.validation import validate_contract
from menu_planner.domain.errors import ErrorCode

ROOT = pathlib.Path(__file__).resolve().parents[2]
GOLDEN_ROOT = ROOT / "fixtures" / "golden" / "m6b_recipe_generation"


class RecipeDraftGenerationTests(unittest.TestCase):
    def test_fake_generator_matches_one_day_golden_fixture(self) -> None:
        request = RecipeDraftGenerationRequest(
            draft_id="recipe_draft_001",
            accepted_menu_item=_accepted_menu_item(),
        )

        first = generate_recipe_draft(request=request)
        second = generate_recipe_draft(request=request)

        self.assertTrue(first.ok, first.errors)
        self.assertTrue(second.ok, second.errors)
        self.assertEqual(first.draft_payload, _load_json("one_day/recipe_draft.json"))
        self.assertEqual(first.draft_payload, second.draft_payload)
        self.assertFalse(first.side_effects_executed)
        self.assertIsNotNone(first.draft)
        assert first.draft is not None
        self.assertEqual(first.draft.status.value, "generated")
        self.assertEqual(first.draft.source_meal_slot_id, "slot_001")

    def test_fake_generator_output_is_validated_before_use(self) -> None:
        result = generate_recipe_draft(
            request=RecipeDraftGenerationRequest(
                draft_id="recipe_draft_001",
                accepted_menu_item=_accepted_menu_item(),
            ),
            generator=MalformedRecipeDraftGenerator(),
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.draft)
        self.assertFalse(result.side_effects_executed)
        self.assertEqual(result.errors[0].code, ErrorCode.MISSING_REQUIRED_FIELD)
        self.assertEqual(result.errors[0].path, ("steps",))

    def test_invalid_fake_output_fixture_has_stable_error(self) -> None:
        result = validate_contract(
            "recipe_draft",
            _load_json("invalid/missing_steps.json"),
        )

        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, ErrorCode.MISSING_REQUIRED_FIELD)
        self.assertEqual(result.errors[0].path, ("steps",))


class MalformedRecipeDraftGenerator(FakeRecipeDraftGenerator):
    name = "malformed_fake_recipe_draft_generator"
    version = "test"

    def generate(self, request: RecipeDraftGenerationRequest) -> JsonObject:
        return cast(JsonObject, _load_json("invalid/missing_steps.json"))


def _accepted_menu_item() -> JsonObject:
    return cast(JsonObject, _load_json("one_day/accepted_menu_item.json"))


def _load_json(relative_path: str) -> object:
    return json.loads((GOLDEN_ROOT / relative_path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
