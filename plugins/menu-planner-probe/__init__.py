"""Stage 0 Menu Planner probe plugin.

This plugin is intentionally inert: it performs no I/O, uses no network, and
contains no Menu Planner business logic. It exists only to prove Hermes can
discover a host-mounted plugin and register a structured tool.
"""

from __future__ import annotations

import json
from typing import Any


TOOL_NAME = "menu_planner_probe_echo"
TOOLSET = "menu_planner_probe"


SCHEMA = {
    "description": "Echo a payload with a caller-supplied request_id.",
    "parameters": {
        "type": "object",
        "properties": {
            "request_id": {
                "type": "string",
                "description": "Caller-generated operation identifier.",
            },
            "payload": {
                "type": "string",
                "description": "Opaque test payload to echo.",
            },
        },
        "required": ["request_id", "payload"],
        "additionalProperties": False,
    },
}


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True)


def _validation_error(message: str, *, request_id: Any = None) -> str:
    return _json(
        {
            "success": False,
            "error": {
                "code": "validation_error",
                "message": message,
            },
            "operation_id": request_id if isinstance(request_id, str) else "",
        }
    )


def _handle_probe_echo(args: dict[str, Any], **_kwargs: Any) -> str:
    request_id = args.get("request_id")
    payload = args.get("payload")

    if not isinstance(request_id, str) or not request_id:
        return _validation_error("request_id must be a non-empty string")
    if not isinstance(payload, str):
        return _validation_error(
            "payload must be a string",
            request_id=request_id,
        )

    return _json(
        {
            "success": True,
            "operation_id": request_id,
            "data": {
                "payload": payload,
            },
        }
    )


def _hook_payload(event: str, **kwargs: Any) -> dict[str, Any]:
    return {
        "plugin": "menu-planner-probe",
        "event": event,
        "tool_name": kwargs.get("tool_name", ""),
        "request_id": (kwargs.get("args") or {}).get("request_id", ""),
        "session_id": kwargs.get("session_id", ""),
        "task_id": kwargs.get("task_id", ""),
        "turn_id": kwargs.get("turn_id", ""),
        "tool_call_id": kwargs.get("tool_call_id", ""),
        "api_request_id": kwargs.get("api_request_id", ""),
        "platform": kwargs.get("platform", ""),
    }


def _on_pre_tool_call(**kwargs: Any) -> dict[str, Any]:
    payload = _hook_payload("pre_tool_call", **kwargs)
    if payload["request_id"] == "stage0-block-001":
        return {
            "action": "block",
            "message": "menu-planner-probe blocked stage0-block-001",
            "probe": payload,
        }
    return payload


def _on_post_tool_call(**kwargs: Any) -> dict[str, Any]:
    payload = _hook_payload("post_tool_call", **kwargs)
    payload["result_seen"] = "result" in kwargs
    return payload


def register(ctx) -> None:
    ctx.register_tool(
        name=TOOL_NAME,
        toolset=TOOLSET,
        schema=SCHEMA,
        handler=_handle_probe_echo,
        description=SCHEMA["description"],
    )
    ctx.register_hook("pre_tool_call", _on_pre_tool_call)
    ctx.register_hook("post_tool_call", _on_post_tool_call)
