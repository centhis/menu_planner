from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from os import environ
import re
from typing import Mapping, Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from menu_planner.domain.contracts.models import JsonObject, JsonValue, WorkflowRun

SCHEMA_VERSION = "m9.telegram_alpha_binding.v1"
TELEGRAM_ALLOWED_USERS_ENV = "TELEGRAM_ALLOWED_USERS"
ALPHA_USER_ID_ENV = "MENU_PLANNER_ALPHA_USER_ID"
ALPHA_MAX_MESSAGE_CHARS_ENV = "MENU_PLANNER_ALPHA_MAX_MESSAGE_CHARS"
ALPHA_RATE_LIMIT_SECONDS_ENV = "MENU_PLANNER_ALPHA_RATE_LIMIT_SECONDS"
ALPHA_TIMEZONE_ENV = "MENU_PLANNER_ALPHA_TIMEZONE"
DEFAULT_MAX_MESSAGE_CHARS = 1200
DEFAULT_RATE_LIMIT_SECONDS = 2
DEFAULT_TIMEZONE = "UTC"
CALLBACK_PREFIX = "mpc"
CHECKLIST_CALLBACK_PREFIX = "mpci"
MAX_CALLBACK_DATA_BYTES = 64
_CALLBACK_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
_CHECKLIST_ITEM_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


@dataclass(frozen=True)
class TelegramAlphaConfig:
    schema_version: str
    allowed_telegram_user_id: str | None
    application_user_id: str | None
    max_message_chars: int = DEFAULT_MAX_MESSAGE_CHARS
    rate_limit_seconds: int = DEFAULT_RATE_LIMIT_SECONDS
    timezone: str = DEFAULT_TIMEZONE

    @property
    def is_configured(self) -> bool:
        return bool(self.allowed_telegram_user_id and self.application_user_id)

    def safe_summary(self) -> dict[str, bool | str]:
        return {
            "schema_version": self.schema_version,
            "allowed_telegram_user_configured": bool(
                self.allowed_telegram_user_id
            ),
            "application_user_configured": bool(self.application_user_id),
            "max_message_chars": str(self.max_message_chars),
            "rate_limit_seconds": str(self.rate_limit_seconds),
            "timezone": self.timezone,
        }


@dataclass(frozen=True)
class TelegramAlphaEvent:
    schema_version: str
    telegram_user_id: str
    chat_id: str
    chat_type: str
    message_id: str
    hermes_session_id: str
    workflow_id: str | None = None
    thread_id: str | None = None


@dataclass(frozen=True)
class TelegramAlphaBinding:
    schema_version: str
    telegram_user_id: str
    application_user_id: str
    workflow_id: str
    hermes_session_id: str
    chat_id: str
    chat_type: str
    message_id: str
    thread_id: str | None


@dataclass(frozen=True)
class TelegramAlphaRejection:
    code: str
    message: str
    retryable: bool


@dataclass(frozen=True)
class TelegramAlphaBindingResult:
    schema_version: str
    allowed: bool
    binding: TelegramAlphaBinding | None
    rejection: TelegramAlphaRejection | None

    def to_json(self) -> dict[str, object]:
        if self.binding is not None:
            binding: dict[str, object] | None = {
                "schema_version": self.binding.schema_version,
                "telegram_user_id": self.binding.telegram_user_id,
                "application_user_id": self.binding.application_user_id,
                "workflow_id": self.binding.workflow_id,
                "hermes_session_id": self.binding.hermes_session_id,
                "chat_id": self.binding.chat_id,
                "chat_type": self.binding.chat_type,
                "message_id": self.binding.message_id,
                "thread_id": self.binding.thread_id,
            }
        else:
            binding = None

        if self.rejection is not None:
            rejection: dict[str, object] | None = {
                "code": self.rejection.code,
                "message": self.rejection.message,
                "retryable": self.rejection.retryable,
            }
        else:
            rejection = None

        return {
            "schema_version": self.schema_version,
            "allowed": self.allowed,
            "binding": binding,
            "rejection": rejection,
        }


@dataclass(frozen=True)
class TelegramAlphaIngressResult:
    schema_version: str
    allowed: bool
    rejection: TelegramAlphaRejection | None
    normalized_dates: dict[str, str]
    normalized_timezone: str | None

    def to_json(self) -> dict[str, object]:
        if self.rejection is not None:
            rejection: dict[str, object] | None = {
                "code": self.rejection.code,
                "message": self.rejection.message,
                "retryable": self.rejection.retryable,
            }
        else:
            rejection = None

        return {
            "schema_version": self.schema_version,
            "allowed": self.allowed,
            "rejection": rejection,
            "normalized_dates": self.normalized_dates,
            "normalized_timezone": self.normalized_timezone,
        }


@dataclass(frozen=True)
class TelegramAlphaPresentation:
    schema_version: str
    kind: str
    text: str
    parse_mode: str = "plain"

    def to_json(self) -> dict[str, str]:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "text": self.text,
            "parse_mode": self.parse_mode,
        }


