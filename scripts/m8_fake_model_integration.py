#!/usr/bin/env python3
"""Provider-free M8 fake model integration runner."""

from __future__ import annotations

import json
import pathlib
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "menu-planner"
FIXTURE_PATH = (
    ROOT / "fixtures" / "hermes" / "menu_planner_modes" / "guided_fake_workflow.v1.json"
)
TRANSCRIPT_PATH = (
    ROOT / "docs" / "experiments" / "m8-bounded-hermes-workflow-transcript.json"
)

if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

import context as context_loader  # noqa: E402
import modes  # noqa: E402
import policy  # noqa: E402


class FakeApplicationClient:
    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response
        self.calls: list[dict[str, Any]] = []

    def get(self, path: str, *, correlation_id: str) -> dict[str, Any]:
        self.calls.append(
            {
                "method": "GET",
                "path": path,
                "correlation_id": correlation_id,
            }
        )
        return self._response

    def post(
        self,
        path: str,
        *,
        payload: dict[str, Any],
        correlation_id: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "method": "POST",
                "path": path,
                "payload": payload,
                "correlation_id": correlation_id,
                "idempotency_key": idempotency_key,
            }
        )
        return self._response


def main() -> int:
    fixture = _load_fixture()
    context_client = FakeApplicationClient(
        {"ok": True, "data": fixture["application_context"]}
    )
    tool_client = FakeApplicationClient(_menu_draft_response())
    message_result = _evaluate_synthetic_message(fixture)
    application_context = context_loader.load_application_context(
        client=context_client,
        user_id=fixture["synthetic_user_message"]["user_id"],
        correlation_id=fixture["fake_model_args"]["correlation_id"],
        memory_hint="memory says workflow_state=profile_required",
    )
    result = modes.run_guided_fake_workflow(
        context=application_context,
        fake_model_args=fixture["fake_model_args"],
        bound_user_id="user_001",
        client_factory=lambda: tool_client,
    )
    transcript = {
        "schema_version": "m8.fake_model_integration_result.v1",
        "ok": (
            message_result["allowed"]
            and bool(application_context.get("ok"))
            and _matches_expectations(fixture, result, tool_client.calls)
        ),
        "provider": "fixture",
        "credentials_used": False,
        "telegram_used": False,
        "direct_db_writes": False,
        "synthetic_user_message": fixture["synthetic_user_message"],
        "pre_message_policy": message_result,
        "application_context": application_context,
        "workflow": {
            "mode": result.get("mode"),
            "tool_name": result.get("tool_name"),
            "http_path": result.get("http_path"),
            "restricted_toolset": application_context.get("allowed_tools", []),
            "context_call_sequence": _call_summary(context_client.calls),
            "tool_call_sequence": _call_summary(tool_client.calls),
        },
        "preview_explanation": _preview_explanation(result),
        "result": result,
    }
    _save_transcript(transcript)
    print(json.dumps(transcript, ensure_ascii=False, sort_keys=True))
    return 0 if transcript["ok"] else 1


def _load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _menu_draft_response() -> dict[str, Any]:
    return {
        "ok": True,
        "data": {
            "menu_draft": {
                "draft_id": "menu_draft_fake_001",
                "source": "m8_fake_model",
            },
            "entity_id": "menu:user_001",
            "entity_version": 1,
            "warnings": [],
        },
    }


def _evaluate_synthetic_message(fixture: dict[str, Any]) -> dict[str, Any]:
    message = fixture["synthetic_user_message"]
    return policy.evaluate_pre_message_policy(
        policy.MessageContext(
            text=message["text"],
            channel=message["channel"],
            user_id=message["user_id"],
            bound_user_id=message["user_id"],
            workflow_state=fixture["application_context"]["workflow_state"],
            authenticated=True,
        )
    )


def _matches_expectations(
    fixture: dict[str, Any],
    result: dict[str, Any],
    calls: list[dict[str, Any]],
) -> bool:
    expected = fixture["expected"]
    expected_sequence = expected.get("tool_call_sequence", [])
    return (
        bool(result.get("ok"))
        and result.get("mode") == expected["mode"]
        and result.get("tool_name") == expected["tool_name"]
        and result.get("http_path") == expected["http_path"]
        and _call_summary(calls) == expected_sequence
    )


def _preview_explanation(result: dict[str, Any]) -> dict[str, str]:
    tool_result = result.get("result")
    if not isinstance(tool_result, dict) or not tool_result.get("success"):
        return {
            "status": "unavailable",
            "text": "No successful preview result is available.",
        }
    data = tool_result.get("data")
    if not isinstance(data, dict):
        data = {}
    menu_draft = data.get("menu_draft")
    draft_id = ""
    if isinstance(menu_draft, dict):
        draft_id = str(menu_draft.get("draft_id", ""))
    return {
        "status": "preview",
        "text": f"Generated menu draft preview {draft_id}; no Telegram UX was used.",
    }


def _call_summary(calls: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "method": str(call["method"]),
            "path": str(call["path"]),
        }
        for call in calls
    ]


def _save_transcript(transcript: dict[str, Any]) -> None:
    TRANSCRIPT_PATH.write_text(
        json.dumps(transcript, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
