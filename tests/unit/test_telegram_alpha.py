from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
import pathlib
import unittest

from menu_planner.application.telegram_alpha import (
    ALPHA_MAX_MESSAGE_CHARS_ENV,
    ALPHA_RATE_LIMIT_SECONDS_ENV,
    ALPHA_TIMEZONE_ENV,
    ALPHA_USER_ID_ENV,
    MAX_CALLBACK_DATA_BYTES,
    SCHEMA_VERSION,
    TELEGRAM_ALLOWED_USERS_ENV,
    PendingConfirmation,
    TelegramAlphaConfig,
    TelegramAlphaEvent,
    TelegramAlphaShoppingItem,
    bind_telegram_alpha_event,
    build_checklist_callback_data,
    build_confirmation_callback_data,
    evaluate_telegram_alpha_ingress,
    load_telegram_alpha_config,
    parse_checklist_callback_data,
    parse_confirmation_callback_data,
    recover_telegram_alpha_after_restart,
    render_telegram_alpha_presentation,
    resolve_checklist_callback,
    resolve_checklist_text_action,
    resolve_cancel_workflow_action,
    resolve_confirmation_callback,
)
from menu_planner.domain.contracts.models import (
    SCHEMA_VERSION as DOMAIN_SCHEMA_VERSION,
    WorkflowRun,
    WorkflowState,
)
from menu_planner.domain.workflow import allowed_actions

ROOT = pathlib.Path(__file__).resolve().parents[2]
PRESENTATION_FIXTURE = ROOT / "fixtures" / "telegram_alpha" / "presentation.v1.json"


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
    def __init__(
        self,
        *,
        last_message_at: datetime | None = None,
        conflicting_action: bool = False,
    ) -> None:
        self.last_message_at = last_message_at
        self.conflicting_action = conflicting_action
        self.last_message_calls: list[dict[str, str]] = []
        self.conflict_calls: list[dict[str, str]] = []

    def get_last_message_at(
        self,
        *,
        telegram_user_id: str,
        hermes_session_id: str,
    ) -> datetime | None:
        self.last_message_calls.append(
            {
                "telegram_user_id": telegram_user_id,
                "hermes_session_id": hermes_session_id,
            }
        )
        return self.last_message_at

    def has_conflicting_action(
        self,
        *,
        application_user_id: str,
        workflow_id: str,
    ) -> bool:
        self.conflict_calls.append(
            {
                "application_user_id": application_user_id,
                "workflow_id": workflow_id,
            }
        )
        return self.conflicting_action


class FakeParallelActionState:
    def __init__(self, *, conflicting_action: bool) -> None:
        self.conflicting_action = conflicting_action
        self.calls: list[dict[str, str]] = []

    def has_conflicting_action(
        self,
        *,
        application_user_id: str,
        workflow_id: str,
    ) -> bool:
        self.calls.append(
            {
                "application_user_id": application_user_id,
                "workflow_id": workflow_id,
            }
        )
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


class FakeRestartConfirmationResolver:
    def __init__(self, confirmation: PendingConfirmation | None) -> None:
        self.confirmation = confirmation
        self.calls: list[dict[str, str]] = []

    def get_pending_confirmation_for_workflow(
        self,
        *,
        user_id: str,
        workflow_id: str,
    ) -> PendingConfirmation | None:
        self.calls.append({"user_id": user_id, "workflow_id": workflow_id})
        return self.confirmation


class FakeShoppingChecklistResolver:
    def __init__(self, items: tuple[TelegramAlphaShoppingItem, ...]) -> None:
        self.items = items
        self.item_calls: list[dict[str, str]] = []
        self.text_calls: list[dict[str, str]] = []
        self.mutation_calls: list[dict[str, str]] = []

    def get_checklist_item(
        self,
        *,
        application_user_id: str,
        workflow_id: str,
        shopping_item_id: str,
    ) -> TelegramAlphaShoppingItem | None:
        self.item_calls.append(
            {
                "application_user_id": application_user_id,
                "workflow_id": workflow_id,
                "shopping_item_id": shopping_item_id,
            }
        )
        for item in self.items:
            if item.shopping_item_id == shopping_item_id:
                return item
        return None

    def find_checklist_items_by_text(
        self,
        *,
        application_user_id: str,
        workflow_id: str,
        text: str,
    ) -> tuple[TelegramAlphaShoppingItem, ...]:
        self.text_calls.append(
            {
                "application_user_id": application_user_id,
                "workflow_id": workflow_id,
                "text": text,
            }
        )
        terms = tuple(
            term
            for term in text.casefold().split()
            if term not in {"bought", "done", "куплено"}
        )
        return tuple(
            item
            for item in self.items
            if all(term in item.display_name.casefold() for term in terms)
        )