@dataclass(frozen=True)
class TelegramAlphaCallback:
    schema_version: str
    action: str
    confirmation_id: str
    expected_version: int
    summary_hash: str


@dataclass(frozen=True)
class TelegramAlphaCallbackResult:
    schema_version: str
    allowed: bool
    action: str | None
    confirmation_id: str | None
    expected_version: int | None
    summary_hash: str | None
    rejection: TelegramAlphaRejection | None

    def to_json(self) -> dict[str, object]:
        if self.rejection is not None:
            rejection: dict[str, object] | None = {
                "code": self.rejection.code,
                "message": self.rejection.message,
                "retryable": self.rejection.retryable,
            }
        else:
            rejection = None

        return {
            "schema_version": self.schema_version,
            "allowed": self.allowed,
            "action": self.action,
            "confirmation_id": self.confirmation_id,
            "expected_version": self.expected_version,
            "summary_hash": self.summary_hash,
            "rejection": rejection,
        }


@dataclass(frozen=True)
class TelegramAlphaShoppingItem:
    schema_version: str
    shopping_item_id: str
    display_name: str
    status: str


@dataclass(frozen=True)
class TelegramAlphaChecklistAction:
    schema_version: str
    action: str
    shopping_item_id: str
    target_status: str


@dataclass(frozen=True)
class TelegramAlphaChecklistActionResult:
    schema_version: str
    allowed: bool
    action: str | None
    shopping_item_id: str | None
    target_status: str | None
    rejection: TelegramAlphaRejection | None
    disambiguation_candidates: tuple[TelegramAlphaShoppingItem, ...] = ()

    def to_json(self) -> dict[str, object]:
        if self.rejection is not None:
            rejection: dict[str, object] | None = {
                "code": self.rejection.code,
                "message": self.rejection.message,
                "retryable": self.rejection.retryable,
            }
        else:
            rejection = None

        return {
            "schema_version": self.schema_version,
            "allowed": self.allowed,
            "action": self.action,
            "shopping_item_id": self.shopping_item_id,
            "target_status": self.target_status,
            "rejection": rejection,
            "disambiguation_candidates": [
                {
                    "schema_version": candidate.schema_version,
                    "shopping_item_id": candidate.shopping_item_id,
                    "display_name": candidate.display_name,
                    "status": candidate.status,
                }
                for candidate in self.disambiguation_candidates
            ],
        }


@dataclass(frozen=True)
class TelegramAlphaWorkflowActionResult:
    schema_version: str
    allowed: bool
    action: str | None
    workflow_id: str | None
    rejection: TelegramAlphaRejection | None

    def to_json(self) -> dict[str, object]:
        if self.rejection is not None:
            rejection: dict[str, object] | None = {
                "code": self.rejection.code,
                "message": self.rejection.message,
                "retryable": self.rejection.retryable,
            }
        else:
            rejection = None

        return {
            "schema_version": self.schema_version,
            "allowed": self.allowed,
            "action": self.action,
            "workflow_id": self.workflow_id,
            "rejection": rejection,
        }


@dataclass(frozen=True)
class TelegramAlphaRestartRecoveryResult:
    schema_version: str
    allowed: bool
    binding: TelegramAlphaBinding | None
    workflow_state: str | None
    allowed_actions: tuple[str, ...]
    pending_confirmation_id: str | None
    expected_version: int | None
    rejection: TelegramAlphaRejection | None

    def to_json(self) -> dict[str, object]:
        if self.rejection is not None:
            rejection: dict[str, object] | None = {
                "code": self.rejection.code,
                "message": self.rejection.message,
                "retryable": self.rejection.retryable,
            }
        else:
            rejection = None

        return {
            "schema_version": self.schema_version,
            "allowed": self.allowed,
            "binding": None if self.binding is None else self.binding.workflow_id,
            "workflow_state": self.workflow_state,
            "allowed_actions": list(self.allowed_actions),
            "pending_confirmation_id": self.pending_confirmation_id,
            "expected_version": self.expected_version,
            "rejection": rejection,
        }


@dataclass(frozen=True)
class PendingConfirmation:
    schema_version: str
    confirmation_id: str
    user_id: str
    workflow_id: str
    expected_version: int
    summary_hash: str
    expires_at: datetime
    consumed_at: datetime | None = None


class WorkflowResolver(Protocol):
    def get_active_workflow(
        self,
        *,
        user_id: str,
        hermes_session_id: str,
    ) -> WorkflowRun | None: ...


class IngressState(Protocol):
    def get_last_message_at(
        self,
        *,
        telegram_user_id: str,
        hermes_session_id: str,
    ) -> datetime | None: ...

    def has_conflicting_action(
        self,
        *,
        application_user_id: str,
        workflow_id: str,
    ) -> bool: ...


class ParallelActionState(Protocol):
    def has_conflicting_action(
        self,
        *,
        application_user_id: str,
        workflow_id: str,
    ) -> bool: ...


