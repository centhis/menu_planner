"""Message and tool policy hooks for the Menu Planner Hermes plugin."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

try:
    from . import toolsets, tools
except ImportError:  # pragma: no cover - supports direct Hermes file loading.
    import toolsets  # type: ignore[no-redef]
    import tools  # type: ignore[no-redef]

JsonObject = dict[str, Any]

MAX_MESSAGE_CHARS = 4000
ALLOWED_CHANNELS = ("telegram", "web", "cli", "test")
ALLOWED_WORKFLOW_STATES = (
    "initial",
    "profile_required",
    "profile_waiting_confirmation",
    "ready",
    "menu_planning",
    "recipe_replacement",
    "shopping_list",
    "read_only",
)

ADMIN_ATTEMPT_TERMS = (
    "admin",
    "browser",
    "credentials",
    "docker",
    "filesystem",
    "ignore previous",
    "model provider",
    "openai_api_key",
    "password",
    "secret",
    "shell",
    "sql",
    "telegram_bot_token",
    "terminal",
    "toolset",
)

SECRET_ACCESS_TERMS = (
    "api_key",
    "auth.json",
    "credential",
    "password",
    "secret",
    "telegram_bot_token",
    "token",
)


@dataclass(frozen=True)
class MessageContext:
    text: str
    channel: str
    user_id: str
    bound_user_id: str
    workflow_state: str
    authenticated: bool
    rate_limited: bool = False


@dataclass(frozen=True)
class ToolCallContext:
    tool_name: str
    args: JsonObject
    workflow_state: str
    user_id: str
    bound_user_id: str


def evaluate_pre_message_policy(context: MessageContext) -> JsonObject:
    violations: list[JsonObject] = []

    if not context.authenticated:
        violations.append(
            _violation("unauthenticated_user", "User is not authenticated.")
        )
    if not context.user_id:
        violations.append(_violation("missing_user", "Message source has no user id."))
    if context.bound_user_id and context.user_id != context.bound_user_id:
        violations.append(_violation("user_binding_mismatch", "User binding mismatch."))
    if context.channel not in ALLOWED_CHANNELS:
        violations.append(_violation("disallowed_channel", "Channel is not allowed."))
    if len(context.text) > MAX_MESSAGE_CHARS:
        violations.append(_violation("message_too_large", "Message is too large."))
    if context.rate_limited:
        violations.append(_violation("rate_limited", "Message is rate limited."))
    if context.workflow_state not in ALLOWED_WORKFLOW_STATES:
        violations.append(_violation("unknown_workflow", "Workflow state is unknown."))
    if _contains_admin_attempt(context.text):
        violations.append(
            _violation(
                "administrative_command_attempt",
                "Administrative commands are not allowed in user sessions.",
            )
        )

    if violations:
        return {
            "allowed": False,
            "action": "skip",
            "reason": violations[0]["code"],
            "violations": violations,
        }

    return {
        "allowed": True,
        "action": "allow",
        "reason": "",
        "violations": [],
    }


def evaluate_pre_tool_policy(context: ToolCallContext) -> JsonObject:
    violations: list[JsonObject] = []
    definition = _tool_definition(context.tool_name)

    if definition is None:
        violations.append(_violation("unknown_tool", "Tool is not in the M8 catalog."))
    if _looks_like_admin_tool(context.tool_name):
        violations.append(_violation("admin_tool", "Administrative tools are blocked."))
    if context.workflow_state not in ALLOWED_WORKFLOW_STATES:
        violations.append(_violation("unknown_workflow", "Workflow state is unknown."))
    elif context.tool_name not in toolsets.user_tool_names_for_state(
        context.workflow_state
    ):
        violations.append(
            _violation("tool_not_in_active_toolset", "Tool is not active now.")
        )
    if not context.user_id:
        violations.append(_violation("missing_user", "Tool call has no user id."))
    if context.bound_user_id and context.user_id != context.bound_user_id:
        violations.append(_violation("user_mismatch", "Tool call user mismatch."))
    if not isinstance(context.args.get("correlation_id"), str):
        violations.append(
            _violation("missing_correlation_id", "Tool call lacks correlation id.")
        )
    if _contains_secret_access(context.args):
        violations.append(_violation("secret_access", "Secret access is blocked."))
    if definition is not None:
        if definition.mutation_policy == tools.MUTATION_REQUIRES_CONFIRMATION:
            if not isinstance(context.args.get("confirmation_id"), str):
                violations.append(
                    _violation(
                        "confirmation_required",
                        "Tool requires an existing confirmation.",
                    )
                )
        violations.extend(_validate_args(definition.parameters, context.args))
        if definition.http_method == "POST" and not isinstance(
            context.args.get("idempotency_key"), str
        ):
            violations.append(
                _violation(
                    "idempotency_key_required",
                    "State-changing tool call requires idempotency key.",
                )
            )

    if violations:
        return {
            "allowed": False,
            "action": "block",
            "reason": violations[0]["code"],
            "violations": violations,
        }

    return {
        "allowed": True,
        "action": "allow",
        "reason": "",
        "violations": [],
    }


def pre_gateway_dispatch(**kwargs: Any) -> JsonObject:
    event = kwargs.get("event")
    context = message_context_from_event(event)
    result = evaluate_pre_message_policy(context)
    if result["allowed"]:
        return {"action": "allow", "policy": result}
    return {
        "action": "skip",
        "reason": result["reason"],
        "policy": result,
    }


def pre_tool_call(**kwargs: Any) -> JsonObject:
    args = kwargs.get("args")
    if not isinstance(args, dict):
        args = {}
    context = ToolCallContext(
        tool_name=_string_or_default(kwargs.get("tool_name"), ""),
        args=args,
        workflow_state=_string_or_default(kwargs.get("workflow_state"), "ready"),
        user_id=_string_or_default(kwargs.get("user_id"), args.get("user_id", "")),
        bound_user_id=_string_or_default(
            kwargs.get("bound_user_id"),
            args.get("user_id", ""),
        ),
    )
    result = evaluate_pre_tool_policy(context)
    if result["allowed"]:
        return {"action": "allow", "policy": result}
    return {
        "action": "block",
        "message": json.dumps(
            {
                "success": False,
                "error": {
                    "code": result["reason"],
                    "message": "Menu Planner pre-tool policy blocked the call.",
                },
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        "policy": result,
    }


def message_context_from_event(event: Any) -> MessageContext:
    source = getattr(event, "source", None)
    metadata = getattr(event, "metadata", None) or {}
    channel = _string_or_default(
        metadata.get("channel"),
        _source_platform(source),
    )
    user_id = _string_or_default(
        metadata.get("user_id"),
        _source_user_id(source),
    )
    bound_user_id = _string_or_default(metadata.get("bound_user_id"), user_id)
    workflow_state = _string_or_default(metadata.get("workflow_state"), "initial")
    authenticated = bool(metadata.get("authenticated", bool(user_id)))
    rate_limited = bool(metadata.get("rate_limited", False))

    return MessageContext(
        text=_string_or_default(getattr(event, "text", ""), ""),
        channel=channel,
        user_id=user_id,
        bound_user_id=bound_user_id,
        workflow_state=workflow_state,
        authenticated=authenticated,
        rate_limited=rate_limited,
    )


def _violation(code: str, message: str) -> JsonObject:
    return {
        "code": code,
        "message": message,
    }


def _contains_admin_attempt(text: str) -> bool:
    normalized = text.casefold()
    return any(term in normalized for term in ADMIN_ATTEMPT_TERMS)


def _contains_secret_access(value: Any) -> bool:
    if isinstance(value, str):
        normalized = value.casefold()
        return any(term in normalized for term in SECRET_ACCESS_TERMS)
    if isinstance(value, dict):
        return any(
            _contains_secret_access(key) or _contains_secret_access(item)
            for key, item in value.items()
        )
    if isinstance(value, list | tuple):
        return any(_contains_secret_access(item) for item in value)
    return False


def _looks_like_admin_tool(tool_name: str) -> bool:
    return any(word in tool_name for word in toolsets.USER_FORBIDDEN_TOOL_WORDS)


def _tool_definition(tool_name: str) -> tools.ToolDefinition | None:
    for definition in tools.all_tool_definitions():
        if definition.name == tool_name:
            return definition
    return None


def _validate_args(schema: JsonObject, args: JsonObject) -> list[JsonObject]:
    violations: list[JsonObject] = []
    properties = schema.get("properties")
    required = schema.get("required")
    if not isinstance(properties, dict) or not isinstance(required, list):
        return [_violation("schema_invalid", "Tool schema is invalid.")]

    for name in required:
        if isinstance(name, str) and name not in args:
            violations.append(
                _violation("missing_required_argument", f"Missing argument: {name}")
            )

    if schema.get("additionalProperties") is False:
        for name in args:
            if name not in properties:
                violations.append(
                    _violation("unexpected_argument", f"Unexpected argument: {name}")
                )

    for name, value in args.items():
        prop_schema = properties.get(name)
        if isinstance(prop_schema, dict) and not _matches_type(prop_schema, value):
            violations.append(_violation("invalid_argument_type", f"Invalid: {name}"))

    return violations


def _matches_type(schema: JsonObject, value: Any) -> bool:
    expected = schema.get("type")
    if expected == "string":
        return isinstance(value, str) and (
            "minLength" not in schema or len(value) >= int(schema["minLength"])
        )
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool) and (
            "minimum" not in schema or value >= int(schema["minimum"])
        )
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    return True


def _source_platform(source: Any) -> str:
    platform = getattr(source, "platform", "")
    value = getattr(platform, "value", platform)
    return _string_or_default(value, "")


def _source_user_id(source: Any) -> str:
    return _string_or_default(getattr(source, "user_id", ""), "")


def _string_or_default(value: Any, default: str) -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return default
    return str(value)
