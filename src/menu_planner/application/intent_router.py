from __future__ import annotations

import re
from typing import cast

from menu_planner.domain.contracts.models import SCHEMA_VERSION, JsonObject, JsonValue


class RuleBasedIntentRouter:
    name = "rule_based_baseline"
    version = "m5.rule_based_baseline.v1"

    def parse(self, user_text: str) -> JsonObject:
        normalized = _normalize(user_text)

        if _is_mixed_status_and_profile_request(normalized):
            return _intent(
                intent="submit_profile_draft",
                operation_class="draft_producing",
                parameters={"candidate_value": "peanuts"},
                ambiguities=[
                    "mixed_read_only_and_state_changing",
                    "strict_restriction_vs_soft_preference",
                ],
                scope="m4_profile",
                suggested_next_action="submit_profile_draft",
            )

        if _is_status_request(normalized):
            return _intent(
                intent="show_status",
                operation_class="read_only",
                scope="current_workflow",
                suggested_next_action="show_status",
            )

        if _is_administrative_request(normalized):
            return _intent(
                intent="install_skill",
                operation_class="administrative",
                parameters={"skill_name": "shell_tools"},
                scope="administrative",
                suggested_next_action="install_skill",
            )

        if _is_menu_generation_request(normalized):
            return _unsupported("generate_menu_draft")

        if _is_profile_confirmation_request(normalized):
            return _intent(
                intent="confirm_profile_draft",
                operation_class="state_changing",
                parameters=_confirmation_parameters(normalized),
                requires_confirmation=True,
                scope="m4_profile",
                suggested_next_action="confirm_profile_draft",
            )

        if _is_cancel_request(normalized):
            return _intent(
                intent="cancel_workflow",
                operation_class="state_changing",
                requires_confirmation=True,
                scope="current_workflow",
                suggested_next_action="cancel_workflow",
            )

        if _is_ambiguous_nuts_request(normalized):
            return _intent(
                intent="submit_profile_draft",
                operation_class="draft_producing",
                parameters={"candidate_value": "nuts"},
                ambiguities=["strict_restriction_vs_soft_preference"],
                scope="m4_profile",
                suggested_next_action="submit_profile_draft",
            )

        if _is_incomplete_profile_request(normalized):
            return _intent(
                intent="submit_profile_draft",
                operation_class="draft_producing",
                missing_fields=["profile_fields"],
                scope="m4_profile",
                suggested_next_action="submit_profile_draft",
            )

        if _is_complete_profile_request(normalized):
            return _intent(
                intent="submit_profile_draft",
                operation_class="draft_producing",
                parameters={"profile_fields": _profile_fields()},
                scope="m4_profile",
                suggested_next_action="submit_profile_draft",
            )

        return _unsupported("unknown")


def _normalize(user_text: str) -> str:
    return " ".join(user_text.casefold().split())


def _is_status_request(text: str) -> bool:
    return (
        "status" in text
        or "where are we" in text
        or re.search(r"\bstatis\b", text) is not None
    )


def _is_administrative_request(text: str) -> bool:
    administrative_terms = (
        "install",
        "skill",
        "shell",
        "terminal",
        "credential",
        "secret",
        "token",
        ".env",
        "model",
        "mcp",
    )
    return any(term in text for term in administrative_terms)


def _is_menu_generation_request(text: str) -> bool:
    return "menu" in text and any(term in text for term in ("plan", "weekly", "dinner"))


def _is_profile_confirmation_request(text: str) -> bool:
    return (
        "confirm" in text
        or "commit my profile" in text
        or "commit profile" in text
    )


def _confirmation_parameters(text: str) -> JsonObject:
    match = re.search(r"\bconfirm_[a-z0-9_]+\b", text)
    if match is None:
        return {}
    return {"confirmation_id": match.group(0)}


def _is_cancel_request(text: str) -> bool:
    return "cancel" in text


def _is_mixed_status_and_profile_request(text: str) -> bool:
    return "status" in text and "peanut" in text and "save" in text


def _is_ambiguous_nuts_request(text: str) -> bool:
    return "avoid nuts" in text or ("nuts" in text and "like" in text)


def _is_incomplete_profile_request(text: str) -> bool:
    incomplete_terms = ("save", "update", "delete", "permanently")
    return "profile" in text and any(term in text for term in incomplete_terms)


def _is_complete_profile_request(text: str) -> bool:
    required_terms = ("profile", "one person", "peanut", "vegetables", "stovetop")
    return all(term in text for term in required_terms)


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


def _unsupported(requested_intent: str) -> JsonObject:
    return _intent(
        intent="unsupported",
        operation_class="unsupported",
        parameters={"requested_intent": requested_intent},
        scope="out_of_scope",
        suggested_next_action="unsupported",
    )


def _intent(
    *,
    intent: str,
    operation_class: str,
    parameters: JsonObject | None = None,
    missing_fields: list[str] | None = None,
    ambiguities: list[str] | None = None,
    requires_confirmation: bool = False,
    scope: str,
    suggested_next_action: str,
) -> JsonObject:
    return {
        "schema_version": SCHEMA_VERSION,
        "intent": intent,
        "confidence": 1.0,
        "parameters": parameters or {},
        "missing_fields": cast(JsonValue, missing_fields or []),
        "ambiguities": cast(JsonValue, ambiguities or []),
        "operation_class": operation_class,
        "requires_confirmation": requires_confirmation,
        "scope": scope,
        "suggested_next_action": suggested_next_action,
    }
