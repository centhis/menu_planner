"""Hermes tool handlers for Menu Planner.

Handlers repeat critical policy checks before touching the Application HTTP API.
Hooks are defense in depth, not the source of authority.
"""

from __future__ import annotations

import os
from typing import Any, Callable

try:
    from . import adapter, policy, results, toolsets, tools
except ImportError:  # pragma: no cover - supports direct Hermes file loading.
    import adapter  # type: ignore[no-redef]
    import policy  # type: ignore[no-redef]
    import results  # type: ignore[no-redef]
    import toolsets  # type: ignore[no-redef]
    import tools  # type: ignore[no-redef]

JsonObject = dict[str, Any]
ClientFactory = Callable[[], adapter.ApplicationHttpClient]

API_BASE_URL_ENV = "MENU_PLANNER_API_BASE_URL"


def register_tools(ctx, *, client_factory: ClientFactory | None = None) -> None:
    for definition in tools.all_tool_definitions():
        ctx.register_tool(
            name=definition.name,
            toolset=tools.TOOLSET,
            schema=definition.schema,
            handler=make_handler(definition, client_factory=client_factory),
            description=definition.description,
        )


def make_handler(
    definition: tools.ToolDefinition,
    *,
    client_factory: ClientFactory | None = None,
) -> Callable[..., str]:
    def handle(args: JsonObject, **kwargs: Any) -> str:
        return handle_tool_call(
            definition=definition,
            args=args,
            workflow_state=_string_or_default(kwargs.get("workflow_state"), ""),
            bound_user_id=_string_or_default(kwargs.get("bound_user_id"), ""),
            client_factory=client_factory,
        )

    return handle


def handle_tool_call(
    *,
    definition: tools.ToolDefinition,
    args: JsonObject,
    workflow_state: str,
    bound_user_id: str,
    client_factory: ClientFactory | None = None,
) -> str:
    correlation_id = _string_or_default(args.get("correlation_id"), "")
    operation_id = _string_or_default(
        args.get("idempotency_key"),
        f"{definition.name}:{correlation_id}",
    )

    policy_result = policy.evaluate_pre_tool_policy(
        policy.ToolCallContext(
            tool_name=definition.name,
            args=args,
            workflow_state=workflow_state,
            user_id=_string_or_default(args.get("user_id"), ""),
            bound_user_id=bound_user_id,
        )
    )
    if not policy_result["allowed"]:
        return results.tool_error(
            operation_id=operation_id,
            correlation_id=correlation_id,
            retryable=False,
            errors=tuple(policy_result["violations"]),
            next_allowed_actions=tuple(
                toolsets.user_tool_names_for_state(workflow_state)
            ),
        )

    client = (client_factory or _default_client_factory)()
    if definition.http_method == "GET":
        response = client.get(definition.http_path, correlation_id=correlation_id)
    else:
        response = client.post(
            definition.http_path,
            payload=args,
            correlation_id=correlation_id,
            idempotency_key=_string_or_default(args.get("idempotency_key"), ""),
        )
    return _tool_result_from_application_response(
        definition=definition,
        response=response,
        operation_id=operation_id,
        correlation_id=correlation_id,
        workflow_state=workflow_state,
    )


def _default_client_factory() -> adapter.ApplicationHttpClient:
    return adapter.ApplicationHttpClient(os.environ.get(API_BASE_URL_ENV, ""))


def _tool_result_from_application_response(
    *,
    definition: tools.ToolDefinition,
    response: JsonObject,
    operation_id: str,
    correlation_id: str,
    workflow_state: str,
) -> str:
    if not response.get("ok"):
        error = response.get("error")
        if not isinstance(error, dict):
            error = {
                "code": "application_error",
                "message": "Application HTTP API returned an error.",
            }
        return results.tool_error(
            operation_id=operation_id,
            correlation_id=correlation_id,
            errors=(error,),
            next_allowed_actions=tuple(
                toolsets.user_tool_names_for_state(workflow_state)
            ),
        )

    data = response.get("data")
    if not isinstance(data, dict):
        data = {}
    return results.tool_success(
        operation_id=operation_id,
        correlation_id=correlation_id,
        data=data,
        entity_id=_optional_string(data.get("entity_id")),
        entity_version=_optional_int(data.get("entity_version")),
        warnings=_string_tuple(data.get("warnings")),
        next_allowed_actions=tuple(toolsets.user_tool_names_for_state(workflow_state)),
    )


def _string_or_default(value: Any, default: str) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return default
    return str(value)


def _optional_string(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _optional_int(value: Any) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        return ()
    return tuple(item for item in value if isinstance(item, str))
