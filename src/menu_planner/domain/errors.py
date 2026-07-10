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
