"""Agentic and guided mode contracts for Menu Planner Hermes integration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

try:
    from . import handlers, tools
except ImportError:  # pragma: no cover - supports direct Hermes file loading.
    import handlers  # type: ignore[no-redef]
    import tools  # type: ignore[no-redef]

JsonObject = dict[str, Any]

MODE_AGENTIC = "agentic"
MODE_GUIDED = "guided"


@dataclass(frozen=True)
class ModePlan:
    mode: str
    tool_name: str
    schema: JsonObject
    http_method: str
    http_path: str


def agentic_tool_plans(context: JsonObject) -> tuple[ModePlan, ...]:
    allowed_tools = context.get("allowed_tools")
    if not isinstance(allowed_tools, list):
        return ()
    return tuple(
        _plan(MODE_AGENTIC, definition)
        for definition in tools.all_tool_definitions()
        if definition.name in allowed_tools
    )


def guided_next_plan(context: JsonObject) -> ModePlan | None:
    workflow_state = context.get("workflow_state")
    if workflow_state == "profile_required":
        return _plan(MODE_GUIDED, _definition("menu_planner_preview_profile"))
    if workflow_state == "menu_planning":
        return _plan(MODE_GUIDED, _definition("menu_planner_generate_menu_draft"))
    if workflow_state == "shopping_list":
        return _plan(MODE_GUIDED, _definition("menu_planner_build_shopping_list"))
    return None


def run_guided_fake_workflow(
    *,
    context: JsonObject,
    fake_model_args: JsonObject,
    bound_user_id: str,
    client_factory: handlers.ClientFactory,
) -> JsonObject:
    plan = guided_next_plan(context)
    if plan is None:
        return {
            "ok": False,
            "mode": MODE_GUIDED,
            "error": {
                "code": "guided_no_step",
                "message": "No guided step is available for this context.",
            },
        }

    result = handlers.handle_tool_call(
        definition=_definition(plan.tool_name),
        args=fake_model_args,
        workflow_state=_string_or_default(context.get("workflow_state"), ""),
        bound_user_id=bound_user_id,
        client_factory=client_factory,
    )
    return {
        "ok": True,
        "mode": MODE_GUIDED,
        "tool_name": plan.tool_name,
        "http_method": plan.http_method,
        "http_path": plan.http_path,
        "result": json.loads(result),
    }


def _plan(mode: str, definition: tools.ToolDefinition) -> ModePlan:
    return ModePlan(
        mode=mode,
        tool_name=definition.name,
        schema=definition.schema,
        http_method=definition.http_method,
        http_path=definition.http_path,
    )


def _definition(tool_name: str) -> tools.ToolDefinition:
    for definition in tools.all_tool_definitions():
        if definition.name == tool_name:
            return definition
    raise ValueError(f"Unknown Menu Planner tool: {tool_name}")


def _string_or_default(value: Any, default: str) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return default
    return str(value)