class ConfirmationResolver(Protocol):
    def get_pending_confirmation(
        self,
        *,
        confirmation_id: str,
    ) -> PendingConfirmation | None: ...


class RestartConfirmationResolver(Protocol):
    def get_pending_confirmation_for_workflow(
        self,
        *,
        user_id: str,
        workflow_id: str,
    ) -> PendingConfirmation | None: ...


class ShoppingChecklistResolver(Protocol):
    def get_checklist_item(
        self,
        *,
        application_user_id: str,
        workflow_id: str,
        shopping_item_id: str,
    ) -> TelegramAlphaShoppingItem | None: ...

    def find_checklist_items_by_text(
        self,
        *,
        application_user_id: str,
        workflow_id: str,
        text: str,
    ) -> tuple[TelegramAlphaShoppingItem, ...]: ...


def load_telegram_alpha_config(
    env: Mapping[str, str] | None = None,
) -> TelegramAlphaConfig:
    source = env or environ
    allowed_users = _split_csv(source.get(TELEGRAM_ALLOWED_USERS_ENV, ""))
    allowed_user_id = allowed_users[0] if len(allowed_users) == 1 else None
    if allowed_user_id == "*":
        allowed_user_id = None

    application_user_id = _blank_to_none(source.get(ALPHA_USER_ID_ENV, ""))
    return TelegramAlphaConfig(
        schema_version=SCHEMA_VERSION,
        allowed_telegram_user_id=allowed_user_id,
        application_user_id=application_user_id,
        max_message_chars=_positive_int(
            source.get(ALPHA_MAX_MESSAGE_CHARS_ENV, ""),
            DEFAULT_MAX_MESSAGE_CHARS,
        ),
        rate_limit_seconds=_non_negative_int(
            source.get(ALPHA_RATE_LIMIT_SECONDS_ENV, ""),
            DEFAULT_RATE_LIMIT_SECONDS,
        ),
        timezone=_blank_to_none(source.get(ALPHA_TIMEZONE_ENV, ""))
        or DEFAULT_TIMEZONE,
    )


def bind_telegram_alpha_event(
    *,
    event: TelegramAlphaEvent,
    config: TelegramAlphaConfig,
    workflow_resolver: WorkflowResolver,
) -> TelegramAlphaBindingResult:
    if not config.is_configured:
        return _reject("alpha_config_missing", "Telegram Alpha is not configured.")

    assert config.allowed_telegram_user_id is not None
    assert config.application_user_id is not None

    if not event.telegram_user_id.strip():
        return _reject("telegram_user_missing", "Telegram user is missing.")

    if event.telegram_user_id != config.allowed_telegram_user_id:
        return _reject("telegram_user_not_allowed", "Telegram user is not allowed.")

    if not event.hermes_session_id.strip():
        return _reject("telegram_session_missing", "Telegram session is missing.")

    workflow = workflow_resolver.get_active_workflow(
        user_id=config.application_user_id,
        hermes_session_id=event.hermes_session_id,
    )
    if workflow is None:
        return _reject("workflow_not_found", "Active workflow was not found.")

    if workflow.user_id != config.application_user_id:
        return _reject("workflow_user_mismatch", "Workflow belongs to another user.")

    if event.workflow_id is not None and event.workflow_id != workflow.workflow_id:
        return _reject("workflow_id_mismatch", "Workflow id does not match session.")

    return TelegramAlphaBindingResult(
        schema_version=SCHEMA_VERSION,
        allowed=True,
        binding=TelegramAlphaBinding(
            schema_version=SCHEMA_VERSION,
            telegram_user_id=event.telegram_user_id,
            application_user_id=config.application_user_id,
            workflow_id=workflow.workflow_id,
            hermes_session_id=event.hermes_session_id,
            chat_id=event.chat_id,
            chat_type=event.chat_type,
            message_id=event.message_id,
            thread_id=event.thread_id,
        ),
        rejection=None,
    )


def evaluate_telegram_alpha_ingress(
    *,
    text: str,
    event: TelegramAlphaEvent,
    config: TelegramAlphaConfig,
    binding: TelegramAlphaBinding,
    ingress_state: IngressState,
    now: datetime,
) -> TelegramAlphaIngressResult:
    if len(text) > config.max_message_chars:
        return _ingress_reject(
            "message_too_large",
            "Telegram message is too large for Alpha.",
        )

    timezone = _load_timezone(config.timezone)
    if timezone is None:
        return _ingress_reject(
            "invalid_timezone",
            "Telegram Alpha timezone is invalid.",
        )

    last_message_at = ingress_state.get_last_message_at(
        telegram_user_id=event.telegram_user_id,
        hermes_session_id=event.hermes_session_id,
    )
    now_utc = _as_utc(now)
    if (
        last_message_at is not None
        and config.rate_limit_seconds > 0
        and now_utc - _as_utc(last_message_at)
        < timedelta(seconds=config.rate_limit_seconds)
    ):
        return _ingress_reject("rate_limited", "Telegram message rate limited.")

    if ingress_state.has_conflicting_action(
        application_user_id=binding.application_user_id,
        workflow_id=binding.workflow_id,
    ):
        return _ingress_reject(
            "conflicting_action_in_progress",
            "Finish or cancel the current action first.",
        )

    local_now = now_utc.astimezone(timezone)
    return TelegramAlphaIngressResult(
        schema_version=SCHEMA_VERSION,
        allowed=True,
        rejection=None,
        normalized_dates=_normalize_relative_dates(text, local_now),
        normalized_timezone=timezone.key,
    )


