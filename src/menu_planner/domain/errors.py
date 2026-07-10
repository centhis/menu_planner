from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from menu_planner.domain.contracts.models import JsonObject


class UserExposure(StrEnum):
    DIRECT = "direct"
    ADAPTER_REQUIRED = "adapter_required"


class ErrorCode(StrEnum):
    INVALID_CONTRACT_SHAPE = "contract.invalid_shape"
    INVALID_ENUM_VALUE = "contract.invalid_enum_value"
    INVALID_FIELD_TYPE = "contract.invalid_field_type"
    INVALID_RANGE = "contract.invalid_range"
    INVALID_SCHEMA_VERSION = "contract.invalid_schema_version"
    MISSING_REQUIRED_FIELD = "contract.missing_required_field"
    ACTION_NOT_ALLOWED = "policy.action_not_allowed"
    ADMINISTRATIVE_ACTION_DENIED = "policy.administrative_action_denied"
    AMBIGUOUS_OR_INCOMPLETE_INTENT = "policy.ambiguous_or_incomplete_intent"
    OWNERSHIP_REQUIRED = "policy.ownership_required"
    RETRY_LIMIT_REACHED = "policy.retry_limit_reached"
    UNSUPPORTED_INTENT = "policy.unsupported_intent"
    CONFIRMATION_NOT_FOUND = "commit.confirmation_not_found"
    CONFIRMATION_EXPIRED = "commit.confirmation_expired"
    CONFIRMATION_ALREADY_USED = "commit.confirmation_already_used"
    CONFIRMATION_REJECTED_OR_CANCELLED = (
        "commit.confirmation_rejected_or_cancelled"
    )
    CONFIRMATION_USER_MISMATCH = "commit.confirmation_user_mismatch"
    CONFIRMATION_OPERATION_MISMATCH = "commit.confirmation_operation_mismatch"
    CONFIRMATION_ENTITY_MISMATCH = "commit.confirmation_entity_mismatch"
    PREVIEW_SUMMARY_HASH_MISMATCH = "commit.preview_summary_hash_mismatch"
    EXPECTED_VERSION_MISMATCH = "commit.expected_version_mismatch"
    DRAFT_VERSION_MISMATCH = "commit.draft_version_mismatch"
    IDEMPOTENCY_KEY_MISSING = "commit.idempotency_key_missing"
    IDEMPOTENCY_REPLAY = "commit.idempotency_replay"
    IDEMPOTENCY_PAYLOAD_MISMATCH = "commit.idempotency_payload_mismatch"
    TRANSACTION_CONFLICT = "commit.transaction_conflict"
    AUDIT_WRITE_FAILURE = "commit.audit_write_failure"


@dataclass(frozen=True)
class ErrorCatalogEntry:
    code: ErrorCode
    developer_message: str
    machine_fields: tuple[str, ...]
    sources: tuple[str, ...]
    user_exposure: UserExposure


@dataclass(frozen=True)
class DomainError:
    code: ErrorCode
    message: str
    path: tuple[str | int, ...] = ()
    details: JsonObject = field(default_factory=dict)

    def to_json(self) -> JsonObject:
        return {
            "code": self.code.value,
            "message": self.message,
            "path": list(self.path),
            "details": self.details,
        }


