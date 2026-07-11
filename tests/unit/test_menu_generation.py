from __future__ import annotations

import json
import pathlib
import unittest
from typing import cast

from menu_planner.application.menu_generation import (
    FakeMenuDraftGenerator,
    MenuDraftGenerationRequest,
    generate_menu_draft,
)
from menu_planner.domain.contracts.models import JsonObject, PlanningContext
from menu_planner.domain.contracts.validation import validate_contract
from menu_planner.domain.errors import ErrorCode

ROOT = pathlib.Path(__file__).resolve().parents[2]
GOLDEN_ROOT = ROOT / "fixtures" / "golden" / "m6a_menu_draft_generation"


class MenuDraftGenerationTests(unittest.TestCase):
    def test_fake_generator_matches_one_day_golden_fixture(self) -> None:
        context = _planning_context()
        request = MenuDraftGenerationRequest(
            draft_id="menu_draft_001",
            planning_context=context,
        )

        first = generate_menu_draft(request=request)
        second = generate_menu_draft(request=request)

        self.assertTrue(first.ok, first.errors)
        self.assertTrue(second.ok, second.errors)
        self.assertEqual(first.draft_payload, _load_json("one_day/menu_draft.json"))
        self.assertEqual(first.draft_payload, second.draft_payload)
        self.assertFalse(first.side_effects_executed)
        self.assertIsNotNone(first.draft)
        assert first.draft is not None
        self.assertEqual(first.draft.status.value, "generated")

    def test_fake_generator_output_is_validated_before_use(self) -> None:
        result = generate_menu_draft(
            request=MenuDraftGenerationRequest(
                draft_id="menu_draft_001",
                planning_context=_planning_context(),
            ),
            generator=MalformedMenuDraftGenerator(),
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.draft)
        self.assertFalse(result.side_effects_executed)
        self.assertEqual(result.errors[0].code, ErrorCode.MISSING_REQUIRED_FIELD)
        self.assertEqual(result.errors[0].path, ("generated_items",))

    def test_invalid_fake_output_fixture_has_stable_error(self) -> None:
        result = validate_contract(
            "menu_draft",
            _load_json("invalid/missing_generated_items.json"),
        )

        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors[0].code, ErrorCode.MISSING_REQUIRED_FIELD)
        self.assertEqual(result.errors[0].path, ("generated_items",))


class MalformedMenuDraftGenerator(FakeMenuDraftGenerator):
    name = "malformed_fake_menu_draft_generator"
    version = "test"

    def generate(self, request: MenuDraftGenerationRequest) -> JsonObject:
        return cast(JsonObject, _load_json("invalid/missing_generated_items.json"))


def _planning_context() -> PlanningContext:
    payload = _load_json("one_day/planning_context.json")
    result = validate_contract("planning_context", payload)
    if not result.is_valid or result.value is None:
        raise AssertionError(result.errors)
    return cast(PlanningContext, result.value)


def _load_json(relative_path: str) -> object:
    return json.loads((GOLDEN_ROOT / relative_path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