class TelegramAlphaBindingTests(unittest.TestCase):
    def test_load_config_accepts_exactly_one_allowed_user_without_exposing_it(
        self,
    ) -> None:
        config = load_telegram_alpha_config(
            {
                TELEGRAM_ALLOWED_USERS_ENV: "12345",
                ALPHA_USER_ID_ENV: "user_001",
            }
        )

        self.assertEqual(config.allowed_telegram_user_id, "12345")
        self.assertEqual(config.application_user_id, "user_001")
        self.assertEqual(
            config.safe_summary(),
            {
                "schema_version": SCHEMA_VERSION,
                "allowed_telegram_user_configured": True,
                "application_user_configured": True,
                "max_message_chars": "1200",
                "rate_limit_seconds": "2",
                "timezone": "UTC",
            },
        )
        self.assertNotIn("12345", str(config.safe_summary()))

    def test_load_config_rejects_wildcard_or_multi_user_allowlist(self) -> None:
        wildcard = load_telegram_alpha_config(
            {
                TELEGRAM_ALLOWED_USERS_ENV: "*",
                ALPHA_USER_ID_ENV: "user_001",
            }
        )
        multiple = load_telegram_alpha_config(
            {
                TELEGRAM_ALLOWED_USERS_ENV: "12345,67890",
                ALPHA_USER_ID_ENV: "user_001",
            }
        )

        self.assertFalse(wildcard.is_configured)
        self.assertFalse(multiple.is_configured)

    def test_load_config_includes_alpha_limits_and_timezone(self) -> None:
        config = load_telegram_alpha_config(
            {
                TELEGRAM_ALLOWED_USERS_ENV: "12345",
                ALPHA_USER_ID_ENV: "user_001",
                ALPHA_MAX_MESSAGE_CHARS_ENV: "400",
                ALPHA_RATE_LIMIT_SECONDS_ENV: "5",
                ALPHA_TIMEZONE_ENV: "Europe/Berlin",
            }
        )

        self.assertEqual(config.max_message_chars, 400)
        self.assertEqual(config.rate_limit_seconds, 5)
        self.assertEqual(config.timezone, "Europe/Berlin")

    def test_allowed_user_binds_to_application_user_and_workflow(self) -> None:
        resolver = FakeWorkflowResolver(
            _workflow(user_id="user_001", workflow_id="workflow_001")
        )

        result = bind_telegram_alpha_event(
            event=_event(),
            config=_config(),
            workflow_resolver=resolver,
        )

        self.assertTrue(result.allowed)
        assert result.binding is not None
        self.assertEqual(result.binding.application_user_id, "user_001")
        self.assertEqual(result.binding.workflow_id, "workflow_001")
        self.assertEqual(result.binding.hermes_session_id, "session_001")
        self.assertEqual(
            resolver.calls,
            [{"user_id": "user_001", "hermes_session_id": "session_001"}],
        )

    def test_disallowed_telegram_user_is_structured_rejection(self) -> None:
        resolver = FakeWorkflowResolver(
            _workflow(user_id="user_001", workflow_id="workflow_001")
        )

        result = bind_telegram_alpha_event(
            event=_event(telegram_user_id="99999"),
            config=_config(),
            workflow_resolver=resolver,
        )

        self.assertFalse(result.allowed)
        self.assertEqual(result.binding, None)
        assert result.rejection is not None
        self.assertEqual(result.rejection.code, "telegram_user_not_allowed")
        self.assertEqual(resolver.calls, [])

    def test_missing_session_or_workflow_is_structured_rejection(self) -> None:
        missing_session = bind_telegram_alpha_event(
            event=_event(hermes_session_id=""),
            config=_config(),
            workflow_resolver=FakeWorkflowResolver(
                _workflow(user_id="user_001", workflow_id="workflow_001")
            ),
        )
        missing_workflow = bind_telegram_alpha_event(
            event=_event(),
            config=_config(),
            workflow_resolver=FakeWorkflowResolver(None),
        )

        assert missing_session.rejection is not None
        assert missing_workflow.rejection is not None
        self.assertEqual(missing_session.rejection.code, "telegram_session_missing")
        self.assertEqual(missing_workflow.rejection.code, "workflow_not_found")

    def test_user_or_workflow_mismatch_cannot_bind_to_another_workflow(self) -> None:
        wrong_user = bind_telegram_alpha_event(
            event=_event(),
            config=_config(),
            workflow_resolver=FakeWorkflowResolver(
                _workflow(user_id="user_999", workflow_id="workflow_001")
            ),
        )
        wrong_workflow = bind_telegram_alpha_event(
            event=_event(workflow_id="workflow_999"),
            config=_config(),
            workflow_resolver=FakeWorkflowResolver(
                _workflow(user_id="user_001", workflow_id="workflow_001")
            ),
        )

        assert wrong_user.rejection is not None
        assert wrong_workflow.rejection is not None
        self.assertEqual(wrong_user.rejection.code, "workflow_user_mismatch")
        self.assertEqual(wrong_workflow.rejection.code, "workflow_id_mismatch")

    def test_result_json_is_machine_readable_and_contains_no_callback_payload(
        self,
    ) -> None:
        result = bind_telegram_alpha_event(
            event=_event(),
            config=_config(),
            workflow_resolver=FakeWorkflowResolver(
                _workflow(user_id="user_001", workflow_id="workflow_001")
            ),
        )

        payload = result.to_json()

        self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
        self.assertTrue(payload["allowed"])
        self.assertNotIn("callback_data", str(payload))
        self.assertNotIn("TELEGRAM_BOT_TOKEN", str(payload))