def render_telegram_alpha_presentation(
    *,
    kind: str,
    payload: JsonObject,
) -> TelegramAlphaPresentation:
    renderers = {
        "clarification": _render_clarification,
        "preview": _render_preview,
        "validation_warnings": _render_validation_warnings,
        "status": _render_status,
        "error": _render_error,
        "expired_confirmation": _render_expired_confirmation,
        "validation_error": _render_validation_error,
        "policy_error": _render_policy_error,
        "restart_recovery": _render_restart_recovery,
        "cancel": _render_cancel,
        "recipe_view": _render_recipe_view,
        "shopping_checklist": _render_shopping_checklist,
    }
    renderer = renderers.get(kind, _render_unknown)
    return TelegramAlphaPresentation(
        schema_version=SCHEMA_VERSION,
        kind=kind if kind in renderers else "error",
        text=renderer(payload),
    )


def build_confirmation_callback_data(
    *,
    action: str,
    confirmation_id: str,
    expected_version: int,
    summary_hash: str,
) -> str:
    callback = (
        f"{CALLBACK_PREFIX}:{action}:{confirmation_id}:"
        f"{expected_version}:{summary_hash}"
    )
    if len(callback.encode("utf-8")) > MAX_CALLBACK_DATA_BYTES:
        raise ValueError("callback_data exceeds Telegram limit")
    for value in (action, confirmation_id, summary_hash):
        if not _is_stable_callback_token(value):
            raise ValueError("callback_data contains an unstable token")
    if expected_version < 0:
        raise ValueError("expected_version must be non-negative")
    return callback


def parse_confirmation_callback_data(data: str) -> TelegramAlphaCallbackResult:
    callback = _parse_confirmation_callback_data(data)
    if isinstance(callback, TelegramAlphaCallbackResult):
        return callback
    return TelegramAlphaCallbackResult(
        schema_version=SCHEMA_VERSION,
        allowed=True,
        action=callback.action,
        confirmation_id=callback.confirmation_id,
        expected_version=callback.expected_version,
        summary_hash=callback.summary_hash,
        rejection=None,
    )


def resolve_confirmation_callback(
    *,
    data: str,
    binding: TelegramAlphaBinding,
    confirmation_resolver: ConfirmationResolver,
    now: datetime,
    parallel_state: ParallelActionState | None = None,
) -> TelegramAlphaCallbackResult:
    callback = _parse_confirmation_callback_data(data)
    if isinstance(callback, TelegramAlphaCallbackResult):
        return callback

    if (
        parallel_state is not None
        and parallel_state.has_conflicting_action(
            application_user_id=binding.application_user_id,
            workflow_id=binding.workflow_id,
        )
    ):
        return _callback_reject(
            "conflicting_action_in_progress",
            "Finish or cancel the current action first.",
        )

    confirmation = confirmation_resolver.get_pending_confirmation(
        confirmation_id=callback.confirmation_id,
    )
    if confirmation is None:
        return _callback_reject("confirmation_not_found", "Confirmation not found.")

    if confirmation.user_id != binding.application_user_id:
        return _callback_reject(
            "confirmation_user_mismatch",
            "Confirmation belongs to another user.",
        )

    if confirmation.workflow_id != binding.workflow_id:
        return _callback_reject(
            "confirmation_workflow_mismatch",
            "Confirmation belongs to another workflow.",
        )

    if confirmation.consumed_at is not None:
        return _callback_reject(
            "confirmation_already_consumed",
            "Confirmation has already been used.",
        )

    if _as_utc(now) >= _as_utc(confirmation.expires_at):
        return _callback_reject(
            "confirmation_expired",
            "Confirmation has expired.",
        )

    if confirmation.expected_version != callback.expected_version:
        return _callback_reject(
            "confirmation_version_mismatch",
            "Confirmation version does not match.",
        )

    if confirmation.summary_hash != callback.summary_hash:
        return _callback_reject(
            "confirmation_hash_mismatch",
            "Confirmation hash does not match.",
        )

    return TelegramAlphaCallbackResult(
        schema_version=SCHEMA_VERSION,
        allowed=True,
        action=callback.action,
        confirmation_id=callback.confirmation_id,
        expected_version=callback.expected_version,
        summary_hash=callback.summary_hash,
        rejection=None,
    )


