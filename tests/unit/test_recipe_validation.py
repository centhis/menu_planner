from __future__ import annotations

import copy
import json
import pathlib
import unittest
from typing import cast

from menu_planner.application.recipe_validation import (
    validate_recipe_draft_for_menu_item,
)
from menu_planner.domain.contracts.models import JsonObject, RecipeDraft
from menu_planner.domain.contracts.validation import validate_contract
from menu_planner.domain.errors import ErrorCode

ROOT = pathlib.Path(__file__).resolve().parents[2]
GOLDEN_ROOT = ROOT / "fixtures" / "golden" / "m6b_recipe_generation"


class RecipeDraftValidationTests(unittest.TestCase):
    def test_valid_recipe_draft_can_persist_valid_version(self) -> None:
        result = validate_recipe_draft_for_menu_item(
            draft=_valid_payload(),
            accepted_menu_item=_accepted_menu_item(),
        )

        self.assertTrue(result.ok, result.errors)
        self.assertTrue(result.can_persist_valid_version)
        self.assertFalse(result.side_effects_executed)
        self.assertIsNotNone(result.draft)

    def test_contract_invalid_recipe_cannot_persist_valid_version(self) -> None:
        result = validate_recipe_draft_for_menu_item(
            draft=cast(JsonObject, _load_json("invalid/missing_steps.json")),
            accepted_menu_item=_accepted_menu_item(),
        )

        self.assertFalse(result.ok)
        self.assertFalse(result.can_persist_valid_version)
        self.assertFalse(result.side_effects_executed)
        self.assertEqual(result.errors[0].code, ErrorCode.MISSING_REQUIRED_FIELD)
        self.assertEqual(result.errors[0].path, ("steps",))
        self.assertIsNone(result.draft)

    def test_source_mismatch_is_machine_readable(self) -> None:
        payload = _valid_payload()
        payload["source_meal_slot_id"] = "slot_999"

        result = validate_recipe_draft_for_menu_item(
            draft=payload,
            accepted_menu_item=_accepted_menu_item(),
        )

        self.assertFalse(result.ok)
        self.assertFalse(result.can_persist_valid_version)
        self.assertEqual(result.errors[0].code, ErrorCode.RECIPE_SOURCE_MISMATCH)
        self.assertEqual(result.errors[0].path, ("source_meal_slot_id",))

    def test_unavailable_equipment_is_machine_readable(self) -> None:
        accepted_menu_item = _accepted_menu_item()
        accepted_menu_item["available_equipment"] = ["oven"]

        result = validate_recipe_draft_for_menu_item(
            draft=_valid_payload(),
            accepted_menu_item=accepted_menu_item,
        )

        self.assertFalse(result.ok)
        self.assertFalse(result.can_persist_valid_version)
        self.assertEqual(
            result.errors[0].code,
            ErrorCode.RECIPE_EQUIPMENT_UNAVAILABLE,
        )
        self.assertEqual(result.errors[0].path, ("equipment",))

    def test_typed_recipe_draft_can_be_validated(self) -> None:
        contract = validate_contract("recipe_draft", _valid_payload())
        self.assertTrue(contract.is_valid, contract.errors)
        assert contract.value is not None

        result = validate_recipe_draft_for_menu_item(
            draft=cast(RecipeDraft, contract.value),
            accepted_menu_item=_accepted_menu_item(),
        )

        self.assertTrue(result.ok, result.errors)
        self.assertTrue(result.can_persist_valid_version)


def _valid_payload() -> JsonObject:
    return cast(JsonObject, copy.deepcopy(_load_json("one_day/recipe_draft.json")))


def _accepted_menu_item() -> JsonObject:
    return cast(
        JsonObject,
        copy.deepcopy(_load_json("one_day/accepted_menu_item.json")),
    )


def _load_json(relative_path: str) -> object:
    return json.loads((GOLDEN_ROOT / relative_path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
