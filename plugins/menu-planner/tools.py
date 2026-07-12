"""Narrow Hermes tool catalog for the Menu Planner plugin."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

JsonObject = dict[str, Any]

TOOLSET = "menu_planner"

MUTATION_READ_ONLY = "read_only"
MUTATION_PREVIEW_ONLY = "preview_only"
MUTATION_REQUIRES_CONFIRMATION = "requires_confirmation"
MUTATION_DIRECT_UPDATE_ALLOWED = "direct_update_allowed"

COMMON_PROPERTIES: JsonObject = {
    "correlation_id": {
        "type": "string",
        "minLength": 1,
        "description": "Caller-generated correlation id propagated to the API.",
    },
    "user_id": {
        "type": "string",
        "minLength": 1,
        "description": "Application user id owned by the Application service.",
    },
}


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: JsonObject
    success_schema: JsonObject
    error_schema: JsonObject
    http_method: str
    http_path: str
    mutation_policy: str

    @property
    def schema(self) -> JsonObject:
        return {
            "description": self.description,
            "parameters": self.parameters,
        }


def all_tool_definitions() -> tuple[ToolDefinition, ...]:
    return (
        ToolDefinition(
            name="menu_planner_get_workflow_status",
            description="Read the current Menu Planner workflow status.",
            parameters=_object_schema(
                properties={
                    **COMMON_PROPERTIES,
                },
                required=("correlation_id", "user_id"),
            ),
            success_schema=_success_schema("workflow_status"),
            error_schema=_error_schema(),
            http_method="GET",
            http_path="/m8/workflow/status",
            mutation_policy=MUTATION_READ_ONLY,
        ),
        ToolDefinition(
            name="menu_planner_preview_profile",
            description="Validate profile fields and create a commit preview.",
            parameters=_object_schema(
                properties={
                    **COMMON_PROPERTIES,
                    "profile_fields": {
                        "type": "object",
                        "description": "Structured profile fields for validation.",
                        "additionalProperties": True,
                    },
                    "idempotency_key": {
                        "type": "string",
                        "minLength": 1,
                    },
                },
                required=(
                    "correlation_id",
                    "user_id",
                    "profile_fields",
                    "idempotency_key",
                ),
            ),
            success_schema=_success_schema("profile_preview"),
            error_schema=_error_schema(),
            http_method="POST",
            http_path="/m8/profile/preview",
            mutation_policy=MUTATION_PREVIEW_ONLY,
        ),
        ToolDefinition(
            name="menu_planner_commit_profile",
            description="Commit a profile preview using an existing confirmation.",
            parameters=_object_schema(
                properties={
                    **COMMON_PROPERTIES,
                    "confirmation_id": {
                        "type": "string",
                        "minLength": 1,
                    },
                    "idempotency_key": {
                        "type": "string",
                        "minLength": 1,
                    },
                },
                required=(
                    "correlation_id",
                    "user_id",
                    "confirmation_id",
                    "idempotency_key",
                ),
            ),
            success_schema=_success_schema("profile_version"),
            error_schema=_error_schema(),
            http_method="POST",
            http_path="/m8/profile/commit",
            mutation_policy=MUTATION_REQUIRES_CONFIRMATION,
        ),
        ToolDefinition(
            name="menu_planner_generate_menu_draft",
            description="Generate a deterministic menu draft for an accepted scope.",
            parameters=_object_schema(
                properties={
                    **COMMON_PROPERTIES,
                    "planning_context_id": {
                        "type": "string",
                        "minLength": 1,
                    },
                    "idempotency_key": {
                        "type": "string",
                        "minLength": 1,
                    },
                },
                required=(
                    "correlation_id",
                    "user_id",
                    "planning_context_id",
                    "idempotency_key",
                ),
            ),
            success_schema=_success_schema("menu_draft"),
            error_schema=_error_schema(),
            http_method="POST",
            http_path="/m8/menu/draft",
            mutation_policy=MUTATION_PREVIEW_ONLY,
        ),
        ToolDefinition(
            name="menu_planner_generate_recipe_draft",
            description="Generate a deterministic recipe draft for one menu item.",
            parameters=_object_schema(
                properties={
                    **COMMON_PROPERTIES,
                    "menu_id": {
                        "type": "string",
                        "minLength": 1,
                    },
                    "menu_item_id": {
                        "type": "string",
                        "minLength": 1,
                    },
                    "idempotency_key": {
                        "type": "string",
                        "minLength": 1,
                    },
                },
                required=(
                    "correlation_id",
                    "user_id",
                    "menu_id",
                    "menu_item_id",
                    "idempotency_key",
                ),
            ),
            success_schema=_success_schema("recipe_draft"),
            error_schema=_error_schema(),
            http_method="POST",
            http_path="/m8/recipes/draft",
            mutation_policy=MUTATION_PREVIEW_ONLY,
        ),
        ToolDefinition(
            name="menu_planner_preview_menu_slot_replacement",
            description="Preview replacement of one meal slot in an accepted menu.",
            parameters=_object_schema(
                properties={
                    **COMMON_PROPERTIES,
                    "menu_id": {
                        "type": "string",
                        "minLength": 1,
                    },
                    "slot_id": {
                        "type": "string",
                        "minLength": 1,
                    },
                    "replacement_request": {
                        "type": "object",
                        "description": "Structured local replacement request.",
                        "additionalProperties": True,
                    },
                    "idempotency_key": {
                        "type": "string",
                        "minLength": 1,
                    },
                },
                required=(
                    "correlation_id",
                    "user_id",
                    "menu_id",
                    "slot_id",
                    "replacement_request",
                    "idempotency_key",
                ),
            ),
            success_schema=_success_schema("replacement_preview"),
            error_schema=_error_schema(),
            http_method="POST",
            http_path="/m8/menu/replacements/preview",
            mutation_policy=MUTATION_PREVIEW_ONLY,
        ),
        ToolDefinition(
            name="menu_planner_build_shopping_list",
            description="Build a deterministic shopping list from accepted sources.",
            parameters=_object_schema(
                properties={
                    **COMMON_PROPERTIES,
                    "menu_id": {
                        "type": "string",
                        "minLength": 1,
                    },
                    "menu_version": {
                        "type": "integer",
                        "minimum": 1,
                    },
                    "idempotency_key": {
                        "type": "string",
                        "minLength": 1,
                    },
                },
                required=(
                    "correlation_id",
                    "user_id",
                    "menu_id",
                    "menu_version",
                    "idempotency_key",
                ),
            ),
            success_schema=_success_schema("shopping_list"),
            error_schema=_error_schema(),
            http_method="POST",
            http_path="/m8/shopping-list/build",
            mutation_policy=MUTATION_PREVIEW_ONLY,
        ),
        ToolDefinition(
            name="menu_planner_update_shopping_checklist_item",
            description="Update one item in an existing shopping checklist.",
            parameters=_object_schema(
                properties={
                    **COMMON_PROPERTIES,
                    "shopping_list_id": {
                        "type": "string",
                        "minLength": 1,
                    },
                    "item_id": {
                        "type": "string",
                        "minLength": 1,
                    },
                    "checked": {
                        "type": "boolean",
                    },
                    "idempotency_key": {
                        "type": "string",
                        "minLength": 1,
                    },
                },
                required=(
                    "correlation_id",
                    "user_id",
                    "shopping_list_id",
                    "item_id",
                    "checked",
                    "idempotency_key",
                ),
            ),
            success_schema=_success_schema("shopping_checklist_item"),
            error_schema=_error_schema(),
            http_method="POST",
            http_path="/m8/shopping-list/items/update",
            mutation_policy=MUTATION_DIRECT_UPDATE_ALLOWED,
        ),
    )


def _object_schema(*, properties: JsonObject, required: tuple[str, ...]) -> JsonObject:
    return {
        "type": "object",
        "properties": properties,
        "required": list(required),
        "additionalProperties": False,
    }


def _success_schema(data_key: str) -> JsonObject:
    return _object_schema(
        properties={
            "success": {
                "type": "boolean",
                "const": True,
            },
            "operation_id": {
                "type": "string",
                "minLength": 1,
            },
            "correlation_id": {
                "type": "string",
                "minLength": 1,
            },
            "data": _object_schema(
                properties={
                    data_key: {
                        "type": "object",
                        "additionalProperties": True,
                    },
                    "next_allowed_actions": _string_array_schema(),
                    "warnings": _string_array_schema(),
                },
                required=(data_key, "next_allowed_actions"),
            ),
        },
        required=("success", "operation_id", "correlation_id", "data"),
    )


def _error_schema() -> JsonObject:
    return _object_schema(
        properties={
            "success": {
                "type": "boolean",
                "const": False,
            },
            "operation_id": {
                "type": "string",
            },
            "correlation_id": {
                "type": "string",
                "minLength": 1,
            },
            "retryable": {
                "type": "boolean",
            },
            "errors": {
                "type": "array",
                "items": _object_schema(
                    properties={
                        "code": {
                            "type": "string",
                            "minLength": 1,
                        },
                        "message": {
                            "type": "string",
                            "minLength": 1,
                        },
                        "field": {
                            "type": "string",
                        },
                    },
                    required=("code", "message"),
                ),
            },
            "next_allowed_actions": _string_array_schema(),
        },
        required=("success", "correlation_id", "retryable", "errors"),
    )


def _string_array_schema() -> JsonObject:
    return {
        "type": "array",
        "items": {
            "type": "string",
            "minLength": 1,
        },
    }
