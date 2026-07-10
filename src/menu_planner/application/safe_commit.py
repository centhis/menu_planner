from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from types import TracebackType
from typing import Protocol

from menu_planner.domain.contracts.models import (
    SCHEMA_VERSION,
    JsonObject,
    OperationPreview,
)
from menu_planner.domain.errors import (
    DomainError,
    confirmation_already_used,
    confirmation_entity_mismatch,
    confirmation_expired,
    confirmation_not_found,
    confirmation_operation_mismatch,
    confirmation_rejected_or_cancelled,
    confirmation_user_mismatch,
    draft_version_mismatch,
    expected_version_mismatch,
    idempotency_key_missing,
    idempotency_payload_mismatch,
    idempotency_replay,
    preview_summary_hash_mismatch,
    transaction_conflict,
)


@dataclass(frozen=True)
class OperationPreviewInput:
    preview_id: str
    operation: str
    user_id: str
    entity_type: str
    entity_id: str
    expected_version: int
    draft_version: int
    committed_relevant_payload: JsonObject
    requires_confirmation: bool = True
    changes: list[JsonObject] | None = None
    schema_version: str = SCHEMA_VERSION


def canonical_preview_payload(preview: OperationPreviewInput) -> JsonObject:
    return {
        "schema_version": preview.schema_version,
        "operation": preview.operation,
        "user_id": preview.user_id,
        "entity_type": preview.entity_type,
        "entity_id": preview.entity_id,
        "expected_version": preview.expected_version,
        "draft_version": preview.draft_version,
        "committed_relevant_payload": preview.committed_relevant_payload,
    }


def operation_preview_summary_hash(preview: OperationPreviewInput) -> str:
    payload = canonical_preview_payload(preview)
    canonical_json = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def build_operation_preview(preview: OperationPreviewInput) -> OperationPreview:
    return OperationPreview(
        schema_version=preview.schema_version,
        preview_id=preview.preview_id,
        operation=preview.operation,
        entity_ref=f"{preview.entity_type}:{preview.entity_id}",
        summary_hash=operation_preview_summary_hash(preview),
        changes=preview.changes or [],
        requires_confirmation=preview.requires_confirmation,
    )


@dataclass(frozen=True)
class ConfirmationRecord:
    confirmation_id: str
    user_id: str
    operation: str
    entity_type: str
    entity_id: str
    expected_version: int
    draft_version: int
    expires_at: datetime
    summary_hash: str
    status: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    confirmed_at: datetime | None = None
    committed_at: datetime | None = None


@dataclass(frozen=True)
class ConfirmationRequest:
    confirmation_id: str
    user_id: str
    operation: str
    entity_type: str
    entity_id: str
    summary_hash: str
    now: datetime


@dataclass(frozen=True)
class ConfirmationLifecycleResult:
    confirmation: ConfirmationRecord | None
    error: DomainError | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass(frozen=True)
class IdempotencyRecord:
    idempotency_record_id: str
    user_id: str
    operation: str
    idempotency_key: str
    request_fingerprint: str
    status: str
    outcome_ref: str | None = None
    error_code: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class IdempotencyRequest:
    idempotency_record_id: str
    user_id: str
    operation: str
    idempotency_key: str
    payload: JsonObject


@dataclass(frozen=True)
class IdempotencyResult:
    record: IdempotencyRecord | None
    error: DomainError | None = None
    replay: bool = False

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass(frozen=True)
class SafeCommitCommand:
    confirmation_id: str
    idempotency_record_id: str
    committed_record_id: str
    audit_event_id: str
    user_id: str
    operation: str
    entity_type: str
    entity_id: str
    expected_version: int
    draft_version: int
    summary_hash: str
    idempotency_key: str
    now: datetime


