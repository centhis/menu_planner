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
    MENU_PERIOD_INCOMPLETE = "menu.period_incomplete"
    MENU_MEAL_SLOT_MISSING = "menu.meal_slot_missing"
    MENU_STRICT_RESTRICTION_VIOLATED = "menu.strict_restriction_violated"
    MENU_EQUIPMENT_UNAVAILABLE = "menu.equipment_unavailable"
    MENU_ACTIVE_TIME_EXCEEDED = "menu.active_time_exceeded"
    MENU_PORTIONS_INVALID = "menu.portions_invalid"
    MENU_REPETITION_VIOLATED = "menu.repetition_violated"
    MENU_REFERENTIAL_INTEGRITY_VIOLATED = (
        "menu.referential_integrity_violated"
    )
    MENU_REPLACEMENT_NOT_LOCAL = "menu.replacement_not_local"
    RECIPE_SOURCE_MISMATCH = "recipe.source_mismatch"
    RECIPE_EQUIPMENT_UNAVAILABLE = "recipe.equipment_unavailable"
    SHOPPING_UNKNOWN_UNIT = "shopping.unknown_unit"
    SHOPPING_UNSUPPORTED_DIMENSION = "shopping.unsupported_dimension"
    SHOPPING_PRODUCT_NOT_FOUND = "shopping.product_not_found"
    SHOPPING_PRODUCT_MATCH_AMBIGUOUS = "shopping.product_match_ambiguous"
    SHOPPING_PACKAGE_SHAPE_INVALID = "shopping.package_shape_invalid"
    SHOPPING_PRICE_MISSING = "shopping.price_missing"
    SHOPPING_ITEM_NOT_FOUND = "shopping.item_not_found"
    SHOPPING_LIST_STALE = "shopping.list_stale"
    SHOPPING_ITEM_MATCH_AMBIGUOUS = "shopping.item_match_ambiguous"


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
    ErrorCode.MENU_PERIOD_INCOMPLETE: ErrorCatalogEntry(
        code=ErrorCode.MENU_PERIOD_INCOMPLETE,
        developer_message="Menu draft does not cover the requested planning period.",
        machine_fields=("expected_start", "expected_end", "actual_start", "actual_end"),
        sources=("menu_validation",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.MENU_MEAL_SLOT_MISSING: ErrorCatalogEntry(
        code=ErrorCode.MENU_MEAL_SLOT_MISSING,
        developer_message="Menu draft does not cover the required meal slots.",
        machine_fields=("expected_slot_ids", "actual_slot_ids"),
        sources=("menu_validation",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.MENU_STRICT_RESTRICTION_VIOLATED: ErrorCatalogEntry(
        code=ErrorCode.MENU_STRICT_RESTRICTION_VIOLATED,
        developer_message="Menu draft violates a strict planning restriction.",
        machine_fields=("restriction", "meal_slot_id", "title"),
        sources=("menu_validation",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.MENU_EQUIPMENT_UNAVAILABLE: ErrorCatalogEntry(
        code=ErrorCode.MENU_EQUIPMENT_UNAVAILABLE,
        developer_message="Menu draft requires unavailable equipment.",
        machine_fields=("required_equipment", "available_equipment", "meal_slot_id"),
        sources=("menu_validation",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.MENU_ACTIVE_TIME_EXCEEDED: ErrorCatalogEntry(
        code=ErrorCode.MENU_ACTIVE_TIME_EXCEEDED,
        developer_message="Menu draft exceeds the active-time limit.",
        machine_fields=("limit_minutes", "actual_minutes", "meal_slot_id"),
        sources=("menu_validation",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.MENU_PORTIONS_INVALID: ErrorCatalogEntry(
        code=ErrorCode.MENU_PORTIONS_INVALID,
        developer_message="Menu draft has invalid portion information.",
        machine_fields=("expected_portions", "actual_portions", "meal_slot_id"),
        sources=("menu_validation",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.MENU_REPETITION_VIOLATED: ErrorCatalogEntry(
        code=ErrorCode.MENU_REPETITION_VIOLATED,
        developer_message="Menu draft repeats the same generated item.",
        machine_fields=("title", "meal_slot_ids"),
        sources=("menu_validation",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.MENU_REFERENTIAL_INTEGRITY_VIOLATED: ErrorCatalogEntry(
        code=ErrorCode.MENU_REFERENTIAL_INTEGRITY_VIOLATED,
        developer_message="Menu draft references unknown or inconsistent meal slots.",
        machine_fields=("meal_slot_id", "known_slot_ids"),
        sources=("menu_validation",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.MENU_REPLACEMENT_NOT_LOCAL: ErrorCatalogEntry(
        code=ErrorCode.MENU_REPLACEMENT_NOT_LOCAL,
        developer_message="Meal replacement must change exactly one target meal slot.",
        machine_fields=("target_meal_slot_id", "changed_meal_slot_ids", "reason"),
        sources=("menu_replacement",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.RECIPE_SOURCE_MISMATCH: ErrorCatalogEntry(
        code=ErrorCode.RECIPE_SOURCE_MISMATCH,
        developer_message="Recipe draft does not match the accepted source menu item.",
        machine_fields=("field", "expected", "actual"),
        sources=("recipe_validation",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.RECIPE_EQUIPMENT_UNAVAILABLE: ErrorCatalogEntry(
        code=ErrorCode.RECIPE_EQUIPMENT_UNAVAILABLE,
        developer_message="Recipe draft requires unavailable equipment.",
        machine_fields=("required_equipment", "available_equipment"),
        sources=("recipe_validation",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.SHOPPING_UNKNOWN_UNIT: ErrorCatalogEntry(
        code=ErrorCode.SHOPPING_UNKNOWN_UNIT,
        developer_message="Shopping-list calculation received an unknown unit.",
        machine_fields=("field", "unit", "supported_units"),
        sources=("shopping_validation",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.SHOPPING_UNSUPPORTED_DIMENSION: ErrorCatalogEntry(
        code=ErrorCode.SHOPPING_UNSUPPORTED_DIMENSION,
        developer_message=(
            "Shopping-list calculation received an unsupported unit dimension."
        ),
        machine_fields=("field", "dimension", "supported_dimensions"),
        sources=("shopping_validation",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.SHOPPING_PRODUCT_NOT_FOUND: ErrorCatalogEntry(
        code=ErrorCode.SHOPPING_PRODUCT_NOT_FOUND,
        developer_message="No reviewed catalog product matches the ingredient.",
        machine_fields=("ingredient_id", "snapshot_id", "snapshot_version"),
        sources=("shopping_catalog_matching",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.SHOPPING_PRODUCT_MATCH_AMBIGUOUS: ErrorCatalogEntry(
        code=ErrorCode.SHOPPING_PRODUCT_MATCH_AMBIGUOUS,
        developer_message=(
            "Multiple reviewed catalog products match the ingredient."
        ),
        machine_fields=(
            "ingredient_id",
            "snapshot_id",
            "snapshot_version",
            "candidate_product_ids",
        ),
        sources=("shopping_catalog_matching",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.SHOPPING_PACKAGE_SHAPE_INVALID: ErrorCatalogEntry(
        code=ErrorCode.SHOPPING_PACKAGE_SHAPE_INVALID,
        developer_message="Catalog package shape cannot satisfy ingredient quantity.",
        machine_fields=("ingredient_id", "product_id", "reason"),
        sources=("shopping_package_calculation",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.SHOPPING_PRICE_MISSING: ErrorCatalogEntry(
        code=ErrorCode.SHOPPING_PRICE_MISSING,
        developer_message="Catalog product has no reviewed price for cost calculation.",
        machine_fields=("product_id",),
        sources=("shopping_package_calculation",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.SHOPPING_ITEM_NOT_FOUND: ErrorCatalogEntry(
        code=ErrorCode.SHOPPING_ITEM_NOT_FOUND,
        developer_message="Shopping list item was not found for exact update.",
        machine_fields=("shopping_list_id", "shopping_item_id", "version"),
        sources=("shopping_checklist_update",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.SHOPPING_LIST_STALE: ErrorCatalogEntry(
        code=ErrorCode.SHOPPING_LIST_STALE,
        developer_message="Shopping list version or source hash is stale.",
        machine_fields=(
            "shopping_list_id",
            "expected_version",
            "actual_version",
            "expected_source_hash",
            "actual_source_hash",
        ),
        sources=("shopping_checklist_update",),
        user_exposure=UserExposure.ADAPTER_REQUIRED,
    ),
    ErrorCode.SHOPPING_ITEM_MATCH_AMBIGUOUS: ErrorCatalogEntry(
        code=ErrorCode.SHOPPING_ITEM_MATCH_AMBIGUOUS,
        developer_message="Checklist text matches multiple shopping list items.",
        machine_fields=("query", "candidate_shopping_item_ids"),
        sources=("shopping_checklist_update",),
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


def shopping_item_not_found(
    shopping_list_id: str,
    shopping_item_id: str,
    version: int,
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.SHOPPING_ITEM_NOT_FOUND,
        path=("generated_items",),
        details={
            "shopping_list_id": shopping_list_id,
            "shopping_item_id": shopping_item_id,
            "version": version,
        },
    )


def shopping_list_stale(
    shopping_list_id: str,
    expected_version: int,
    actual_version: int,
    expected_source_hash: str,
    actual_source_hash: str,
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.SHOPPING_LIST_STALE,
        details={
            "shopping_list_id": shopping_list_id,
            "expected_version": expected_version,
            "actual_version": actual_version,
            "expected_source_hash": expected_source_hash,
            "actual_source_hash": actual_source_hash,
        },
    )


def shopping_item_match_ambiguous(
    query: str,
    candidate_shopping_item_ids: list[str],
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.SHOPPING_ITEM_MATCH_AMBIGUOUS,
        details={
            "query": query,
            "candidate_shopping_item_ids": ",".join(candidate_shopping_item_ids),
        },
    )


def menu_period_incomplete(
    expected_start: str,
    expected_end: str,
    actual_start: str,
    actual_end: str,
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.MENU_PERIOD_INCOMPLETE,
        path=("period_start",),
        details={
            "expected_start": expected_start,
            "expected_end": expected_end,
            "actual_start": actual_start,
            "actual_end": actual_end,
        },
    )


def menu_meal_slot_missing(
    expected_slot_ids: list[str],
    actual_slot_ids: list[str],
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.MENU_MEAL_SLOT_MISSING,
        path=("meal_slots",),
        details={
            "expected_slot_ids": ",".join(expected_slot_ids),
            "actual_slot_ids": ",".join(actual_slot_ids),
        },
    )


def menu_strict_restriction_violated(
    restriction: str,
    meal_slot_id: str,
    title: str,
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.MENU_STRICT_RESTRICTION_VIOLATED,
        path=("generated_items",),
        details={
            "restriction": restriction,
            "meal_slot_id": meal_slot_id,
            "title": title,
        },
    )


def menu_equipment_unavailable(
    required_equipment: list[str],
    available_equipment: list[str],
    meal_slot_id: str,
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.MENU_EQUIPMENT_UNAVAILABLE,
        path=("generated_items",),
        details={
            "required_equipment": ",".join(required_equipment),
            "available_equipment": ",".join(available_equipment),
            "meal_slot_id": meal_slot_id,
        },
    )


def menu_active_time_exceeded(
    limit_minutes: int,
    actual_minutes: int,
    meal_slot_id: str,
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.MENU_ACTIVE_TIME_EXCEEDED,
        path=("generated_items",),
        details={
            "limit_minutes": limit_minutes,
            "actual_minutes": actual_minutes,
            "meal_slot_id": meal_slot_id,
        },
    )


def menu_portions_invalid(
    expected_portions: int,
    actual_portions: int,
    meal_slot_id: str,
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.MENU_PORTIONS_INVALID,
        path=("generated_items",),
        details={
            "expected_portions": expected_portions,
            "actual_portions": actual_portions,
            "meal_slot_id": meal_slot_id,
        },
    )


def menu_repetition_violated(title: str, meal_slot_ids: list[str]) -> DomainError:
    return _catalog_error(
        code=ErrorCode.MENU_REPETITION_VIOLATED,
        path=("generated_items",),
        details={"title": title, "meal_slot_ids": ",".join(meal_slot_ids)},
    )


def menu_referential_integrity_violated(
    meal_slot_id: str,
    known_slot_ids: list[str],
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.MENU_REFERENTIAL_INTEGRITY_VIOLATED,
        path=("generated_items",),
        details={
            "meal_slot_id": meal_slot_id,
            "known_slot_ids": ",".join(known_slot_ids),
        },
    )


def menu_replacement_not_local(
    target_meal_slot_id: str,
    changed_meal_slot_ids: list[str],
    reason: str,
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.MENU_REPLACEMENT_NOT_LOCAL,
        path=("generated_items",),
        details={
            "target_meal_slot_id": target_meal_slot_id,
            "changed_meal_slot_ids": ",".join(changed_meal_slot_ids),
            "reason": reason,
        },
    )


def recipe_source_mismatch(field: str, expected: str, actual: str) -> DomainError:
    return _catalog_error(
        code=ErrorCode.RECIPE_SOURCE_MISMATCH,
        path=(field,),
        details={"field": field, "expected": expected, "actual": actual},
    )


def recipe_equipment_unavailable(
    required_equipment: list[str],
    available_equipment: list[str],
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.RECIPE_EQUIPMENT_UNAVAILABLE,
        path=("equipment",),
        details={
            "required_equipment": ",".join(required_equipment),
            "available_equipment": ",".join(available_equipment),
        },
    )


def shopping_unknown_unit(
    field: str,
    unit: str,
    supported_units: list[str],
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.SHOPPING_UNKNOWN_UNIT,
        path=(field,),
        details={
            "field": field,
            "unit": unit,
            "supported_units": ",".join(supported_units),
        },
    )


def shopping_unsupported_dimension(
    field: str,
    dimension: str,
    supported_dimensions: list[str],
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.SHOPPING_UNSUPPORTED_DIMENSION,
        path=(field,),
        details={
            "field": field,
            "dimension": dimension,
            "supported_dimensions": ",".join(supported_dimensions),
        },
    )


def shopping_product_not_found(
    ingredient_id: str,
    snapshot_id: str,
    snapshot_version: int,
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.SHOPPING_PRODUCT_NOT_FOUND,
        path=("ingredient_id",),
        details={
            "ingredient_id": ingredient_id,
            "snapshot_id": snapshot_id,
            "snapshot_version": snapshot_version,
        },
    )


def shopping_product_match_ambiguous(
    ingredient_id: str,
    snapshot_id: str,
    snapshot_version: int,
    candidate_product_ids: list[str],
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.SHOPPING_PRODUCT_MATCH_AMBIGUOUS,
        path=("ingredient_id",),
        details={
            "ingredient_id": ingredient_id,
            "snapshot_id": snapshot_id,
            "snapshot_version": snapshot_version,
            "candidate_product_ids": ",".join(candidate_product_ids),
        },
    )


def shopping_package_shape_invalid(
    ingredient_id: str,
    product_id: str,
    reason: str,
) -> DomainError:
    return _catalog_error(
        code=ErrorCode.SHOPPING_PACKAGE_SHAPE_INVALID,
        path=("package_quantity",),
        details={
            "ingredient_id": ingredient_id,
            "product_id": product_id,
            "reason": reason,
        },
    )


def shopping_price_missing(product_id: str) -> DomainError:
    return _catalog_error(
        code=ErrorCode.SHOPPING_PRICE_MISSING,
        path=("price_minor_units",),
        details={"product_id": product_id},
    )
