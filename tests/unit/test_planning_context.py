from __future__ import annotations

import unittest

from menu_planner.application.planning_context import (
    BuildPlanningContextRequest,
    PlanningMealSlotRequest,
    build_planning_context,
)
from menu_planner.domain.contracts.models import (
    SCHEMA_VERSION,
    JsonObject,
    ProfileVersion,
)
from menu_planner.domain.errors import ErrorCode


class PlanningContextBuilderTests(unittest.TestCase):
    def test_builds_context_from_confirmed_profile_and_explicit_request(self) -> None:
        result = build_planning_context(
            confirmed_profile=_profile_version(),
            request=_request(),
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.errors, ())
        self.assertIsNotNone(result.context)
        assert result.context is not None
        self.assertEqual(result.context.user_id, "user_001")
        self.assertEqual(result.context.profile_version, 1)
        self.assertEqual(result.context.planning_request_id, "planning_request_001")
        self.assertEqual(result.context.period_start, "2026-07-10")
        self.assertEqual(result.context.period_end, "2026-07-10")
        self.assertEqual(len(result.context.meal_slots), 1)
        self.assertEqual(
            result.context.constraints["available_equipment"],
            ["stovetop"],
        )
        self.assertEqual(result.context.constraints["max_active_time_minutes"], 30)

    def test_rejects_unvalidated_profile_fields_with_stable_error(self) -> None:
        profile = ProfileVersion(
            schema_version=SCHEMA_VERSION,
            user_id="user_001",
            profile_id="profile:user_001",
            version=1,
            fields={},
        )

        result = build_planning_context(
            confirmed_profile=profile,
            request=_request(),
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.context)
        self.assertEqual(result.errors[0].code, ErrorCode.MISSING_REQUIRED_FIELD)
        self.assertEqual(result.errors[0].path, ("fields.user_facts",))

    def test_rejects_empty_explicit_meal_slots(self) -> None:
        result = build_planning_context(
            confirmed_profile=_profile_version(),
            request=_request(meal_slots=()),
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.context)
        self.assertEqual(result.errors[0].code, ErrorCode.INVALID_RANGE)
        self.assertEqual(result.errors[0].path, ("meal_slots",))

    def test_rejects_profile_user_mismatch(self) -> None:
        result = build_planning_context(
            confirmed_profile=_profile_version(),
            request=_request(user_id="user_002"),
        )

        self.assertFalse(result.ok)
        self.assertIsNone(result.context)
        self.assertEqual(result.errors[0].code, ErrorCode.OWNERSHIP_REQUIRED)
        self.assertEqual(
            result.errors[0].details,
            {"entity_ref": "profile:user_001", "user_id": "user_002"},
        )


def _request(
    *,
    user_id: str = "user_001",
    meal_slots: tuple[PlanningMealSlotRequest, ...] | None = None,
) -> BuildPlanningContextRequest:
    return BuildPlanningContextRequest(
        planning_request_id="planning_request_001",
        user_id=user_id,
        context_id="planning_context_001",
        period_start="2026-07-10",
        period_end="2026-07-10",
        meal_slots=meal_slots
        if meal_slots is not None
        else (
            PlanningMealSlotRequest(
                slot_id="slot_001",
                date="2026-07-10",
                meal_type="dinner",
                requirements={},
            ),
        ),
    )


def _profile_version() -> ProfileVersion:
    return ProfileVersion(
        schema_version=SCHEMA_VERSION,
        user_id="user_001",
        profile_id="profile:user_001",
        version=1,
        fields=_profile_fields(),
    )


def _profile_fields() -> JsonObject:
    return {
        "user_facts": {
            "people_count": 1,
            "locale": "en-US",
            "timezone": "UTC",
            "available_equipment": ["stovetop"],
            "default_max_active_time_minutes": 30,
        },
        "strict_restrictions": [
            {
                "kind": "ingredient_exclusion",
                "value": "peanut",
            }
        ],
        "soft_preferences": [
            {
                "direction": "prefer",
                "value": "vegetables",
            }
        ],
    }


if __name__ == "__main__":
    unittest.main()
