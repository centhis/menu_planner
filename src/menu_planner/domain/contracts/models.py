from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

SCHEMA_VERSION = "m2.v1"

type JsonValue = (
    str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
)
type JsonObject = dict[str, JsonValue]


class OperationClass(StrEnum):
    READ_ONLY = "read_only"
    DRAFT_PRODUCING = "draft_producing"
    STATE_CHANGING = "state_changing"
    ADMINISTRATIVE = "administrative"
    UNSUPPORTED = "unsupported"


class PolicyDecisionOutcome(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    CLARIFY = "clarify"
    CONFIRM = "confirm"
    UNSUPPORTED = "unsupported"


class DraftStatus(StrEnum):
    CREATED = "created"
    GENERATED = "generated"
    VALIDATION_FAILED = "validation_failed"
    REVISION_REQUESTED = "revision_requested"
    VALIDATED = "validated"
    WAITING_CONFIRMATION = "waiting_confirmation"
    COMMITTED = "committed"
    REJECTED = "rejected"
    ABANDONED = "abandoned"


class WorkflowState(StrEnum):
    PROFILE_REQUIRED = "profile_required"
    PROFILE_WAITING_CONFIRMATION = "profile_waiting_confirmation"
    CONTEXT_PREPARING = "context_preparing"
    MENU_GENERATING = "menu_generating"
    MENU_VALIDATING = "menu_validating"
    MENU_REVISION_REQUIRED = "menu_revision_required"
    MENU_WAITING_CONFIRMATION = "menu_waiting_confirmation"
    RECIPES_GENERATING = "recipes_generating"
    RECIPES_VALIDATING = "recipes_validating"
    PRODUCTS_MATCHING = "products_matching"
    SHOPPING_LIST_BUILDING = "shopping_list_building"
    READY = "ready"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ParsedIntent:
    schema_version: str
    intent: str
    confidence: float
    parameters: JsonObject
    missing_fields: list[str]
    ambiguities: list[str]
    operation_class: OperationClass
    requires_confirmation: bool
    scope: str
    suggested_next_action: str


@dataclass(frozen=True)
class ProfileDraft:
    schema_version: str
    user_id: str
    draft_id: str
    status: DraftStatus
    fields: JsonObject


@dataclass(frozen=True)
class ProfileVersion:
    schema_version: str
    user_id: str
    profile_id: str
    version: int
    fields: JsonObject


@dataclass(frozen=True)
class PlanningContext:
    schema_version: str
    user_id: str
    context_id: str
    profile_version: int
    constraints: JsonObject


@dataclass(frozen=True)
class MealSlot:
    schema_version: str
    date: str
    meal_type: str
    requirements: JsonObject


@dataclass(frozen=True)
class MenuDraft:
    schema_version: str
    user_id: str
    draft_id: str
    status: DraftStatus
    meal_slots: list[JsonObject]


@dataclass(frozen=True)
class MenuVersion:
    schema_version: str
    user_id: str
    menu_id: str
    version: int
    meal_slots: list[JsonObject]


@dataclass(frozen=True)
class Ingredient:
    schema_version: str
    name: str
    quantity: float
    unit: str


@dataclass(frozen=True)
class RecipeDraft:
    schema_version: str
    user_id: str
    draft_id: str
    status: DraftStatus
    ingredients: list[JsonObject]


@dataclass(frozen=True)
class RecipeVersion:
    schema_version: str
    user_id: str
    recipe_id: str
    version: int
    ingredients: list[JsonObject]


@dataclass(frozen=True)
class ShoppingListItem:
    schema_version: str
    name: str
    quantity: float
    unit: str
    status: str


@dataclass(frozen=True)
class ShoppingList:
    schema_version: str
    user_id: str
    shopping_list_id: str
    items: list[JsonObject]


@dataclass(frozen=True)
class WorkflowRun:
    schema_version: str
    workflow_id: str
    user_id: str
    state: WorkflowState
    allowed_actions: list[str]
    attempts: int


@dataclass(frozen=True)
class ValidationResult:
    schema_version: str
    is_valid: bool
    errors: list[JsonObject]


@dataclass(frozen=True)
class OperationPreview:
    schema_version: str
    preview_id: str
    operation: str
    entity_ref: str
    summary_hash: str
    changes: list[JsonObject]
    requires_confirmation: bool


@dataclass(frozen=True)
class Confirmation:
    schema_version: str
    confirmation_id: str
    user_id: str
    operation: str
    entity_id: str
    expected_version: int
    draft_version: int
    expires_at: str
    summary_hash: str
    status: str


@dataclass(frozen=True)
class PolicyDecision:
    schema_version: str
    outcome: PolicyDecisionOutcome
    allowed: bool
    operation_class: OperationClass
    reason_code: str
    current_state: str
    allowed_actions: list[str]
    required_data: list[str]
    missing_fields: list[str]
    ambiguities: list[str]
    requires_confirmation: bool
    errors: list[JsonObject]


@dataclass(frozen=True)
class AuditEvent:
    schema_version: str
    event_id: str
    user_id: str
    operation: str
    occurred_at: str
    outcome: str
    details: JsonObject


@dataclass(frozen=True)
class ToolSuccessEnvelope:
    schema_version: str
    ok: bool
    result: JsonObject


@dataclass(frozen=True)
class ToolErrorEnvelope:
    schema_version: str
    ok: bool
    errors: list[JsonObject]
