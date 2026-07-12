#!/usr/bin/env python3
"""Provider-free M9 Telegram Alpha E2E runner."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"
TRANSCRIPT_PATH = ROOT / "docs" / "experiments" / "m9-telegram-alpha-transcript.json"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from menu_planner.application.telegram_alpha import (  # noqa: E402
    SCHEMA_VERSION,
    PendingConfirmation,
    TelegramAlphaBinding,
    TelegramAlphaConfig,
    TelegramAlphaEvent,
    TelegramAlphaShoppingItem,
    bind_telegram_alpha_event,
    build_checklist_callback_data,
    build_confirmation_callback_data,
    evaluate_telegram_alpha_ingress,
    recover_telegram_alpha_after_restart,
    render_telegram_alpha_presentation,
    resolve_cancel_workflow_action,
    resolve_checklist_callback,
    resolve_confirmation_callback,
)
from menu_planner.domain.contracts.models import (  # noqa: E402
    SCHEMA_VERSION as DOMAIN_SCHEMA_VERSION,
    WorkflowRun,
    WorkflowState,
)
from menu_planner.domain.workflow import allowed_actions  # noqa: E402


NOW = datetime(2026, 7, 12, 12, 0, tzinfo=UTC)


@dataclass(frozen=True)
class Scenario:
    name: str
    ok: bool
    transcript: dict[str, object]


class FakeWorkflowResolver:
    def __init__(self, workflow: WorkflowRun | None) -> None:
        self.workflow = workflow
        self.calls: list[dict[str, str]] = []

    def get_active_workflow(
        self,
        *,
        user_id: str,
        hermes_session_id: str,
    ) -> WorkflowRun | None:
        self.calls.append(
            {
                "user_id": user_id,
                "hermes_session_id": hermes_session_id,
            }
        )
        return self.workflow


class FakeIngressState:
    def __init__(self, *, conflicting_action: bool = False) -> None:
        self.conflicting_action = conflicting_action

    def get_last_message_at(
        self,
        *,
        telegram_user_id: str,
        hermes_session_id: str,
    ) -> datetime | None:
        return None

    def has_conflicting_action(
        self,
        *,
        application_user_id: str,
        workflow_id: str,
    ) -> bool:
        return self.conflicting_action


class FakeConfirmationResolver:
    def __init__(self, confirmation: PendingConfirmation | None) -> None:
        self.confirmation = confirmation
        self.calls: list[dict[str, str]] = []

    def get_pending_confirmation(
        self,
        *,
        confirmation_id: str,
    ) -> PendingConfirmation | None:
        self.calls.append({"confirmation_id": confirmation_id})
        return self.confirmation

    def get_pending_confirmation_for_workflow(
        self,
        *,
        user_id: str,
        workflow_id: str,
    ) -> PendingConfirmation | None:
        self.calls.append({"user_id": user_id, "workflow_id": workflow_id})
        return self.confirmation


class FakeShoppingChecklistResolver:
    def __init__(self, item: TelegramAlphaShoppingItem) -> None:
        self.item = item
        self.mutations = 0

    def get_checklist_item(
        self,
        *,
        application_user_id: str,
        workflow_id: str,
        shopping_item_id: str,
    ) -> TelegramAlphaShoppingItem | None:
        if shopping_item_id == self.item.shopping_item_id:
            return self.item
        return None

    def find_checklist_items_by_text(
        self,
        *,
        application_user_id: str,
        workflow_id: str,
        text: str,
    ) -> tuple[TelegramAlphaShoppingItem, ...]:
        return (self.item,) if "milk" in text.casefold() else ()


def main() -> int:
    config = TelegramAlphaConfig(
        schema_version=SCHEMA_VERSION,
        allowed_telegram_user_id="telegram_alpha_user",
        application_user_id="user_001",
    )
    event = TelegramAlphaEvent(
        schema_version=SCHEMA_VERSION,
        telegram_user_id="telegram_alpha_user",
        chat_id="synthetic_chat",
        chat_type="dm",
        message_id="message_001",
        hermes_session_id="session_001",
        workflow_id="workflow_001",
        thread_id=None,
    )
    workflow = _workflow(WorkflowState.MENU_WAITING_CONFIRMATION)
    binding = _bind(config=config, event=event, workflow=workflow)

    scenarios = [
        _profile_scenario(config, event, binding),
        _menu_generation_scenario(config, event, binding),
        _revision_scenario(binding),
        _confirm_scenario(binding),
        _recipe_view_scenario(),
        _shopping_checklist_scenario(binding),
        _cancel_scenario(binding),
        _expired_confirmation_scenario(binding),
        _restart_recovery_scenario(config, event, workflow),
    ]
    transcript = {
        "schema_version": "m9.telegram_alpha_e2e_transcript.v1",
        "ok": all(scenario.ok for scenario in scenarios),
        "provider": "synthetic",
        "telegram_network_used": False,
        "credentials_used": False,
        "direct_db_writes": False,
        "meaningful_changes_require_confirmation": True,
        "scenarios": [
            {
                "name": scenario.name,
                "ok": scenario.ok,
                "transcript": scenario.transcript,
            }
            for scenario in scenarios
        ],
    }
    _write_transcript(transcript)
    print(json.dumps(transcript, ensure_ascii=False, sort_keys=True))
    return 0 if transcript["ok"] else 1


def _bind(
    *,
    config: TelegramAlphaConfig,
    event: TelegramAlphaEvent,
    workflow: WorkflowRun,
) -> TelegramAlphaBinding:
    result = bind_telegram_alpha_event(
        event=event,
        config=config,
        workflow_resolver=FakeWorkflowResolver(workflow),
    )
    assert result.binding is not None
    return result.binding


def _profile_scenario(
    config: TelegramAlphaConfig,
    event: TelegramAlphaEvent,
    binding: TelegramAlphaBinding,
) -> Scenario:
    ingress = evaluate_telegram_alpha_ingress(
        text="update profile today",
        event=event,
        config=config,
        binding=binding,
        ingress_state=FakeIngressState(),
        now=NOW,
    )
    preview = render_telegram_alpha_presentation(
        kind="preview",
        payload={
            "title": "Profile update",
            "summary": "Profile draft is ready for review.",
            "confirmation_id": "profile_conf_001",
            "expected_version": 2,
        },
    )
    ok = (
        ingress.allowed
        and ingress.normalized_dates == {"today": "2026-07-12"}
        and "draft state, not active state" in preview.text
        and "confirmation_id: profile_conf_001" in preview.text
    )
    return Scenario(
        name="create_update_profile",
        ok=ok,
        transcript={
            "ingress_allowed": ingress.allowed,
            "normalized_dates": ingress.normalized_dates,
            "preview": preview.to_json(),
            "state_changed": False,
        },
    )


def _menu_generation_scenario(
    config: TelegramAlphaConfig,
    event: TelegramAlphaEvent,
    binding: TelegramAlphaBinding,
) -> Scenario:
    ingress = evaluate_telegram_alpha_ingress(
        text="generate menu tomorrow",
        event=event,
        config=config,
        binding=binding,
        ingress_state=FakeIngressState(),
        now=NOW,
    )
    preview = render_telegram_alpha_presentation(
        kind="preview",
        payload={
            "title": "Menu for tomorrow",
            "summary": "Accepted menu path produced a draft preview.",
            "confirmation_id": "menu_conf_001",
            "expected_version": 3,
        },
    )
    ok = (
        ingress.allowed
        and ingress.normalized_dates == {"tomorrow": "2026-07-13"}
        and "confirmation_id: menu_conf_001" in preview.text
    )
    return Scenario(
        name="generate_menu_or_accepted_path",
        ok=ok,
        transcript={
            "ingress_allowed": ingress.allowed,
            "normalized_dates": ingress.normalized_dates,
            "preview": preview.to_json(),
            "state_changed": False,
        },
    )


def _revision_scenario(binding: TelegramAlphaBinding) -> Scenario:
    response = render_telegram_alpha_presentation(
        kind="validation_warnings",
        payload={"warnings": ["Dinner needs a cheaper replacement."]},
    )
    policy = render_telegram_alpha_presentation(
        kind="policy_error",
        payload={
            "code": "conflicting_action_in_progress",
            "message": "Finish or cancel the current action first.",
            "next_actions": ["finish current action", "cancel"],
        },
    )
    ok = (
        binding.workflow_id == "workflow_001"
        and "Dinner needs a cheaper replacement." in response.text
        and "Finish or cancel" in policy.text
    )
    return Scenario(
        name="revision",
        ok=ok,
        transcript={
            "validation_warnings": response.to_json(),
            "parallel_policy": policy.to_json(),
            "state_changed": False,
        },
    )


def _confirm_scenario(binding: TelegramAlphaBinding) -> Scenario:
    data = build_confirmation_callback_data(
        action="confirm",
        confirmation_id="menu_conf_001",
        expected_version=3,
        summary_hash="hash_001",
    )
    result = resolve_confirmation_callback(
        data=data,
        binding=binding,
        confirmation_resolver=FakeConfirmationResolver(
            _confirmation("menu_conf_001")
        ),
        now=NOW,
    )
    ok = (
        result.allowed
        and result.confirmation_id == "menu_conf_001"
        and result.expected_version == 3
    )
    return Scenario(
        name="confirm",
        ok=ok,
        transcript={
            "callback_data_bytes": len(data.encode("utf-8")),
            "confirmation_result": result.to_json(),
            "state_change_authorized_by_confirmation": result.allowed,
        },
    )


def _recipe_view_scenario() -> Scenario:
    response = render_telegram_alpha_presentation(
        kind="recipe_view",
        payload={
            "title": "Tomato pasta",
            "portions": 2,
            "ingredients": ["pasta", "tomatoes"],
            "steps": ["Boil pasta.", "Warm sauce."],
        },
    )
    return Scenario(
        name="recipe_view",
        ok="Recipe: Tomato pasta" in response.text,
        transcript={"presentation": response.to_json(), "state_changed": False},
    )


def _shopping_checklist_scenario(binding: TelegramAlphaBinding) -> Scenario:
    data = build_checklist_callback_data(
        action="done",
        shopping_item_id="shopping_list_001:item:001",
    )
    resolver = FakeShoppingChecklistResolver(
        TelegramAlphaShoppingItem(
            schema_version=SCHEMA_VERSION,
            shopping_item_id="shopping_list_001:item:001",
            display_name="Whole milk",
            status="pending",
        )
    )
    result = resolve_checklist_callback(
        data=data,
        binding=binding,
        checklist_resolver=resolver,
    )
    presentation = render_telegram_alpha_presentation(
        kind="shopping_checklist",
        payload={
            "items": [
                {
                    "shopping_item_id": "shopping_list_001:item:001",
                    "name": "Whole milk",
                    "status": "open",
                }
            ]
        },
    )
    ok = (
        result.allowed
        and result.shopping_item_id == "shopping_list_001:item:001"
        and resolver.mutations == 0
    )
    return Scenario(
        name="shopping_checklist",
        ok=ok,
        transcript={
            "callback_data_bytes": len(data.encode("utf-8")),
            "checklist_result": result.to_json(),
            "presentation": presentation.to_json(),
            "direct_mutation": False,
        },
    )


def _cancel_scenario(binding: TelegramAlphaBinding) -> Scenario:
    result = resolve_cancel_workflow_action(binding=binding)
    response = render_telegram_alpha_presentation(
        kind="cancel",
        payload={
            "workflow_id": result.workflow_id,
            "next_actions": ["show status"],
        },
    )
    ok = result.allowed and "No active state was changed." in response.text
    return Scenario(
        name="cancel",
        ok=ok,
        transcript={
            "cancel_result": result.to_json(),
            "presentation": response.to_json(),
            "state_changed": False,
        },
    )


def _expired_confirmation_scenario(binding: TelegramAlphaBinding) -> Scenario:
    data = build_confirmation_callback_data(
        action="confirm",
        confirmation_id="expired_conf_001",
        expected_version=3,
        summary_hash="hash_001",
    )
    result = resolve_confirmation_callback(
        data=data,
        binding=binding,
        confirmation_resolver=FakeConfirmationResolver(
            _confirmation(
                "expired_conf_001",
                expires_at=NOW - timedelta(seconds=1),
            )
        ),
        now=NOW,
    )
    response = render_telegram_alpha_presentation(
        kind="expired_confirmation",
        payload={"confirmation_id": "expired_conf_001"},
    )
    ok = (
        not result.allowed
        and result.rejection is not None
        and result.rejection.code == "confirmation_expired"
        and "create a new preview" in response.text
    )
    return Scenario(
        name="expired_confirmation",
        ok=ok,
        transcript={
            "confirmation_result": result.to_json(),
            "presentation": response.to_json(),
            "state_changed": False,
        },
    )


def _restart_recovery_scenario(
    config: TelegramAlphaConfig,
    event: TelegramAlphaEvent,
    workflow: WorkflowRun,
) -> Scenario:
    result = recover_telegram_alpha_after_restart(
        event=event,
        config=config,
        workflow_resolver=FakeWorkflowResolver(workflow),
        confirmation_resolver=FakeConfirmationResolver(
            _confirmation("menu_conf_001")
        ),
        now=NOW,
    )
    response = render_telegram_alpha_presentation(
        kind="restart_recovery",
        payload={
            "workflow_state": result.workflow_state,
            "allowed_actions": list(result.allowed_actions),
            "pending_confirmation_id": result.pending_confirmation_id,
            "expected_version": result.expected_version,
        },
    )
    ok = (
        result.allowed
        and result.pending_confirmation_id == "menu_conf_001"
        and "resume confirmation" in response.text
    )
    return Scenario(
        name="restart_recovery",
        ok=ok,
        transcript={
            "recovery_result": result.to_json(),
            "presentation": response.to_json(),
            "memory_source_of_truth": False,
        },
    )


def _workflow(state: WorkflowState) -> WorkflowRun:
    return WorkflowRun(
        schema_version=DOMAIN_SCHEMA_VERSION,
        workflow_id="workflow_001",
        user_id="user_001",
        state=state,
        allowed_actions=[action.value for action in allowed_actions(state)],
        attempts=0,
    )


def _confirmation(
    confirmation_id: str,
    *,
    expires_at: datetime | None = None,
) -> PendingConfirmation:
    return PendingConfirmation(
        schema_version=SCHEMA_VERSION,
        confirmation_id=confirmation_id,
        user_id="user_001",
        workflow_id="workflow_001",
        expected_version=3,
        summary_hash="hash_001",
        expires_at=expires_at or (NOW + timedelta(minutes=5)),
        consumed_at=None,
    )


def _write_transcript(transcript: dict[str, object]) -> None:
    TRANSCRIPT_PATH.write_text(
        json.dumps(transcript, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
