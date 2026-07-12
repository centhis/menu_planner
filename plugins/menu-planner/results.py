"""Structured Hermes tool result helpers for Menu Planner."""

from __future__ import annotations

import json
from typing import Any

JsonObject = dict[str, Any]

ERROR_RETRYABLE_BY_CODE = {
    "application_timeout",
    "application_unreachable",
}


def tool_success(
    *,
    operation_id: str,
    correlation_id: str,
    data: JsonObject,
    next_allowed_actions: tuple[str, ...],
    entity_id: str | None = None,
    entity_version: int | None = None,
    warnings: tuple[str, ...] = (),
) -> str:
    result: JsonObject = {
        "success": True,
        "operation_id": operation_id,
        "correlation_id": correlation_id,
        "data": {
            **data,
            "next_allowed_actions": list(next_allowed_actions),
            "warnings": list(warnings),
        },
    }
    if entity_id is not None:
        result["entity_id"] = entity_id
    if entity_version is not None:
        result["entity_version"] = entity_version
    return _json(result)


def tool_error(
    *,
    correlation_id: str,
    errors: tuple[JsonObject, ...],
    operation_id: str = "",
    retryable: bool | None = None,
    next_allowed_actions: tuple[str, ...] = (),
) -> str:
    normalized_errors = tuple(_normalize_error(error) for error in errors)
    if retryable is None:
        retryable = any(
            error["code"] in ERROR_RETRYABLE_BY_CODE for error in normalized_errors
        )

    return _json(
        {
            "success": False,
            "operation_id": operation_id,
            "correlation_id": correlation_id,
            "retryable": retryable,
            "errors": list(normalized_errors),
            "next_allowed_actions": list(next_allowed_actions),
        }
    )


def unexpected_exception_result(
    *,
    correlation_id: str,
    operation_id: str = "",
) -> str:
    return tool_error(
        correlation_id=correlation_id,
        operation_id=operation_id,
        retryable=False,
        errors=(
            {
                "code": "unexpected_tool_error",
                "message": "Unexpected Menu Planner tool error.",
            },
        ),
    )


def _normalize_error(error: JsonObject) -> JsonObject:
    code = error.get("code")
    message = error.get("message")
    if not isinstance(code, str) or not code:
        code = "tool_error"
    if not isinstance(message, str) or not message:
        message = "Menu Planner tool error."

    normalized: JsonObject = {
        "code": code,
        "message": message,
    }
    field = error.get("field")
    if isinstance(field, str) and field:
        normalized["field"] = field
    return normalized


def _json(payload: JsonObject) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)
