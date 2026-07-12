"""Application-sourced context loader for Menu Planner Hermes tools."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

try:
    from . import adapter, toolsets
except ImportError:  # pragma: no cover - supports direct Hermes file loading.
    import adapter  # type: ignore[no-redef]
    import toolsets  # type: ignore[no-redef]

JsonObject = dict[str, Any]

MAX_MEMORY_HINT_CHARS = 500
CONTEXT_PATH_PREFIX = "/m8/context/users/"
CONFIRMED_STATE_KEYS = (
    "confirmed_profile",
    "confirmed_menu",
    "confirmed_recipes",
    "confirmed_shopping_list",
)


def load_application_context(
    *,
    client: adapter.ApplicationHttpClient,
    user_id: str,
    correlation_id: str,
    memory_hint: str | None = None,
) -> JsonObject:
    response = client.get(
        CONTEXT_PATH_PREFIX + quote(user_id, safe=""),
        correlation_id=correlation_id,
    )
    if not response.get("ok"):
        return {
            "ok": False,
            "correlation_id": correlation_id,
            "source": "application_api",
            "error": response.get(
                "error",
                {
                    "code": "application_context_unavailable",
                    "message": "Application context is unavailable.",
                },
            ),
        }

    data = response.get("data")
    if not isinstance(data, dict):
        return _invalid_context(
            correlation_id,
            "Application context payload is invalid.",
        )

    workflow_state = data.get("workflow_state")
    if not isinstance(workflow_state, str) or not workflow_state:
        return _invalid_context(
            correlation_id,
            "Application context lacks workflow_state.",
        )

    return {
        "ok": True,
        "correlation_id": correlation_id,
        "source": "application_api",
        "user_id": user_id,
        "workflow_state": workflow_state,
        "allowed_tools": list(toolsets.user_tool_names_for_state(workflow_state)),
        "toolsets": toolsets.as_config(),
        "confirmed_state": {
            key: data.get(key) for key in CONFIRMED_STATE_KEYS if key in data
        },
        "memory_hint": _bounded_memory_hint(memory_hint),
    }


def _invalid_context(correlation_id: str, message: str) -> JsonObject:
    return {
        "ok": False,
        "correlation_id": correlation_id,
        "source": "application_api",
        "error": {
            "code": "application_context_invalid",
            "message": message,
        },
    }


def _bounded_memory_hint(memory_hint: str | None) -> str:
    if not memory_hint:
        return ""
    return memory_hint[:MAX_MEMORY_HINT_CHARS]
