from __future__ import annotations

import copy
import json
import pathlib
import unittest
from typing import cast

from menu_planner.application.menu_generation import MenuDraftGenerationRequest
from menu_planner.application.menu_repair import (
    MenuDraftRepairGenerator,
    repair_menu_draft,
)
from menu_planner.domain.contracts.models import JsonObject, PlanningContext
from menu_planner.domain.contracts.validation import validate_contract
from menu_planner.domain.errors import DomainError, ErrorCode

ROOT = pathlib.Path(__file__).resolve().parents[2]
GOLDEN_ROOT = ROOT / "fixtures" / "golden" / "m6a_menu_draft_generation"


class MenuDraftRepairTests(unittest.TestCase):
    def test_happy_repair_path_uses_structured_errors_and_stops(self) -> None:
        generator = OneBrokenThenValidRepairGenerator()

        result = repair_menu_draft(
            request=_request(),
            max_attempts=3,
            repair_generator=generator,
        )

        self.assertTrue(result.ok, result.errors)
        self.assertIsNotNone(result.draft)
        self.assertEqual(
            generator.previous_error_codes_seen,
            ("menu.meal_slot_missing",),
        )
        self.assertEqual(len(result.attempts), 2)
        self.assertFalse(result.attempts[0].ok)
        self.assertTrue(result.attempts[1].ok)
        self.assertEqual(result.attempts[0].error_codes, ("menu.meal_slot_missing",))
        self.assertFalse(result.side_effects_executed)
        self.assertFalse(result.confirmed_state_changed)

    def test_max_attempt_failure_is_controlled(self) -> None:
        result = repair_menu_draft(
            request=_request(),
            max_attempts=2,
            repair_generator=AlwaysBrokenRepairGenerator(),
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.draft)
        self.assertEqual(len(result.attempts), 2)
        self.assertEqual(result.max_attempts, 2)
        self.assertIn(ErrorCode.MENU_MEAL_SLOT_MISSING, _error_codes(result.errors))
        self.assertFalse(result.side_effects_executed)
        self.assertFalse(result.confirmed_state_changed)

    def test_malformed_output_is_reported_without_preview_or_commit(self) -> None:
        result = repair_menu_draft(
            request=_request(),
            max_attempts=1,
            repair_generator=MalformedRepairGenerator(),
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.draft)
        self.assertEqual(result.errors[0].code, ErrorCode.MISSING_REQUIRED_FIELD)
        self.assertEqual(
            result.attempts[0].error_codes,
            ("contract.missing_required_field",),
        )
        self.assertFalse(result.validation.can_create_safe_preview)
        self.assertFalse(result.side_effects_executed)
        self.assertFalse(result.confirmed_state_changed)

    def test_invalid_max_attempts_is_rejected_before_generation(self) -> None:
        generator = AlwaysBrokenRepairGenerator()

        with self.assertRaises(ValueError):
            repair_menu_draft(
                request=_request(),
                max_attempts=0,
                repair_generator=generator,
            )

        self.assertEqual(generator.calls, 0)


class OneBrokenThenValidRepairGenerator(MenuDraftRepairGenerator):
    name = "one_broken_then_valid_repair_generator"
    version = "test"

    def __init__(self) -> None:
        self.calls = 0
        self.previous_error_codes_seen: tuple[str, ...] = ()

    def generate_repair(
        self,
        *,
        request: MenuDraftGenerationRequest,
        previous_errors: tuple[DomainError, ...],
    ) -> JsonObject:
        self.calls += 1
        if previous_errors:
            self.previous_error_codes_seen = tuple(
                error.code.value for error in previous_errors
            )
        if self.calls == 1:
            return _payload_with_extra_draft_slot()
        return _valid_payload()


class AlwaysBrokenRepairGenerator(MenuDraftRepairGenerator):
    name = "always_broken_repair_generator"
    version = "test"

    def __init__(self) -> None:
        self.calls = 0

    def generate_repair(
        self,
        *,
        request: MenuDraftGenerationRequest,
        previous_errors: tuple[DomainError, ...],
    ) -> JsonObject:
        self.calls += 1
        return _payload_with_extra_draft_slot()


class MalformedRepairGenerator(MenuDraftRepairGenerator):
    name = "malformed_repair_generator"
    version = "test"

    def generate_repair(
        self,
        *,
        request: MenuDraftGenerationRequest,
        previous_errors: tuple[DomainError, ...],
    ) -> JsonObject:
        return cast(JsonObject, _load_json("invalid/missing_generated_items.json"))


def _request() -> MenuDraftGenerationRequest:
    return MenuDraftGenerationRequest(
        draft_id="menu_draft_001",
        planning_context=_planning_context(),
    )


def _planning_context() -> PlanningContext:
    payload = cast(JsonObject, _load_json("one_day/planning_context.json"))
    result = validate_contract("planning_context", payload)
    if not result.is_valid or result.value is None:
        raise AssertionError(result.errors)
    return cast(PlanningContext, result.value)


def _valid_payload() -> JsonObject:
    return cast(JsonObject, copy.deepcopy(_load_json("one_day/menu_draft.json")))


def _payload_with_extra_draft_slot() -> JsonObject:
    payload = _valid_payload()
    cast(list[JsonObject], payload["meal_slots"]).append(
        {
            "schema_version": "m2.v1",
            "slot_id": "slot_002",
            "date": "2026-07-10",
            "meal_type": "lunch",
            "requirements": {},
        }
    )
    return payload


def _error_codes(errors: tuple[DomainError, ...]) -> set[ErrorCode]:
    return {error.code for error in errors}


def _load_json(relative_path: str) -> object:
    return json.loads((GOLDEN_ROOT / relative_path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