def build_checklist_callback_data(
    *,
    action: str,
    shopping_item_id: str,
) -> str:
    if _checklist_action_target_status(action) is None:
        raise ValueError("checklist callback action is invalid")
    if not _is_stable_checklist_item_id(shopping_item_id):
        raise ValueError("checklist callback item id is invalid")

    callback = f"{CHECKLIST_CALLBACK_PREFIX}|{action}|{shopping_item_id}"
    if len(callback.encode("utf-8")) > MAX_CALLBACK_DATA_BYTES:
        raise ValueError("callback_data exceeds Telegram limit")
    return callback


def parse_checklist_callback_data(
    data: str,
) -> TelegramAlphaChecklistActionResult:
    action = _parse_checklist_callback_data(data)
    if isinstance(action, TelegramAlphaChecklistActionResult):
        return action
    return TelegramAlphaChecklistActionResult(
        schema_version=SCHEMA_VERSION,
        allowed=True,
        action=action.action,
        shopping_item_id=action.shopping_item_id,
        target_status=action.target_status,
        rejection=None,
    )


def resolve_checklist_callback(
    *,
    data: str,
    binding: TelegramAlphaBinding,
    checklist_resolver: ShoppingChecklistResolver,
    parallel_state: ParallelActionState | None = None,
) -> TelegramAlphaChecklistActionResult:
    action = _parse_checklist_callback_data(data)
    if isinstance(action, TelegramAlphaChecklistActionResult):
        return action

    if (
        parallel_state is not None
        and parallel_state.has_conflicting_action(
            application_user_id=binding.application_user_id,
            workflow_id=binding.workflow_id,
        )
    ):
        return _checklist_reject(
            "conflicting_action_in_progress",
            "Finish or cancel the current action first.",
        )

    item = checklist_resolver.get_checklist_item(
        application_user_id=binding.application_user_id,
        workflow_id=binding.workflow_id,
        shopping_item_id=action.shopping_item_id,
    )
    if item is None:
        return _checklist_reject(
            "checklist_item_not_found",
            "Shopping checklist item was not found.",
        )

    if item.status == action.target_status:
        return _checklist_reject(
            "checklist_item_already_in_target_status",
            "Shopping checklist item already has that status.",
        )

    return TelegramAlphaChecklistActionResult(
        schema_version=SCHEMA_VERSION,
        allowed=True,
        action=action.action,
        shopping_item_id=action.shopping_item_id,
        target_status=action.target_status,
        rejection=None,
    )


def resolve_checklist_text_action(
    *,
    text: str,
    binding: TelegramAlphaBinding,
    checklist_resolver: ShoppingChecklistResolver,
) -> TelegramAlphaChecklistActionResult:
    action = _text_checklist_action(text)
    if action is None:
        return _checklist_reject(
            "checklist_text_action_unsupported",
            "Checklist text action is unsupported.",
        )
    target_status = _checklist_action_target_status(action)
    assert target_status is not None

    matches = checklist_resolver.find_checklist_items_by_text(
        application_user_id=binding.application_user_id,
        workflow_id=binding.workflow_id,
        text=text,
    )
    if not matches:
        return _checklist_reject(
            "checklist_item_not_found",
            "Shopping checklist item was not found.",
        )
    if len(matches) > 1:
        return _checklist_reject(
            "checklist_item_match_ambiguous",
            "Checklist text matches multiple shopping items.",
            disambiguation_candidates=matches,
        )

    item = matches[0]
    if item.status == target_status:
        return _checklist_reject(
            "checklist_item_already_in_target_status",
            "Shopping checklist item already has that status.",
        )

    return TelegramAlphaChecklistActionResult(
        schema_version=SCHEMA_VERSION,
        allowed=True,
        action=action,
        shopping_item_id=item.shopping_item_id,
        target_status=target_status,
        rejection=None,
    )


def resolve_cancel_workflow_action(
    *,
    binding: TelegramAlphaBinding,
) -> TelegramAlphaWorkflowActionResult:
    if not binding.workflow_id.strip():
        return TelegramAlphaWorkflowActionResult(
            schema_version=SCHEMA_VERSION,
            allowed=False,
            action=None,
            workflow_id=None,
            rejection=TelegramAlphaRejection(
                code="workflow_id_missing",
                message="Workflow id is missing.",
                retryable=False,
            ),
        )

    return TelegramAlphaWorkflowActionResult(
        schema_version=SCHEMA_VERSION,
        allowed=True,
        action="cancel",
        workflow_id=binding.workflow_id,
        rejection=None,
    )


