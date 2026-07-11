from __future__ import annotations

import copy
import json
import pathlib
import unittest
from dataclasses import replace
from typing import cast

from menu_planner.application.menu_validation import validate_menu_draft_for_context
from menu_planner.domain.contracts.models import JsonObject, PlanningContext
from menu_planner.domain.contracts.validation import validate_contract
from menu_planner.domain.errors import DomainError, ErrorCode

ROOT = pathlib.Path(__file__).resolve().parents[2]
GOLDEN_ROOT = ROOT / "fixtures" / "golden" / "m6a_menu_draft_generation"


class MenuDraftValidationTests(unittest.TestCase):
    def test_valid_golden_draft_allows_safe_preview(self) -> None:
        result = validate_menu_draft_for_context(
            draft=_valid_payload(),
            planning_context=_planning_context(),
        )

        self.assertTrue(result.ok, result.errors)
        self.assertTrue(result.can_create_safe_preview)
        self.assertFalse(result.side_effects_executed)
        self.assertIsNotNone(result.draft)

    def test_contract_invalid_draft_cannot_create_safe_preview(self) -> None:
        result = validate_menu_draft_for_context(
            draft=cast(JsonObject, _load_json("invalid/missing_generated_items.json")),
            planning_context=_planning_context(),
        )

        self.assertFalse(result.ok)
        self.assertFalse(result.can_create_safe_preview)
        self.assertFalse(result.side_effects_executed)
        self.assertEqual(result.errors[0].code, ErrorCode.MISSING_REQUIRED_FIELD)
        self.assertIsNone(result.draft)

    def test_period_mismatch_is_machine_readable(self) -> None:
        payload = _valid_payload()
        payload["period_start"] = "2026-07-11"
        payload["period_end"] = "2026-07-11"

        result = validate_menu_draft_for_context(
            draft=payload,
            planning_context=_planning_context(),
        )

        self.assertIn(ErrorCode.MENU_PERIOD_INCOMPLETE, _error_codes(result.errors))
        self.assertFalse(result.can_create_safe_preview)

    def test_missing_meal_slot_is_machine_readable(self) -> None:
        context = _context_with_second_slot()

        result = validate_menu_draft_for_context(
            draft=_valid_payload(),
            planning_context=context,
        )

        self.assertIn(ErrorCode.MENU_MEAL_SLOT_MISSING, _error_codes(result.errors))
        self.assertFalse(result.can_create_safe_preview)

    def test_strict_restriction_violation_is_machine_readable(self) -> None:
        payload = _valid_payload()
        cast(list[JsonObject], payload["generated_items"])[0]["title"] = "Peanut bowl"
        context = _context_with_constraints(
            {
                "strict_restrictions": [
                    {"kind": "ingredient_exclusion", "value": "peanut"}
                ]
            }
        )

        result = validate_menu_draft_for_context(
            draft=payload,
            planning_context=context,
        )

        self.assertIn(
            ErrorCode.MENU_STRICT_RESTRICTION_VIOLATED,
            _error_codes(result.errors),
        )
        self.assertFalse(result.can_create_safe_preview)

    def test_unavailable_equipment_is_machine_readable(self) -> None:
        payload = _valid_payload()
        cast(list[JsonObject], payload["generated_items"])[0][
            "required_equipment"
        ] = ["oven"]
        context = _context_with_constraints({"available_equipment": ["stovetop"]})

        result = validate_menu_draft_for_context(
            draft=payload,
            planning_context=context,
        )

        self.assertIn(ErrorCode.MENU_EQUIPMENT_UNAVAILABLE, _error_codes(result.errors))
        self.assertFalse(result.can_create_safe_preview)

    def test_active_time_limit_is_machine_readable(self) -> None:
        payload = _valid_payload()
        cast(list[JsonObject], payload["generated_items"])[0][
            "active_time_minutes"
        ] = 45
        context = _context_with_constraints({"max_active_time_minutes": 30})

        result = validate_menu_draft_for_context(
            draft=payload,
            planning_context=context,
        )

        self.assertIn(ErrorCode.MENU_ACTIVE_TIME_EXCEEDED, _error_codes(result.errors))
        self.assertFalse(result.can_create_safe_preview)

    def test_invalid_portions_are_machine_readable(self) -> None:
        payload = _valid_payload()
        cast(list[JsonObject], payload["generated_items"])[0]["portions"] = 0
        context = _context_with_constraints({"people_count": 2})

        result = validate_menu_draft_for_context(
            draft=payload,
            planning_context=context,
        )

        self.assertIn(ErrorCode.MENU_PORTIONS_INVALID, _error_codes(result.errors))
        self.assertFalse(result.can_create_safe_preview)

    def test_repetition_violation_is_machine_readable(self) -> None:
        context = _context_with_second_slot()
        payload = _valid_payload_with_second_slot()
        for item in cast(list[JsonObject], payload["generated_items"]):
            item["title"] = "Repeated dinner"

        result = validate_menu_draft_for_context(
            draft=payload,
            planning_context=context,
        )

        self.assertIn(ErrorCode.MENU_REPETITION_VIOLATED, _error_codes(result.errors))
        self.assertFalse(result.can_create_safe_preview)

    def test_referential_integrity_violation_is_machine_readable(self) -> None:
        payload = _valid_payload()
        cast(list[JsonObject], payload["generated_items"])[0][
            "meal_slot_id"
        ] = "unknown_slot"

        result = validate_menu_draft_for_context(
            draft=payload,
            planning_context=_planning_context(),
        )

        self.assertIn(
            ErrorCode.MENU_REFERENTIAL_INTEGRITY_VIOLATED,
            _error_codes(result.errors),
        )
        self.assertFalse(result.can_create_safe_preview)


def _planning_context() -> PlanningContext:
    payload = cast(JsonObject, _load_json("one_day/planning_context.json"))
    result = validate_contract("planning_context", payload)
    if not result.is_valid or result.value is None:
        raise AssertionError(result.errors)
    return cast(PlanningContext, result.value)


def _context_with_constraints(extra_constraints: JsonObject) -> PlanningContext:
    context = _planning_context()
    constraints = dict(context.constraints)
    constraints.update(extra_constraints)
    return replace(context, constraints=cast(JsonObject, constraints))


def _context_with_second_slot() -> PlanningContext:
    context = _planning_context()
    return replace(
        context,
        meal_slots=[*context.meal_slots, _second_meal_slot()],
    )


def _valid_payload() -> JsonObject:
    return cast(JsonObject, copy.deepcopy(_load_json("one_day/menu_draft.json")))


def _valid_payload_with_second_slot() -> JsonObject:
    payload = _valid_payload()
    cast(list[JsonObject], payload["meal_slots"]).append(_second_meal_slot())
    cast(list[JsonObject], payload["generated_items"]).append(
        {
            "meal_slot_id": "slot_002",
            "title": "M6A fake lunch",
        }
    )
    return payload


def _second_meal_slot() -> JsonObject:
    return {
        "schema_version": "m2.v1",
        "slot_id": "slot_002",
        "date": "2026-07-10",
        "meal_type": "lunch",
        "requirements": {},
    }


def _error_codes(errors: tuple[DomainError, ...]) -> set[ErrorCode]:
    return {error.code for error in errors}


def _load_json(relative_path: str) -> object:
    return json.loads((GOLDEN_ROOT / relative_path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