class TelegramAlphaIngressTests(unittest.TestCase):
    def test_oversized_message_is_rejected_before_state_checks(self) -> None:
        state = FakeIngressState()

        result = evaluate_telegram_alpha_ingress(
            text="x" * 6,
            event=_event(),
            config=_config(max_message_chars=5),
            binding=_binding(),
            ingress_state=state,
            now=_now(),
        )

        self.assertFalse(result.allowed)
        assert result.rejection is not None
        self.assertEqual(result.rejection.code, "message_too_large")
        self.assertEqual(state.last_message_calls, [])
        self.assertEqual(state.conflict_calls, [])

    def test_rate_limit_is_deterministic(self) -> None:
        result = evaluate_telegram_alpha_ingress(
            text="status",
            event=_event(),
            config=_config(rate_limit_seconds=10),
            binding=_binding(),
            ingress_state=FakeIngressState(
                last_message_at=_now() - timedelta(seconds=3)
            ),
            now=_now(),
        )

        self.assertFalse(result.allowed)
        assert result.rejection is not None
        self.assertEqual(result.rejection.code, "rate_limited")

    def test_conflicting_action_is_rejected(self) -> None:
        result = evaluate_telegram_alpha_ingress(
            text="generate menu",
            event=_event(),
            config=_config(),
            binding=_binding(),
            ingress_state=FakeIngressState(conflicting_action=True),
            now=_now(),
        )

        self.assertFalse(result.allowed)
        assert result.rejection is not None
        self.assertEqual(result.rejection.code, "conflicting_action_in_progress")

    def test_two_text_messages_use_explicit_conflict_rejection(self) -> None:
        state = FakeIngressState(conflicting_action=True)

        result = evaluate_telegram_alpha_ingress(
            text="replace dinner",
            event=_event(message_id="message_002"),
            config=_config(),
            binding=_binding(),
            ingress_state=state,
            now=_now(),
        )
        response = render_telegram_alpha_presentation(
            kind="policy_error",
            payload={
                "code": result.rejection.code if result.rejection else "",
                "message": result.rejection.message if result.rejection else "",
                "next_actions": ["finish current action", "cancel"],
            },
        )

        self.assertFalse(result.allowed)
        assert result.rejection is not None
        self.assertEqual(result.rejection.code, "conflicting_action_in_progress")
        self.assertIn("Finish or cancel the current action first.", response.text)
        self.assertEqual(
            state.conflict_calls,
            [
                {
                    "application_user_id": "user_001",
                    "workflow_id": "workflow_001",
                }
            ],
        )

    def test_relative_dates_normalize_against_configured_timezone(self) -> None:
        result = evaluate_telegram_alpha_ingress(
            text="Plan tomorrow and show today.",
            event=_event(),
            config=_config(timezone="Europe/Berlin"),
            binding=_binding(),
            ingress_state=FakeIngressState(),
            now=datetime(2026, 7, 12, 22, 30, tzinfo=UTC),
        )

        self.assertTrue(result.allowed)
        self.assertEqual(result.normalized_timezone, "Europe/Berlin")
        self.assertEqual(
            result.normalized_dates,
            {
                "today": "2026-07-13",
                "tomorrow": "2026-07-14",
            },
        )

    def test_invalid_timezone_is_structured_rejection(self) -> None:
        result = evaluate_telegram_alpha_ingress(
            text="tomorrow",
            event=_event(),
            config=_config(timezone="No/Such_Zone"),
            binding=_binding(),
            ingress_state=FakeIngressState(),
            now=_now(),
        )

        self.assertFalse(result.allowed)
        assert result.rejection is not None
        self.assertEqual(result.rejection.code, "invalid_timezone")