def recover_telegram_alpha_after_restart(
    *,
    event: TelegramAlphaEvent,
    config: TelegramAlphaConfig,
    workflow_resolver: WorkflowResolver,
    confirmation_resolver: RestartConfirmationResolver,
    now: datetime,
) -> TelegramAlphaRestartRecoveryResult:
    binding_result = bind_telegram_alpha_event(
        event=event,
        config=config,
        workflow_resolver=workflow_resolver,
    )
    if not binding_result.allowed or binding_result.binding is None:
        return TelegramAlphaRestartRecoveryResult(
            schema_version=SCHEMA_VERSION,
            allowed=False,
            binding=None,
            workflow_state=None,
            allowed_actions=(),
            pending_confirmation_id=None,
            expected_version=None,
            rejection=binding_result.rejection,
        )

    binding = binding_result.binding
    workflow = workflow_resolver.get_active_workflow(
        user_id=binding.application_user_id,
        hermes_session_id=binding.hermes_session_id,
    )
    if workflow is None:
        return TelegramAlphaRestartRecoveryResult(
            schema_version=SCHEMA_VERSION,
            allowed=False,
            binding=binding,
            workflow_state=None,
            allowed_actions=(),
            pending_confirmation_id=None,
            expected_version=None,
            rejection=TelegramAlphaRejection(
                code="workflow_not_found",
                message="Active workflow was not found.",
                retryable=False,
            ),
        )

    confirmation = confirmation_resolver.get_pending_confirmation_for_workflow(
        user_id=binding.application_user_id,
        workflow_id=binding.workflow_id,
    )
    resumable_confirmation = _resumable_confirmation(
        confirmation=confirmation,
        binding=binding,
        now=now,
    )
    return TelegramAlphaRestartRecoveryResult(
        schema_version=SCHEMA_VERSION,
        allowed=True,
        binding=binding,
        workflow_state=workflow.state.value,
        allowed_actions=tuple(workflow.allowed_actions),
        pending_confirmation_id=None
        if resumable_confirmation is None
        else resumable_confirmation.confirmation_id,
        expected_version=None
        if resumable_confirmation is None
        else resumable_confirmation.expected_version,
        rejection=None,
    )


def _reject(code: str, message: str) -> TelegramAlphaBindingResult:
    return TelegramAlphaBindingResult(
        schema_version=SCHEMA_VERSION,
        allowed=False,
        binding=None,
        rejection=TelegramAlphaRejection(
            code=code,
            message=message,
            retryable=False,
        ),
    )


def _callback_reject(code: str, message: str) -> TelegramAlphaCallbackResult:
    return TelegramAlphaCallbackResult(
        schema_version=SCHEMA_VERSION,
        allowed=False,
        action=None,
        confirmation_id=None,
        expected_version=None,
        summary_hash=None,
        rejection=TelegramAlphaRejection(
            code=code,
            message=message,
            retryable=False,
        ),
    )


def _checklist_reject(
    code: str,
    message: str,
    *,
    disambiguation_candidates: tuple[TelegramAlphaShoppingItem, ...] = (),
) -> TelegramAlphaChecklistActionResult:
    return TelegramAlphaChecklistActionResult(
        schema_version=SCHEMA_VERSION,
        allowed=False,
        action=None,
        shopping_item_id=None,
        target_status=None,
        rejection=TelegramAlphaRejection(
            code=code,
            message=message,
            retryable=False,
        ),
        disambiguation_candidates=disambiguation_candidates,
    )


def _ingress_reject(code: str, message: str) -> TelegramAlphaIngressResult:
    return TelegramAlphaIngressResult(
        schema_version=SCHEMA_VERSION,
        allowed=False,
        rejection=TelegramAlphaRejection(
            code=code,
            message=message,
            retryable=False,
        ),
        normalized_dates={},
        normalized_timezone=None,
    )