ERROR_CATALOG: dict[ErrorCode, ErrorCatalogEntry] = {
    ErrorCode.INVALID_CONTRACT_SHAPE: ErrorCatalogEntry(
        code=ErrorCode.INVALID_CONTRACT_SHAPE,
        developer_message="Contract payload must be a JSON object.",
        machine_fields=(),
        sources=("contract_validation",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.INVALID_ENUM_VALUE: ErrorCatalogEntry(
        code=ErrorCode.INVALID_ENUM_VALUE,
        developer_message="Field contains an unsupported enum value.",
        machine_fields=("field", "expected"),
        sources=("contract_validation",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.INVALID_FIELD_TYPE: ErrorCatalogEntry(
        code=ErrorCode.INVALID_FIELD_TYPE,
        developer_message="Field has an invalid JSON type.",
        machine_fields=("field", "expected"),
        sources=("contract_validation",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.INVALID_RANGE: ErrorCatalogEntry(
        code=ErrorCode.INVALID_RANGE,
        developer_message="Field is outside the allowed deterministic range.",
        machine_fields=("field", "minimum", "maximum", "actual"),
        sources=("contract_validation", "policy"),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.INVALID_SCHEMA_VERSION: ErrorCatalogEntry(
        code=ErrorCode.INVALID_SCHEMA_VERSION,
        developer_message="Contract schema_version is unsupported.",
        machine_fields=("actual",),
        sources=("contract_validation",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.MISSING_REQUIRED_FIELD: ErrorCatalogEntry(
        code=ErrorCode.MISSING_REQUIRED_FIELD,
        developer_message="A required contract field is missing.",
        machine_fields=("field",),
        sources=("contract_validation",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.ACTION_NOT_ALLOWED: ErrorCatalogEntry(
        code=ErrorCode.ACTION_NOT_ALLOWED,
        developer_message="Action is not allowed in the current workflow state.",
        machine_fields=("state", "action", "allowed_actions"),
        sources=("workflow_policy", "state_machine"),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.ADMINISTRATIVE_ACTION_DENIED: ErrorCatalogEntry(
        code=ErrorCode.ADMINISTRATIVE_ACTION_DENIED,
        developer_message="Administrative action is denied in the user workflow.",
        machine_fields=("action", "channel"),
        sources=("workflow_policy",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.AMBIGUOUS_OR_INCOMPLETE_INTENT: ErrorCatalogEntry(
        code=ErrorCode.AMBIGUOUS_OR_INCOMPLETE_INTENT,
        developer_message="Intent requires clarification before policy can allow it.",
        machine_fields=("intent", "missing_fields", "ambiguities"),
        sources=("intent_policy", "workflow_policy"),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.OWNERSHIP_REQUIRED: ErrorCatalogEntry(
        code=ErrorCode.OWNERSHIP_REQUIRED,
        developer_message="Ownership context is required but unavailable.",
        machine_fields=("entity_ref", "user_id"),
        sources=("workflow_policy",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.RETRY_LIMIT_REACHED: ErrorCatalogEntry(
        code=ErrorCode.RETRY_LIMIT_REACHED,
        developer_message="Workflow retry limit has been reached.",
        machine_fields=("workflow_id", "state", "attempts", "limit"),
        sources=("state_machine", "workflow_policy"),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.UNSUPPORTED_INTENT: ErrorCatalogEntry(
        code=ErrorCode.UNSUPPORTED_INTENT,
        developer_message="Intent is unsupported by the M2 policy surface.",
        machine_fields=("intent",),
        sources=("intent_policy", "workflow_policy"),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.CONFIRMATION_NOT_FOUND: ErrorCatalogEntry(
        code=ErrorCode.CONFIRMATION_NOT_FOUND,
        developer_message="Confirmation was not found for the commit request.",
        machine_fields=("confirmation_id", "user_id"),
        sources=("safe_commit", "confirmation_repository"),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.CONFIRMATION_EXPIRED: ErrorCatalogEntry(
        code=ErrorCode.CONFIRMATION_EXPIRED,
        developer_message="Confirmation expired before the commit request.",
        machine_fields=("confirmation_id", "expires_at", "now"),
        sources=("safe_commit", "confirmation_repository"),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.CONFIRMATION_ALREADY_USED: ErrorCatalogEntry(
        code=ErrorCode.CONFIRMATION_ALREADY_USED,
        developer_message="Confirmation has already been used for commit.",
        machine_fields=("confirmation_id", "status"),
        sources=("safe_commit", "confirmation_repository"),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.CONFIRMATION_REJECTED_OR_CANCELLED: ErrorCatalogEntry(
        code=ErrorCode.CONFIRMATION_REJECTED_OR_CANCELLED,
        developer_message="Confirmation was rejected or cancelled before commit.",
        machine_fields=("confirmation_id", "status"),
        sources=("safe_commit", "confirmation_repository"),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.CONFIRMATION_USER_MISMATCH: ErrorCatalogEntry(
        code=ErrorCode.CONFIRMATION_USER_MISMATCH,
        developer_message="Confirmation belongs to a different user.",
        machine_fields=("confirmation_id", "expected_user_id", "actual_user_id"),
        sources=("safe_commit", "confirmation_repository"),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.CONFIRMATION_OPERATION_MISMATCH: ErrorCatalogEntry(
        code=ErrorCode.CONFIRMATION_OPERATION_MISMATCH,
        developer_message="Confirmation operation does not match the commit request.",
        machine_fields=(
            "confirmation_id",
            "expected_operation",
            "actual_operation",
        ),
        sources=("safe_commit", "confirmation_repository"),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.CONFIRMATION_ENTITY_MISMATCH: ErrorCatalogEntry(
        code=ErrorCode.CONFIRMATION_ENTITY_MISMATCH,
        developer_message="Confirmation entity does not match the commit request.",
        machine_fields=("confirmation_id", "expected_entity_id", "actual_entity_id"),
        sources=("safe_commit", "confirmation_repository"),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.PREVIEW_SUMMARY_HASH_MISMATCH: ErrorCatalogEntry(
        code=ErrorCode.PREVIEW_SUMMARY_HASH_MISMATCH,
        developer_message="Preview summary hash does not match the confirmation.",
        machine_fields=(
            "confirmation_id",
            "expected_summary_hash",
            "actual_summary_hash",
        ),
        sources=("safe_commit", "preview_hash"),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.EXPECTED_VERSION_MISMATCH: ErrorCatalogEntry(
        code=ErrorCode.EXPECTED_VERSION_MISMATCH,
        developer_message="Current committed version does not match expected_version.",
        machine_fields=("entity_id", "expected_version", "actual_version"),
        sources=("safe_commit", "version_repository"),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.DRAFT_VERSION_MISMATCH: ErrorCatalogEntry(
        code=ErrorCode.DRAFT_VERSION_MISMATCH,
        developer_message="Draft version does not match the confirmation.",
        machine_fields=("entity_id", "expected_draft_version", "actual_draft_version"),
        sources=("safe_commit", "version_repository"),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.IDEMPOTENCY_KEY_MISSING: ErrorCatalogEntry(
        code=ErrorCode.IDEMPOTENCY_KEY_MISSING,
        developer_message="State-changing commit request requires an idempotency key.",
        machine_fields=("operation", "user_id"),
        sources=("safe_commit", "idempotency_repository"),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.IDEMPOTENCY_REPLAY: ErrorCatalogEntry(
        code=ErrorCode.IDEMPOTENCY_REPLAY,
        developer_message="Idempotency key already has a stored compatible outcome.",
        machine_fields=("idempotency_key", "operation", "outcome_ref"),
        sources=("safe_commit", "idempotency_repository"),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.IDEMPOTENCY_PAYLOAD_MISMATCH: ErrorCatalogEntry(
        code=ErrorCode.IDEMPOTENCY_PAYLOAD_MISMATCH,
        developer_message="Idempotency key was reused with a different payload.",
        machine_fields=(
            "idempotency_key",
            "operation",
            "expected_payload_hash",
            "actual_payload_hash",
        ),
        sources=("safe_commit", "idempotency_repository"),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.TRANSACTION_CONFLICT: ErrorCatalogEntry(
        code=ErrorCode.TRANSACTION_CONFLICT,
        developer_message="Commit transaction conflicted with another transaction.",
        machine_fields=("operation", "entity_id"),
        sources=("safe_commit", "transaction"),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.AUDIT_WRITE_FAILURE: ErrorCatalogEntry(
        code=ErrorCode.AUDIT_WRITE_FAILURE,
        developer_message="Audit event could not be written in the commit transaction.",
        machine_fields=("operation", "entity_id", "reason_code"),
        sources=("safe_commit", "audit_repository"),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
}


def _catalog_error(
    code: ErrorCode,
    path: tuple[str | int, ...] = (),
    details: JsonObject | None = None,
) -> DomainError:
    entry = ERROR_CATALOG[code]
    return DomainError(
        code=entry.code,
        message=entry.developer_message,
        path=path,
        details=details or {},
    )


def missing_required_field(field_name: str) -> DomainError:
    return _catalog_error(
        code=ErrorCode.MISSING_REQUIRED_FIELD,
        path=(field_name,),
        details={"field": field_name},
    )


def invalid_schema_version(actual: str) -> DomainError:
    return _catalog_error(
        code=ErrorCode.INVALID_SCHEMA_VERSION,
        path=("schema_version",),
        details={"actual": actual},
    )


def invalid_field_type(field_name: str, expected: str) -> DomainError:
    return _catalog_error(
        code=ErrorCode.INVALID_FIELD_TYPE,
        path=(field_name,),
        details={"field": field_name, "expected": expected},
    )


def invalid_enum_value(field_name: str, expected: list[str]) -> DomainError:
    return _catalog_error(
        code=ErrorCode.INVALID_ENUM_VALUE,
        path=(field_name,),
        details={"field": field_name, "expected": ",".join(expected)},
    )


def invalid_range(
    field_name: str,
    minimum: int | float,
    maximum: int | float,
    actual: int | float,
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.INVALID_RANGE,
        path=(field_name,),
        details={
            "field": field_name,
            "minimum": minimum,
            "maximum": maximum,
            "actual": actual,
        },
    )


def invalid_contract_shape() -> DomainError:
    return _catalog_error(
        code=ErrorCode.INVALID_CONTRACT_SHAPE,
    )


def action_not_allowed(
    state: str,
    action: str,
    allowed_actions: list[str],
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.ACTION_NOT_ALLOWED,
        details={
            "state": state,
            "action": action,
            "allowed_actions": ",".join(allowed_actions),
        },
    )


def administrative_action_denied(action: str, channel: str) -> DomainError:
    return _catalog_error(
        code=ErrorCode.ADMINISTRATIVE_ACTION_DENIED,
        details={"action": action, "channel": channel},
    )


def ambiguous_or_incomplete_intent(
    intent: str,
    missing_fields: list[str],
    ambiguities: list[str],
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.AMBIGUOUS_OR_INCOMPLETE_INTENT,
        details={
            "intent": intent,
            "missing_fields": ",".join(missing_fields),
            "ambiguities": ",".join(ambiguities),
        },
    )


def unsupported_intent(intent: str) -> DomainError:
    return _catalog_error(
        code=ErrorCode.UNSUPPORTED_INTENT,
        details={"intent": intent},
    )


def ownership_required(entity_ref: str, user_id: str) -> DomainError:
    return _catalog_error(
        code=ErrorCode.OWNERSHIP_REQUIRED,
        details={"entity_ref": entity_ref, "user_id": user_id},
    )


def retry_limit_reached(
    workflow_id: str,
    state: str,
    attempts: int,
    limit: int,
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.RETRY_LIMIT_REACHED,
        details={
            "workflow_id": workflow_id,
            "state": state,
            "attempts": attempts,
            "limit": limit,
        },
    )


def confirmation_not_found(confirmation_id: str, user_id: str) -> DomainError:
    return _catalog_error(
        code=ErrorCode.CONFIRMATION_NOT_FOUND,
        details={"confirmation_id": confirmation_id, "user_id": user_id},
    )


def confirmation_expired(
    confirmation_id: str,
    expires_at: str,
    now: str,
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.CONFIRMATION_EXPIRED,
        details={
            "confirmation_id": confirmation_id,
            "expires_at": expires_at,
            "now": now,
        },
    )


def confirmation_already_used(confirmation_id: str, status: str) -> DomainError:
    return _catalog_error(
        code=ErrorCode.CONFIRMATION_ALREADY_USED,
        details={"confirmation_id": confirmation_id, "status": status},
    )


def confirmation_rejected_or_cancelled(
    confirmation_id: str,
    status: str,
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.CONFIRMATION_REJECTED_OR_CANCELLED,
        details={"confirmation_id": confirmation_id, "status": status},
    )


def confirmation_user_mismatch(
    confirmation_id: str,
    expected_user_id: str,
    actual_user_id: str,
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.CONFIRMATION_USER_MISMATCH,
        details={
            "confirmation_id": confirmation_id,
            "expected_user_id": expected_user_id,
            "actual_user_id": actual_user_id,
        },
    )


def confirmation_operation_mismatch(
    confirmation_id: str,
    expected_operation: str,
    actual_operation: str,
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.CONFIRMATION_OPERATION_MISMATCH,
        details={
            "confirmation_id": confirmation_id,
            "expected_operation": expected_operation,
            "actual_operation": actual_operation,
        },
    )


def confirmation_entity_mismatch(
    confirmation_id: str,
    expected_entity_id: str,
    actual_entity_id: str,
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.CONFIRMATION_ENTITY_MISMATCH,
        details={
            "confirmation_id": confirmation_id,
            "expected_entity_id": expected_entity_id,
            "actual_entity_id": actual_entity_id,
        },
    )


def preview_summary_hash_mismatch(
    confirmation_id: str,
    expected_summary_hash: str,
    actual_summary_hash: str,
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.PREVIEW_SUMMARY_HASH_MISMATCH,
        details={
            "confirmation_id": confirmation_id,
            "expected_summary_hash": expected_summary_hash,
            "actual_summary_hash": actual_summary_hash,
        },
    )


def expected_version_mismatch(
    entity_id: str,
    expected_version: int,
    actual_version: int,
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.EXPECTED_VERSION_MISMATCH,
        details={
            "entity_id": entity_id,
            "expected_version": expected_version,
            "actual_version": actual_version,
        },
    )


def draft_version_mismatch(
    entity_id: str,
    expected_draft_version: int,
    actual_draft_version: int,
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.DRAFT_VERSION_MISMATCH,
        details={
            "entity_id": entity_id,
            "expected_draft_version": expected_draft_version,
            "actual_draft_version": actual_draft_version,
        },
    )


def idempotency_key_missing(operation: str, user_id: str) -> DomainError:
    return _catalog_error(
        code=ErrorCode.IDEMPOTENCY_KEY_MISSING,
        details={"operation": operation, "user_id": user_id},
    )


def idempotency_replay(
    idempotency_key: str,
    operation: str,
    outcome_ref: str,
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.IDEMPOTENCY_REPLAY,
        details={
            "idempotency_key": idempotency_key,
            "operation": operation,
            "outcome_ref": outcome_ref,
        },
    )


def idempotency_payload_mismatch(
    idempotency_key: str,
    operation: str,
    expected_payload_hash: str,
    actual_payload_hash: str,
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.IDEMPOTENCY_PAYLOAD_MISMATCH,
        details={
            "idempotency_key": idempotency_key,
            "operation": operation,
            "expected_payload_hash": expected_payload_hash,
            "actual_payload_hash": actual_payload_hash,
        },
    )


def transaction_conflict(operation: str, entity_id: str) -> DomainError:
    return _catalog_error(
        code=ErrorCode.TRANSACTION_CONFLICT,
        details={"operation": operation, "entity_id": entity_id},
    )


def audit_write_failure(
    operation: str,
    entity_id: str,
    reason_code: str,
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.AUDIT_WRITE_FAILURE,
        details={
            "operation": operation,
            "entity_id": entity_id,
            "reason_code": reason_code,
        },
    )