class TelegramAlphaPresentationTests(unittest.TestCase):
    def test_presentation_cases_match_fixture(self) -> None:
        fixture = json.loads(PRESENTATION_FIXTURE.read_text(encoding="utf-8"))

        for case in fixture["cases"]:
            with self.subTest(kind=case["kind"]):
                result = render_telegram_alpha_presentation(
                    kind=case["kind"],
                    payload=case["payload"],
                )

                self.assertEqual(result.text, "\n".join(case["expected_lines"]))
                self.assertEqual(result.parse_mode, "plain")

    def test_preview_distinguishes_draft_from_active_state(self) -> None:
        result = render_telegram_alpha_presentation(
            kind="preview",
            payload={"title": "Menu", "summary": "Review it."},
        )

        self.assertIn("draft state", result.text)
        self.assertIn("not active state", result.text)

    def test_sensitive_payload_fields_are_not_displayed(self) -> None:
        for kind in ("error", "validation_error", "policy_error"):
            with self.subTest(kind=kind):
                result = render_telegram_alpha_presentation(
                    kind=kind,
                    payload={
                        "code": "application_error",
                        "message": "Could not finish request.",
                        "token": "should-not-render",
                        "callback_data": "full-payload",
                        "raw_exception": "Traceback with password",
                    },
                )

                self.assertIn("application_error", result.text)
                self.assertNotIn("should-not-render", result.text)
                self.assertNotIn("full-payload", result.text)
                self.assertNotIn("Traceback", result.text)
                self.assertNotIn("password", result.text.lower())

    def test_expired_confirmation_ux_has_recovery_hints(self) -> None:
        result = render_telegram_alpha_presentation(
            kind="expired_confirmation",
            payload={"confirmation_id": "conf_001"},
        )

        self.assertEqual(
            result.text,
            "\n".join(
                [
                    "Confirmation expired",
                    "This preview can no longer be confirmed.",
                    "confirmation_id: conf_001",
                    "Next actions:",
                    "- show status",
                    "- create a new preview",
                ]
            ),
        )

    def test_cancel_workflow_action_is_structured_and_non_committing(self) -> None:
        result = resolve_cancel_workflow_action(binding=_binding())
        presentation = render_telegram_alpha_presentation(
            kind="cancel",
            payload={
                "workflow_id": result.workflow_id,
                "next_actions": ["show status"],
            },
        )

        self.assertTrue(result.allowed)
        self.assertEqual(result.action, "cancel")
        self.assertEqual(result.workflow_id, "workflow_001")
        self.assertNotIn("commit", str(result.to_json()).casefold())
        self.assertEqual(
            presentation.text,
            "\n".join(
                [
                    "Cancelled workflow workflow_001. "
                    "No active state was changed.",
                    "Next actions:",
                    "- show status",
                ]
            ),
        )