@dataclass(frozen=True)
class SafeCommitResult:
    committed_record: VersionedRecord | None = None
    audit_event: AuditEventRecord | None = None
    idempotency_record: IdempotencyRecord | None = None
    error: DomainError | None = None
    replay: bool = False

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass(frozen=True)
class AuditEventRecord:
    audit_event_id: str
    user_id: str
    operation: str
    entity_type: str
    entity_id: str
    result_status: str
    previous_version: int | None = None
    new_version: int | None = None
    confirmation_id: str | None = None
    idempotency_key: str | None = None
    summary_hash: str | None = None
    reason_code: str | None = None
    event_metadata: JsonObject | None = None
    created_at: datetime | None = None


@dataclass(frozen=True)
class VersionedRecord:
    record_id: str
    user_id: str
    entity_type: str
    entity_id: str
    version: int
    lifecycle_status: str
    payload: JsonObject
    confirmation_id: str | None = None
    idempotency_key: str | None = None
    audit_event_id: str | None = None
    created_at: datetime | None = None


class ConfirmationRepository(Protocol):
    def add(self, record: ConfirmationRecord) -> None: ...

    def get(self, confirmation_id: str) -> ConfirmationRecord | None: ...

    def get_for_user(
        self,
        confirmation_id: str,
        user_id: str,
    ) -> ConfirmationRecord | None: ...

    def update_status(
        self,
        confirmation_id: str,
        status: str,
        *,
        confirmed_at: datetime | None = None,
        committed_at: datetime | None = None,
    ) -> None: ...


class IdempotencyRepository(Protocol):
    def add(self, record: IdempotencyRecord) -> None: ...

    def get(
        self,
        user_id: str,
        operation: str,
        idempotency_key: str,
    ) -> IdempotencyRecord | None: ...

    def update_outcome(
        self,
        idempotency_record_id: str,
        status: str,
        *,
        outcome_ref: str | None = None,
        error_code: str | None = None,
    ) -> None: ...


class AuditEventRepository(Protocol):
    def add(self, record: AuditEventRecord) -> None: ...

    def get(self, audit_event_id: str) -> AuditEventRecord | None: ...


class VersionedRecordRepository(Protocol):
    def add(self, record: VersionedRecord) -> None: ...

    def get(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
        version: int,
        lifecycle_status: str,
    ) -> VersionedRecord | None: ...

    def get_current_committed(
        self,
        user_id: str,
        entity_type: str,
        entity_id: str,
    ) -> VersionedRecord | None: ...


class SafeCommitUnitOfWork(Protocol):
    confirmations: ConfirmationRepository
    idempotency_records: IdempotencyRepository
    audit_events: AuditEventRepository
    versioned_records: VersionedRecordRepository

    def __enter__(self) -> SafeCommitUnitOfWork: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


def idempotency_request_fingerprint(payload: JsonObject) -> str:
    canonical_json = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


class IdempotencyService:
    def __init__(self, repository: IdempotencyRepository) -> None:
        self._repository = repository

    def start(self, request: IdempotencyRequest) -> IdempotencyResult:
        if not request.idempotency_key:
            return IdempotencyResult(
                record=None,
                error=idempotency_key_missing(request.operation, request.user_id),
            )

        fingerprint = idempotency_request_fingerprint(request.payload)
        existing = self._repository.get(
            request.user_id,
            request.operation,
            request.idempotency_key,
        )
        if existing is None:
            record = IdempotencyRecord(
                idempotency_record_id=request.idempotency_record_id,
                user_id=request.user_id,
                operation=request.operation,
                idempotency_key=request.idempotency_key,
                request_fingerprint=fingerprint,
                status="in_progress",
            )
            self._repository.add(record)
            return IdempotencyResult(record=record)

        if existing.request_fingerprint != fingerprint:
            return IdempotencyResult(
                record=existing,
                error=idempotency_payload_mismatch(
                    request.idempotency_key,
                    request.operation,
                    existing.request_fingerprint,
                    fingerprint,
                ),
            )

        return IdempotencyResult(
            record=existing,
            error=idempotency_replay(
                request.idempotency_key,
                request.operation,
                existing.outcome_ref or existing.status,
            ),
            replay=True,
        )

    def record_outcome(
        self,
        idempotency_record_id: str,
        status: str,
        *,
        outcome_ref: str | None = None,
        error_code: str | None = None,
    ) -> None:
        self._repository.update_outcome(
            idempotency_record_id,
            status,
            outcome_ref=outcome_ref,
            error_code=error_code,
        )