def _split_csv(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _blank_to_none(value: str) -> str | None:
    normalized = value.strip()
    return normalized or None


def _positive_int(value: str, default: int) -> int:
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def _non_negative_int(value: str, default: int) -> int:
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed >= 0 else default


def _load_timezone(name: str) -> ZoneInfo | None:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _normalize_relative_dates(text: str, local_now: datetime) -> dict[str, str]:
    lowered = text.casefold()
    dates: dict[str, str] = {}
    if "today" in lowered:
        dates["today"] = local_now.date().isoformat()
    if "tomorrow" in lowered:
        dates["tomorrow"] = (local_now.date() + timedelta(days=1)).isoformat()
    return dates


def _resumable_confirmation(
    *,
    confirmation: PendingConfirmation | None,
    binding: TelegramAlphaBinding,
    now: datetime,
) -> PendingConfirmation | None:
    if confirmation is None:
        return None
    if confirmation.user_id != binding.application_user_id:
        return None
    if confirmation.workflow_id != binding.workflow_id:
        return None
    if confirmation.consumed_at is not None:
        return None
    if _as_utc(now) >= _as_utc(confirmation.expires_at):
        return None
    return confirmation


def _parse_confirmation_callback_data(
    data: str,
) -> TelegramAlphaCallback | TelegramAlphaCallbackResult:
    if len(data.encode("utf-8")) > MAX_CALLBACK_DATA_BYTES:
        return _callback_reject("callback_data_too_large", "Callback data too large.")

    parts = data.split(":")
    if len(parts) != 5 or parts[0] != CALLBACK_PREFIX:
        return _callback_reject("callback_data_invalid", "Callback data is invalid.")

    _, action, confirmation_id, version_text, summary_hash = parts
    if action not in {"confirm", "cancel"}:
        return _callback_reject("callback_action_invalid", "Callback action invalid.")

    if not all(
        _is_stable_callback_token(value)
        for value in (action, confirmation_id, version_text, summary_hash)
    ):
        return _callback_reject("callback_data_unstable", "Callback data unstable.")

    try:
        expected_version = int(version_text)
    except ValueError:
        return _callback_reject(
            "callback_version_invalid",
            "Callback version is invalid.",
        )

    if expected_version < 0:
        return _callback_reject(
            "callback_version_invalid",
            "Callback version is invalid.",
        )

    return TelegramAlphaCallback(
        schema_version=SCHEMA_VERSION,
        action=action,
        confirmation_id=confirmation_id,
        expected_version=expected_version,
        summary_hash=summary_hash,
    )


def _parse_checklist_callback_data(
    data: str,
) -> TelegramAlphaChecklistAction | TelegramAlphaChecklistActionResult:
    if len(data.encode("utf-8")) > MAX_CALLBACK_DATA_BYTES:
        return _checklist_reject(
            "callback_data_too_large",
            "Callback data too large.",
        )

    parts = data.split("|")
    if len(parts) != 3 or parts[0] != CHECKLIST_CALLBACK_PREFIX:
        return _checklist_reject(
            "callback_data_invalid",
            "Callback data is invalid.",
        )

    _, action, shopping_item_id = parts
    target_status = _checklist_action_target_status(action)
    if target_status is None:
        return _checklist_reject(
            "callback_action_invalid",
            "Callback action invalid.",
        )
    if not _is_stable_checklist_item_id(shopping_item_id):
        return _checklist_reject(
            "callback_data_unstable",
            "Callback data unstable.",
        )

    return TelegramAlphaChecklistAction(
        schema_version=SCHEMA_VERSION,
        action=action,
        shopping_item_id=shopping_item_id,
        target_status=target_status,
    )


def _is_stable_callback_token(value: str) -> bool:
    return bool(value) and bool(_CALLBACK_TOKEN_RE.fullmatch(value))


def _is_stable_checklist_item_id(value: str) -> bool:
    return bool(value) and bool(_CHECKLIST_ITEM_ID_RE.fullmatch(value))


def _checklist_action_target_status(action: str) -> str | None:
    return {
        "done": "completed",
        "open": "pending",
    }.get(action)


def _text_checklist_action(text: str) -> str | None:
    normalized_terms = set(_normalize_text(text).split())
    done_terms = {"bought", "done", "куплено", "купил", "купила"}
    if normalized_terms & done_terms:
        return "done"
    return None


def _normalize_text(text: str) -> str:
    return " ".join(text.casefold().replace("_", " ").replace(".", " ").split())


def _render_clarification(payload: JsonObject) -> str:
    question = _text(payload.get("question"), "I need one clarification.")
    choices = _string_list(payload.get("choices"))
    lines = ["Clarification needed", question]
    if choices:
        lines.append("Options:")
        lines.extend(f"{index}. {choice}" for index, choice in enumerate(choices, 1))
    return "\n".join(lines)


def _render_preview(payload: JsonObject) -> str:
    title = _text(payload.get("title"), "Preview")
    summary = _text(payload.get("summary"), "Review the draft before confirming.")
    confirmation_id = _text(payload.get("confirmation_id"), "")
    expected_version = _text(payload.get("expected_version"), "")
    lines = [
        f"Draft preview: {title}",
        summary,
        "This is draft state, not active state.",
    ]
    if confirmation_id:
        lines.append(f"confirmation_id: {confirmation_id}")
    if expected_version:
        lines.append(f"expected_version: {expected_version}")
    return "\n".join(lines)


def _render_validation_warnings(payload: JsonObject) -> str:
    warnings = _string_list(payload.get("warnings"))
    if not warnings:
        return "Validation warnings\nNo warnings."
    lines = ["Validation warnings"]
    lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines)


def _render_status(payload: JsonObject) -> str:
    workflow_state = _text(payload.get("workflow_state"), "unknown")
    draft_state = _text(payload.get("draft_state"), "none")
    active_state = _text(payload.get("active_state"), "none")
    next_action = _text(payload.get("next_action"), "")
    lines = [
        "Status",
        f"Workflow: {workflow_state}",
        f"Draft state: {draft_state}",
        f"Active state: {active_state}",
    ]
    if next_action:
        lines.append(f"Next: {next_action}")
    return "\n".join(lines)


def _render_error(payload: JsonObject) -> str:
    code = _text(payload.get("code"), "unknown_error")
    message = _text(payload.get("message"), "Something went wrong.")
    next_actions = _string_list(payload.get("next_actions"))
    lines = ["Error", f"{code}: {message}"]
    if next_actions:
        lines.append("Next actions:")
        lines.extend(f"- {action}" for action in next_actions)
    return "\n".join(lines)