class TelegramAlphaRestartRecoveryTests(unittest.TestCase):
    def test_restart_reloads_workflow_confirmation_and_allowed_actions(self) -> None:
        workflow_resolver = FakeWorkflowResolver(
            _workflow(
                user_id="user_001",
                workflow_id="workflow_001",
                state=WorkflowState.MENU_WAITING_CONFIRMATION,
            )
        )
        confirmation_resolver = FakeRestartConfirmationResolver(_confirmation())

        result = recover_telegram_alpha_after_restart(
            event=_event(),
            config=_config(),
            workflow_resolver=workflow_resolver,
            confirmation_resolver=confirmation_resolver,
            now=_now(),
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

        self.assertTrue(result.allowed)
        self.assertEqual(result.workflow_state, "menu_waiting_confirmation")
        self.assertIn("confirm_menu_draft", result.allowed_actions)
        self.assertEqual(result.pending_confirmation_id, "conf_001")
        self.assertEqual(result.expected_version, 3)
        self.assertEqual(
            confirmation_resolver.calls,
            [{"user_id": "user_001", "workflow_id": "workflow_001"}],
        )
        self.assertIn("Recovered active workflow", response.text)
        self.assertIn("pending_confirmation_id: conf_001", response.text)
        self.assertIn("- resume confirmation", response.text)
        self.assertIn("- cancel", response.text)

    def test_restart_does_not_resume_consumed_or_expired_confirmation(self) -> None:
        workflow_resolver = FakeWorkflowResolver(
            _workflow(
                user_id="user_001",
                workflow_id="workflow_001",
                state=WorkflowState.MENU_WAITING_CONFIRMATION,
            )
        )
        cases = [
            _confirmation(consumed_at=_now() - timedelta(seconds=1)),
            _confirmation(expires_at=_now() - timedelta(seconds=1)),
            _confirmation(user_id="user_999"),
            _confirmation(workflow_id="workflow_999"),
        ]

        for confirmation in cases:
            with self.subTest(confirmation=confirmation):
                result = recover_telegram_alpha_after_restart(
                    event=_event(),
                    config=_config(),
                    workflow_resolver=workflow_resolver,
                    confirmation_resolver=FakeRestartConfirmationResolver(
                        confirmation
                    ),
                    now=_now(),
                )

                self.assertTrue(result.allowed)
                self.assertEqual(result.pending_confirmation_id, None)
                self.assertEqual(result.expected_version, None)
                self.assertNotIn("conf_001", str(result.to_json()))

    def test_restart_missing_workflow_returns_recoverable_rejection(self) -> None:
        result = recover_telegram_alpha_after_restart(
            event=_event(),
            config=_config(),
            workflow_resolver=FakeWorkflowResolver(None),
            confirmation_resolver=FakeRestartConfirmationResolver(_confirmation()),
            now=_now(),
        )

        self.assertFalse(result.allowed)
        assert result.rejection is not None
        self.assertEqual(result.rejection.code, "workflow_not_found")


class TelegramAlphaCallbackTests(unittest.TestCase):
    def test_callback_data_is_short_and_contains_stable_confirmation_refs(
        self,
    ) -> None:
        data = build_confirmation_callback_data(
            action="confirm",
            confirmation_id="conf_001",
            expected_version=3,
            summary_hash="hash_001",
        )

        self.assertLessEqual(len(data.encode("utf-8")), MAX_CALLBACK_DATA_BYTES)
        self.assertEqual(data, "mpc:confirm:conf_001:3:hash_001")

        parsed = parse_confirmation_callback_data(data)
        self.assertTrue(parsed.allowed)
        self.assertEqual(parsed.action, "confirm")
        self.assertEqual(parsed.confirmation_id, "conf_001")
        self.assertEqual(parsed.expected_version, 3)
        self.assertEqual(parsed.summary_hash, "hash_001")

    def test_callback_data_rejects_full_payload_or_unstable_tokens(self) -> None:
        with self.assertRaises(ValueError):
            build_confirmation_callback_data(
                action="confirm",
                confirmation_id="conf_001:{payload}",
                expected_version=3,
                summary_hash="hash_001",
            )

        payload = (
            "mpc:confirm:conf_001:3:"
            "{\"menu_draft\":{\"private\":\"payload\"}}"
        )
        parsed = parse_confirmation_callback_data(payload)

        self.assertFalse(parsed.allowed)
        assert parsed.rejection is not None
        self.assertIn(
            parsed.rejection.code,
            {
                "callback_data_invalid",
                "callback_data_too_large",
                "callback_data_unstable",
            },
        )

    def test_valid_confirmation_callback_resolves_without_committing(self) -> None:
        data = build_confirmation_callback_data(
            action="confirm",
            confirmation_id="conf_001",
            expected_version=3,
            summary_hash="hash_001",
        )
        resolver = FakeConfirmationResolver(_confirmation())

        result = resolve_confirmation_callback(
            data=data,
            binding=_binding(),
            confirmation_resolver=resolver,
            now=_now(),
        )

        self.assertTrue(result.allowed)
        self.assertEqual(result.action, "confirm")
        self.assertEqual(result.confirmation_id, "conf_001")
        self.assertEqual(result.expected_version, 3)
        self.assertEqual(result.summary_hash, "hash_001")
        self.assertEqual(resolver.calls, [{"confirmation_id": "conf_001"}])
        self.assertNotIn("commit", str(result.to_json()).casefold())

    def test_confirmation_callback_rejects_conflict_before_state_lookup(self) -> None:
        data = build_confirmation_callback_data(
            action="confirm",
            confirmation_id="conf_001",
            expected_version=3,
            summary_hash="hash_001",
        )
        resolver = FakeConfirmationResolver(_confirmation())
        parallel_state = FakeParallelActionState(conflicting_action=True)

        result = resolve_confirmation_callback(
            data=data,
            binding=_binding(),
            confirmation_resolver=resolver,
            now=_now(),
            parallel_state=parallel_state,
        )
        response = render_telegram_alpha_presentation(
            kind="policy_error",
            payload={
                "code": result.rejection.code if result.rejection else "",
                "message": result.rejection.message if result.rejection else "",
                "next_actions": ["finish current action", "cancel"],
            },
        )

        self.assertFalse(result.allowed)
        assert result.rejection is not None
        self.assertEqual(result.rejection.code, "conflicting_action_in_progress")
        self.assertEqual(resolver.calls, [])
        self.assertIn("Finish or cancel the current action first.", response.text)
        self.assertEqual(
            parallel_state.calls,
            [
                {
                    "application_user_id": "user_001",
                    "workflow_id": "workflow_001",
                }
            ],
        )

    def test_expired_or_consumed_confirmation_callback_is_rejected(self) -> None:
        data = build_confirmation_callback_data(
            action="confirm",
            confirmation_id="conf_001",
            expected_version=3,
            summary_hash="hash_001",
        )
        expired = resolve_confirmation_callback(
            data=data,
            binding=_binding(),
            confirmation_resolver=FakeConfirmationResolver(
                _confirmation(expires_at=_now() - timedelta(seconds=1))
            ),
            now=_now(),
        )
        consumed = resolve_confirmation_callback(
            data=data,
            binding=_binding(),
            confirmation_resolver=FakeConfirmationResolver(
                _confirmation(consumed_at=_now() - timedelta(seconds=1))
            ),
            now=_now(),
        )

        assert expired.rejection is not None
        assert consumed.rejection is not None
        self.assertEqual(expired.rejection.code, "confirmation_expired")
        self.assertEqual(
            consumed.rejection.code,
            "confirmation_already_consumed",
        )

    def test_confirmation_user_workflow_version_and_hash_are_checked(self) -> None:
        data = build_confirmation_callback_data(
            action="confirm",
            confirmation_id="conf_001",
            expected_version=3,
            summary_hash="hash_001",
        )
        cases = [
            (
                _confirmation(user_id="user_999"),
                "confirmation_user_mismatch",
            ),
            (
                _confirmation(workflow_id="workflow_999"),
                "confirmation_workflow_mismatch",
            ),
            (
                _confirmation(expected_version=4),
                "confirmation_version_mismatch",
            ),
            (
                _confirmation(summary_hash="hash_999"),
                "confirmation_hash_mismatch",
            ),
        ]

        for confirmation, code in cases:
            with self.subTest(code=code):
                result = resolve_confirmation_callback(
                    data=data,
                    binding=_binding(),
                    confirmation_resolver=FakeConfirmationResolver(confirmation),
                    now=_now(),
                )

                self.assertFalse(result.allowed)
                assert result.rejection is not None
                self.assertEqual(result.rejection.code, code)


class TelegramAlphaChecklistCallbackTests(unittest.TestCase):
    def test_exact_item_callback_resolves_stable_shopping_item_id(self) -> None:
        data = build_checklist_callback_data(
            action="done",
            shopping_item_id="shopping_list_001:item:001",
        )
        resolver = FakeShoppingChecklistResolver(
            (_shopping_item("shopping_list_001:item:001", "Milk"),)
        )

        parsed = parse_checklist_callback_data(data)
        result = resolve_checklist_callback(
            data=data,
            binding=_binding(),
            checklist_resolver=resolver,
        )

        self.assertLessEqual(len(data.encode("utf-8")), MAX_CALLBACK_DATA_BYTES)
        self.assertEqual(data, "mpci|done|shopping_list_001:item:001")
        self.assertTrue(parsed.allowed)
        self.assertEqual(parsed.shopping_item_id, "shopping_list_001:item:001")
        self.assertEqual(parsed.target_status, "completed")
        self.assertTrue(result.allowed)
        self.assertEqual(result.action, "done")
        self.assertEqual(result.shopping_item_id, "shopping_list_001:item:001")
        self.assertEqual(result.target_status, "completed")
        self.assertEqual(
            resolver.item_calls,
            [
                {
                    "application_user_id": "user_001",
                    "workflow_id": "workflow_001",
                    "shopping_item_id": "shopping_list_001:item:001",
                }
            ],
        )
        self.assertEqual(resolver.mutation_calls, [])

    def test_repeated_item_callback_is_rejected_without_mutation(self) -> None:
        data = build_checklist_callback_data(
            action="done",
            shopping_item_id="shopping_list_001:item:001",
        )
        resolver = FakeShoppingChecklistResolver(
            (
                _shopping_item(
                    "shopping_list_001:item:001",
                    "Milk",
                    status="completed",
                ),
            )
        )

        result = resolve_checklist_callback(
            data=data,
            binding=_binding(),
            checklist_resolver=resolver,
        )

        self.assertFalse(result.allowed)
        assert result.rejection is not None
        self.assertEqual(
            result.rejection.code,
            "checklist_item_already_in_target_status",
        )
        self.assertEqual(resolver.mutation_calls, [])

    def test_checklist_callback_rejects_conflict_before_item_lookup(self) -> None:
        data = build_checklist_callback_data(
            action="done",
            shopping_item_id="shopping_list_001:item:001",
        )
        resolver = FakeShoppingChecklistResolver(
            (_shopping_item("shopping_list_001:item:001", "Milk"),)
        )
        parallel_state = FakeParallelActionState(conflicting_action=True)

        result = resolve_checklist_callback(
            data=data,
            binding=_binding(),
            checklist_resolver=resolver,
            parallel_state=parallel_state,
        )

        self.assertFalse(result.allowed)
        assert result.rejection is not None
        self.assertEqual(result.rejection.code, "conflicting_action_in_progress")
        self.assertEqual(resolver.item_calls, [])
        self.assertEqual(resolver.mutation_calls, [])
        self.assertEqual(
            parallel_state.calls,
            [
                {
                    "application_user_id": "user_001",
                    "workflow_id": "workflow_001",
                }
            ],
        )

    def test_checklist_callback_rejects_payload_like_item_id(self) -> None:
        with self.assertRaises(ValueError):
            build_checklist_callback_data(
                action="done",
                shopping_item_id="{\"shopping_item_id\":\"item_001\"}",
            )

        parsed = parse_checklist_callback_data(
            "mpci|done|{\"shopping_item_id\":\"item_001\"}"
        )

        self.assertFalse(parsed.allowed)
        assert parsed.rejection is not None
        self.assertEqual(parsed.rejection.code, "callback_data_unstable")

    def test_text_bought_path_resolves_one_deterministic_match(self) -> None:
        resolver = FakeShoppingChecklistResolver(
            (_shopping_item("shopping_list_001:item:001", "Whole milk"),)
        )

        result = resolve_checklist_text_action(
            text="milk bought",
            binding=_binding(),
            checklist_resolver=resolver,
        )

        self.assertTrue(result.allowed)
        self.assertEqual(result.action, "done")
        self.assertEqual(result.shopping_item_id, "shopping_list_001:item:001")
        self.assertEqual(result.target_status, "completed")
        self.assertEqual(
            resolver.text_calls,
            [
                {
                    "application_user_id": "user_001",
                    "workflow_id": "workflow_001",
                    "text": "milk bought",
                }
            ],
        )
        self.assertEqual(resolver.mutation_calls, [])

    def test_ambiguous_text_returns_disambiguation_without_mutation(self) -> None:
        resolver = FakeShoppingChecklistResolver(
            (
                _shopping_item("shopping_list_001:item:001", "Whole milk"),
                _shopping_item("shopping_list_001:item:003", "Oat milk"),
            )
        )

        result = resolve_checklist_text_action(
            text="milk bought",
            binding=_binding(),
            checklist_resolver=resolver,
        )

        self.assertFalse(result.allowed)
        assert result.rejection is not None
        self.assertEqual(result.rejection.code, "checklist_item_match_ambiguous")
        self.assertEqual(
            [
                candidate.shopping_item_id
                for candidate in result.disambiguation_candidates
            ],
            ["shopping_list_001:item:001", "shopping_list_001:item:003"],
        )
        self.assertEqual(
            result.to_json()["disambiguation_candidates"],
            [
                {
                    "schema_version": SCHEMA_VERSION,
                    "shopping_item_id": "shopping_list_001:item:001",
                    "display_name": "Whole milk",
                    "status": "pending",
                },
                {
                    "schema_version": SCHEMA_VERSION,
                    "shopping_item_id": "shopping_list_001:item:003",
                    "display_name": "Oat milk",
                    "status": "pending",
                },
            ],
        )
        self.assertEqual(resolver.mutation_calls, [])


def _config(
    *,
    max_message_chars: int = 1200,
    rate_limit_seconds: int = 2,
    timezone: str = "UTC",
) -> TelegramAlphaConfig:
    return TelegramAlphaConfig(
        schema_version=SCHEMA_VERSION,
        allowed_telegram_user_id="12345",
        application_user_id="user_001",
        max_message_chars=max_message_chars,
        rate_limit_seconds=rate_limit_seconds,
        timezone=timezone,
    )


def _event(
    *,
    telegram_user_id: str = "12345",
    hermes_session_id: str = "session_001",
    workflow_id: str | None = "workflow_001",
    message_id: str = "message_001",
) -> TelegramAlphaEvent:
    return TelegramAlphaEvent(
        schema_version=SCHEMA_VERSION,
        telegram_user_id=telegram_user_id,
        chat_id="chat_001",
        chat_type="dm",
        message_id=message_id,
        hermes_session_id=hermes_session_id,
        workflow_id=workflow_id,
        thread_id=None,
    )


def _workflow(
    *,
    user_id: str,
    workflow_id: str,
    state: WorkflowState = WorkflowState.PROFILE_REQUIRED,
) -> WorkflowRun:
    return WorkflowRun(
        schema_version=DOMAIN_SCHEMA_VERSION,
        workflow_id=workflow_id,
        user_id=user_id,
        state=state,
        allowed_actions=[action.value for action in allowed_actions(state)],
        attempts=0,
    )


def _binding() -> object:
    result = bind_telegram_alpha_event(
        event=_event(),
        config=_config(),
        workflow_resolver=FakeWorkflowResolver(
            _workflow(user_id="user_001", workflow_id="workflow_001")
        ),
    )
    assert result.binding is not None
    return result.binding


def _confirmation(
    *,
    user_id: str = "user_001",
    workflow_id: str = "workflow_001",
    confirmation_id: str = "conf_001",
    expected_version: int = 3,
    summary_hash: str = "hash_001",
    expires_at: datetime | None = None,
    consumed_at: datetime | None = None,
) -> PendingConfirmation:
    return PendingConfirmation(
        schema_version=SCHEMA_VERSION,
        confirmation_id=confirmation_id,
        user_id=user_id,
        workflow_id=workflow_id,
        expected_version=expected_version,
        summary_hash=summary_hash,
        expires_at=expires_at or (_now() + timedelta(minutes=5)),
        consumed_at=consumed_at,
    )


def _shopping_item(
    shopping_item_id: str,
    display_name: str,
    *,
    status: str = "pending",
) -> TelegramAlphaShoppingItem:
    return TelegramAlphaShoppingItem(
        schema_version=SCHEMA_VERSION,
        shopping_item_id=shopping_item_id,
        display_name=display_name,
        status=status,
    )


def _now() -> datetime:
    return datetime(2026, 7, 12, 12, 0, tzinfo=UTC)


if __name__ == "__main__":
    unittest.main()