class SafeCommitOrchestrator:
    def __init__(
        self,
        unit_of_work_factory: Callable[[], SafeCommitUnitOfWork],
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    def commit(self, command: SafeCommitCommand) -> SafeCommitResult:
        with self._unit_of_work_factory() as unit_of_work:
            confirmation_lifecycle = ConfirmationLifecycle(unit_of_work.confirmations)
            idempotency = IdempotencyService(unit_of_work.idempotency_records)

            idempotency_result = idempotency.start(
                IdempotencyRequest(
                    idempotency_record_id=command.idempotency_record_id,
                    user_id=command.user_id,
                    operation=command.operation,
                    idempotency_key=command.idempotency_key,
                    payload=_safe_commit_idempotency_payload(command),
                )
            )
            if idempotency_result.replay or idempotency_result.error is not None:
                unit_of_work.rollback()
                return SafeCommitResult(
                    idempotency_record=idempotency_result.record,
                    error=idempotency_result.error,
                    replay=idempotency_result.replay,
                )
            if idempotency_result.record is None:
                unit_of_work.rollback()
                return SafeCommitResult(
                    error=transaction_conflict(command.operation, command.entity_id)
                )

            confirmation_result = confirmation_lifecycle.validate_for_commit(
                ConfirmationRequest(
                    confirmation_id=command.confirmation_id,
                    user_id=command.user_id,
                    operation=command.operation,
                    entity_type=command.entity_type,
                    entity_id=command.entity_id,
                    summary_hash=command.summary_hash,
                    now=command.now,
                )
            )
            if confirmation_result.error is not None:
                _record_failed_idempotency(
                    idempotency,
                    idempotency_result.record,
                    confirmation_result.error,
                )
                unit_of_work.commit()
                return SafeCommitResult(
                    idempotency_record=idempotency_result.record,
                    error=confirmation_result.error,
                )

            version_error = _version_error(command, unit_of_work.versioned_records)
            if version_error is not None:
                _record_failed_idempotency(
                    idempotency,
                    idempotency_result.record,
                    version_error,
                )
                unit_of_work.commit()
                return SafeCommitResult(
                    idempotency_record=idempotency_result.record,
                    error=version_error,
                )

            draft = unit_of_work.versioned_records.get(
                command.user_id,
                command.entity_type,
                command.entity_id,
                command.draft_version,
                "draft",
            )
            if draft is None:
                error = draft_version_mismatch(
                    command.entity_id,
                    command.draft_version,
                    -1,
                )
                _record_failed_idempotency(
                    idempotency,
                    idempotency_result.record,
                    error,
                )
                unit_of_work.commit()
                return SafeCommitResult(
                    idempotency_record=idempotency_result.record,
                    error=error,
                )

            current = unit_of_work.versioned_records.get_current_committed(
                command.user_id,
                command.entity_type,
                command.entity_id,
            )
            previous_version = current.version if current is not None else None
            committed = VersionedRecord(
                record_id=command.committed_record_id,
                user_id=command.user_id,
                entity_type=command.entity_type,
                entity_id=command.entity_id,
                version=draft.version,
                lifecycle_status="committed",
                payload=draft.payload,
                confirmation_id=command.confirmation_id,
                idempotency_key=command.idempotency_key,
                audit_event_id=command.audit_event_id,
            )
            audit_event = AuditEventRecord(
                audit_event_id=command.audit_event_id,
                user_id=command.user_id,
                operation=command.operation,
                entity_type=command.entity_type,
                entity_id=command.entity_id,
                result_status="succeeded",
                previous_version=previous_version,
                new_version=committed.version,
                confirmation_id=command.confirmation_id,
                idempotency_key=command.idempotency_key,
                summary_hash=command.summary_hash,
                event_metadata={"draft_record_id": draft.record_id},
            )

            try:
                unit_of_work.versioned_records.add(committed)
            except Exception:  # noqa: BLE001 - adapters normalize DB conflicts.
                unit_of_work.rollback()
                return SafeCommitResult(
                    error=transaction_conflict(command.operation, command.entity_id)
                )

            try:
                confirmation_lifecycle.mark_committed(
                    command.confirmation_id,
                    command.now,
                )
                idempotency.record_outcome(
                    idempotency_result.record.idempotency_record_id,
                    "completed",
                    outcome_ref=committed.record_id,
                )
                unit_of_work.audit_events.add(audit_event)
            except Exception:  # noqa: BLE001 - rollback keeps commit atomic.
                unit_of_work.rollback()
                return SafeCommitResult(
                    error=transaction_conflict(command.operation, command.entity_id)
                )

            unit_of_work.commit()
            completed_record = unit_of_work.idempotency_records.get(
                command.user_id,
                command.operation,
                command.idempotency_key,
            )
            return SafeCommitResult(
                committed_record=committed,
                audit_event=audit_event,
                idempotency_record=completed_record,
            )


class ConfirmationLifecycle:
    def __init__(self, repository: ConfirmationRepository) -> None:
        self._repository = repository

    def create_pending(self, record: ConfirmationRecord) -> ConfirmationRecord:
        if record.status != "pending":
            raise ValueError("new confirmation must start with pending status")
        self._repository.add(record)
        return record

    def get_for_user(
        self,
        confirmation_id: str,
        user_id: str,
    ) -> ConfirmationLifecycleResult:
        confirmation = self._repository.get_for_user(confirmation_id, user_id)
        if confirmation is None:
            return ConfirmationLifecycleResult(
                confirmation=None,
                error=confirmation_not_found(confirmation_id, user_id),
            )
        return ConfirmationLifecycleResult(confirmation=confirmation)

    def confirm(self, request: ConfirmationRequest) -> ConfirmationLifecycleResult:
        result = self._validate_request(
            request,
            allowed_statuses={"pending"},
        )
        if result.error is not None or result.confirmation is None:
            return result

        self._repository.update_status(
            request.confirmation_id,
            "confirmed",
            confirmed_at=request.now,
        )
        confirmed = self._repository.get(request.confirmation_id) or result.confirmation
        return ConfirmationLifecycleResult(confirmation=confirmed)

    def reject(
        self,
        confirmation_id: str,
        user_id: str,
    ) -> ConfirmationLifecycleResult:
        confirmation = self._repository.get(confirmation_id)
        if confirmation is None:
            return ConfirmationLifecycleResult(
                confirmation=None,
                error=confirmation_not_found(confirmation_id, user_id),
            )
        if confirmation.user_id != user_id:
            return ConfirmationLifecycleResult(
                confirmation=confirmation,
                error=confirmation_user_mismatch(
                    confirmation_id,
                    user_id,
                    confirmation.user_id,
                ),
            )
        if confirmation.status in {"committed", "used"}:
            return ConfirmationLifecycleResult(
                confirmation=confirmation,
                error=confirmation_already_used(confirmation_id, confirmation.status),
            )
        if confirmation.status == "rejected":
            return ConfirmationLifecycleResult(
                confirmation=confirmation,
                error=confirmation_rejected_or_cancelled(
                    confirmation_id,
                    confirmation.status,
                ),
            )

        self._repository.update_status(confirmation_id, "rejected")
        rejected = self._repository.get(confirmation_id) or confirmation
        return ConfirmationLifecycleResult(confirmation=rejected)

    def validate_for_commit(
        self,
        request: ConfirmationRequest,
    ) -> ConfirmationLifecycleResult:
        return self._validate_request(
            request,
            allowed_statuses={"confirmed"},
        )

    def mark_committed(
        self,
        confirmation_id: str,
        committed_at: datetime,
    ) -> None:
        self._repository.update_status(
            confirmation_id,
            "committed",
            committed_at=committed_at,
        )

    def mark_used(self, confirmation_id: str) -> None:
        self._repository.update_status(confirmation_id, "used")

    def _validate_request(
        self,
        request: ConfirmationRequest,
        allowed_statuses: set[str],
    ) -> ConfirmationLifecycleResult:
        confirmation = self._repository.get(request.confirmation_id)
        if confirmation is None:
            return ConfirmationLifecycleResult(
                confirmation=None,
                error=confirmation_not_found(request.confirmation_id, request.user_id),
            )

        error = _confirmation_request_error(confirmation, request, allowed_statuses)
        if error is not None:
            return ConfirmationLifecycleResult(confirmation=confirmation, error=error)
        return ConfirmationLifecycleResult(confirmation=confirmation)


def _confirmation_request_error(
    confirmation: ConfirmationRecord,
    request: ConfirmationRequest,
    allowed_statuses: set[str],
) -> DomainError | None:
    if confirmation.user_id != request.user_id:
        return confirmation_user_mismatch(
            confirmation.confirmation_id,
            request.user_id,
            confirmation.user_id,
        )
    if confirmation.operation != request.operation:
        return confirmation_operation_mismatch(
            confirmation.confirmation_id,
            request.operation,
            confirmation.operation,
        )
    if (
        confirmation.entity_type != request.entity_type
        or confirmation.entity_id != request.entity_id
    ):
        return confirmation_entity_mismatch(
            confirmation.confirmation_id,
            f"{request.entity_type}:{request.entity_id}",
            f"{confirmation.entity_type}:{confirmation.entity_id}",
        )
    if confirmation.expires_at <= request.now:
        return confirmation_expired(
            confirmation.confirmation_id,
            confirmation.expires_at.isoformat(),
            request.now.isoformat(),
        )
    if confirmation.status in {"committed", "used"}:
        return confirmation_already_used(
            confirmation.confirmation_id,
            confirmation.status,
        )
    if confirmation.status in {"rejected", "expired"}:
        return confirmation_rejected_or_cancelled(
            confirmation.confirmation_id,
            confirmation.status,
        )
    if confirmation.status not in allowed_statuses:
        return confirmation_already_used(
            confirmation.confirmation_id,
            confirmation.status,
        )
    if confirmation.summary_hash != request.summary_hash:
        return preview_summary_hash_mismatch(
            confirmation.confirmation_id,
            confirmation.summary_hash,
            request.summary_hash,
        )
    return None


def _record_failed_idempotency(
    idempotency: IdempotencyService,
    record: IdempotencyRecord,
    error: DomainError,
) -> None:
    idempotency.record_outcome(
        record.idempotency_record_id,
        "failed",
        error_code=error.code.value,
    )


def _safe_commit_idempotency_payload(command: SafeCommitCommand) -> JsonObject:
    return {
        "confirmation_id": command.confirmation_id,
        "user_id": command.user_id,
        "operation": command.operation,
        "entity_type": command.entity_type,
        "entity_id": command.entity_id,
        "expected_version": command.expected_version,
        "draft_version": command.draft_version,
        "summary_hash": command.summary_hash,
    }


def _version_error(
    command: SafeCommitCommand,
    repository: VersionedRecordRepository,
) -> DomainError | None:
    current = repository.get_current_committed(
        command.user_id,
        command.entity_type,
        command.entity_id,
    )
    actual_version = current.version if current is not None else 0
    if actual_version != command.expected_version:
        return expected_version_mismatch(
            command.entity_id,
            command.expected_version,
            actual_version,
        )

    draft = repository.get(
        command.user_id,
        command.entity_type,
        command.entity_id,
        command.draft_version,
        "draft",
    )
    if draft is None:
        return draft_version_mismatch(command.entity_id, command.draft_version, -1)
    return None