def _render_expired_confirmation(payload: JsonObject) -> str:
    confirmation_id = _text(payload.get("confirmation_id"), "")
    next_actions = _string_list(payload.get("next_actions"))
    lines = [
        "Confirmation expired",
        "This preview can no longer be confirmed.",
    ]
    if confirmation_id:
        lines.append(f"confirmation_id: {confirmation_id}")
    lines.append("Next actions:")
    if next_actions:
        lines.extend(f"- {action}" for action in next_actions)
    else:
        lines.extend(("- show status", "- create a new preview"))
    return "\n".join(lines)


def _render_validation_error(payload: JsonObject) -> str:
    code = _text(payload.get("code"), "validation_error")
    message = _text(payload.get("message"), "Request failed validation.")
    errors = _string_list(payload.get("errors"))
    next_actions = _string_list(payload.get("next_actions"))
    lines = ["Validation error", f"{code}: {message}"]
    if errors:
        lines.append("Issues:")
        lines.extend(f"- {error}" for error in errors)
    if next_actions:
        lines.append("Next actions:")
        lines.extend(f"- {action}" for action in next_actions)
    return "\n".join(lines)


def _render_policy_error(payload: JsonObject) -> str:
    code = _text(payload.get("code"), "policy_error")
    message = _text(payload.get("message"), "Action is not allowed now.")
    next_actions = _string_list(payload.get("next_actions"))
    lines = ["Policy error", f"{code}: {message}"]
    if next_actions:
        lines.append("Next actions:")
        lines.extend(f"- {action}" for action in next_actions)
    return "\n".join(lines)


def _render_restart_recovery(payload: JsonObject) -> str:
    workflow_state = _text(payload.get("workflow_state"), "unknown")
    confirmation_id = _text(payload.get("pending_confirmation_id"), "")
    expected_version = _text(payload.get("expected_version"), "")
    allowed_actions = _string_list(payload.get("allowed_actions"))
    lines = ["Recovered active workflow", f"Workflow: {workflow_state}"]
    if confirmation_id:
        lines.append(f"pending_confirmation_id: {confirmation_id}")
    if expected_version:
        lines.append(f"expected_version: {expected_version}")
    if allowed_actions:
        lines.append("Allowed actions:")
        lines.extend(f"- {action}" for action in allowed_actions)
    lines.append("Next actions:")
    if confirmation_id:
        lines.extend(("- resume confirmation", "- cancel"))
    else:
        lines.extend(("- continue", "- cancel"))
    return "\n".join(lines)


def _render_cancel(payload: JsonObject) -> str:
    workflow_id = _text(payload.get("workflow_id"), "")
    next_actions = _string_list(payload.get("next_actions"))
    if workflow_id:
        lines = [f"Cancelled workflow {workflow_id}. No active state was changed."]
    else:
        lines = ["Cancelled. No active state was changed."]
    if next_actions:
        lines.append("Next actions:")
        lines.extend(f"- {action}" for action in next_actions)
    return "\n".join(lines)


def _render_recipe_view(payload: JsonObject) -> str:
    title = _text(payload.get("title"), "Recipe")
    portions = _text(payload.get("portions"), "")
    ingredients = _string_list(payload.get("ingredients"))
    steps = _string_list(payload.get("steps"))
    lines = [f"Recipe: {title}"]
    if portions:
        lines.append(f"Portions: {portions}")
    if ingredients:
        lines.append("Ingredients:")
        lines.extend(f"- {ingredient}" for ingredient in ingredients)
    if steps:
        lines.append("Steps:")
        lines.extend(f"{index}. {step}" for index, step in enumerate(steps, 1))
    return "\n".join(lines)


def _render_shopping_checklist(payload: JsonObject) -> str:
    items_value = payload.get("items")
    lines = ["Shopping checklist"]
    if not isinstance(items_value, list) or not items_value:
        lines.append("No items.")
        return "\n".join(lines)

    for item in items_value:
        if not isinstance(item, dict):
            continue
        item_id = _text(item.get("shopping_item_id"), "")
        name = _text(item.get("name"), "item")
        status = _text(item.get("status"), "open")
        prefix = "[x]" if status == "done" else "[ ]"
        if item_id:
            lines.append(f"{prefix} {name} ({item_id})")
        else:
            lines.append(f"{prefix} {name}")
    return "\n".join(lines)


def _render_unknown(_: JsonObject) -> str:
    return "Error\nunsupported_presentation: Unsupported response type."


def _text(value: JsonValue | None, default: str) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, int | float | bool):
        return str(value)
    return default


def _string_list(value: JsonValue | None) -> list[str]:
    if not isinstance(value, list):
        return []
    return [
        item
        for item in (_text(entry, "") for entry in value)
        if item
    ]
