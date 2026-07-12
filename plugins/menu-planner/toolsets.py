"""Workflow-scoped Hermes toolsets for Menu Planner."""

from __future__ import annotations

from dataclasses import dataclass

TOOLSET_SCHEMA_VERSION = "m8.toolsets.v1"

ROLE_USER = "user"
ROLE_ADMIN_DEV = "admin_dev"

STATE_INITIAL = "initial"
STATE_PROFILE_REQUIRED = "profile_required"
STATE_PROFILE_WAITING_CONFIRMATION = "profile_waiting_confirmation"
STATE_READY = "ready"
STATE_MENU_PLANNING = "menu_planning"
STATE_RECIPE_REPLACEMENT = "recipe_replacement"
STATE_SHOPPING_LIST = "shopping_list"
STATE_READ_ONLY = "read_only"

READ_ONLY_TOOLSET = "menu_planner_read_only"
PROFILE_TOOLSET = "menu_planner_profile"
MENU_TOOLSET = "menu_planner_menu"
RECIPE_TOOLSET = "menu_planner_recipe"
SHOPPING_TOOLSET = "menu_planner_shopping"
ADMIN_DEV_TOOLSET = "menu_planner_admin_dev"

STATUS_TOOL = "menu_planner_get_workflow_status"
PROFILE_PREVIEW_TOOL = "menu_planner_preview_profile"
PROFILE_COMMIT_TOOL = "menu_planner_commit_profile"
MENU_DRAFT_TOOL = "menu_planner_generate_menu_draft"
RECIPE_DRAFT_TOOL = "menu_planner_generate_recipe_draft"
REPLACEMENT_PREVIEW_TOOL = "menu_planner_preview_menu_slot_replacement"
SHOPPING_LIST_BUILD_TOOL = "menu_planner_build_shopping_list"
SHOPPING_CHECKLIST_UPDATE_TOOL = "menu_planner_update_shopping_checklist_item"

USER_FORBIDDEN_TOOL_WORDS = (
    "terminal",
    "shell",
    "filesystem",
    "browser",
    "sql",
    "secret",
    "admin",
    "model",
    "skill",
)


@dataclass(frozen=True)
class ToolsetDefinition:
    name: str
    role: str
    workflow_states: tuple[str, ...]
    tool_names: tuple[str, ...]


def all_toolsets() -> tuple[ToolsetDefinition, ...]:
    return (
        ToolsetDefinition(
            name=READ_ONLY_TOOLSET,
            role=ROLE_USER,
            workflow_states=(
                STATE_INITIAL,
                STATE_PROFILE_REQUIRED,
                STATE_PROFILE_WAITING_CONFIRMATION,
                STATE_READY,
                STATE_MENU_PLANNING,
                STATE_RECIPE_REPLACEMENT,
                STATE_SHOPPING_LIST,
                STATE_READ_ONLY,
            ),
            tool_names=(STATUS_TOOL,),
        ),
        ToolsetDefinition(
            name=PROFILE_TOOLSET,
            role=ROLE_USER,
            workflow_states=(
                STATE_INITIAL,
                STATE_PROFILE_REQUIRED,
                STATE_PROFILE_WAITING_CONFIRMATION,
            ),
            tool_names=(PROFILE_PREVIEW_TOOL, PROFILE_COMMIT_TOOL),
        ),
        ToolsetDefinition(
            name=MENU_TOOLSET,
            role=ROLE_USER,
            workflow_states=(STATE_READY, STATE_MENU_PLANNING),
            tool_names=(MENU_DRAFT_TOOL,),
        ),
        ToolsetDefinition(
            name=RECIPE_TOOLSET,
            role=ROLE_USER,
            workflow_states=(STATE_READY, STATE_RECIPE_REPLACEMENT),
            tool_names=(RECIPE_DRAFT_TOOL, REPLACEMENT_PREVIEW_TOOL),
        ),
        ToolsetDefinition(
            name=SHOPPING_TOOLSET,
            role=ROLE_USER,
            workflow_states=(STATE_READY, STATE_SHOPPING_LIST),
            tool_names=(SHOPPING_LIST_BUILD_TOOL, SHOPPING_CHECKLIST_UPDATE_TOOL),
        ),
        ToolsetDefinition(
            name=ADMIN_DEV_TOOLSET,
            role=ROLE_ADMIN_DEV,
            workflow_states=(),
            tool_names=(),
        ),
    )


def user_tool_names_for_state(workflow_state: str) -> tuple[str, ...]:
    names: list[str] = []
    for toolset in all_toolsets():
        if toolset.role != ROLE_USER:
            continue
        if workflow_state not in toolset.workflow_states:
            continue
        names.extend(toolset.tool_names)
    return tuple(dict.fromkeys(names))


def as_config() -> dict[str, object]:
    return {
        "schema_version": TOOLSET_SCHEMA_VERSION,
        "toolsets": [
            {
                "name": toolset.name,
                "role": toolset.role,
                "workflow_states": list(toolset.workflow_states),
                "tool_names": list(toolset.tool_names),
            }
            for toolset in all_toolsets()
        ],
    }
