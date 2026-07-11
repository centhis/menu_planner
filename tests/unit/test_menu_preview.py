from __future__ import annotations

import copy
import json
import pathlib
import unittest
from typing import cast

from menu_planner.application.menu_preview import (
    MENU_ENTITY_TYPE,
    MENU_PREVIEW_OPERATION,
    CreateMenuPreviewCommand,
    create_menu_preview,
)
from menu_planner.application.menu_validation import validate_menu_draft_for_context
from menu_planner.domain.contracts.models import JsonObject, PlanningContext
from menu_planner.domain.contracts.validation import validate_contract
from menu_planner.domain.errors import ErrorCode

ROOT = pathlib.Path(__file__).resolve().parents[2]
GOLDEN_ROOT = ROOT / "fixtures" / "golden" / "m6a_menu_draft_generation"


class MenuPreviewTests(unittest.TestCase):
    def test_validated_menu_draft_creates_safe_preview(self) -> None:
        result = create_menu_preview(_command_for_payload(_valid_payload()))

        self.assertTrue(result.ok, result.errors)
        self.assertIsNotNone(result.preview)
        assert result.preview is not None
        self.assertEqual(result.preview.operation, MENU_PREVIEW_OPERATION)
        self.assertEqual(result.preview.entity_ref, f"{MENU_ENTITY_TYPE}:menu_001")
        self.assertTrue(result.preview.requires_confirmation)
        self.assertFalse(result.side_effects_executed)
        self.assertFalse(result.confirmed_state_changed)
        self.assertEqual(result.preview.changes[0]["kind"], "menu_preview")
        self.assertEqual(result.preview.changes[0]["meal_count"], 1)

    def test_invalid_draft_cannot_create_preview(self) -> None:
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

        result = create_menu_preview(_command_for_payload(payload))

        self.assertFalse(result.ok)
        self.assertIsNone(result.preview)
        self.assertEqual(result.errors[0].code, ErrorCode.MENU_MEAL_SLOT_MISSING)
        self.assertFalse(result.side_effects_executed)
        self.assertFalse(result.confirmed_state_changed)

    def test_preview_hash_changes_when_menu_data_changes(self) -> None:
        base = create_menu_preview(_command_for_payload(_valid_payload()))
        changed_payload = _valid_payload()
        cast(list[JsonObject], changed_payload["generated_items"])[0][
            "title"
        ] = "Changed dinner"
        changed = create_menu_preview(_command_for_payload(changed_payload))

        self.assertTrue(base.ok, base.errors)
        self.assertTrue(changed.ok, changed.errors)
        assert base.preview is not None
        assert changed.preview is not None
        self.assertNotEqual(base.preview.summary_hash, changed.preview.summary_hash)

    def test_preview_does_not_bypass_confirmation_boundary(self) -> None:
        result = create_menu_preview(
            _command_for_payload(
                _valid_payload(),
                preview_id="preview_002",
                expected_version=0,
                draft_version=2,
            )
        )

        self.assertTrue(result.ok, result.errors)
        self.assertIsNotNone(result.preview)
        assert result.preview is not None
        self.assertTrue(result.preview.requires_confirmation)
        self.assertFalse(result.confirmed_state_changed)


def _command_for_payload(
    payload: JsonObject,
    *,
    preview_id: str = "preview_001",
    expected_version: int = 0,
    draft_version: int = 1,
) -> CreateMenuPreviewCommand:
    validation = validate_menu_draft_for_context(
        draft=payload,
        planning_context=_planning_context(),
    )
    return CreateMenuPreviewCommand(
        preview_id=preview_id,
        menu_id="menu_001",
        expected_version=expected_version,
        draft_version=draft_version,
        validation=validation,
    )


def _planning_context() -> PlanningContext:
    payload = cast(JsonObject, _load_json("one_day/planning_context.json"))
    result = validate_contract("planning_context", payload)
    if not result.is_valid or result.value is None:
        raise AssertionError(result.errors)
    return cast(PlanningContext, result.value)


def _valid_payload() -> JsonObject:
    return cast(JsonObject, copy.deepcopy(_load_json("one_day/menu_draft.json")))


def _load_json(relative_path: str) -> object:
    return json.loads((GOLDEN_ROOT / relative_path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
